#!/usr/bin/env python3
import os
import sys
import json
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from automation.device_manager import DeviceManager
from automation.task_runner import InstagramTaskRunner

def test_device_manager():
    """Test the device manager functionality"""
    print("\n=== Testing Device Manager ===")
    
    # Initialize device manager with test config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'devices.json')
    device_manager = DeviceManager(config_path)
    
    # Print server info
    print("\nServer Status:")
    for server_id, server_info in device_manager.servers.items():
        print(f"  {server_id}: {server_info['config']['host']}:{server_info['config']['port']} "
              f"({server_info['device_count']}/{server_info['config']['max_devices']} devices)")
    
    # Add test devices
    print("\nAdding test devices:")
    
    # Add iOS device
    result = device_manager.add_device(
        name="Test iPhone",
        udid="iphone123456",
        platform_name="iOS",
        platform_version="15.0",
        device_name="iPhone 12",
        automation_name="XCUITest"
    )
    print(f"  Added iOS device: {result}")
    
    # Add Android device
    result = device_manager.add_device(
        name="Test Android",
        udid="android123456",
        platform_name="Android",
        platform_version="12.0",
        device_name="Pixel 6",
        automation_name="UiAutomator2"
    )
    print(f"  Added Android device: {result}")
    
    # Print updated server info
    print("\nUpdated Server Status:")
    for server_id, server_info in device_manager.servers.items():
        print(f"  {server_id}: {server_info['config']['host']}:{server_info['config']['port']} "
              f"({server_info['device_count']}/{server_info['config']['max_devices']} devices)")
    
    # Check device assignments
    print("\nDevice assignments:")
    for device in device_manager.config['devices']:
        print(f"  {device['name']} ({device['udid']}): assigned to {device['server']}")
    
    # Save the config
    device_manager.save_config(config_path)
    print(f"\nConfig saved to {config_path}")
    
    return device_manager

def test_task_runner(device_manager):
    """Test the task runner functionality"""
    print("\n=== Testing Task Runner ===")
    
    # Initialize task runner
    ui_map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instagram_map.json')
    task_runner = InstagramTaskRunner(device_manager, ui_map_path)
    
    # Print available UI map screens
    print("\nUI Map Screens:")
    if task_runner.ui_map:
        for screen_name in task_runner.ui_map.keys():
            element_count = len(task_runner.ui_map[screen_name])
            print(f"  {screen_name}: {element_count} elements")
    else:
        print("  No UI map loaded")
    
    return task_runner

def main():
    """Run tests"""
    print("=== Instagram Automation System Test ===")
    
    # Test device manager
    device_manager = test_device_manager()
    
    # Test task runner
    task_runner = test_task_runner(device_manager)
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    main() 