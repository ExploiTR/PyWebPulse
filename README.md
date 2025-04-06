# Browse Speed Benchmarker (PyWebPulse)

A Python GUI application built with PyQt6 and Selenium to benchmark website load times and analyze Browse speed performance. It provides detailed metrics, configurable test parameters, and reporting capabilities.

**Note:** The initial code structure and significant portions of this application were generated with the assistance of Google's Gemini AI based on user specifications and refined through iterative discussion.

## Features

* **Graphical User Interface:** Easy-to-use interface built with PyQt6.
* **Multi-URL Testing:** Benchmark one or multiple websites sequentially.
* **Configurable Test Runs:** Set the number of times each URL should be tested.
* **Browser Selection:** Supports testing with Google Chrome and Mozilla Firefox.
* **Headless Mode:** Option to run browser tests without displaying the browser window.
* **Flexible Wait Strategies:** Choose how page load completion is determined (`Combined`, `ReadyState`, `LoadEventEnd`).
* **Basic Anti-Detection:** Optional measures to make Selenium less detectable (effectiveness varies).
* **Detailed Timing Metrics:** Captures data from the Navigation Timing API (TTFB, DOM Load, Full Load, DNS Lookup Time, etc.).
* **Real-time Results:** View test results as they come in within a results table.
* **Background Testing:** Selenium tests run in a separate thread to keep the GUI responsive.
* **Persistent Configuration:** Saves your URLs and settings in `settings.json`.
* **Automatic Dependency Installation:** Attempts to install required Python packages on the first run.
* **Automatic WebDriver Management:** Uses `webdriver-manager` to download and manage appropriate browser drivers.
* **Exportable Reports:**
    * Export summarized results (Avg, Median, Min, Max per URL) to **CSV**.
    * Export detailed raw results, summary, and configuration to **JSON**.
* **DNS Latency Benchmark (Optional):** Test DNS lookup latency against your system's DNS and standard public DNS servers (Google, Cloudflare, etc.) using `dnspython`.

## Technology Stack

* **Language:** Python 3.x
* **GUI Framework:** PyQt6
* **Browser Automation:** Selenium
* **WebDriver Management:** webdriver-manager
* **DNS Testing:** dnspython

## Prerequisites

* **Python:** Python 3.8 or higher recommended.
* **Pip:** Python package installer (usually comes with Python).
* **Browsers:** Google Chrome and/or Mozilla Firefox installed.
* **Internet Connection:** Required for downloading dependencies, drivers, and accessing websites.

## Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd speed-benchmark
    ```
    (Or download the source code ZIP and extract it.)

2.  **Run the Application:**
    ```bash
    python main.py
    ```

3.  **Automatic Dependency Installation:**
    * On the first run, the script will check for required Python packages (`PyQt6`, `selenium`, `webdriver-manager`, `dnspython`).
    * If any are missing, it will attempt to install them automatically using `pip`.
    * You might need administrator privileges if your Python installation is system-wide. Using a Python virtual environment is recommended (`python -m venv venv`, `source venv/bin/activate` or `venv\Scripts\activate`).

4.  **Automatic WebDriver Download:**
    * When you start a test for the first time with a specific browser (e.g., Chrome), the application will use `webdriver-manager` to automatically download the correct ChromeDriver (or GeckoDriver for Firefox) executable and cache it (usually in `~/.wdm/` or `C:\Users\<User>\.wdm\`).

## How to Use

1.  **Launch:** Run `python main.py`.
2.  **Add URLs:** Enter a full URL (including `http://` or `https://`) in the top input field and click "Add URL" or press Enter. Repeat for all desired URLs.
3.  **Configure Test:**
    * Adjust "Runs per URL".
    * Select "Browser" (Chrome/Firefox).
    * Check/uncheck "Run Headless".
    * Check/uncheck "Enable Anti-Detection" (disable if causing issues).
    * Set "Page Load Timeout".
    * Choose a "Wait Strategy".
    * Check/uncheck "Run DNS Latency Benchmark".
4.  **Start Test:** Click the "Start Test" button.
5.  **Monitor:** Observe the progress bar, status messages at the bottom, the results table filling up, and the detailed log area. If DNS benchmark is enabled, results will appear in the DNS section.
6.  **Stop Test:** Click "Stop Test" to gracefully halt the current testing process (it might finish the currently running step).
7.  **Export:** Once the test is finished (or stopped), click "Export Report". Choose a file name and format (CSV for summary, JSON for detailed).
8.  **Clear:** Click "Clear Results" to clear the results table, log area, and DNS results display.
9.  **Settings:** Configuration is automatically saved to `settings.json` when starting a test or closing the application.

## Configuration (`settings.json`)

This file stores the list of URLs and your last used configuration settings. You can manually edit it (e.g., to pre-populate URLs) but be careful with the format. The application loads this on startup and saves it on exit/test start.

## Troubleshooting & Notes

* **First Run vs Subsequent Runs:** Expect the first load time for a URL to often be higher than subsequent runs due to various caching layers (DNS, connection reuse, HTTP cache, server-side cache). Analyze the detailed Navigation Timing data in the JSON export or logs to see where time differences occur. Trying aggressive cache-disabling options (see `selenium_utils.py`) might help but isn't foolproof.
* **Anti-Detection:** The implemented anti-detection methods are basic and may not bypass detection on sophisticated websites. If you encounter issues or crashes, try running tests with this option disabled.
* **WebDriver Errors:**
    * Ensure Chrome/Firefox is installed correctly.
    * If tests fail immediately with driver errors, try deleting the driver cache (`~/.wdm/` or `C:\Users\<User>\.wdm\`) and let the application redownload it.
    * Ensure you have permissions to download and execute the drivers.
    * Rarely, browser auto-updates might temporarily break compatibility before `webdriver-manager` updates.
* **Crashes (`0xC0000409` etc.):** Stability issues can sometimes occur due to interactions between Selenium, the WebDriver, the browser version, and specific website behavior. If crashes persist:
    * Ensure "Enable Anti-Detection" is OFF.
    * Try the other browser (Firefox if Chrome crashes, or vice-versa).
    * Ensure your browser and the downloaded driver versions are compatible.

## Contributing

Contributions, issues, and feature requests are welcome! Please feel free to submit them via GitHub Issues or Pull Requests.

## License

This project is licensed under the Unlicense - see the `LICENSE` file for details (or choose another license if you prefer).

## Acknowledgements

* This application's initial structure and features were developed with assistance from Google's Gemini AI.
* Uses the powerful Selenium library for browser automation.
* Relies on PyQt6 for the graphical user interface.
* Leverages webdriver-manager for easy driver handling.
* Employs dnspython for DNS latency testing.
