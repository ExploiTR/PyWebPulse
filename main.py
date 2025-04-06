import sys
import subprocess
import logging
import importlib.metadata
import os

# Ensure the script directory is in the path if running from elsewhere
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# --- Dependency Check and Installation ---
REQUIRED_PACKAGES = {
    'PyQt6': 'PyQt6',
    'selenium': 'selenium',
    'webdriver-manager': 'webdriver-manager',
    'dnspython': 'dnspython' # Add this line
}


def check_and_install_dependencies():
    """Checks for required packages and attempts to install missing ones using pip."""
    missing_packages = []
    for import_name, install_name in REQUIRED_PACKAGES.items():
        try:
            importlib.metadata.version(install_name)
            print(f"Requirement already satisfied: {install_name}")
        except importlib.metadata.PackageNotFoundError:
            print(f"Requirement not satisfied: {install_name}. Marked for installation.")
            missing_packages.append(install_name)
        except Exception as e:
            print(f"Error checking package {install_name}: {e}. Assuming it needs installation.")
            missing_packages.append(install_name)  # Be safe

    if not missing_packages:
        print("All dependencies are satisfied.")
        return True

    print(f"\nAttempting to install missing packages: {', '.join(missing_packages)}")
    pip_executable = sys.executable.replace('pythonw.exe', 'python.exe')  # Ensure using console python for pip

    # Ensure pip is available and up-to-date (optional but good practice)
    try:
        print("Ensuring pip is up-to-date...")
        subprocess.check_call([pip_executable, "-m", "pip", "install", "--upgrade", "pip"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to upgrade pip. Proceeding with installation anyway. Error: {e}")
    except FileNotFoundError:
        print(
            "Error: Could not find pip executable. Please ensure Python and pip are correctly installed and in your PATH.")
        return False

    # Install missing packages
    for package in missing_packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([pip_executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(
                f"ERROR: Failed to install {package}. Please install it manually (e.g., 'pip install {package}') and restart the application.")
            print(f"Error details: {e}")
            # Ask user to install manually and exit? Or try to continue?
            # For robustness, let's report error and exit if critical deps fail.
            if package in ['PyQt6', 'selenium']:  # Critical dependencies
                return False
        except FileNotFoundError:
            print(f"Error: Could not execute pip command. Is '{pip_executable}' correct and in PATH?")
            return False

    print("\nDependency installation attempt finished.")
    # Optional: Re-verify after installation
    print("Re-verifying dependencies...")
    final_missing = []
    for import_name, install_name in REQUIRED_PACKAGES.items():
        if install_name in missing_packages:  # Only re-check those we tried to install
            try:
                importlib.metadata.version(install_name)
            except importlib.metadata.PackageNotFoundError:
                print(f"Verification failed: {install_name} still not found after installation attempt.")
                final_missing.append(install_name)

    if final_missing:
        print(
            f"ERROR: Failed to install the following critical dependencies: {', '.join(final_missing)}. The application cannot continue.")
        print("Please install them manually and try again.")
        return False

    print("All required dependencies seem to be installed now.")
    return True


# --- Main Application Execution ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        handlers=[logging.FileHandler("benchmark_app.log"), logging.StreamHandler()])

    logging.info("Application starting...")
    print("Checking dependencies...")

    # Change to the script's directory to ensure settings.json is found correctly
    os.chdir(script_dir)
    logging.info(f"Working directory set to: {os.getcwd()}")

    if not check_and_install_dependencies():
        logging.critical("Dependency check/installation failed. Exiting.")
        # Show a simple GUI message box if possible, otherwise print and exit
        try:
            # Try importing PyQt even if check failed, maybe it was just the check?
            from PyQt6.QtWidgets import QApplication, QMessageBox

            # Need to create a dummy app instance to show message box before main loop
            temp_app = QApplication.instance()  # Check if already exists
            if temp_app is None:
                temp_app = QApplication(sys.argv)  # Create QApplication instance for message box

            QMessageBox.critical(None, "Dependency Error",
                                 "Failed to install required packages. Please check the console output (run from terminal if needed), install manually, and restart.")

        except ImportError:
            print("\nCRITICAL ERROR: PyQt6 is missing and installation failed. Cannot show GUI error message.")
            print("Please install dependencies manually (pip install PyQt6 selenium webdriver-manager) and restart.")
        except Exception as e:
            print(f"\nAn unexpected error occurred trying to show the error message: {e}")

        sys.exit(1)  # Exit if dependencies failed

    # Now safe to import GUI elements
    from PyQt6.QtWidgets import QApplication
    from gui import SpeedBenchmarkerApp  # Import after dependency check

    logging.info("Dependencies satisfied. Initializing GUI...")
    app = QApplication(sys.argv)
    main_window = SpeedBenchmarkerApp()
    main_window.show()
    logging.info("GUI displayed. Starting event loop.")
    sys.exit(app.exec())