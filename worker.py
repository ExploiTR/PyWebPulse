import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal
from selenium.common.exceptions import WebDriverException

# Make sure to import setup_driver and measure_load_time
from selenium_utils import setup_driver, measure_load_time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestWorker(QThread):
    progress = pyqtSignal(int, int)
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    dns_results_ready = pyqtSignal(dict)

    def __init__(self, urls, config):
        super().__init__()
        self.urls = urls
        self.config = config # Store the whole config
        # Extract specific config values needed often
        self.runs_per_url = config.get('runs_per_url', 1)
        self.browser = config.get('browser', 'Chrome')
        self.headless = config.get('headless', False)
        self.timeout = config.get('timeout_seconds', 60)
        self.wait_strategy = config.get('wait_strategy', 'Combined')
        # IMPORTANT: Keep anti-detection OFF while debugging this crash
        self.anti_detection = config.get('anti_detection_enabled', False) # Defaulting to False now
        self._is_running = True
        self.driver = None # Driver will be managed inside the loop

    def run(self):
        total_steps = len(self.urls) * self.runs_per_url
        current_step = 0
        # Driver setup is now MOVED INSIDE the URL loop

        # --- Run DNS Benchmark if requested ---
        if self.config.get('run_dns_benchmark', False):
            self.status_update.emit("Running DNS latency benchmark...")
            try:
                # Import the function from dns_utils
                from dns_utils import run_dns_benchmark
                dns_results = run_dns_benchmark()
                self.dns_results_ready.emit(dns_results)  # Emit results
                self.status_update.emit("DNS benchmark finished.")
            except Exception as dns_err:
                logging.exception("Error running DNS benchmark.")
                self.status_update.emit(f"Error during DNS benchmark: {dns_err}")
                # Optionally emit an error result for DNS
                self.dns_results_ready.emit({"Error": {"status": str(dns_err)}})

        # Check if stopped during DNS test
        if not self._is_running:
            self.status_update.emit("Test stopped after DNS benchmark.")
            self.finished.emit()
            return

        # --- Existing Browse Test Loop ---
        self.status_update.emit("Starting Browse speed tests...")

        for url in self.urls:
            if not self._is_running:
                self.status_update.emit("Test stopped by user.")
                break

            # --- Setup driver INSIDE the URL loop ---
            self.driver = None # Ensure driver reference is clear before setup
            try:
                self.status_update.emit(f"Initializing driver for URL: {url}...")
                # Ensure anti_detection is definitely off if checkbox was checked
                current_anti_detection_setting = self.config.get('anti_detection_enabled', False)
                logging.info(f"Driver setup for {url} with anti-detection: {current_anti_detection_setting}")

                self.driver = setup_driver(
                    browser_name=self.browser,
                    headless=self.headless,
                    anti_detection=current_anti_detection_setting # Use current setting
                )
                if not self.driver: # Check if setup_driver potentially returned None
                    raise WebDriverException("setup_driver returned None unexpectedly.")
                self.status_update.emit(f"Driver ready for {url}.")
                logging.info(f"Driver successfully initialized for {url}")

            except Exception as setup_error: # Catch setup errors per URL
                error_msg = f"Fatal Error initializing driver for {url}: {setup_error}"
                logging.exception(f"Driver setup failed for {url}") # Log full traceback
                self.status_update.emit(error_msg)
                self.error_occurred.emit(error_msg) # Can signal GUI about setup failure

                # Mark all runs for this specific URL as failed because driver failed
                for run_num_fail in range(self.runs_per_url):
                     current_step += 1
                     self.progress.emit(current_step, total_steps)
                     error_result = {
                         "url": url,
                         "load_time_ms": -1,
                         "status": "Error",
                         "error_message": f"Driver setup failed: {setup_error}",
                         "timestamp": time.time(),
                         "run_number": run_num_fail + 1,
                         # Include config used for reporting clarity
                         "config": self.config.copy()
                     }
                     self.result_ready.emit(error_result)
                # Skip to the next URL since driver setup failed
                continue # Important!

            # --- Run tests for the current URL ---
            self.status_update.emit(f"Testing URL: {url} ({self.runs_per_url} runs)")
            for run in range(self.runs_per_url):
                if not self._is_running:
                    logging.info(f"Stopping inner loop for {url} due to user request.")
                    break # Break inner loop (runs)

                current_step += 1
                self.progress.emit(current_step, total_steps)
                self.status_update.emit(f"Running test {run + 1}/{self.runs_per_url} for {url}...")
                logging.info(f"Starting measure_load_time for {url}, run {run + 1}")

                measurement_result = measure_load_time(
                    self.driver, url, self.timeout, self.wait_strategy
                )
                measurement_result['run_number'] = run + 1
                measurement_result['config'] = self.config.copy() # Add config used

                logging.info(f"Finished measure_load_time for {url}, run {run + 1}. Status: {measurement_result['status']}")

                if not self._is_running: # Check again before emitting result
                    logging.info(f"Skipping result emission for {url} run {run + 1} due to stop request.")
                    break
                self.result_ready.emit(measurement_result)

                # Reset browser state after each run
                try:
                    self.driver.get("about:blank")
                    self.driver.delete_all_cookies()
                    self.driver.execute_cdp_cmd('Storage.clearDataForOrigin', {'origin': '*', 'storageTypes': 'all'})
                except Exception as reset_error:
                    logging.warning(f"Error resetting browser state: {reset_error}")

                # Add a small delay between runs might help stabilize things? (Optional)
                #time.sleep(0.5)

            # --- Quit driver AFTER all runs for the current URL ---
            if self.driver:
                try:
                    logging.info(f"Quitting driver for URL: {url}")
                    self.driver.quit()
                    self.status_update.emit(f"Browser driver closed for {url}.")
                    logging.info(f"Driver quit successfully for {url}.")
                except Exception as quit_error:
                    self.status_update.emit(f"Warning: Error quitting driver for {url}: {quit_error}")
                    logging.warning(f"Error quitting driver: {quit_error}")
            self.driver = None # Explicitly clear reference after quitting

            if not self._is_running: # Check if outer loop should break
                 logging.info(f"Stopping outer loop after {url} due to user request.")
                 break

        # Final driver quit is REMOVED as it's handled per URL
        logging.info("Worker thread run method finished.")
        if self._is_running: # Only emit finished normally if not stopped early
            self.status_update.emit("Testing finished.")
        self.finished.emit()

    def stop(self):
        """Signals the worker thread to stop gracefully."""
        logging.info("Stop requested for worker thread.")
        self.status_update.emit("Stopping test...")
        self._is_running = False
        # Note: If a measure_load_time is in progress, it will likely complete.
        # The check happens before the *next* run or *next* URL.