import time
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# Use Navigation Timing API for detailed metrics
# https://developer.mozilla.org/en-US/docs/Web/API/Navigation_Timing_API
JS_NAVIGATION_TIMING = "return window.performance.timing.toJSON()"
JS_READY_STATE = "return document.readyState"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver(browser_name="Chrome", headless=False, anti_detection=True):
    """Sets up and returns a Selenium WebDriver instance."""
    driver = None
    options = None
    service = None

    try:
        if browser_name.lower() == "chrome":
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080") # Recommended for headless
            options.add_argument("--disable-gpu") # Often needed for headless
            options.add_argument("--no-sandbox") # Often needed in containerized/linux envs
            options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems

            # Aggressive Cache Disabling Attempts
            options.add_argument('--disable-application-cache')
            options.add_argument('--disk-cache-size=1')  # Set very small size
            options.add_argument('--media-cache-size=1')  # Set very small size

            if anti_detection:
                # Standard Selenium anti-detection options
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument('--disable-blink-features=AutomationControlled')
                # Spoof user agent (replace with a common one if needed)
                # options.add_argument("user-agent=Mozilla/5.0...")

            logging.info("Setting up ChromeDriver...")
            try:
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                logging.error(f"Failed to install/start ChromeDriver via webdriver-manager: {e}")
                # Fallback or specific path might be needed depending on system
                raise WebDriverException(f"ChromeDriver setup failed: {e}") from e

            # In selenium_utils.py -> setup_driver, inside the 'chrome' block
            # logging.info("Setting up ChromeDriver using manual path...")
            # try:
            #     # Replace with the actual path where you saved chromedriver.exe
            #     driver_path = "D:/Softwares/Developing/chrome_driver/chrome-win64/chrome.exe"
            #     service = ChromeService(executable_path=driver_path)
            #     driver = webdriver.Chrome(service=service, options=options)
            # except Exception as e:
            #     logging.error(f"Failed to start ChromeDriver from manual path: {e}")
            #     raise WebDriverException(f"ChromeDriver manual setup failed: {e}") from e

            if anti_detection:
                 # Evade webdriver detection script
                 driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                     "source": """
                         Object.defineProperty(navigator, 'webdriver', {
                           get: () => undefined
                         })
                       """
                 })

        elif browser_name.lower() == "firefox":
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")

            # Aggressive Cache Disabling Attempts
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
            options.set_preference("browser.cache.offline.enable", False)
            options.set_preference("network.http.use-cache", False)

            if anti_detection:
                 # Firefox equivalent options
                 options.set_preference("dom.webdriver.enabled", False)
                 options.set_preference('useAutomationExtension', False)
                 # Update user agent if needed
                 # options.set_preference("general.useragent.override", "Mozilla/5.0...")


            logging.info("Setting up GeckoDriver (Firefox)...")
            try:
                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=options)
            except Exception as e:
                 logging.error(f"Failed to install/start GeckoDriver via webdriver-manager: {e}")
                 raise WebDriverException(f"GeckoDriver setup failed: {e}") from e

            # Firefox doesn't have CDP like Chrome for easy script injection on new doc
            # Anti-detection might be less effective or require different techniques


        else:
            raise ValueError(f"Unsupported browser: {browser_name}")

        if driver and anti_detection and browser_name.lower() == "chrome": # Redundant check for safety
             # Additional CDP commands can be added here if needed
             pass

        logging.info(f"{browser_name} driver initialized {'(Headless)' if headless else ''} {'(Anti-detection enabled)' if anti_detection else ''}.")
        return driver

    except WebDriverException as e:
        logging.error(f"WebDriver setup failed: {e}")
        if driver:
            driver.quit()
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during driver setup: {e}")
        if driver:
            driver.quit()
        raise WebDriverException(f"Unexpected driver setup error: {e}") from e


