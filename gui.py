import sys
import csv
import json
import logging
import time
from datetime import datetime
import statistics # For median calculation

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QSpinBox, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QStatusBar, QMessageBox, QFileDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSlot

from settings_manager import load_settings, save_settings
from worker import TestWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SpeedBenchmarkerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.test_worker = None
        self.results_data = [] # Store detailed results from worker

        self.setWindowTitle("Browse Speed Benchmarker")
        self.setGeometry(100, 100, 900, 700) # x, y, width, height

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Section: URL Management ---
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL (e.g., https://example.com) and press Enter or Add")
        self.url_input.returnPressed.connect(self.add_url)
        add_url_button = QPushButton("Add URL")
        add_url_button.clicked.connect(self.add_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(add_url_button)
        main_layout.addLayout(url_layout)

        self.url_list_widget = QListWidget()
        self.url_list_widget.addItems(self.settings.get('urls', []))
        main_layout.addWidget(QLabel("URLs to Test:"))
        main_layout.addWidget(self.url_list_widget)

        url_buttons_layout = QHBoxLayout()
        remove_url_button = QPushButton("Remove Selected URL")
        remove_url_button.clicked.connect(self.remove_url)
        clear_urls_button = QPushButton("Clear All URLs")
        clear_urls_button.clicked.connect(self.clear_urls)
        url_buttons_layout.addWidget(remove_url_button)
        url_buttons_layout.addWidget(clear_urls_button)
        url_buttons_layout.addStretch()
        main_layout.addLayout(url_buttons_layout)

        # --- Middle Section: Config & Results ---
        middle_layout = QHBoxLayout()

        # Config Panel
        config_layout = QVBoxLayout()
        config_layout.addWidget(QLabel("Configuration:"))

        # Runs per URL
        runs_layout = QHBoxLayout()
        runs_layout.addWidget(QLabel("Runs per URL:"))
        self.runs_spinbox = QSpinBox()
        self.runs_spinbox.setMinimum(1)
        self.runs_spinbox.setValue(self.settings.get('runs_per_url', 3))
        runs_layout.addWidget(self.runs_spinbox)
        config_layout.addLayout(runs_layout)

        # Browser Selection
        browser_layout = QHBoxLayout()
        browser_layout.addWidget(QLabel("Browser:"))
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome", "Firefox"])
        self.browser_combo.setCurrentText(self.settings.get('browser', 'Chrome'))
        browser_layout.addWidget(self.browser_combo)
        config_layout.addLayout(browser_layout)

        # Headless Mode
        self.headless_checkbox = QCheckBox("Run Headless")
        self.headless_checkbox.setChecked(self.settings.get('headless', False))
        config_layout.addWidget(self.headless_checkbox)

        # Anti-Detection
        self.anti_detect_checkbox = QCheckBox("Enable Anti-Detection")
        self.anti_detect_checkbox.setChecked(self.settings.get('anti_detection_enabled', True))
        config_layout.addWidget(self.anti_detect_checkbox)

        # DNS Latency
        self.dns_test_checkbox = QCheckBox("Run DNS Latency Benchmark (Before Tests)")
        self.dns_test_checkbox.setChecked(False)  # Default off
        config_layout.addWidget(self.dns_test_checkbox)  # Add to config layout

        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Page Load Timeout (s):"))
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setMinimum(10)
        self.timeout_spinbox.setMaximum(300)
        self.timeout_spinbox.setValue(self.settings.get('timeout_seconds', 60))
        timeout_layout.addWidget(self.timeout_spinbox)
        config_layout.addLayout(timeout_layout)

        # Wait Strategy
        wait_layout = QHBoxLayout()
        wait_layout.addWidget(QLabel("Wait Strategy:"))
        self.wait_combo = QComboBox()
        self.wait_combo.addItems(["Combined", "ReadyState", "LoadEventEnd"]) # Order matters for default
        self.wait_combo.setCurrentText(self.settings.get('wait_strategy', 'Combined'))
        wait_layout.addWidget(self.wait_combo)
        config_layout.addLayout(wait_layout)

        config_layout.addStretch() # Push controls to top
        config_widget = QWidget()
        config_widget.setLayout(config_layout)
        middle_layout.addWidget(config_widget)

        # Results Panel
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("Results:"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6) # URL, Run, Load Time (ms), Status, Details, Timestamp
        self.results_table.setHorizontalHeaderLabels(["URL", "Run", "Load Time (ms)", "Status", "Details/Error", "Timestamp"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Read-only
        results_layout.addWidget(self.results_table)

        # DNS Result
        results_layout.addWidget(QLabel("DNS Benchmark Results:"))
        self.dns_results_area = QTextEdit()
        self.dns_results_area.setReadOnly(True)
        self.dns_results_area.setFixedHeight(100)
        results_layout.addWidget(self.dns_results_area)

        # Log/Details Area (Optional but helpful)
        results_layout.addWidget(QLabel("Run Log / Detailed Timing:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(100) # Limit height initially
        results_layout.addWidget(self.log_area)

        middle_layout.addLayout(results_layout)
        middle_layout.setStretch(1, 3) # Give results area more space

        main_layout.addLayout(middle_layout)

        # --- Bottom Section: Controls & Status ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.start_button.clicked.connect(self.start_test)
        self.stop_button = QPushButton("Stop Test")
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        self.clear_results_button = QPushButton("Clear Results")
        self.clear_results_button.clicked.connect(self.clear_results_display)
        self.export_button = QPushButton("Export Report")
        self.export_button.clicked.connect(self.export_report)

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.clear_results_button)
        controls_layout.addWidget(self.export_button)
        main_layout.addLayout(controls_layout)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Load settings or configure test.")

    # --- URL List Management ---
    def add_url(self):
        url = self.url_input.text().strip()
        if url and url.startswith(('http://', 'https://')):
            # Avoid duplicates
            items = [self.url_list_widget.item(i).text() for i in range(self.url_list_widget.count())]
            if url not in items:
                self.url_list_widget.addItem(url)
                self.url_input.clear()
            else:
                self.status_bar.showMessage("URL already in the list.", 3000)
        elif url:
            QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
        self.url_input.clear() # Clear even if invalid or empty

    def remove_url(self):
        selected_items = self.url_list_widget.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("Select a URL to remove.", 3000)
            return
        for item in selected_items:
            self.url_list_widget.takeItem(self.url_list_widget.row(item))

    def clear_urls(self):
        self.url_list_widget.clear()

    # --- Test Execution Control ---
    def update_config_from_ui(self):
        """Reads UI settings and updates the self.settings dictionary."""
        self.settings['urls'] = [self.url_list_widget.item(i).text() for i in range(self.url_list_widget.count())]
        self.settings['runs_per_url'] = self.runs_spinbox.value()
        self.settings['browser'] = self.browser_combo.currentText()
        self.settings['headless'] = self.headless_checkbox.isChecked()
        self.settings['anti_detection_enabled'] = self.anti_detect_checkbox.isChecked()
        self.settings['timeout_seconds'] = self.timeout_spinbox.value()
        self.settings['wait_strategy'] = self.wait_combo.currentText()
        self.settings['run_dns_benchmark'] = self.dns_test_checkbox.isChecked()
        # Save updated settings automatically or provide a save button
        save_settings(self.settings)


    def start_test(self):
        self.update_config_from_ui() # Get latest settings from UI
        urls_to_test = self.settings.get('urls', [])

        if not urls_to_test:
            QMessageBox.warning(self, "No URLs", "Please add at least one URL to test.")
            return

        if self.test_worker and self.test_worker.isRunning():
             QMessageBox.warning(self, "Test Running", "A test is already in progress.")
             return

        # Clear previous results before starting
        self.clear_results_display()
        self.results_data = [] # Clear internal data too

        self.status_bar.showMessage("Starting test...")
        self.progress_bar.setValue(0)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.set_config_enabled(False) # Disable config widgets during test

        # Create and start the worker thread
        self.test_worker = TestWorker(urls_to_test, self.settings)
        self.test_worker.progress.connect(self.update_progress)
        self.test_worker.status_update.connect(self.update_status)
        self.test_worker.result_ready.connect(self.handle_result)
        self.test_worker.finished.connect(self.test_finished)
        self.test_worker.error_occurred.connect(self.handle_worker_error)
        self.test_worker.dns_results_ready.connect(self.handle_dns_results)  # Connect new signal
        self.test_worker.start()
        self.test_worker.start()

    def stop_test(self):
        if self.test_worker and self.test_worker.isRunning():
            self.status_bar.showMessage("Attempting to stop test gracefully...")
            self.test_worker.stop()
            self.stop_button.setEnabled(False) # Disable stop button once clicked
            # GUI will be re-enabled fully in test_finished slot
        else:
             self.status_bar.showMessage("No test is currently running.", 3000)


    def set_config_enabled(self, enabled):
        """Enable/disable configuration widgets."""
        self.url_input.setEnabled(enabled)
        self.url_list_widget.setEnabled(enabled)
        # Find buttons related to URL list and enable/disable them
        for button in self.findChildren(QPushButton):
             if button.text() in ["Add URL", "Remove Selected URL", "Clear All URLs"]:
                 button.setEnabled(enabled)
        self.runs_spinbox.setEnabled(enabled)
        self.browser_combo.setEnabled(enabled)
        self.headless_checkbox.setEnabled(enabled)
        self.anti_detect_checkbox.setEnabled(enabled)
        self.timeout_spinbox.setEnabled(enabled)
        self.wait_combo.setEnabled(enabled)
        self.dns_test_checkbox.setEnabled(enabled)
        self.clear_results_button.setEnabled(enabled)
        # Start button is handled separately
        # Export button is enabled only after test finishes


    # --- Worker Signal Slots ---
    @pyqtSlot(int, int)
    def update_progress(self, current_step, total_steps):
        if total_steps > 0:
            percentage = int((current_step / total_steps) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"%p% ({current_step}/{total_steps})")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Waiting...")


    @pyqtSlot(str)
    def update_status(self, message):
        self.status_bar.showMessage(message)
        self.log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}") # Also log status

    # Add this method to SpeedBenchmarkerApp class
    @pyqtSlot(dict)
    def handle_dns_results(self, dns_results):
        self.dns_results_area.clear()
        self.dns_results_area.append("--- DNS Latency Test ---")
        for server, result in dns_results.items():
            if result['status'] == 'Success':
                self.dns_results_area.append(f"- {server}: {result['latency_ms']:.2f} ms")
            else:
                self.dns_results_area.append(f"- {server}: {result['status']}")
        self.dns_results_area.append("------------------------")

    @pyqtSlot(dict)
    def handle_result(self, result):
        """Receives a result dictionary from the worker and updates the table."""
        self.results_data.append(result) # Store raw data

        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)

        load_time_str = f"{result['load_time_ms']:.2f}" if result['load_time_ms'] >= 0 else "N/A"
        status_str = result.get('status', 'Unknown')
        details_str = result.get('error_message', '') if status_str == 'Error' else 'OK'
        timestamp_str = datetime.fromtimestamp(result.get('timestamp', time.time())).strftime('%Y-%m-%d %H:%M:%S')
        run_num_str = str(result.get('run_number', '-'))

        self.results_table.setItem(row_position, 0, QTableWidgetItem(result['url']))
        self.results_table.setItem(row_position, 1, QTableWidgetItem(run_num_str))
        self.results_table.setItem(row_position, 2, QTableWidgetItem(load_time_str))
        self.results_table.setItem(row_position, 3, QTableWidgetItem(status_str))
        self.results_table.setItem(row_position, 4, QTableWidgetItem(details_str))
        self.results_table.setItem(row_position, 5, QTableWidgetItem(timestamp_str))

        # Optionally log detailed timing if available
        if result.get('navigation_timing') and status_str == 'Success':
             timing = result['navigation_timing']
             # Format timing nicely
             timing_details = f"Timing for {result['url']} (Run {run_num_str}): "
             timing_details += f"TTFB: {timing.get('ttfb', 'N/A')}ms | "
             timing_details += f"DOM Load: {timing.get('dom_content_loaded', 'N/A') - timing.get('navigation_start', 0)}ms | "
             timing_details += f"Full Load: {timing.get('total_load_from_nav_start', 'N/A')}ms"
             self.log_area.append(timing_details)

        self.results_table.resizeColumnsToContents()


    @pyqtSlot()
    def test_finished(self):
        if self.test_worker and not self.test_worker._is_running : # Check if stopped by user
             self.status_bar.showMessage("Test stopped by user.", 5000)
        else:
             self.status_bar.showMessage("Test finished.", 5000)
             self.progress_bar.setValue(100)
             self.progress_bar.setFormat("Completed")

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(len(self.results_data) > 0) # Enable export if there are results
        self.set_config_enabled(True) # Re-enable config widgets
        self.test_worker = None # Clear worker reference


    @pyqtSlot(str)
    def handle_worker_error(self, error_message):
         """Handles critical errors reported by the worker (e.g., driver setup)."""
         QMessageBox.critical(self, "Worker Error", f"A critical error occurred:\n{error_message}\n\nPlease check logs and ensure drivers are correctly installed or accessible.")
         # GUI is typically re-enabled by the finished signal which should still emit
         self.log_area.append(f"[ERROR] {error_message}")


    # --- Results Management ---
    def clear_results_display(self):
        self.results_table.setRowCount(0) # Clear table contents
        self.log_area.clear()
        self.dns_results_area.clear()
        self.results_data = [] # Clear internal data storage
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.status_bar.showMessage("Results cleared.", 3000)
        self.export_button.setEnabled(False)


    # --- Reporting ---
    def generate_summary_report(self):
        """Analyzes results_data and generates summary statistics."""
        summary = {}
        if not self.results_data:
            return summary

        urls = sorted(list(set(r['url'] for r in self.results_data)))

        for url in urls:
            url_results = [r for r in self.results_data if r['url'] == url and r['status'] == 'Success']
            url_errors = [r for r in self.results_data if r['url'] == url and r['status'] == 'Error']

            load_times = [r['load_time_ms'] for r in url_results if r['load_time_ms'] >= 0]

            if load_times:
                summary[url] = {
                    'url': url,
                    'num_successful_runs': len(load_times),
                    'num_errors': len(url_errors),
                    'avg_load_time_ms': round(statistics.mean(load_times), 2),
                    'min_load_time_ms': round(min(load_times), 2),
                    'max_load_time_ms': round(max(load_times), 2),
                    'median_load_time_ms': round(statistics.median(load_times), 2),
                    'std_dev_load_time_ms': round(statistics.stdev(load_times), 2) if len(load_times) > 1 else 0.0,
                    'error_messages': [e.get('error_message', 'Unknown Error') for e in url_errors]
                }
            else:
                 summary[url] = {
                    'url': url,
                    'num_successful_runs': 0,
                    'num_errors': len(url_errors),
                    'avg_load_time_ms': 'N/A',
                    'min_load_time_ms': 'N/A',
                    'max_load_time_ms': 'N/A',
                    'median_load_time_ms': 'N/A',
                    'std_dev_load_time_ms': 'N/A',
                    'error_messages': [e.get('error_message', 'Unknown Error') for e in url_errors]
                 }
        return summary


    def export_report(self):
        if not self.results_data:
            QMessageBox.information(self, "No Results", "No results to export.")
            return

        default_filename = f"Browse_speed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_filter = "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        # Determine preferred format from settings maybe?
        # preferred_suffix = ".csv" if self.settings.get('export_format', 'CSV').upper() == 'CSV' else ".json"

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            default_filename,
            file_filter
        )

        if not filename:
            return # User cancelled

        export_format = "CSV" # Default
        if "JSON" in selected_filter:
             export_format = "JSON"
             if not filename.lower().endswith(".json"):
                 filename += ".json"
        elif "CSV" in selected_filter:
             export_format = "CSV"
             if not filename.lower().endswith(".csv"):
                 filename += ".csv"
        # Add other formats if needed


        try:
            if export_format == "CSV":
                # Option 1: Export raw results
                # Option 2: Export summary report (more useful)
                summary = self.generate_summary_report()
                if not summary:
                     QMessageBox.warning(self, "Export Error", "Could not generate summary report.")
                     return

                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    # Define headers based on summary keys, ensuring consistent order
                    fieldnames = [
                        'url', 'num_successful_runs', 'num_errors',
                        'avg_load_time_ms', 'median_load_time_ms',
                        'min_load_time_ms', 'max_load_time_ms',
                        'std_dev_load_time_ms', 'error_messages'
                        ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for url_summary in summary.values():
                         # Convert list of errors to a string for CSV
                         url_summary['error_messages'] = "; ".join(url_summary.get('error_messages', []))
                         writer.writerow(url_summary)

            elif export_format == "JSON":
                 # Export both raw data and summary
                 export_data = {
                     "summary_report": self.generate_summary_report(),
                     "raw_results": self.results_data,
                     "test_configuration": {k: v for k, v in self.settings.items() if k != 'results'} # Exclude raw results from config part
                 }
                 with open(filename, 'w', encoding='utf-8') as f:
                     json.dump(export_data, f, indent=2)

            self.status_bar.showMessage(f"Report exported successfully to {filename}", 5000)

        except IOError as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save report file:\n{e}")
            self.status_bar.showMessage(f"Error exporting report: {e}", 5000)
        except Exception as e:
             QMessageBox.critical(self, "Export Error", f"An unexpected error occurred during export:\n{e}")
             self.status_bar.showMessage(f"Unexpected error during export: {e}", 5000)
             logging.exception("Unexpected error during report export.")


    def closeEvent(self, event):
        """Handle window close event."""
        # Stop worker thread if running
        if self.test_worker and self.test_worker.isRunning():
             reply = QMessageBox.question(self, 'Test Running',
                                         "A test is currently running. Are you sure you want to quit?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

             if reply == QMessageBox.StandardButton.Yes:
                 self.stop_test()
                 # Allow some time for thread to potentially stop?
                 # Or just proceed to close. Depending on worker's stop logic robustness.
                 # self.test_worker.wait(1000) # Wait max 1 sec (optional)
                 event.accept()
             else:
                 event.ignore()
                 return

        # Save current UI settings before closing
        self.update_config_from_ui()
        logging.info("Application closing. Settings saved.")
        event.accept()