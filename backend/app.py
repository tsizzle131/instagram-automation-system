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
    task_runner = InstagramTaskRunner(device_manager, DEFAULT_UI_MAP_PATH)
    
    logger.info("System initialized")

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
        initialize_system()
        
        # Initialize devices from config
        device_count = device_manager.initialize_all_devices()
        
        return jsonify({
            'success': True,
            'devices_initialized': device_count
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
            device_manager.save_config(DEFAULT_CONFIG_PATH)
            
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
            
            # Parse the output to find real devices (not simulators)
            for line in result.stdout.splitlines():
                # Look for lines with device info like "iPhone (14.0) (00008020-00...)"
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
                            ios_devices.append({
                                "name": device_name,
                                "udid": udid,
                                "platformName": "iOS",
                                "platformVersion": ios_version,
                                "deviceName": device_name.split(" ")[-1],  # Usually iPhone, iPad, etc.
                                "automationName": "XCUITest"
                            })
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
                if '\t' in line and not "offline" in line:
                    try:
                        parts = line.strip().split('\t')
                        udid = parts[0].strip()
                        
                        if udid and len(udid) > 5:
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
                                "automationName": "UiAutomator2"
                            })
                    except Exception as parse_error:
                        logger.error(f"Error parsing Android device: {line}, error: {str(parse_error)}")
        except Exception as android_error:
            logger.error(f"Error getting Android devices: {str(android_error)}")
        
        # Combine all devices
        all_devices = ios_devices + android_devices
        logger.info(f"Found {len(all_devices)} devices: {all_devices}")
        
        if not all_devices:
            return jsonify({
                'success': False,
                'message': 'No devices found connected to the computer'
            }), 404
        
        # Check which devices are already registered
        existing_devices = [d['udid'] for d in device_manager.config['devices']]
        new_devices = []
        updated_devices = []
        
        # Process each detected device
        for device in all_devices:
            device_id = device['udid']
            
            if device_id in existing_devices:
                logger.info(f"Device {device['name']} ({device_id}) already registered")
                # Try to initialize if not already active
                for config_device in device_manager.config['devices']:
                    if config_device['udid'] == device_id:
                        # Only initialize if not already connected
                        device_status = device_manager.get_device_status().get(device_id, {}).get('status')
                        if device_status not in ['ready', 'busy']:
                            success = device_manager.initialize_device(config_device)
                            if success:
                                updated_devices.append(device_id)
                                logger.info(f"Re-initialized existing device: {device['name']}")
                            else:
                                logger.error(f"Failed to initialize existing device: {device['name']}")
                        else:
                            logger.info(f"Device {device['name']} already active with status: {device_status}")
                            updated_devices.append(device_id)
            else:
                # Add new device
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
        
        return jsonify({
            'success': True,
            'message': f"Device refresh complete: {len(new_devices)} new, {len(updated_devices)} updated",
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