def measure_load_time(driver, url, timeout, wait_strategy):
    """Navigates to URL and measures load time using the specified strategy."""
    results = {
        "url": url,
        "load_time_ms": -1,
        "status": "Error",
        "error_message": None,
        "navigation_timing": None,
        "timestamp": time.time()
    }
    start_time = time.perf_counter()

    try:
        driver.get(url)
        wait = WebDriverWait(driver, timeout)

        load_event_end_time = 0
        dom_complete_time = 0

        # --- Wait Strategy ---
        if wait_strategy == "ReadyState":
            # Wait only for document.readyState == 'complete'
            wait.until(lambda d: d.execute_script(JS_READY_STATE) == 'complete')

        elif wait_strategy == "LoadEventEnd":
            # Wait for loadEventEnd > 0 in Navigation Timing API
            # This often corresponds closely to the browser's load indicator stopping
            wait.until(lambda d: d.execute_script("return window.performance.timing.loadEventEnd") > 0)

        elif wait_strategy == "Combined":
             # Wait for readyState == 'complete' first (usually faster)
            wait.until(lambda d: d.execute_script(JS_READY_STATE) == 'complete')
            # Then, explicitly wait a bit longer or check loadEventEnd for robustness
            # Option A: Check loadEventEnd as well (more reliable if available)
            wait.until(lambda d: d.execute_script("return window.performance.timing.loadEventEnd") > 0)
            # Option B: Add a small fixed delay (heuristic, less reliable)
            # time.sleep(1) # Wait 1 extra second for async JS

        else:
            raise ValueError(f"Invalid wait_strategy: {wait_strategy}")

        end_time = time.perf_counter()
        results["load_time_ms"] = (end_time - start_time) * 1000
        results["status"] = "Success"

        # --- Get Detailed Timing ---
        try:
            timing_data = driver.execute_script(JS_NAVIGATION_TIMING)
            if timing_data:
                # Calculate meaningful metrics if navigationStart exists
                nav_start = timing_data.get('navigationStart', 0)
                if nav_start > 0:
                    results["navigation_timing"] = {
                        "navigation_start": nav_start,
                        "fetch_start": timing_data.get('fetchStart', 0),
                        "dns_lookup_time": timing_data.get('domainLookupEnd', 0) - timing_data.get('domainLookupStart', 0),
                        "connect_time": timing_data.get('connectEnd', 0) - timing_data.get('connectStart', 0),
                        "ttfb": timing_data.get('responseStart', 0) - timing_data.get('requestStart', 0), # Time To First Byte
                        "dom_interactive": timing_data.get('domInteractive', 0),
                        "dom_content_loaded": timing_data.get('domContentLoadedEventEnd', 0),
                        "dom_complete": timing_data.get('domComplete', 0),
                        "load_event_start": timing_data.get('loadEventStart', 0),
                        "load_event_end": timing_data.get('loadEventEnd', 0),
                         # Derived metrics relative to navigationStart
                        "total_load_from_nav_start": timing_data.get('loadEventEnd', 0) - nav_start if timing_data.get('loadEventEnd', 0) else -1,
                        "dom_processing_time": timing_data.get('domComplete', 0) - timing_data.get('domInteractive', 0) if timing_data.get('domInteractive', 0) and timing_data.get('domComplete', 0) else -1,
                    }
        except Exception as e:
            logging.warning(f"Could not retrieve Navigation Timing API data for {url}: {e}")
            results["navigation_timing"] = {"error": str(e)}


    except TimeoutException:
        results["status"] = "Error"
        results["error_message"] = f"Timeout after {timeout} seconds waiting for page load ({wait_strategy} strategy)."
        logging.warning(f"Timeout loading {url}")
    except WebDriverException as e:
        results["status"] = "Error"
        results["error_message"] = f"WebDriver error: {e}"
        logging.error(f"WebDriver error loading {url}: {e}")
        # Re-raise critical errors if needed, or just log them
    except Exception as e:
        results["status"] = "Error"
        results["error_message"] = f"Unexpected error: {e}"
        logging.error(f"Unexpected error loading {url}: {e}")

    finally:
        # Ensure load time is recorded even on timeout/error, reflects time until failure
        if results["load_time_ms"] < 0 and results["status"] == "Error":
             end_time = time.perf_counter()
             results["load_time_ms"] = (end_time - start_time) * 1000 # Time spent until error

    return results