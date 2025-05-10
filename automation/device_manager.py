import os
import json
import logging
import time
import threading
import requests
import subprocess
import re
from appium import webdriver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeviceManager:
    """Manages multiple devices running Instagram automation across multiple Appium servers"""
    
    def __init__(self, config_path=None):
        """Initialize device manager with configuration"""
        self.devices = {}  # Stores device info
        self.drivers = {}  # Stores Appium drivers
        self.servers = {}  # Stores server info
        self.lock = threading.Lock()  # For thread safety
        self.real_device_udids = self._get_real_device_udids()  # Cache real device UDIDs
        
        # Load config if provided, otherwise use defaults
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Default config with multiple servers
            self.config = {
                "appium_servers": [
                    {
                        "name": "server-1",
                        "host": "127.0.0.1",
                        "port": 4723,
                        "max_devices": 5
                    }
                ],
                "devices": []
            }
            logger.warning("No config file found. Using default configuration.")
        
        # Initialize servers tracking
        self._initialize_servers()
    
    def _get_real_device_udids(self):
        """Get list of connected real device UDIDs"""
        real_devices = []
        
        # Get iOS devices using idevice_id
        try:
            result = subprocess.run(['idevice_id', '-l'], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        real_devices.append(line.strip())
        except Exception as e:
            logger.warning(f"Error getting iOS device list: {str(e)}")
        
        # Get Android devices
        try:
            result = subprocess.run(['adb', 'devices'], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
            
            if result.returncode == 0:
                for line in result.stdout.splitlines()[1:]:  # Skip header
                    if '\t' in line and 'device' in line:
                        udid = line.split('\t')[0].strip()
                        if udid:
                            real_devices.append(udid)
        except Exception as e:
            logger.warning(f"Error getting Android device list: {str(e)}")
        
        logger.info(f"Detected real devices: {real_devices}")
        return real_devices
    
    def is_simulator(self, udid):
        """Check if a device is a simulator based on its UDID"""
        # Refresh real devices list
        if not hasattr(self, 'real_device_udids') or not self.real_device_udids:
            self.real_device_udids = self._get_real_device_udids()
        
        # Common iOS simulator patterns
        ios_simulator_patterns = [
            # Simulator UDIDs are typically UUIDs
            r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$'
        ]
        
        # Check if it's in our list of real devices
        if udid in self.real_device_udids:
            return False
        
        # Check against simulator patterns
        for pattern in ios_simulator_patterns:
            if re.match(pattern, udid, re.IGNORECASE):
                return True
                
        # If the UDID is very short, it's likely an emulator
        if len(udid) < 10:
            return True
            
        # Default to real device if we can't determine
        return False
    
    def check_appium_server(self, host, port):
        """Check if Appium server is running on the specified host and port"""
        try:
            response = requests.get(f"http://{host}:{port}/status", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _initialize_servers(self):
        """Set up the server tracking from configuration"""
        if "appium_servers" not in self.config:
            # Convert old format to new format
            self.config["appium_servers"] = [
                {
                    "name": "server-1",
                    "host": self.config.get("appium_server", {}).get("host", "127.0.0.1"),
                    "port": self.config.get("appium_server", {}).get("port", 4723),
                    "max_devices": 5
                }
            ]
            
            # Remove old format if it exists
            if "appium_server" in self.config:
                del self.config["appium_server"]
        
        # Initialize server tracking
        for server_config in self.config["appium_servers"]:
            server_id = server_config["name"]
            
            # Count devices assigned to this server
            device_count = sum(1 for d in self.config["devices"] 
                              if d.get("server") == server_id)
            
            self.servers[server_id] = {
                "config": server_config,
                "device_count": device_count,
                "status": "disconnected"
            }
            
            logger.info(f"Initialized server {server_id} with {device_count} assigned devices")
    
    def add_device(self, name, udid, platform_name, platform_version, device_name, automation_name):
        """Add a device to be managed with automatic server assignment"""
        # Find server with capacity
        assigned_server = None
        
        with self.lock:
            # Look for servers with remaining capacity
            for server_id, server_info in self.servers.items():
                if server_info["device_count"] < server_info["config"]["max_devices"]:
                    assigned_server = server_id
                    break
        
            if not assigned_server:
                logger.error("No servers with capacity available")
                return False
            
            # Create device config
            device_config = {
                "name": name,
                "udid": udid,
                "platformName": platform_name,
                "platformVersion": platform_version,
                "deviceName": device_name,
                "automationName": automation_name,
                "server": assigned_server
            }
            
            # Add to devices config
            self.config["devices"].append(device_config)
            
            # Update server device count
            self.servers[assigned_server]["device_count"] += 1
            
            logger.info(f"Added device: {name} ({udid}) to server {assigned_server}")
            return True
    
    def initialize_device(self, device_config):
        """Initialize Appium driver for a specific device"""
        device_id = device_config['udid']
        server_id = device_config.get('server')
        
        # If device has no server assigned, assign one
        if not server_id:
            server_id = self._assign_server(device_id)
            if not server_id:
                logger.error(f"No servers available for device {device_config['name']}")
                return False
            device_config['server'] = server_id
        
        # Get server config
        if server_id not in self.servers:
            logger.error(f"Server {server_id} not found in configuration")
            return False
            
        server_config = self.servers[server_id]["config"]
        
        try:
            logger.info(f"Initializing device: {device_config['name']} ({device_id}) on server {server_id}")
            
            # Create desired capabilities based on platform
            desired_caps = {
                'platformName': device_config['platformName'],
                'platformVersion': device_config['platformVersion'],
                'deviceName': device_config['deviceName'],
                'udid': device_id,
                'automationName': device_config['automationName'],
                'noReset': True,  # Keep app data between sessions
                'newCommandTimeout': 360,
                'wdaLocalPort': 8100
            }
            
            logger.info(f"Using capabilities: {desired_caps}")
            
            # Connect to Appium server
            # Use the direct URL format (Appium 2.x) instead of /wd/hub (Appium 1.x)
            appium_url = f"http://{server_config['host']}:{server_config['port']}"
            logger.info(f"Connecting to Appium at: {appium_url}")
            
            driver = webdriver.Remote(appium_url, desired_caps)
            logger.info("Driver created successfully!")
            
            # Get screen dimensions
            screen_size = driver.get_window_size()
            logger.info(f"Screen size: {screen_size}")
            
            # Store device info
            with self.lock:
                self.drivers[device_id] = driver
                self.devices[device_id] = {
                    'config': device_config,
                    'screen_width': screen_size['width'],
                    'screen_height': screen_size['height'],
                    'status': 'ready',
                    'last_active': time.time(),
                    'server': server_id
                }
                
                # Ensure server status is updated
                self.servers[server_id]['status'] = 'running'
            
            logger.info(f"Device {device_config['name']} initialized successfully on server {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize device {device_config['name']}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _assign_server(self, device_id):
        """Assign a device to the least loaded server"""
        with self.lock:
            # Find the server with the least devices
            available_servers = [(s_id, info) for s_id, info in self.servers.items() 
                               if info['device_count'] < info['config']['max_devices']]
            
            if not available_servers:
                logger.error("No servers with capacity available")
                return None
                
            # Sort by number of devices (ascending)
            available_servers.sort(key=lambda x: x[1]['device_count'])
            
            # Pick the server with the fewest devices
            server_id = available_servers[0][0]
            
            # Update device config with server assignment
            for device in self.config['devices']:
                if device['udid'] == device_id:
                    device['server'] = server_id
                    break
            
            # Update server device count
            self.servers[server_id]['device_count'] += 1
            
            logger.info(f"Device {device_id} automatically assigned to server {server_id}")
            return server_id
    
    def initialize_all_devices(self):
        """Initialize all devices from configuration"""
        initialized_count = 0
        
        for device_config in self.config['devices']:
            if self.initialize_device(device_config):
                initialized_count += 1
        
        return initialized_count
    
    def get_device_status(self):
        """Get status of all devices"""
        statuses = {}
        
        with self.lock:
            for device_id, device_info in self.devices.items():
                # Determine if this is a simulator
                is_sim = self.is_simulator(device_id)
                
                statuses[device_id] = {
                    'name': device_info['config']['name'],
                    'status': device_info['status'],
                    'last_active': device_info['last_active'],
                    'server': device_info['server'],
                    'is_simulator': is_sim
                }
        
        return statuses
    
    def get_server_status(self):
        """Get status of all Appium servers"""
        statuses = {}
        
        with self.lock:
            for server_id, server_info in self.servers.items():
                statuses[server_id] = {
                    'name': server_id,
                    'status': server_info['status'],
                    'device_count': server_info['device_count'],
                    'max_devices': server_info['config']['max_devices'],
                    'port': server_info['config']['port']
                }
                
        return statuses
    
    def get_available_device(self):
        """Get an available device for automation tasks"""
        with self.lock:
            for device_id, device_info in self.devices.items():
                if device_info['status'] == 'ready':
                    # Mark as busy
                    self.devices[device_id]['status'] = 'busy'
                    self.devices[device_id]['last_active'] = time.time()
                    return device_id, self.drivers[device_id]
        
        return None, None
    
    def release_device(self, device_id):
        """Mark a device as available again"""
        with self.lock:
            if device_id in self.devices:
                self.devices[device_id]['status'] = 'ready'
                self.devices[device_id]['last_active'] = time.time()
                logger.info(f"Device {self.devices[device_id]['config']['name']} released")
    
    def close_device(self, device_id):
        """Close a specific device's Appium session"""
        with self.lock:
            if device_id in self.drivers:
                try:
                    self.drivers[device_id].quit()
                    del self.drivers[device_id]
                    if device_id in self.devices:
                        self.devices[device_id]['status'] = 'disconnected'
                    logger.info(f"Closed session for device {device_id}")
                    return True
                except Exception as e:
                    logger.error(f"Error closing device session: {e}")
        
        return False
    
    def close_all_devices(self):
        """Close all Appium sessions"""
        for device_id in list(self.drivers.keys()):
            self.close_device(device_id)
        
        logger.info("All device sessions closed")
        
    def save_config(self, config_path=None):
        """Save the current configuration to file"""
        if not config_path and hasattr(self, 'config_path'):
            config_path = self.config_path
            
        if config_path:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
            return True
        else:
            logger.error("No config path specified")
            return False 