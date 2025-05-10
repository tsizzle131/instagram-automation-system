#!/usr/bin/env python3
import os
import shutil
import sys
import json

def setup_ui_map():
    # Get the absolute path of the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the source Instagram UI map
    source_map_path = os.path.join(os.path.dirname(project_root), 'instagram map')
    
    # Target path in the project root
    target_map_path = os.path.join(project_root, 'instagram_map.json')
    
    # If target already exists, we don't need to copy
    if os.path.exists(target_map_path):
        try:
            # Verify the existing UI map is valid JSON
            with open(target_map_path, 'r') as f:
                json.load(f)
            print(f"Using existing UI map at: {target_map_path}")
            return True
        except json.JSONDecodeError:
            # If it's invalid JSON, we'll try to replace it
            print(f"Existing UI map is invalid JSON, attempting to replace it.")
    
    print(f"Checking for Instagram UI map at: {source_map_path}")
    
    if not os.path.exists(source_map_path):
        print("Warning: Instagram UI map not found in parent directory")
        print("Using built-in sample UI map")
        
        # Create a simple sample UI map
        sample_ui_map = {
            "initial_screen": {
                "home": {
                    "name": "home",
                    "label": "Home feed",
                    "x": 0.1,
                    "y": 0.95
                },
                "search": {
                    "name": "search",
                    "label": "Search",
                    "x": 0.3,
                    "y": 0.95
                },
                "add": {
                    "name": "add",
                    "label": "Create",
                    "x": 0.5,
                    "y": 0.95
                },
                "reels": {
                    "name": "reels",
                    "label": "Reels",
                    "x": 0.7,
                    "y": 0.95
                },
                "profile": {
                    "name": "profile",
                    "label": "Profile",
                    "x": 0.9,
                    "y": 0.95
                }
            },
            "profile_screen": {
                "followers": {
                    "name": "followers",
                    "label": "Followers",
                    "x": 0.35,
                    "y": 0.25
                },
                "following": {
                    "name": "following",
                    "label": "Following",
                    "x": 0.65,
                    "y": 0.25
                }
            }
        }
        
        # Write the sample UI map to the target location
        with open(target_map_path, 'w') as f:
            json.dump(sample_ui_map, f, indent=2)
            
        print(f"Sample UI map created at: {target_map_path}")
        return True
    
    try:
        # Try to read the map file and parse it
        try:
            with open(source_map_path, 'r') as f:
                ui_map = json.load(f)
            
            # If successful, write to target location
            with open(target_map_path, 'w') as f:
                json.dump(ui_map, f, indent=2)
                
            print(f"Instagram UI map copied and validated at: {target_map_path}")
            return True
        except json.JSONDecodeError as e:
            print(f"Error: Source UI map is not valid JSON: {e}")
            print("Creating a simple sample UI map instead.")
            
            # Create a simple sample UI map
            sample_ui_map = {
                "initial_screen": {
                    "home": {"name": "home", "label": "Home feed", "x": 0.1, "y": 0.95},
                    "profile": {"name": "profile", "label": "Profile", "x": 0.9, "y": 0.95}
                }
            }
            
            # Write the sample UI map to the target location
            with open(target_map_path, 'w') as f:
                json.dump(sample_ui_map, f, indent=2)
                
            print(f"Sample UI map created at: {target_map_path}")
            return True
            
    except Exception as e:
        print(f"Error setting up UI map: {e}")
        return False

if __name__ == "__main__":
    result = setup_ui_map()
    sys.exit(0 if result else 1) 