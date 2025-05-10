from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import sys
import time
import subprocess

# Add parent directory to path so we can import automation modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automation.device_manager import DeviceManager
from automation.task_runner import InstagramTaskRunner

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default paths
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'devices.json')
DEFAULT_UI_MAP_PATH = os.path.join(BASE_DIR, 'instagram_map.json')

# Initialize managers
device_manager = None
task_runner = None

def initialize_system():
    """Initialize the system components"""
    global device_manager, task_runner
    
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
    
    # Initialize device manager
    device_manager = DeviceManager(DEFAULT_CONFIG_PATH)
    
    # Initialize task runner
    task_runner = InstagramTaskRunner(device_manager)
    
    logger.info("System core initialized. Attempting to initialize all configured devices...")
    if device_manager: # Add a check to be safe
        try:
            # Initialize devices from config
            device_count = device_manager.initialize_all_devices()
            logger.info(f"Attempted to initialize {device_count} devices on startup.")
        except Exception as e:
            logger.error(f"Error during automatic device initialization on startup: {str(e)}")
            
    logger.info("Full system initialization routine complete.")

# API routes
@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    if not device_manager:
        return jsonify({
            'status': 'not_initialized',
            'message': 'System not initialized'
        })
    
    devices = device_manager.get_device_status()
    servers = device_manager.get_server_status()
    tasks = {}
    
    # Add managed accounts to device status
    managed_accounts_path = os.path.join(BASE_DIR, 'config', 'managed_accounts.json')
    if os.path.exists(managed_accounts_path):
        try:
            with open(managed_accounts_path, 'r') as f:
                managed_accounts = json.load(f)
            
            # Add accounts to each device in the status
            for device_id, device_info in devices.items():
                device_info['managed_accounts'] = managed_accounts.get(device_id, [])
        except Exception as e:
            logger.error(f"Error loading managed accounts: {str(e)}")
    
    if task_runner:
        tasks = task_runner.get_running_tasks()
    
    return jsonify({
        'status': 'running',
        'devices': devices,
        'servers': servers,
        'tasks': tasks
    })

@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the system"""
    try:
        # Re-call the main initialization logic, which now includes device init
        initialize_system()

        # The return value from initialize_all_devices is now logged within initialize_system
        # We can get the current count of ready devices for the response if needed
        ready_devices_count = 0
        if device_manager:
            ready_devices_count = len([d for d in device_manager.get_device_status().values() if d['status'] == 'ready'])

        return jsonify({
            'success': True,
            'message': 'System initialization triggered. Check status for device readiness.',
            'devices_initialized_or_ready': ready_devices_count
        })
    except Exception as e:
        logger.exception("Failed to initialize system")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get all devices"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    return jsonify(device_manager.get_device_status())

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Get all Appium servers"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    return jsonify(device_manager.get_server_status())

@app.route('/api/devices', methods=['POST'])
def add_device():
    """Add a new device"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    data = request.json
    
    try:
        success = device_manager.add_device(
            name=data['name'],
            udid=data['udid'],
            platform_name=data['platformName'],
            platform_version=data['platformVersion'],
            device_name=data['deviceName'],
            automation_name=data['automationName']
        )
        
        if success:
            # Save the updated config
            # device_manager.save_config(DEFAULT_CONFIG_PATH) # This is now handled by DeviceManager.add_device()
            
            return jsonify({
                'success': True,
                'message': f"Device {data['name']} added successfully"
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Failed to add device - no servers with capacity available"
            }), 400
            
    except KeyError as e:
        return jsonify({
            'success': False,
            'error': f"Missing required field: {str(e)}"
        }), 400
    except Exception as e:
        logger.exception("Error adding device")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/<device_id>/initialize', methods=['POST'])
