import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// API base URL
const API_BASE_URL = 'http://localhost:8001/api';

function App() {
  // State
  const [status, setStatus] = useState('loading');
  const [devices, setDevices] = useState({});
  const [servers, setServers] = useState({});
  const [serverDevices, setServerDevices] = useState({}); // Map of server ID to array of device IDs
  const [tasks, setTasks] = useState({});
  const [expandedServers, setExpandedServers] = useState({});
  const [showOnlyRealDevices, setShowOnlyRealDevices] = useState(true); // Default to showing only real devices
  const [newDevice, setNewDevice] = useState({
    name: '',
    udid: '',
    platformName: 'iOS',
    platformVersion: '',
    deviceName: '',
    automationName: 'XCUITest'
  });
  const [newServer, setNewServer] = useState({
    name: '',
    host: '127.0.0.1',
    port: '',
    max_devices: 5
  });
  const [isAddingDevice, setIsAddingDevice] = useState(false);
  const [isAddingServer, setIsAddingServer] = useState(false);
  const [error, setError] = useState(null);
  const [taskResult, setTaskResult] = useState(null);
  const [taskInterval, setTaskInterval] = useState('');

  // Toggle showing simulators
  const toggleShowOnlyRealDevices = () => {
    setShowOnlyRealDevices(!showOnlyRealDevices);
  };

  // Get filtered devices (real or all)
  const getFilteredDevices = () => {
    if (!showOnlyRealDevices) {
      return devices;
    }
    
    // Filter out simulators
    const filtered = {};
    Object.entries(devices).forEach(([deviceId, deviceInfo]) => {
      if (!deviceInfo.is_simulator) {
        filtered[deviceId] = deviceInfo;
      }
    });
    
    return filtered;
  };

  // Fetch system status when component mounts
  useEffect(() => {
    fetchStatus();
    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  // Toggle server expansion
  const toggleServerExpansion = (serverId) => {
    setExpandedServers(prev => ({
      ...prev,
      [serverId]: !prev[serverId]
    }));
  };

  // Get devices assigned to a specific server
  const getDevicesForServer = (serverId) => {
    // Use the pre-built mapping of server -> device IDs
    const deviceIds = serverDevices[serverId] || [];
    
    // Convert device IDs to device objects and apply filter if needed
    const devicesList = deviceIds
      .map(deviceId => ({
        id: deviceId,
        ...devices[deviceId]
      }))
      .filter(device => !showOnlyRealDevices || !device.is_simulator);
    
    return devicesList;
  };

  // Fetch the status from the API
  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status`);
      
      setStatus(response.data.status);
      setDevices(response.data.devices || {});
      setServers(response.data.servers || {});
      setTasks(response.data.tasks || {});
      
      // Create a mapping of server ID -> device IDs
      const tempServerDevices = {};
      
      // Process device data to create server to device mapping
      Object.entries(response.data.devices || {}).forEach(([deviceId, deviceInfo]) => {
        const serverId = deviceInfo.server;
        if (serverId) {
          if (!tempServerDevices[serverId]) {
            tempServerDevices[serverId] = [];
          }
          tempServerDevices[serverId].push(deviceId);
        }
      });
      
      setServerDevices(tempServerDevices);
      
      setError(null);
    } catch (err) {
      setError(`Error fetching status: ${err.message}`);
      console.error('Error fetching status:', err);
    }
  };

  // Initialize the system
  const initializeSystem = async () => {
    try {
      setStatus('initializing');
      await axios.post(`${API_BASE_URL}/initialize`);
      await fetchStatus();
    } catch (err) {
      setError(`Error initializing system: ${err.message}`);
      console.error('Error initializing system:', err);
    }
  };

  // Initialize a device
  const initializeDevice = async (deviceId) => {
    try {
      await axios.post(`${API_BASE_URL}/devices/${deviceId}/initialize`);
      await fetchStatus();
    } catch (err) {
      setError(`Error initializing device: ${err.message}`);
      console.error('Error initializing device:', err);
    }
  };

  // Refresh devices - scan for new devices and initialize them
  const refreshDevices = async () => {
    try {
      setError(null);
      const response = await axios.post(`${API_BASE_URL}/refresh`);
      
      if (response.data.success) {
        // Show a temporary success message
        setError(`${response.data.message} (${response.data.detected_devices_count} devices detected)`);
        
        // Refresh the dashboard
        await fetchStatus();
      } else {
        setError(`Error refreshing devices: ${response.data.error || response.data.message}`);
      }
    } catch (err) {
      setError(`Error refreshing devices: ${err.response?.data?.error || err.message}`);
      console.error('Error refreshing devices:', err);
    }
  };

  // Add a new device
  const addDevice = async (e) => {
    e.preventDefault();
    
    try {
      await axios.post(`${API_BASE_URL}/devices`, newDevice);
      setIsAddingDevice(false);
      setNewDevice({
        name: '',
        udid: '',
        platformName: 'iOS',
        platformVersion: '',
        deviceName: '',
        automationName: 'XCUITest'
      });
      await fetchStatus();
    } catch (err) {
      setError(`Error adding device: ${err.response?.data?.error || err.message}`);
      console.error('Error adding device:', err);
    }
  };

  // Add a new server
  const addServer = async (e) => {
    e.preventDefault();
    
    try {
      await axios.post(`${API_BASE_URL}/servers`, {
        ...newServer,
        port: parseInt(newServer.port, 10),
        max_devices: parseInt(newServer.max_devices, 10)
      });
      setIsAddingServer(false);
      setNewServer({
        name: '',
        host: '127.0.0.1',
        port: '',
        max_devices: 5
      });
      await fetchStatus();
    } catch (err) {
      setError(`Error adding server: ${err.response?.data?.error || err.message}`);
      console.error('Error adding server:', err);
    }
  };

  // Execute a task on a device
  // const executeTask = async (deviceId) => { // Commented out original executeTask, will be replaced or removed if not used elsewhere
  //   try {
  //     setTaskResult(null);
      
  //     const payload = {
  //       task_name: selectedTask
  //     };
      
  //     // Add repeat interval if provided
  //     if (taskInterval && !isNaN(taskInterval) && parseInt(taskInterval) > 0) {
  //       payload.repeat_interval = parseInt(taskInterval);
  //     }
      
  //     const response = await axios.post(
  //       `${API_BASE_URL}/devices/${deviceId}/task`, 
  //       payload
  //     );
      
  //     setTaskResult({
  //       device: deviceId,
  //       task: selectedTask,
  //       result: response.data
  //     });
      
  //     await fetchStatus();
  //   } catch (err) {
  //     setError(`Error executing task: ${err.response?.data?.error || err.message}`);
  //     console.error('Error executing task:', err);
  //   }
  // };

  // New function to execute the "setup_device" task
  const executeSetupDeviceTask = async (deviceId) => {
    try {
      setTaskResult(null); // Clear previous task results
      setError(null); // Clear previous errors

      const response = await axios.post(`${API_BASE_URL}/devices/${deviceId}/setup`);
      
      setTaskResult({
        device: deviceId,
        task: 'setup_device', // Task name is fixed
        result: response.data
      });
      
      if (response.data.success) {
        // Optionally show a success message or handle as needed
        console.log(`Setup device task started successfully for ${deviceId}:`, response.data.message);
      } else {
        setError(`Error starting setup task for ${deviceId}: ${response.data.error || 'Unknown error'}`);
      }
      
      await fetchStatus(); // Refresh status to reflect any changes
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to execute setup task';
      setError(`Error executing setup task for ${deviceId}: ${errorMessage}`);
      console.error('Error executing setup_device task:', err);
      // Ensure taskResult reflects the failure if the request itself fails
      setTaskResult({
        device: deviceId,
        task: 'setup_device',
        result: { success: false, error: errorMessage }
      });
    }
  };

  // Stop a scheduled task
  const stopTask = async (deviceId, taskName) => {
    try {
      await axios.post(`${API_BASE_URL}/devices/${deviceId}/task/${taskName}/stop`);
      await fetchStatus();
    } catch (err) {
      setError(`Error stopping task: ${err.response?.data?.error || err.message}`);
      console.error('Error stopping task:', err);
    }
  };

  // Handle form input changes for new device
  const handleDeviceInputChange = (e) => {
    const { name, value } = e.target;
    setNewDevice(prev => ({ ...prev, [name]: value }));
  };

  // Handle form input changes for new server
  const handleServerInputChange = (e) => {
    const { name, value } = e.target;
    setNewServer(prev => ({ ...prev, [name]: value }));
  };

  // Format time duration
  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Get server info for a device
  const getServerForDevice = (deviceInfo) => {
    const serverId = deviceInfo.server;
    return servers[serverId] || null;
  };

  // Add this component for displaying the device card with managed accounts
  const DeviceCard = ({ device, deviceId }) => {
    const hasAccounts = device.managed_accounts && device.managed_accounts.length > 0;
    
    return (
      <div className={`device-card device-status-${device.status}`}>
        <div className="device-header">
          <h4>{device.name}</h4>
          <span className={`status-badge status-${device.status}`}>
            {device.status}
          </span>
        </div>
        <div className="device-details">
          <p><strong>UDID:</strong> {deviceId}</p>
          <p><strong>Platform:</strong> {device.platform_name} {device.platform_version}</p>
          <p><strong>Model:</strong> {device.model || 'Unknown'}</p>
          {device.error && <p className="error-message">{device.error}</p>}
          
          {/* Display managed accounts */}
          <div className="managed-accounts">
            <h5>Instagram Accounts:</h5>
            {hasAccounts ? (
              <ul className="accounts-list">
                {device.managed_accounts.map((account, index) => (
                  <li key={index} className="account-item">{account}</li>
                ))}
              </ul>
            ) : (
              <p className="no-accounts">No accounts discovered. Run Setup Device to discover accounts.</p>
            )}
          </div>
        </div>
        <div className="device-actions">
          <button 
            onClick={() => initializeDevice(deviceId)} 
            disabled={device.status === 'initializing'}
            className="action-button"
          >
            Initialize
          </button>
          <button 
            onClick={() => executeSetupDeviceTask(deviceId)}
            disabled={device.status !== 'ready'}
            className="action-button"
          >
            Setup Device
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Instagram Automation Dashboard</h1>
        <div className={`status-indicator status-${status}`}>
          Status: {status === 'running' ? 'Running' : status === 'loading' ? 'Loading...' : 'Not Initialized'}
        </div>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div className="dashboard-container">
        {/* Appium Servers Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Appium Servers</h2>
            {!isAddingServer ? (
              <button onClick={() => setIsAddingServer(true)} className="add-button">
                Add Server
              </button>
            ) : (
              <button onClick={() => setIsAddingServer(false)} className="cancel-button">
                Cancel
              </button>
            )}
          </div>

          {isAddingServer ? (
            <div className="form-container">
              <h3>Add New Appium Server</h3>
              <form onSubmit={addServer}>
                <div className="form-group">
                  <label>Name:</label>
                  <input
                    type="text"
                    name="name"
                    value={newServer.name}
                    onChange={handleServerInputChange}
                    placeholder="server-3"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Host:</label>
                  <input
                    type="text"
                    name="host"
                    value={newServer.host}
                    onChange={handleServerInputChange}
                    placeholder="127.0.0.1"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Port:</label>
                  <input
                    type="number"
                    name="port"
                    value={newServer.port}
                    onChange={handleServerInputChange}
                    placeholder="4725"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Max Devices:</label>
                  <input
                    type="number"
                    name="max_devices"
                    value={newServer.max_devices}
                    onChange={handleServerInputChange}
                    placeholder="5"
                    required
                  />
                </div>
                <button type="submit" className="submit-button">Add Server</button>
              </form>
            </div>
          ) : (
            <div className="servers-list">
              {Object.keys(servers).length === 0 ? (
                <div className="empty-message">No servers configured</div>
              ) : (
                Object.entries(servers).map(([serverId, serverInfo]) => {
                  const serverDevicesList = getDevicesForServer(serverId);
                  const isExpanded = expandedServers[serverId];
                  
                  // Count real devices on this server
                  const realDeviceCount = serverDevicesList.filter(device => !device.is_simulator).length;
                  
                  // Check if we have any devices for this server
                  const hasDevices = serverDevicesList && serverDevicesList.length > 0;
                  
                  return (
                    <div key={serverId} className={`server-card status-${serverInfo.status}`}>
                      <div className="server-header">
                        <h3>{serverInfo.name}</h3>
                        <span className={`server-status ${serverInfo.status}`}>
                          {serverInfo.status}
                        </span>
                      </div>
                      <div className="server-details">
                        <p><strong>Host:</strong> {serverInfo.config?.host || "Unknown"}</p>
                        <p><strong>Port:</strong> {serverInfo.port}</p>
                        <p className="device-count-row">
                          <strong>Devices:</strong> {showOnlyRealDevices ? 
                            `${realDeviceCount} real / ${serverInfo.max_devices}` : 
                            `${serverInfo.device_count} / ${serverInfo.max_devices}`}
                          <button 
                            className={`expand-button ${isExpanded ? 'expanded' : ''}`}
                            onClick={() => toggleServerExpansion(serverId)}
                          >
                            {isExpanded ? '▼' : '▶'}
                          </button>
                        </p>
                      </div>
                      {isExpanded && (
                        <div className="server-devices">
                          {!hasDevices ? (
                            <p className="no-devices">
                              {showOnlyRealDevices 
                                ? 'No real devices assigned to this server' 
                                : 'No devices assigned to this server'}
                            </p>
                          ) : (
                            <ul className="device-list">
                              {serverDevicesList.map((device) => (
                                <li key={device.id} className={`device-item status-${device.status} ${device.is_simulator ? 'simulator' : 'real-device'}`}>
                                  <span className="device-name">
                                    {device.name}
                                    {device.is_simulator && <span className="mini-simulator-badge">Sim</span>}
                                  </span>
                                  <span className={`device-status ${device.status}`}>
                                    {device.status}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Devices Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Connected Devices</h2>
            <div className="header-buttons">
              <button 
                onClick={toggleShowOnlyRealDevices} 
                className={`filter-button ${showOnlyRealDevices ? 'active' : ''}`}
              >
                {showOnlyRealDevices ? 'Real Devices Only' : 'Show All Devices'}
              </button>
              <button onClick={refreshDevices} className="refresh-button">
                Refresh Devices
              </button>
              {!isAddingDevice ? (
                <button onClick={() => setIsAddingDevice(true)} className="add-button">
                  Add Device
                </button>
              ) : (
                <button onClick={() => setIsAddingDevice(false)} className="cancel-button">
                  Cancel
                </button>
              )}
            </div>
          </div>

          {isAddingDevice ? (
            <div className="form-container">
              <h3>Add New Device</h3>
              <form onSubmit={addDevice}>
                <div className="form-group">
                  <label>Name:</label>
                  <input
                    type="text"
                    name="name"
                    value={newDevice.name}
                    onChange={handleDeviceInputChange}
                    placeholder="iPhone 12"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>UDID:</label>
                  <input
                    type="text"
                    name="udid"
                    value={newDevice.udid}
                    onChange={handleDeviceInputChange}
                    placeholder="12345678-1234-1234-1234-123456789012"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Platform:</label>
                  <select
                    name="platformName"
                    value={newDevice.platformName}
                    onChange={handleDeviceInputChange}
                    required
                  >
                    <option value="iOS">iOS</option>
                    <option value="Android">Android</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Version:</label>
                  <input
                    type="text"
                    name="platformVersion"
                    value={newDevice.platformVersion}
                    onChange={handleDeviceInputChange}
                    placeholder="14.5"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Device Name:</label>
                  <input
                    type="text"
                    name="deviceName"
                    value={newDevice.deviceName}
                    onChange={handleDeviceInputChange}
                    placeholder="iPhone"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Automation:</label>
                  <select
                    name="automationName"
                    value={newDevice.automationName}
                    onChange={handleDeviceInputChange}
                    required
                  >
                    <option value="XCUITest">XCUITest (iOS)</option>
                    <option value="UiAutomator2">UiAutomator2 (Android)</option>
                  </select>
                </div>
                <button type="submit" className="submit-button">Add Device</button>
              </form>
            </div>
          ) : (
            <div className="devices-list">
              {Object.keys(getFilteredDevices()).length === 0 ? (
                <div className="empty-message">
                  {showOnlyRealDevices 
                    ? "No real devices connected. Connect a device or toggle to show simulators." 
                    : "No devices connected"}
                </div>
              ) : (
                Object.entries(getFilteredDevices()).map(([deviceId, deviceInfo]) => {
                  const serverInfo = getServerForDevice(deviceInfo);
                  
                  return (
                    <DeviceCard key={deviceId} device={deviceInfo} deviceId={deviceId} />
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Running Tasks Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Running Tasks</h2>
          </div>
          
          <div className="tasks-list">
            {Object.keys(tasks).length === 0 ? (
              <div className="empty-message">No tasks running</div>
            ) : (
              Object.entries(tasks).map(([taskKey, taskInfo]) => (
                <div key={taskKey} className="task-card">
                  <div className="task-header">
                    <h3>{taskInfo.task_name}</h3>
                    <span className="task-device">
                      Device: {devices[taskInfo.device_id]?.name || taskInfo.device_id}
                    </span>
                  </div>
                  <div className="task-details">
                    <p><strong>Running for:</strong> {formatDuration(taskInfo.running_for)}</p>
                    <p><strong>Interval:</strong> {taskInfo.interval} seconds</p>
                  </div>
                  <div className="task-actions">
                    <button 
                      onClick={() => stopTask(taskInfo.device_id, taskInfo.task_name)} 
                      className="action-button stop"
                    >
                      Stop Task
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Task Result Section */}
        {taskResult && (
          <div className="dashboard-section">
            <div className="section-header">
              <h2>Last Task Result</h2>
              <button onClick={() => setTaskResult(null)} className="close-button">×</button>
            </div>
            <div className="task-result">
              <h3>
                {taskResult.task} on {devices[taskResult.device]?.name || taskResult.device}
              </h3>
              <div className="result-details">
                <p>
                  <strong>Success:</strong>{' '}
                  <span className={taskResult.result.success ? 'success' : 'error'}>
                    {taskResult.result.success ? 'Yes' : 'No'}
                  </span>
                </p>
                {taskResult.result.error && (
                  <p><strong>Error:</strong> {taskResult.result.error}</p>
                )}
                {taskResult.result.scheduled && (
                  <p><strong>Task scheduled:</strong> Will repeat every {taskInterval} seconds</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {status === 'not_initialized' && (
        <div className="initialize-prompt">
          <p>System is not initialized. Initialize to connect to devices?</p>
          <button onClick={initializeSystem} className="initialize-button">
            Initialize System
          </button>
        </div>
      )}
    </div>
  );
}

export default App; 