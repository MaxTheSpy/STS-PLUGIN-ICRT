import os
from PyQt5 import QtWidgets, uic
import logging

class ICRTApp(QtWidgets.QWidget):
    def __init__(self, parent=None, logger=None):
        super().__init__(parent)
        self.logger = logger or logging.getLogger("ICRT_Fallback")

        # Correct path to UI file
        plugin_dir = os.path.dirname(os.path.abspath(__file__))  # Dynamically get the plugin's directory
        ui_path = os.path.join(plugin_dir, "ICRT.ui")

        try:
            uic.loadUi(ui_path, self)
            self.logger.info("UI file loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load UI file: {ui_path}. Error: {e}")
            raise

        # Connect UI components and initialize
        self.checkBox_Trailing_Period.stateChanged.connect(self.toggle_trailing_period_state)
        self.lineEdit_ill_char.setText('<>:"/\\|?*')
        self.lineEdit_rep_char.setText('-')
        self.pushButton_select_2.clicked.connect(self.select_directory)
        self.pushButton_analyze_2.clicked.connect(self.analyze_directory)

        self.tableView_results_2.setColumnCount(4)
        self.tableView_results_2.setHorizontalHeaderLabels(["Name", "Target Character", "Override", "Action"])

        header = self.tableView_results_2.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.tableView_results_2.setColumnWidth(2, 100)
        self.tableView_results_2.setColumnWidth(3, 100)

        self.files_with_issues = []
        self.files_with_trailing_periods = []

        self.logger.info("ICRT initialized.")

    def select_directory(self):
        """Open a dialog to select a directory."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.lineEdit_directory_2.setText(directory)
            self.logger.info(f"Directory selected: {directory}")
        else:
            self.logger.warning("No directory selected.")

    def analyze_directory(self, suppress_logs=False):
        """Analyze the directory for files and folders with illegal characters and/or trailing periods."""
        directory = self.lineEdit_directory_2.text().strip()
        illegal_chars = self.lineEdit_ill_char.text().strip()

        if not directory:
            if not suppress_logs:
                self.logger.warning("Analysis aborted: No directory selected.")
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a directory.")
            return

        if not illegal_chars:
            if not suppress_logs:
                self.logger.warning("Analysis aborted: No illegal characters specified.")
            QtWidgets.QMessageBox.warning(self, "Error", "Please specify illegal characters.")
            return

        if not suppress_logs:
            self.logger.info(f"Starting analysis on directory: {directory} with illegal characters: '{illegal_chars}'")
        
        self.files_with_issues = self.find_files_with_issues(directory, illegal_chars)

        if self.checkBox_Trailing_Period.isChecked():
            self.files_with_trailing_periods = self.find_files_with_trailing_periods(directory)

        combined_results = self.files_with_issues + self.files_with_trailing_periods

        if not suppress_logs:
            num_illegal_files = len(self.files_with_issues)
            num_trailing_periods = len(self.files_with_trailing_periods)
            total_issues = len(combined_results)

            self.logger.info(f"Analysis complete. {num_illegal_files} files and folders with illegal characters, "
                            f"{num_trailing_periods} files and folders with trailing periods. Total issues: {total_issues}.")

        self.populate_results_table(illegal_chars, combined_results)


    def find_files_with_issues(self, directory, illegal_chars):
        """Find all files and directories with illegal characters."""
        files_with_issues = []
        for root, dirs, files in os.walk(directory):
            for name in dirs + files:
                if any(char in name for char in illegal_chars):
                    files_with_issues.append((root, name))
        return files_with_issues

    def find_files_with_trailing_periods(self, directory):
        """Find files and directories with trailing periods."""
        files_with_trailing_periods = []
        for root, dirs, files in os.walk(directory):
            for name in dirs + files:
                if name.endswith('.'):
                    files_with_trailing_periods.append((root, name))
        return files_with_trailing_periods

    def populate_results_table(self, illegal_chars, files_list):
        """Populate the results table with files and folders containing illegal characters or trailing periods."""
        self.tableView_results_2.setRowCount(0)  # Clear existing rows

        for root, name in files_list:
            file_name = name
            # Determine the target character or trailing period
            target_character = next((char for char in name if char in illegal_chars), "Trailing Period" if name.endswith('.') else "")

            row_position = self.tableView_results_2.rowCount()
            self.tableView_results_2.insertRow(row_position)

            # Add file/folder name
            self.tableView_results_2.setItem(row_position, 0, QtWidgets.QTableWidgetItem(file_name))
            self.tableView_results_2.setItem(row_position, 1, QtWidgets.QTableWidgetItem(target_character))

            # Add override field
            override_field = QtWidgets.QLineEdit()
            override_field.setMaxLength(1)
            self.tableView_results_2.setCellWidget(row_position, 2, override_field)

            # Add Replace button
            replace_button = QtWidgets.QPushButton("Replace")
            replace_button.clicked.connect(lambda _, r=root, n=name, of=override_field: self.replace_illegal_characters(r, n, of))
            self.tableView_results_2.setCellWidget(row_position, 3, replace_button)


    def replace_illegal_characters(self, root, name, override_field):
        """Replace illegal characters or trailing periods in a specific file or folder."""
        illegal_chars = self.lineEdit_ill_char.text().strip()
        replacement = self.lineEdit_rep_char.text().strip()
        override = override_field.text().strip()

        # Validate replacement settings
        if not illegal_chars and not self.checkBox_Trailing_Period.isChecked():
            self.logger.error("No illegal characters specified and trailing period replacement is disabled.")
            QtWidgets.QMessageBox.warning(self, "Error", "No replacement settings specified.")
            return

        if len(replacement) > 1:
            self.logger.error("Replacement character length exceeds 1.")
            QtWidgets.QMessageBox.warning(self, "Error", "Replacement character length must be 1.")
            return

        old_path = os.path.join(root, name)

        # Handle trailing periods
        if name.endswith('.'):
            replacement_char = override or replacement
            new_name = name.rstrip('.') + (replacement_char if self.checkBox_Trailing_Period.isChecked() else '')
        else:
            replacement_char = override or replacement
            new_name = self.sanitize_data(name, illegal_chars, replacement_char)

        new_path = os.path.join(root, new_name)

        try:
            os.rename(old_path, new_path)
            self.logger.info(f"Renamed: {old_path} -> {new_path}")
            self.analyze_directory(suppress_logs=True)  # Suppress logs during refresh
        except Exception as e:
            self.logger.error(f"Failed to rename: {old_path}. Error: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to rename:\n\n{old_path}\n\nError: {e}")



    def sanitize_data(self, value, illegal_chars, replacement):
        """Sanitize a string by replacing illegal characters."""
        for char in illegal_chars:
            value = value.replace(char, replacement)
        return value

    def toggle_trailing_period_state(self):
        pass


def main(parent_widget=None, parent_logger=None):
    if parent_logger:
        plugin_logger = parent_logger.getChild("ICRT")
    else:
        import logging
        plugin_logger = logging.getLogger("ICRT_Fallback")

    plugin_logger.info("ICRT Plugin initialized.")
    app = ICRTApp(parent_widget, plugin_logger)
    return app