def initialize_device(device_id):
    """Initialize a specific device"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    # Find device config
    device_config = None
    for device in device_manager.config['devices']:
        if device['udid'] == device_id:
            device_config = device
            break
            
    if not device_config:
        return jsonify({
            'success': False,
            'error': f"Device {device_id} not found"
        }), 404
    
    # Initialize the device
    success = device_manager.initialize_device(device_config)
    
    if success:
        return jsonify({
            'success': True,
            'message': f"Device {device_config['name']} initialized successfully"
        })
    else:
        return jsonify({
            'success': False,
            'error': f"Failed to initialize device {device_config['name']}"
        }), 500

@app.route('/api/devices/<device_id>/setup', methods=['POST'])
def setup_device_endpoint(device_id):
    """Endpoint to trigger the 'setup_device' task for a specific device."""
    if not device_manager or not task_runner:
        logger.error("setup_device_endpoint: System not initialized.")
        return jsonify({'success': False, 'error': 'System not initialized'}), 500

    logger.info(f"Received request to setup device: {device_id}")
    
    # Check if device exists and get its info
    all_devices_status = device_manager.get_device_status()
    if device_id not in all_devices_status:
        logger.error(f"setup_device_endpoint: Device {device_id} not found in device manager.")
        return jsonify({'success': False, 'error': 'Device not found'}), 404
    
    device_info = all_devices_status[device_id]
    
    # Check if device is ready for a new task (e.g., not busy, connected)
    if device_info['status'] != 'ready': # Assuming 'ready' is the correct status
        logger.warning(f"Device {device_id} is not in 'ready' state (current: {device_info['status']}). Task may fail or be queued.")
        # Allowing task to proceed, TaskRunner should handle non-ready states if necessary
        # Or, uncomment below to return an error if not ready:
        # return jsonify({'success': False, 'error': f'Device not ready (status: {device_info["status"]})'}), 409

    logger.info(f"Executing setup_device task for device: {device_id}, info: {device_info}")
    result = task_runner.execute_task('setup_device', device_id, device_info=device_info)
    
    return jsonify(result)

@app.route('/api/devices/<device_id>/task', methods=['POST'])
def execute_task(device_id):
    """Execute a task on a specific device"""
    if not device_manager or not task_runner:
        return jsonify({'error': 'System not initialized'}), 500
        
    data = request.json
    task_name = data.get('task_name')
    repeat_interval = data.get('repeat_interval')
    
    if not task_name:
        return jsonify({
            'success': False,
            'error': "Missing required field: task_name"
        }), 400
    
    # Additional parameters for the task
    kwargs = {k: v for k, v in data.items() if k not in ['task_name', 'repeat_interval']}
    
    try:
        # Execute scheduled task if interval provided, otherwise just run once
        if repeat_interval:
            result = task_runner.run_scheduled_task(task_name, device_id, repeat_interval, **kwargs)
        else:
            result = task_runner.execute_task(task_name, device_id, **kwargs)
            
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error executing task {task_name}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/<device_id>/task/<task_name>/stop', methods=['POST'])
def stop_task(device_id, task_name):
    """Stop a scheduled task"""
    if not task_runner:
        return jsonify({'error': 'System not initialized'}), 500
        
    try:
        result = task_runner.stop_scheduled_task(task_name, device_id)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error stopping task {task_name}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all running tasks"""
    if not task_runner:
        return jsonify({'error': 'System not initialized'}), 500
        
    return jsonify(task_runner.get_running_tasks())

