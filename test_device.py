#!/usr/bin/env python3
import time
from appium import webdriver

# iOS device capabilities
capabilities = {
    'platformName': 'iOS',
    'platformVersion': '18.0',
    'deviceName': 'iPhone',
    'udid': '00008110-000A04D11AD3801E',
    'automationName': 'XCUITest',
    'noReset': True
}

# Connect to Appium server - using the base URL without /wd/hub for Appium 2.x
print("Connecting to Appium server...")
driver = webdriver.Remote('http://localhost:4724', capabilities)

# Simple test to verify connection
print("Connected to the device successfully!")
print(f"Device info: {driver.capabilities}")

# Keep session alive briefly
time.sleep(5)

# Close the session
print("Closing the session")
driver.quit() 