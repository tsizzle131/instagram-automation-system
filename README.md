# Instagram Automation System

A multi-device Instagram automation system that controls phones with Appium to perform tasks on Instagram.

## Features

- Control multiple phones concurrently
- Use UI map for precise element targeting
- Dashboard to monitor and control devices
- Automated tasks including:
  - Opening Instagram
  - Navigating to profile
  - Scrolling through feed
- Multiple Appium servers for better scaling
- Automatic device assignment across servers
- Scheduled automated tasks with customizable intervals

## Requirements

- Python 3.8+
- Node.js 14+ and npm
- Appium Server 2.0+
- iOS/Android devices or simulators
- Instagram app installed and logged in on devices

## Architecture

The system uses a multi-server architecture for scalability:

- Multiple Appium servers can be configured to handle different groups of devices
- Each server can handle up to 5 devices by default (configurable)
- Devices are automatically assigned to the server with the lowest load
- The system can run scheduled tasks on specific devices or any available device
- All servers and devices are managed through a centralized dashboard

## Setup

### 1. Install Appium Server

```bash
npm install -g appium
npm install -g appium-doctor
```

Run `appium-doctor` to ensure your system is set up correctly for automation.

### 2. Install Python Backend Dependencies

```bash
cd instagram-automation
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd instagram-automation/frontend
npm install
```

### 4. Configure Devices and Servers

The system will create a default configuration file at `config/devices.json` when started. You can modify this directly or use the UI to add devices and servers.

Default configuration includes two Appium servers:
- server-1: 127.0.0.1:4723
- server-2: 127.0.0.1:4724

## Usage

### 1. Start the System

```bash
cd instagram-automation
python run.py
```

This will:
- Start the required Appium servers
- Start the Flask backend
- Start the React frontend
- Open the dashboard in your browser

### 2. Using the Dashboard

1. **Add Appium Servers**:
   - Click "Add Server" to add additional Appium servers
   - Each server needs a unique name, host, port, and max device count

2. **Add Devices**:
   - Click "Add Device" to add your iOS or Android devices
   - Provide the required device information (UDID, platform, etc.)
   - Devices will be automatically assigned to servers with capacity

3. **Initialize Devices**:
   - Click "Initialize" on each device to start the Appium session
   - The device status will change to "ready" when successful

4. **Run Tasks**:
   - Select a task from the dropdown
   - Optionally set a repeat interval (in seconds)
   - Click "Run" to execute the task
   - Tasks will appear in the "Running Tasks" section if scheduled

5. **Stop Tasks**:
   - Click "Stop Task" on any running task to terminate it

## Scaling the System

To handle more devices (20+ phones):

1. Add more Appium servers through the UI or by editing the config file
2. Each server should handle around 5 devices for optimal performance
3. Servers can be run on different machines by specifying different IP addresses
4. The central dashboard will manage all servers and devices

## Customizing Tasks

To add custom tasks:

1. Update the `task_runner.py` file with new task methods
2. Add the task names to the UI dropdown in `App.js`
3. Implement the task execution logic using the UI map for element targeting

## Troubleshooting

- **Appium Connection Issues**: Make sure Appium server is running and the port is correct
- **Device Not Found**: Verify UDID and device connection
- **UI Element Not Found**: Check the UI map for correct element identifiers
- **Task Failures**: Review logs for detailed error information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Project Structure

```
/instagram-automation/
├── automation/            # Appium automation scripts
│   ├── device_manager.py  # Manages multiple devices
│   └── task_runner.py     # Executes Instagram tasks
├── backend/               # Flask backend API
│   └── app.py             # API endpoints
├── frontend/              # React dashboard
│   ├── public/            # Static assets
│   └── src/               # React source code
├── config/                # Configuration files
├── instagram_map.json     # UI map for element targeting
└── requirements.txt       # Python dependencies
```

## Common Issues and Solutions

- **Connection Issues**: Ensure Appium server is running and devices are connected
- **Element Not Found**: Update the UI map or use relative positioning fallbacks
- **Appium Session Failed**: Check device is properly connected and UDID is correct

## Security Considerations

- This tool assumes Instagram accounts are already logged in
- Store credentials securely if implementing login functionality
- Use this tool responsibly and within Instagram's terms of service 