@app.route('/api/servers', methods=['POST'])
def add_server():
    """Add a new Appium server"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    data = request.json
    
    try:
        # Validate required fields
        required_fields = ['name', 'host', 'port', 'max_devices']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        # Check for duplicate name or port
        for server in device_manager.config['appium_servers']:
            if server['name'] == data['name']:
                return jsonify({
                    'success': False,
                    'error': f"Server with name '{data['name']}' already exists"
                }), 400
            if server['port'] == data['port'] and server['host'] == data['host']:
                return jsonify({
                    'success': False,
                    'error': f"Server with host:port {data['host']}:{data['port']} already exists"
                }), 400
        
        # Add server to config
        device_manager.config['appium_servers'].append({
            'name': data['name'],
            'host': data['host'],
            'port': data['port'],
            'max_devices': data['max_devices']
        })
        
        # Initialize server in device manager
        device_manager.servers[data['name']] = {
            'config': {
                'name': data['name'],
                'host': data['host'],
                'port': data['port'],
                'max_devices': data['max_devices']
            },
            'device_count': 0,
            'status': 'disconnected'
        }
        
        # Save config
        device_manager.save_config(DEFAULT_CONFIG_PATH)
        
        return jsonify({
            'success': True,
            'message': f"Server {data['name']} added successfully"
        })
    except Exception as e:
        logger.exception("Error adding server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    return jsonify(device_manager.config)

@app.route('/api/refresh', methods=['POST'])
def refresh_devices():
    """Scan for connected devices, assign them to servers, and initialize them"""
    if not device_manager:
        return jsonify({'error': 'System not initialized'}), 500
        
    try:
        logger.info("Refreshing devices - scanning for connected iOS and Android devices")
        
        # Get iOS devices using xcrun
        ios_devices = []
        try:
            # Run xcrun to list iOS devices - fixed for Python 3.6 compatibility
            result = subprocess.run(['xcrun', 'xctrace', 'list', 'devices'], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True,
                                   check=True)
            
            # Parse the output to find ONLY real devices (not simulators)
            for line in result.stdout.splitlines():
                # Filter out simulators and Macs - only include real iOS devices
                if "(" in line and ")" in line and not "Simulator" in line and not "Mac" in line:
                    try:
                        # Extract device name and UDID
                        parts = line.strip().split('(')
                        device_name = parts[0].strip()
                        # Extract UDID which is usually the last (xxx) part
                        udid = parts[-1].split(')')[0].strip()
                        
                        # Validate that it looks like a UDID
                        if len(udid) > 10 and not udid.startswith("com."):
                            ios_version = parts[-2].split(')')[0].strip() if len(parts) > 2 else "Unknown"
                            
                            # Extra check to make sure it's a real device and not a simulator
                            if device_manager._get_real_device_udids() and udid in device_manager._get_real_device_udids():
                                ios_devices.append({
                                    "name": device_name,
                                    "udid": udid,
                                    "platformName": "iOS",
                                    "platformVersion": ios_version,
                                    "deviceName": device_name.split(" ")[-1],  # Usually iPhone, iPad, etc.
                                    "automationName": "XCUITest",
                                    "is_simulator": False
                                })
                                logger.info(f"Found real iOS device: {device_name} ({udid})")
                            else:
                                logger.info(f"Skipping simulator or virtual device: {device_name} ({udid})")
                    except Exception as parse_error:
                        logger.error(f"Error parsing iOS device line: {line}, error: {str(parse_error)}")
        except Exception as ios_error:
            logger.error(f"Error getting iOS devices: {str(ios_error)}")
        
        # Get Android devices using adb
        android_devices = []
        try:
            # Run adb to list Android devices - fixed for Python 3.6 compatibility
            result = subprocess.run(['adb', 'devices'], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True,
                                   check=True)
            
            # Parse the output to find connected devices
            lines = result.stdout.splitlines()
            for line in lines[1:]:  # Skip the first line which is the header
                if '\t' in line and not "offline" in line and not "emulator" in line:  # Skip emulators
                    try:
                        parts = line.strip().split('\t')
                        udid = parts[0].strip()
                        
                        # Skip emulators
                        if udid and len(udid) > 5 and not udid.startswith("emulator-"):
                            # Get device model and version - fixed for Python 3.6 compatibility
                            model_cmd = subprocess.run(
                                ['adb', '-s', udid, 'shell', 'getprop', 'ro.product.model'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
                            model = model_cmd.stdout.strip() if model_cmd.returncode == 0 else "Android Device"
                            
                            version_cmd = subprocess.run(
                                ['adb', '-s', udid, 'shell', 'getprop', 'ro.build.version.release'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
                            version = version_cmd.stdout.strip() if version_cmd.returncode == 0 else "Unknown"
                            
                            android_devices.append({
                                "name": f"{model}",
                                "udid": udid,
                                "platformName": "Android",
                                "platformVersion": version,
                                "deviceName": model,
                                "automationName": "UiAutomator2",
                                "is_simulator": False
                            })
                    except Exception as parse_error:
                        logger.error(f"Error parsing Android device: {line}, error: {str(parse_error)}")
        except Exception as android_error:
            logger.error(f"Error getting Android devices: {str(android_error)}")
        
        # Combine all devices
        all_devices = ios_devices + android_devices
        logger.info(f"Found {len(all_devices)} real devices: {all_devices}")
        
        if not all_devices:
            return jsonify({
                'success': False,
                'message': 'No real devices found connected to the computer'
            }), 404
        
        # Check which devices are already registered
        existing_devices = [d['udid'] for d in device_manager.config['devices']]
        new_devices = []
        updated_devices = []
        
        # Process each detected device
        for device in all_devices:
            device_id = device['udid']
            config_device_payload = None # To store the config for init

            if device_id in existing_devices:
                logger.info(f"Device {device['name']} ({device_id}) is physically connected and already in config.")
                # Find the existing config for this device
                for cfg_dev in device_manager.config['devices']:
                    if cfg_dev['udid'] == device_id:
                        config_device_payload = cfg_dev
                        break
                
                if not config_device_payload:
                    logger.error(f"Logic error: Device {device_id} in existing_devices but no config found. Skipping.")
                    continue

                # Check if the session is actually alive, or if status is not ready/busy
                force_reinit = False
                current_device_status_info = device_manager.devices.get(device_id)
                
                if current_device_status_info and current_device_status_info.get('status') in ['ready', 'busy']:
                    driver_instance = device_manager.drivers.get(device_id)
                    if driver_instance:
                        try:
                            # A lightweight check to see if session is alive
                            _ = driver_instance.session_id 
                            logger.info(f"Session for device {device['name']} seems alive.")
                        except Exception: # Typically NoSuchDriverException or similar if session is dead
                            logger.warning(f"Session for device {device['name']} ({device_id}) is dead. Forcing re-initialization.")
                            force_reinit = True
                    else:
                        # Driver not found for a supposedly ready/busy device, something is wrong
                        logger.warning(f"Device {device['name']} ({device_id}) is ready/busy but no driver instance found. Forcing re-initialization.")
                        force_reinit = True
                else:
                    # Status is not ready/busy (e.g., disconnected, error, initializing)
                    logger.info(f"Device {device['name']} ({device_id}) status is '{current_device_status_info.get('status', 'unknown')}'. Will attempt initialization.")
                    force_reinit = True # Also re-initialize if status is not ideal

                if force_reinit:
                    logger.info(f"Attempting to re-initialize existing device: {device['name']}")
                    success = device_manager.initialize_device(config_device_payload)
                    if success:
                        updated_devices.append(device_id)
                        logger.info(f"Successfully re-initialized existing device: {device['name']}")
                    else:
                        logger.error(f"Failed to re-initialize existing device: {device['name']}")
                else:
                    # If session is alive and status is good, we can just mark it as updated
                    logger.info(f"Device {device['name']} is already active and session is live.")
                    updated_devices.append(device_id)
            else:
                # Add new device
                logger.info(f"Device {device['name']} ({device_id}) is new. Attempting to add and initialize.")
                success = device_manager.add_device(
                    name=device['name'],
                    udid=device['udid'],
                    platform_name=device['platformName'],
                    platform_version=device['platformVersion'],
                    device_name=device['deviceName'],
                    automation_name=device['automationName']
                )
                
                if success:
                    logger.info(f"Added new device: {device['name']}")
                    
                    # Find the newly added device in config
                    for config_device in device_manager.config['devices']:
                        if config_device['udid'] == device_id:
                            # Initialize the device
                            init_success = device_manager.initialize_device(config_device)
                            if init_success:
                                new_devices.append(device_id)
                                logger.info(f"Initialized new device: {device['name']}")
                            else:
                                logger.error(f"Failed to initialize new device: {device['name']}")
                            break
                else:
                    logger.error(f"Failed to add device: {device['name']}")
        
        # Save the updated configuration
        device_manager.save_config(DEFAULT_CONFIG_PATH)
        
        # NEW STEP: Update status for configured devices that are no longer physically detected
        physically_detected_udids = {d['udid'] for d in all_devices}
        with device_manager.lock: # Ensure thread safety
            configured_devices_in_memory = list(device_manager.config['devices']) # Iterate over a copy
            for config_device in configured_devices_in_memory:
                config_udid = config_device['udid']
                if config_udid not in physically_detected_udids:
                    logger.info(f"Configured device {config_device.get('name', 'Unknown')} ({config_udid}) was not physically detected. Marking as disconnected.")
                    # Update or create entry in the live device status dictionary
                    if config_udid not in device_manager.devices:
                        device_manager.devices[config_udid] = {
                            'config': config_device,
                            'status': 'disconnected',
                            'last_active': time.time(),
                            'server': config_device.get('server')
                        }
                    else:
                        device_manager.devices[config_udid]['status'] = 'disconnected'
                        device_manager.devices[config_udid]['last_active'] = time.time()
                    
                    # Clean up driver if it exists for this now disconnected device
                    if config_udid in device_manager.drivers:
                        logger.info(f"Attempting to quit driver for disconnected device {config_udid}.")
                        try:
                            device_manager.drivers[config_udid].quit()
                        except Exception as e_quit:
                            logger.warning(f"Error quitting driver for disconnected {config_udid}: {str(e_quit)}")
                        finally:
                            # Always remove from drivers dict if we're marking as disconnected
                            if config_udid in device_manager.drivers:
                                del device_manager.drivers[config_udid]
        
        return jsonify({
            'success': True,
            'message': f"Device refresh complete: {len(new_devices)} new, {len(updated_devices)} updated. Check status for disconnected devices.",
            'new_devices': new_devices,
            'updated_devices': updated_devices,
            'detected_devices_count': len(all_devices)
        })
        
    except Exception as e:
        logger.exception("Failed to refresh devices")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Serve static files from the frontend build folder"""
    build_dir = os.path.join(BASE_DIR, 'frontend', 'build')
    if os.path.exists(build_dir):
        return send_from_directory(build_dir, 'index.html')
    else:
        return jsonify({
            'status': 'running',
            'message': 'Instagram Automation API server is running',
            'frontend_missing': True
        })

# Initialize on startup
initialize_system()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8001) 