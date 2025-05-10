#!/usr/bin/env python3
import os
import sys
import time
import traceback
from appium import webdriver
from appium.webdriver.common.mobileby import MobileBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

# iOS device capabilities
caps = {
    'platformName': 'iOS',
    'platformVersion': '18.0', 
    'deviceName': 'iPhone',
    'udid': '00008110-000A04D11AD3801E',
    'automationName': 'XCUITest',
    'xcodeOrgId': os.environ.get('XCODE_ORG_ID', ''),  # Your Team ID from Apple Developer account
    'xcodeSigningId': 'iPhone Developer',
    'newCommandTimeout': 360,
    'noReset': True,
    'startIWDP': True,  # Start iOS WebKit Debug Proxy for web inspector
    'wdaLocalPort': 8100,  # Port for WebDriverAgent
}

# Appium server URL
appium_server_url = 'http://localhost:4723'  # Appium 2.x format
# For Appium 1.x you may need to use: appium_server_url = 'http://localhost:4723/wd/hub'

try:
    print("========== DEBUG INFO ==========")
    print(f"Connecting to Appium server at: {appium_server_url}")
    print(f"Using capabilities: {caps}")
    
    # Initialize the driver
    print("Initializing driver...")
    driver = webdriver.Remote(appium_server_url, caps)
    
    # Wait for the driver to be ready
    print("Driver initialized successfully!")
    print(f"Session ID: {driver.session_id}")
    print(f"Device info: {driver.capabilities}")
    
    # Test a simple action - get available contexts
    print("\nGetting available contexts...")
    contexts = driver.contexts
    print(f"Available contexts: {contexts}")
    
    # Test another action - take a screenshot
    print("\nTaking a screenshot...")
    screenshot = driver.get_screenshot_as_base64()
    print(f"Screenshot taken, length: {len(screenshot)} characters")
    
    # Keep session alive briefly 
    print("\nTest completed successfully! Waiting 5 seconds before closing...")
    time.sleep(5)
    
except Exception as e:
    print("\n========== ERROR ==========")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nStacktrace:")
    traceback.print_exc()
    print("\nTrying to get more info about the Appium server:")
    try:
        import requests
        response = requests.get('http://localhost:4723/status')
        print(f"Appium server status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as server_error:
        print(f"Couldn't get server info: {str(server_error)}")
    
    sys.exit(1)
    
finally:
    # Close the session
    print("\nClosing the session...")
    try:
        if 'driver' in locals():
            driver.quit()
            print("Session closed successfully")
    except Exception as close_error:
        print(f"Error closing session: {str(close_error)}")

print("\nScript completed!") 