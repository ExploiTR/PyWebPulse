import json
import os
import logging

SETTINGS_FILE = 'settings.json'
DEFAULT_SETTINGS = {
  "urls": [
    "https://www.google.com",
    "https://www.wikipedia.org",
    "https://github.com"
  ],
  "runs_per_url": 3,
  "browser": "Chrome", # Options: Chrome, Firefox
  "headless": False,
  "timeout_seconds": 60,
   # Options: ReadyState, LoadEventEnd, Combined
  "wait_strategy": "Combined",
  "anti_detection_enabled": True,
  "export_format": "CSV", # Options: CSV, JSON
  "results": [] # Stores past results if needed, or keep empty
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_settings():
    """Loads settings from SETTINGS_FILE, using defaults if file not found or invalid."""
    if not os.path.exists(SETTINGS_FILE):
        logging.warning(f"{SETTINGS_FILE} not found. Creating with default settings.")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Ensure all default keys exist
            updated = False
            for key, value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
                    updated = True
            if updated:
                save_settings(settings) # Save back if keys were missing
            return settings
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading {SETTINGS_FILE}: {e}. Using default settings.")
        # Optionally backup the corrupted file here
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Saves the given settings dictionary to SETTINGS_FILE."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        logging.info(f"Settings saved to {SETTINGS_FILE}")
    except IOError as e:
        logging.error(f"Error saving settings to {SETTINGS_FILE}: {e}")

# Example usage (optional, for testing)
if __name__ == '__main__':
    settings = load_settings()
    print("Loaded settings:", settings)
    settings['runs_per_url'] = 5 # Modify a setting
    save_settings(settings)
    print("Settings saved.")