import time
import random
import logging
import json
import os
from appium.webdriver.common.touch_action import TouchAction

logger = logging.getLogger(__name__)

class InstagramTaskRunner:
    """Executes Instagram automation tasks on connected devices"""
    
    def __init__(self, device_manager, ui_map_path=None):
        """
        Initialize the task runner
        
        Args:
            device_manager: The device manager instance
            ui_map_path: Path to the Instagram UI map JSON
        """
        self.device_manager = device_manager
        self.ui_map = None
        
        # Load UI map if provided
        if ui_map_path and os.path.exists(ui_map_path):
            with open(ui_map_path, 'r') as f:
                self.ui_map = json.load(f)
        
        # Running tasks
        self.running_tasks = {}
        
        logger.info("Task runner initialized")
    
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
        
        # Perform the tap with a small random delay
        touch_action = TouchAction(driver)
        touch_action.press(x=x, y=y).wait(random.randint(50, 150)).release().perform()
        
        # Random delay after tap
        time.sleep(random.uniform(0.5, 1.5))
        
        return True
        
    def swipe(self, driver, start_x, start_y, end_x, end_y, duration=None):
        """Perform a swipe gesture"""
        if duration is None:
            # Random duration for more human-like swipes
            duration = random.randint(300, 1000)
            
        touch_action = TouchAction(driver)
        touch_action.press(x=start_x, y=start_y).wait(duration).move_to(x=end_x, y=end_y).release().perform()
        
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
    
    def execute_task(self, task_name, device_id=None, **kwargs):
        """Execute a task on a device"""
        # Get next available device if not specified
        if not device_id:
            device_id, driver = self.device_manager.get_available_device()
            if not device_id:
                logger.error("No available devices")
                return {"success": False, "error": "No available devices"}
        else:
            # Get driver for the specified device
            if device_id not in self.device_manager.drivers:
                logger.error(f"Device {device_id} not found")
                return {"success": False, "error": f"Device {device_id} not found"}
            driver = self.device_manager.drivers[device_id]
        
        # Get device info
        device_info = self.device_manager.devices[device_id]
        
        try:
            # Execute the appropriate task
            if task_name == "open_instagram":
                result = self.open_instagram(driver, device_info, **kwargs)
            elif task_name == "go_to_profile":
                result = self.go_to_profile(driver, device_info, **kwargs)
            elif task_name == "scroll_feed":
                result = self.scroll_feed(driver, device_info, **kwargs)
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
            if not device_id:
                self.device_manager.release_device(device_id)
        
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
            # First ensure we're on a screen where the profile icon is visible
            # Tap on the profile icon (usually in the bottom navigation)
            if self.tap_element(driver, "initial_screen", "profile", device_info):
                logger.info("Tapped on profile icon")
                
                # Wait for profile to load
                time.sleep(random.uniform(1, 2))
                
                return {"success": True}
            else:
                return {"success": False, "error": "Could not find profile icon"}
        except Exception as e:
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