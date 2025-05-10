import time
import random
import logging
import json
import os
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.interaction import POINTER_TOUCH

logger = logging.getLogger(__name__)

class InstagramTaskRunner:
    """Executes Instagram automation tasks on connected devices"""
    
    def __init__(self, device_manager):
        """
        Initialize the task runner
        
        Args:
            device_manager: The device manager instance
        """
        self.device_manager = device_manager
        self.ui_map = None
        
        # Running tasks
        self.running_tasks = {}
        
        logger.info("Task runner initialized")
    
    def _load_ui_map_for_device(self, device_info):
        """Load the UI map for the specific device based on its model."""
        if not device_info or 'config' not in device_info or 'model' not in device_info['config']:
            logger.error("Device model not found in device_info.")
            self.ui_map = None
            return False

        device_model = device_info['config']['model']
        ui_map_filename = "instagram_map.json" # Standard name for the map file
        # Construct path relative to the project root where task_runner.py is likely executed from
        # Assuming task_runner.py is in automation/ and ui_maps/ is at the project root
        # So, ../ui_maps/{device_model}/instagram_map.json from automation/
        # Or, if running from project root: ui_maps/{device_model}/instagram_map.json
        # Let's assume execution context is project root for simplicity of path construction for now.
        # This might need adjustment based on how scripts are run.
        # For now, using a path relative to the root of the project.
        # A more robust way would be to get the script's directory or a base path.
        
        # Let's determine the base path. Assuming this script is in 'automation' directory
        # and 'ui_maps' is a sibling of 'automation'.
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root_dir = os.path.dirname(current_script_dir) # Goes up one level from 'automation' to project root
        map_path = os.path.join(project_root_dir, "ui_maps", device_model, ui_map_filename)

        if not os.path.exists(map_path):
            logger.error(f"UI map file not found for model {device_model} at {map_path}")
            self.ui_map = None
            return False
        
        try:
            with open(map_path, 'r') as f:
                self.ui_map = json.load(f)
            logger.info(f"Successfully loaded UI map for model {device_model} from {map_path}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from UI map file {map_path}: {e}")
            self.ui_map = None
            return False
        except Exception as e:
            logger.error(f"Failed to load UI map {map_path}: {e}")
            self.ui_map = None
            return False
    
    def get_element_position(self, screen_name, element_name, device_width, device_height):
        """Get the position of an element based on screen dimensions"""
        if not self.ui_map or screen_name not in self.ui_map:
            logger.error(f"Screen {screen_name} not found in UI map")
            return None
            
        if element_name not in self.ui_map[screen_name]:
            logger.error(f"Element {element_name} not found in {screen_name} screen")
            return None
            
        element_info = self.ui_map[screen_name][element_name]
        
        # Use relative positioning to adjust for different screen sizes
        # Assuming UI map contains positions as percentages
        rel_x = element_info.get("x", 0.5)  # Default to center if not specified
        rel_y = element_info.get("y", 0.5)  # Default to center if not specified
        
        # Convert to actual screen coordinates
        x = int(rel_x * device_width)
        y = int(rel_y * device_height)
        
        return (x, y)
    
    def tap_element(self, driver, screen_name, element_name, device_info):
        """Tap on an element based on UI map"""
        # Get device dimensions
        device_width = device_info['screen_width']
        device_height = device_info['screen_height']
        
        # Get element position
        position = self.get_element_position(screen_name, element_name, device_width, device_height)
        if not position:
            logger.error(f"Could not get position for {element_name} on {screen_name}")
            return False
            
        # Add small random offset for more human-like behavior (±5% of position)
        x_offset = random.randint(-int(device_width * 0.05), int(device_width * 0.05))
        y_offset = random.randint(-int(device_height * 0.05), int(device_height * 0.05))
        
        # Ensure we stay within screen bounds
        x = max(10, min(position[0] + x_offset, device_width - 10))
        y = max(10, min(position[1] + y_offset, device_height - 10))
        
        # Perform the tap with a small random delay using mobile gestures
        logger.info(f"Tapping at general coordinates ({x}, {y}) using mobile gestures")
        
        # Use mobile: gesture commands which are supported by iOS 18 and Appium 2.x
        driver.execute_script('mobile: tap', {
            'x': x,
            'y': y
        })
        
        # Random delay after tap
        time.sleep(random.uniform(0.5, 1.5))
        
        return True
        
    def swipe(self, driver, start_x, start_y, end_x, end_y, duration=None):
        """Perform a swipe gesture using mobile gestures"""
        if duration is None:
            # Random duration for more human-like swipes (in seconds for mobile gestures)
            duration_sec = random.uniform(0.3, 1.0)
        else:
            # Convert from milliseconds to seconds if needed
            duration_sec = duration / 1000.0 if duration > 10 else duration

        logger.info(f"Swiping from ({start_x},{start_y}) to ({end_x},{end_y}) with duration {duration_sec}s using mobile gestures")
        
        # Use mobile: dragFromToForDuration which is supported by iOS 18 and Appium 2.x
        driver.execute_script('mobile: dragFromToForDuration', {
            'fromX': start_x,
            'fromY': start_y,
            'toX': end_x,
            'toY': end_y,
            'duration': duration_sec
        })
        
        # Random delay after swipe
        time.sleep(random.uniform(0.5, 1.5))
        
    def scroll_down(self, driver, device_info, distance=None):
        """Scroll down on the screen"""
        device_width = device_info['screen_width']
        device_height = device_info['screen_height']
        
        # Start from middle-bottom area
        start_x = device_width // 2
        start_y = int(device_height * 0.7)
        
        # End at middle-top area
        end_x = device_width // 2
        
        # If distance specified, use it, otherwise scroll about half the screen
        if distance:
            end_y = max(10, start_y - distance)
        else:
            end_y = int(device_height * 0.3)
        
        # Perform swipe with random duration
        self.swipe(driver, start_x, start_y, end_x, end_y)
        
    def scroll_up(self, driver, device_info, distance=None):
        """Scroll up on the screen"""
        device_width = device_info['screen_width']
        device_height = device_info['screen_height']
        
        # Start from middle-top area
        start_x = device_width // 2
        start_y = int(device_height * 0.3)
        
        # End at middle-bottom area
        end_x = device_width // 2
        
        # If distance specified, use it, otherwise scroll about half the screen
        if distance:
            end_y = min(device_height - 10, start_y + distance)
        else:
            end_y = int(device_height * 0.7)
        
        # Perform swipe
        self.swipe(driver, start_x, start_y, end_x, end_y)
    
    def execute_task(self, task_name, device_id=None, device_info=None, **kwargs):
        """Execute a task on a device"""
        # Get next available device if not specified
        _device_id_to_release = None # Keep track if we got a device we need to release
        if not device_id:
            selected_device_id, driver = self.device_manager.get_available_device()
            if not selected_device_id:
                logger.error("No available devices")
                return {"success": False, "error": "No available devices"}
            device_id = selected_device_id
            _device_id_to_release = device_id # Mark for release
        else:
            # Get driver for the specified device
            if device_id not in self.device_manager.drivers:
                logger.error(f"Device {device_id} not found or not initialized.")
                # Attempt to initialize if known but not in drivers (e.g. after a restart)
                if device_id in self.device_manager.devices:
                    logger.info(f"Attempting to initialize device {device_id} for task.")
                    if not self.device_manager.initialize_device(device_id):
                        logger.error(f"Failed to initialize device {device_id} for task.")
                        return {"success": False, "error": f"Device {device_id} could not be initialized."}
                    driver = self.device_manager.drivers.get(device_id)
                    if not driver:
                         logger.error(f"Driver not available for {device_id} even after init attempt.")
                         return {"success": False, "error": f"Driver for {device_id} unavailable."}
                else: # Device ID is not even in the known devices list
                    logger.error(f"Device {device_id} is not a known device.")
                    return {"success": False, "error": f"Device {device_id} not a known device"}

            driver = self.device_manager.drivers[device_id] # Now get the driver
        
        # Get device info (which now includes screen dimensions and model from config)
        # If device_info was provided as parameter, use it instead of trying to fetch
        if device_info is None:
            logger.error(f"No device info provided for {device_id}")
            if _device_id_to_release: # Release if we acquired it
                self.device_manager.release_device(_device_id_to_release)
            return {"success": False, "error": f"No device info provided for {device_id}"}

        # Load the UI map for this specific device model
        if not self._load_ui_map_for_device(device_info):
            logger.error(f"Failed to load UI map for device {device_id} (model: {device_info.get('config', {}).get('model', 'N/A')}). Cannot proceed with UI-dependent task.")
            if _device_id_to_release: # Release if we acquired it
                self.device_manager.release_device(_device_id_to_release)
            return {"success": False, "error": "Failed to load UI map for the device model."}

        try:
            # Execute the appropriate task
            if task_name == "open_instagram":
                result = self.open_instagram(driver, device_info, **kwargs)
            elif task_name == "go_to_profile":
                result = self.go_to_profile(driver, device_info, **kwargs)
            elif task_name == "scroll_feed":
                result = self.scroll_feed(driver, device_info, **kwargs)
            elif task_name == "setup_device":
                result = self.setup_device(driver, device_info, **kwargs)
            else:
                result = {"success": False, "error": f"Unknown task: {task_name}"}
                
            # If not successful, log the error
            if not result.get("success", False):
                logger.error(f"Task {task_name} failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.exception(f"Error executing task {task_name}")
            result = {"success": False, "error": str(e)}
        finally:
            # Release the device if we acquired one for this task
            if _device_id_to_release: # Use the tracked ID for release
                self.device_manager.release_device(_device_id_to_release)
        
        return result
                
    def open_instagram(self, driver, device_info, **kwargs):
        """Open Instagram app"""
        logger.info(f"Opening Instagram on {device_info['config']['name']}")
        
        try:
            # For iOS, the app should already launch through desired capabilities
            # For Android, we can use this to relaunch the app if needed
            if device_info['config']['platformName'].lower() == 'android':
                driver.activate_app('com.instagram.android')
            else:
                driver.activate_app('com.burbn.instagram')
                
            # Wait for app to load
            time.sleep(random.uniform(2, 4))
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def go_to_profile(self, driver, device_info, **kwargs):
        """Navigate to the profile page"""
        logger.info(f"Navigating to profile on {device_info['config']['name']}")
        
        try:
            # Tap on the profile tab using the UI map
            tap_result = self._tap_on_element_from_map(driver, "initial_screen_before_profile", "profile-tab_Profile")
            
            if tap_result and tap_result.get("success"):
                logger.info("Successfully tapped on profile tab")
                
                # Wait for profile to load
                time.sleep(random.uniform(1, 2))
                
                return {"success": True}
            else:
                error_message = tap_result.get("error") if tap_result else "Unknown error"
                logger.error(f"Failed to tap on profile tab: {error_message}")
                return {"success": False, "error": f"Could not tap profile tab: {error_message}"}
        except Exception as e:
            logger.exception("Error navigating to profile")
            return {"success": False, "error": str(e)}
    
    def scroll_feed(self, driver, device_info, iterations=5, **kwargs):
        """Scroll through the feed"""
        device_name = device_info['config']['name']
        logger.info(f"Scrolling feed on {device_name}, {iterations} iterations")
        
        try:
            # First go to home feed if not already there
            if self.tap_element(driver, "initial_screen", "home", device_info):
                logger.info(f"Tapped on home icon on {device_name}")
            
            # Wait for feed to load
            time.sleep(random.uniform(1, 2))
            
            # Scroll down several times
            for i in range(iterations):
                logger.info(f"Scroll iteration {i+1}/{iterations} on {device_name}")
                self.scroll_down(driver, device_info)
                
                # Random pause between scrolls (2-5 seconds)
                time.sleep(random.uniform(2, 5))
                
            return {"success": True, "iterations_completed": iterations}
        except Exception as e:
            return {"success": False, "error": str(e), "iterations_completed": i}
            
    def setup_device(self, driver, device_info, **kwargs):
        """
        Sets up a device by opening Instagram, navigating to the profile,
        tapping the username to open the account switcher, scraping account names,
        and storing them.
        """
        device_name = device_info['config']['name']
        logger.info(f"Starting device setup task for {device_name}")

        try:
            # Step 1: Open Instagram
            open_result = self.open_instagram(driver, device_info, **kwargs)
            if not open_result.get("success"):
                err_msg = f"Failed to open Instagram on {device_name}: {open_result.get('error')}"
                logger.error(err_msg)
                return {"success": False, "error": err_msg, "stage": "open_instagram"}
            logger.info(f"Successfully opened Instagram on {device_name}")
            time.sleep(random.uniform(1, 2))

            # Step 2: Go to Profile
            profile_result = self.go_to_profile(driver, device_info, **kwargs)
            if not profile_result.get("success"):
                err_msg = f"Failed to navigate to profile on {device_name}: {profile_result.get('error')}"
                logger.error(err_msg)
                return {"success": False, "error": err_msg, "stage": "go_to_profile"}
            logger.info(f"Successfully navigated to profile on {device_name}")
            time.sleep(random.uniform(1, 2))

            # Step 3: Tap Profile Username
            logger.info(f"Attempting to tap profile username on {device_name} to open account switcher...")
            tapped_username_result = self.tap_profile_username(driver, device_info)
            if not tapped_username_result.get("success"):
                err_msg = f"Failed to tap profile username on {device_name}: {tapped_username_result.get('error')}"
                logger.error(err_msg)
                return {"success": False, "error": err_msg, "stage": "tap_profile_username"}
            logger.info(f"Successfully tapped profile username on {device_name}")
            time.sleep(random.uniform(2, 3)) # Wait for account switcher to appear

            # Step 4: Scrape Account Names from Switcher
            logger.info(f"Attempting to scrape account names from switcher on {device_name}...")
            scraped_accounts_result = self.scrape_account_names_from_switcher(driver, device_info)
            if not scraped_accounts_result.get("success"):
                err_msg = f"Failed to scrape account names on {device_name}: {scraped_accounts_result.get('error')}"
                logger.error(err_msg)
                # We might still proceed to store if some accounts were scraped before an error
                discovered_accounts = scraped_accounts_result.get("accounts", [])
                if not discovered_accounts: # If no accounts at all, then it's a hard fail for this stage
                    return {"success": False, "error": err_msg, "stage": "scrape_account_names"}
            else:
                discovered_accounts = scraped_accounts_result.get("accounts", [])
            
            logger.info(f"Discovered {len(discovered_accounts)} accounts on {device_name}: {discovered_accounts}")

            # Step 5: Store Discovered Accounts
            if discovered_accounts:
                device_udid = device_info['config']['udid']  # Extract device_udid from device_info
                logger.info(f"Storing discovered accounts for device {device_udid}...")
                store_result = self.store_discovered_accounts(device_udid, discovered_accounts)
                if not store_result.get("success"):
                    logger.error(f"Failed to store discovered accounts for {device_udid}: {store_result.get('error')}")
                    # This might not be a fatal error for the whole task, but we should report it
                    # For now, let's continue and report overall success if other steps passed.
            else:
                logger.info(f"No accounts discovered or scraped for {device_name}, nothing to store.")

            return {"success": True, "message": f"Device setup task completed for {device_name}. Discovered accounts: {discovered_accounts}"}

        except Exception as e:
            logger.exception(f"Error during setup_device task for {device_name}")
            return {"success": False, "error": str(e), "stage": "unknown"}
    
    def run_scheduled_task(self, task_name, device_id, repeat_interval=None, **kwargs):
        """Run a task and optionally schedule it to repeat"""
        task_key = f"{device_id}_{task_name}"
        
        # Check if task is already running
        if task_key in self.running_tasks:
            return {"success": False, "error": f"Task {task_name} is already running on device {device_id}"}
        
        # Start task
        result = self.execute_task(task_name, device_id, **kwargs)
        
        # If repeat interval is set and task was successful, schedule repeating task
        if repeat_interval and result.get("success", False):
            import threading
            
            # Function to run the task repeatedly
            def run_repeating():
                while task_key in self.running_tasks:
                    # Sleep for the interval
                    time.sleep(repeat_interval)
                    
                    # Run the task again
                    if task_key in self.running_tasks:  # Check again in case it was stopped
                        try:
                            self.execute_task(task_name, device_id, **kwargs)
                        except Exception as e:
                            logger.error(f"Error in repeating task {task_name}: {e}")
            
            # Create and start the thread
            thread = threading.Thread(target=run_repeating)
            thread.daemon = True  # Thread will exit when main program exits
            thread.start()
            
            # Store thread reference
            self.running_tasks[task_key] = {
                "thread": thread,
                "interval": repeat_interval,
                "started_at": time.time()
            }
            
            result["scheduled"] = True
            
        return result
    
    def stop_scheduled_task(self, task_name, device_id):
        """Stop a repeating task"""
        task_key = f"{device_id}_{task_name}"
        
        if task_key in self.running_tasks:
            # Remove from running tasks to signal thread to stop
            task_info = self.running_tasks.pop(task_key)
            
            return {
                "success": True, 
                "duration": time.time() - task_info["started_at"],
                "interval": task_info["interval"]
            }
        else:
            return {"success": False, "error": f"No running task {task_name} for device {device_id}"}
    
    def get_running_tasks(self):
        """Get list of currently running tasks"""
        tasks = {}
        
        for task_key, task_info in self.running_tasks.items():
            device_id, task_name = task_key.split('_', 1)
            
            tasks[task_key] = {
                "device_id": device_id,
                "task_name": task_name,
                "interval": task_info["interval"],
                "running_for": time.time() - task_info["started_at"]
            }
            
        return tasks 

    def _tap_on_element_from_map(self, driver, screen_name, element_key):
        """
        Taps on an element from the UI map based on its coordinates.
        
        Args:
            driver: The Appium driver
            screen_name: The screen section in the UI map
            element_key: The element key to tap on
            
        Returns:
            dict: Result of the operation
        """
        logger.info(f"Attempting to tap on '{element_key}' in screen '{screen_name}'")
        
        if not self.ui_map:
            logger.error("UI map is not loaded")
            return {"success": False, "error": "UI map not loaded"}
            
        screen_map = self.ui_map.get(screen_name)
        if not screen_map:
            logger.error(f"Screen '{screen_name}' not found in UI map")
            return {"success": False, "error": f"Screen '{screen_name}' not found in UI map"}
            
        element_data = screen_map.get(element_key)
        if not element_data:
            # Try to find element keys that contain the element_key string
            matching_keys = [k for k in screen_map.keys() if element_key in k]
            if matching_keys:
                logger.info(f"Element '{element_key}' not found, but found possible matches: {matching_keys}")
                element_key = matching_keys[0]  # Use the first matching key
                element_data = screen_map.get(element_key)
            else:
                logger.error(f"Element '{element_key}' not found in '{screen_name}' screen")
                return {"success": False, "error": f"Element '{element_key}' not found"}
        
        try:
            # Extract coordinates from UI map
            x = int(element_data.get("x", 0)) + int(element_data.get("width", 0)) // 2
            y = int(element_data.get("y", 0)) + int(element_data.get("height", 0)) // 2
            
            # Add small random offset for more human-like behavior
            window_size = driver.get_window_size()
            device_width = window_size['width']
            device_height = window_size['height']
            
            x_offset = random.randint(-int(device_width * 0.02), int(device_width * 0.02))
            y_offset = random.randint(-int(device_height * 0.02), int(device_height * 0.02))
            
            # Ensure coordinates stay within screen bounds
            x = max(5, min(x + x_offset, device_width - 5))
            y = max(5, min(y + y_offset, device_height - 5))
            
            # Perform tap
            logger.info(f"Tapping at coordinates ({x}, {y}) for element '{element_key}' using mobile gestures")
            
            # Use mobile: gesture commands which are supported by iOS 18 and Appium 2.x
            driver.execute_script('mobile: tap', {
                'x': x,
                'y': y
            })
            
            # Wait a moment after tapping
            time.sleep(random.uniform(0.8, 1.5))
            
            return {"success": True, "message": f"Tapped on '{element_key}'"}
        except Exception as e:
            logger.exception(f"Error tapping on '{element_key}'")
            return {"success": False, "error": str(e)}

    def tap_profile_username(self, driver, device_info):
        """Taps on the profile username at the top of the profile screen to open the account switcher."""
        # The key for the profile username button in 'profile_screen_details'
        # Based on the user's instagram_ios_ui_map.json, this is "user-switch-title-button"
        element_key = "user-switch-title-button"
        screen_name = "profile_screen_details" # This screen should contain the username button

        logger.info(f"Attempting to tap '{element_key}' on screen '{screen_name}' for device {device_info.get('name', 'Unknown')}")

        tap_result = self._tap_on_element_from_map(driver, screen_name, element_key)
        if tap_result and tap_result.get("success"):
            logger.info(f"Successfully tapped on '{element_key}'.")
            return {"success": True, "message": f"Tapped on {element_key}"}
        else:
            error_message = tap_result.get("error") if tap_result else "Element not found or tap failed"
            logger.error(f"Failed to tap on '{element_key}': {error_message}")
            return {"success": False, "error": error_message}

    def scrape_account_names_from_switcher(self, driver, device_info):
        """
        Scrapes account names from the account switcher UI using the mapped elements.
        """
        device_name = device_info.get('name', 'Unknown')
        logger.info(f"Attempting to scrape account names from switcher on {device_name} using UI map...")

        if not self.ui_map:
            logger.error("UI map is not loaded. Cannot scrape account names.")
            return {"success": False, "error": "UI map not loaded."}

        account_switcher_screen_map = self.ui_map.get("account_switcher_details")
        if not account_switcher_screen_map:
            logger.error("'account_switcher_details' not found in UI map. Cannot scrape accounts.")
            logger.error("Please ensure the crawler has successfully mapped this screen.")
            return {"success": False, "error": "'account_switcher_details' not found in UI map."}

        discovered_accounts = set()  # Use a set to store unique account names

        try:
            # Look specifically for account buttons in the switcher
            # For iPhone 13 Pro Max UI map, these are the buttons like "morgancryerthequeen, Shared access"
            account_buttons = []
            
            for element_key, element_data in account_switcher_screen_map.items():
                if (element_data.get("type") == "XCUIElementTypeButton" and 
                    "Shared access" in element_data.get("label", "") and 
                    element_data.get("visible") == "true"):
                    account_buttons.append(element_data)
            
            logger.info(f"Found {len(account_buttons)} account buttons in the switcher")
            
            # Extract account names from button labels
            for button_data in account_buttons:
                label = button_data.get("label", "")
                if label:
                    # Extract the account name part before ", Shared access"
                    account_name = label.split(",")[0].strip()
                    if account_name:
                        discovered_accounts.add(account_name)
                        logger.info(f"Discovered account: {account_name}")
            
            if not discovered_accounts:
                # Fallback: try to find account names by other patterns in the UI map
                logger.info("No accounts found with preferred method, trying fallback...")
                for element_key, element_data in account_switcher_screen_map.items():
                    label = element_data.get("label", "")
                    if "Instagram account" in label or "account" in label.lower():
                        # This might be a button related to account management
                        logger.info(f"Found potential account element: {label}")
                        if element_data.get("visible") == "true":
                            # Try to tap on this to see more accounts
                            element_name = element_data.get("name", "")
                            self._tap_on_element_from_map(driver, "account_switcher_details", element_name)
                            time.sleep(1.5)  # Wait for UI to update
                
            return {
                "success": True, 
                "accounts": list(discovered_accounts),
                "message": f"Found {len(discovered_accounts)} accounts"
            }
        
        except Exception as e:
            logger.exception(f"Error scraping account names from switcher: {e}")
            return {
                "success": False, 
                "error": str(e),
                "accounts": list(discovered_accounts) if discovered_accounts else []
            }

    def store_discovered_accounts(self, device_udid, accounts_list):
        """Stores the list of discovered accounts for a given device UDID."""
        if not device_udid or not isinstance(accounts_list, list):
            return {"success": False, "error": "Invalid device_udid or accounts_list provided."}

        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
                logger.info(f"Created config directory: {config_dir}")
            except OSError as e:
                logger.error(f"Error creating config directory {config_dir}: {e}")
                return {"success": False, "error": f"Could not create config directory: {str(e)}"}

        managed_accounts_path = os.path.join(config_dir, 'managed_accounts.json')
        
        all_managed_accounts = {}
        if os.path.exists(managed_accounts_path):
            try:
                with open(managed_accounts_path, 'r') as f:
                    all_managed_accounts = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode existing managed_accounts.json. Will overwrite.")
            except Exception as e:
                logger.error(f"Error reading {managed_accounts_path}: {e}")
                return {"success": False, "error": f"Error reading existing managed accounts file: {str(e)}"}

        # Replace the existing accounts with the newly discovered accounts for this device
        # This ensures accounts are only associated with their correct device
        all_managed_accounts[device_udid] = accounts_list
        logger.info(f"Setting {len(accounts_list)} accounts for device {device_udid}: {accounts_list}")
        
        try:
            with open(managed_accounts_path, 'w') as f:
                json.dump(all_managed_accounts, f, indent=4)
            logger.info(f"Successfully stored accounts for {device_udid} in {managed_accounts_path}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error writing to {managed_accounts_path}: {e}")
            return {"success": False, "error": f"Error writing managed accounts file: {str(e)}"} 