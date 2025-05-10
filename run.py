#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import argparse
import webbrowser
import json
import requests

def check_appium_running(port=4723):
    """Check if Appium server is running on the specified port"""
    try:
        response = requests.get(f"http://localhost:{port}/status", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_appium_servers(config_path):
    """Start multiple Appium servers based on configuration"""
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return {}
        
    # Get server configs
    if "appium_servers" not in config:
        # Default to single server if not using multi-server config
        servers = [{
            "name": "server-1",
            "host": "127.0.0.1",
            "port": 4723
        }]
    else:
        servers = config["appium_servers"]
        
    # Start each server
    appium_processes = {}
    
    for server in servers:
        server_name = server["name"]
        port = server["port"]
        
        # Check if already running
        if check_appium_running(port):
            print(f"Appium server already running on port {port}")
            continue
            
        print(f"Starting Appium server {server_name} on port {port}...")
        try:
            # Start Appium on the specified port
            cmd = ["appium", "--port", str(port)]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give it time to start
            time.sleep(3)
            
            # Verify it's running
            if check_appium_running(port):
                print(f"Appium server {server_name} started successfully on port {port}")
                appium_processes[server_name] = process
            else:
                print(f"Failed to start Appium server {server_name} on port {port}")
                process.terminate()
                
        except FileNotFoundError:
            print("Error: Appium not found. Please install Appium: npm install -g appium")
        except Exception as e:
            print(f"Error starting Appium server {server_name}: {e}")
    
    return appium_processes

def start_backend():
    """Start the Flask backend"""
    print("Starting Flask backend...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "backend/app.py"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Give the backend a moment to start
        time.sleep(3)
        return backend_process
    except Exception as e:
        print(f"Error starting backend: {e}")
        return None

def start_frontend_dev():
    """Start the React development server"""
    print("Starting React development server...")
    try:
        os.chdir("frontend")
        frontend_process = subprocess.Popen(
            ["npm", "start"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        os.chdir("..")
        # Give the frontend a moment to start
        time.sleep(5)
        return frontend_process
    except Exception as e:
        print(f"Error starting frontend: {e}")
        os.chdir("..")
        return None

def setup_ui_map():
    """Set up the Instagram UI map"""
    print("Setting up Instagram UI map...")
    try:
        result = subprocess.run(
            [sys.executable, "setup_ui_map.py"],
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print("Error setting up UI map")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the Instagram Automation System")
    parser.add_argument("--no-appium", action="store_true", help="Don't start Appium servers")
    parser.add_argument("--no-frontend", action="store_true", help="Don't start React dev server")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--config", default="config/devices.json", help="Path to configuration file")
    args = parser.parse_args()
    
    # Full path to config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.config)
    
    # Make sure config directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        default_config = {
            "appium_servers": [
                {
                    "name": "server-1",
                    "host": "127.0.0.1",
                    "port": 4723,
                    "max_devices": 5
                },
                {
                    "name": "server-2",
                    "host": "127.0.0.1",
                    "port": 4724,
                    "max_devices": 5
                }
            ],
            "devices": []
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default configuration at {config_path}")
    
    # Initialize processes
    appium_processes = {}
    backend_process = None
    frontend_process = None
    
    try:
        # Set up the UI map
        if not setup_ui_map():
            print("Warning: UI map setup failed. System may not work properly.")
            
        # Start Appium servers if needed
        if not args.no_appium:
            appium_processes = start_appium_servers(config_path)
            if not appium_processes:
                print("Warning: No Appium servers started")
        
        # Start the backend
        backend_process = start_backend()
        if not backend_process:
            return 1
            
        # Start the frontend if needed
        if not args.no_frontend:
            frontend_process = start_frontend_dev()
            if not frontend_process:
                return 1
        
        # Open the browser if requested
        if not args.no_browser:
            if args.no_frontend:
                # Open backend endpoint
                webbrowser.open("http://localhost:8000")
            else:
                # Open frontend 
                webbrowser.open("http://localhost:3000")
        
        # Count running processes
        running_servers = len(appium_processes)
        print(f"\nInstagram Automation System is running!")
        print(f"- Appium Servers: {running_servers} running")
        print(f"- Backend: Running on http://localhost:8000")
        if frontend_process:
            print(f"- Frontend: Running on http://localhost:3000")
        print("Press Ctrl+C to stop all services\n")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up processes
        if frontend_process:
            print("Stopping frontend...")
            os.kill(frontend_process.pid, signal.SIGTERM)
            
        if backend_process:
            print("Stopping backend...")
            os.kill(backend_process.pid, signal.SIGTERM)
            
        for server_name, process in appium_processes.items():
            print(f"Stopping Appium server {server_name}...")
            os.kill(process.pid, signal.SIGTERM)
            
        print("System stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 