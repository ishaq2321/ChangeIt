from PyQt5.QtWidgets import (QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QListWidget, QListWidgetItem, QLabel, 
                           QLineEdit, QGroupBox, QDialog, QFileDialog, 
                           QMessageBox, QApplication, QComboBox, QInputDialog)  # Added QInputDialog
from PyQt5.QtCore import Qt
import platform  # Added platform for OS detection
import os
import json
import hashlib
from utils.app_manager import AppManager  # Add this import

class AppFolderManager(QDialog):
    def __init__(self, active_tab="applications", category=None, parent=None):
        super().__init__(parent)
        self.category = category
        self.folder_manager = parent.folder_manager  # Get FolderManager from parent
        self.setWindowTitle(f"{category} - Application & Folder Management")
        self.setMinimumSize(600, 400)
        self.initUI(active_tab)
        
    def initUI(self, active_tab):
        layout = QVBoxLayout()
        
        # Add category label
        category_label = QLabel(f"Category: {self.category}")
        category_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        layout.addWidget(category_label)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.addTab(ApplicationsTab(self.category), "Applications")
        self.tabs.addTab(FoldersTab(self.category, self.folder_manager), "Folders")  # Pass folder_manager
        
        # Set the active tab based on parameter
        if active_tab == "folders":
            self.tabs.setCurrentIndex(1)
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

class ApplicationsTab(QWidget):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Sub-tabs for different application actions
        tabs = QTabWidget()
        tabs.addTab(InstallAppTab(self.category), "Install Applications")
        tabs.addTab(UninstallAppTab(self.category), "Uninstall Applications")
        tabs.addTab(EnableDisableAppTab(self.category), "Enable/Disable")
        tabs.addTab(LockAppTab(self.category), "Lock Applications")
        
        layout.addWidget(tabs)
        self.setLayout(layout)

class FoldersTab(QWidget):
    def __init__(self, category, folder_manager):
        super().__init__()
        self.category = category
        self.folder_manager = folder_manager  # Store folder_manager
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Create tab widget
        tabs = QTabWidget()
        tabs.addTab(LockUnlockFolderTab(self.folder_manager), "Lock/Unlock")  # Pass folder_manager
        tabs.addTab(HideUnhideFolderTab(), "Hide/Unhide")
        
        layout.addWidget(tabs)
        self.setLayout(layout)

class LockUnlockFolderTab(QWidget):
    def __init__(self, folder_manager):
        super().__init__()
        self.folder_manager = folder_manager  # Store folder_manager
        self.locked_folders = []
        self.initUI()
        self.load_folders()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Browse folder
        browse_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder to lock/unlock...")
        self.path_input.textChanged.connect(self.check_path_exists)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        browse_layout.addWidget(self.path_input)
        browse_layout.addWidget(browse_btn)
        layout.addLayout(browse_layout)
        
        # Lock/Unlock button
        self.lock_unlock_btn = QPushButton("Lock Folder")
        self.lock_unlock_btn.clicked.connect(self.lock_unlock_folder)
        layout.addWidget(self.lock_unlock_btn)
        
        # Locked folders list
        layout.addWidget(QLabel("Locked Folders:"))
        self.folders_list = QListWidget()
        layout.addWidget(self.folders_list)
        
        # Unlock button
        unlock_btn = QPushButton("Unlock Selected")
        unlock_btn.clicked.connect(self.unlock_selected)
        layout.addWidget(unlock_btn)
        
        self.setLayout(layout)
        self.refresh_list()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)

    def check_path_exists(self, path):
        if os.path.exists(path):
            self.path_input.setStyleSheet("")
        else:
            self.path_input.setStyleSheet("border: 1px solid red;")

    def lock_unlock_folder(self):
        folder_path = self.path_input.text().strip()
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Warning", "Invalid folder path")
            return
        
        if folder_path in self.locked_folders:
            QMessageBox.warning(self, "Warning", "Folder is already locked")
            return

        # Ask for PIN
        pin, ok = QInputDialog.getText(self, "Lock Folder", "Enter PIN:", QLineEdit.Password)
        if ok and pin:
            hashed_pin = hashlib.sha256(pin.encode('utf-8')).hexdigest()
            
            # Save folder and hashed PIN
            self.locked_folders.append((folder_path, hashed_pin))
            self.save_folders()
            self.refresh_list()
            QMessageBox.information(self, "Success", "Folder locked successfully")

    def unlock_selected(self):
        """Unlock selected folders and remove their lock scripts"""
        selected_items = self.folders_list.selectedItems()
        if not selected_items:
            return

        # Verify sudo access before proceeding
        if not self.folder_manager.sudo_helper.is_verified():
            QMessageBox.warning(self, "Error", "Sudo access not available. Please check your settings.")
            return

        for item in selected_items:
            folder_path = item.text()
            # Ask for PIN
            pin, ok = QInputDialog.getText(self, "Unlock Folder", f"Enter PIN for {folder_path}:", QLineEdit.Password)
            if ok and pin:
                # Hash the entered PIN for comparison
                hashed_pin = hashlib.sha256(pin.encode('utf-8')).hexdigest()
                
                # Find matching folder and PIN
                matching_folder = None
                for folder_data in self.locked_folders:
                    if isinstance(folder_data, dict):
                        if folder_data.get('path') == folder_path:
                            matching_folder = folder_data
                            break
                    elif isinstance(folder_data, list) and len(folder_data) == 2:
                        if folder_data[0] == folder_path:
                            matching_folder = {'path': folder_data[0], 'pin': folder_data[1]}
                            break

                # Compare hashed PINs
                if matching_folder and hashed_pin == matching_folder.get('pin'):
                    # Use the folder_manager instance directly
                    success, msg = self.folder_manager.unlock_folder(folder_path)
                    if success:
                        # Remove the lock script and desktop entry
                        script_path = os.path.join(
                            os.path.expanduser("~/.config/changeit/folder_locks"),
                            f"{os.path.basename(folder_path)}_lock.sh"
                        )
                        desktop_path = os.path.join(
                            os.path.expanduser("~/.local/share/applications"),
                            f"folder_access_{os.path.basename(folder_path)}.desktop"
                        )
                        try:
                            if os.path.exists(script_path):
                                os.remove(script_path)
                            if os.path.exists(desktop_path):
                                os.remove(desktop_path)
                        except Exception as e:
                            print(f"Warning: Could not remove lock files: {e}")

                        # Remove from locked_folders list
                        if matching_folder in self.locked_folders:
                            self.locked_folders.remove(matching_folder)
                        elif [folder_path, matching_folder['pin']] in self.locked_folders:
                            self.locked_folders.remove([folder_path, matching_folder['pin']])

                        self.save_folders()
                        self.refresh_list()
                        QMessageBox.information(self, "Success", f"Folder unlocked: {folder_path}")
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to unlock folder: {msg}")
                else:
                    QMessageBox.warning(self, "Error", "Incorrect PIN")

    def refresh_list(self):
        self.folders_list.clear()
        for folder, _ in self.locked_folders:
            self.folders_list.addItem(folder)

    def load_folders(self):
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                self.locked_folders = all_settings.get("locked_folders", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.locked_folders = []
        self.refresh_list()

    def save_folders(self):
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            all_settings["locked_folders"] = self.locked_folders
            
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

class HideUnhideFolderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.hidden_folders = []
        self.initUI()
        self.load_folders()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Browse folder
        browse_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder to hide/unhide...")
        self.path_input.textChanged.connect(self.check_path_exists)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        browse_layout.addWidget(self.path_input)
        browse_layout.addWidget(browse_btn)
        layout.addLayout(browse_layout)
        
        # Hide/Unhide button
        self.hide_unhide_btn = QPushButton("Hide Folder")
        self.hide_unhide_btn.clicked.connect(self.hide_unhide_folder)
        layout.addWidget(self.hide_unhide_btn)
        
        # Hidden folders list
        layout.addWidget(QLabel("Hidden Folders:"))
        self.folders_list = QListWidget()
        layout.addWidget(self.folders_list)
        
        # Unhide button
        unhide_btn = QPushButton("Unhide Selected")
        unhide_btn.clicked.connect(self.unhide_selected)
        layout.addWidget(unhide_btn)
        
        self.setLayout(layout)
        self.refresh_list()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)

    def check_path_exists(self, path):
        if os.path.exists(path):
            self.path_input.setStyleSheet("")
        else:
            self.path_input.setStyleSheet("border: 1px solid red;")

    def hide_unhide_folder(self):
        folder_path = self.path_input.text().strip()
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Warning", "Invalid folder path")
            return
        
        if folder_path in self.hidden_folders:
            QMessageBox.warning(self, "Warning", "Folder is already hidden")
            return

        self.hidden_folders.append(folder_path)
        self.save_folders()
        self.refresh_list()
        QMessageBox.information(self, "Success", "Folder hidden successfully")

    def unhide_selected(self):
        selected_items = self.folders_list.selectedItems()
        if not selected_items:
            return
        
        folder_path = selected_items[0].text()
        if folder_path in self.hidden_folders:
            self.hidden_folders.remove(folder_path)
            self.save_folders()
            self.refresh_list()
            QMessageBox.information(self, "Success", "Folder unhidden successfully")

    def refresh_list(self):
        self.folders_list.clear()
        for folder in self.hidden_folders:
            self.folders_list.addItem(folder)

    def load_folders(self):
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                self.hidden_folders = all_settings.get("hidden_folders", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.hidden_folders = []
        self.refresh_list()

    def save_folders(self):
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            all_settings["hidden_folders"] = self.hidden_folders
            
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

# Application Management Sub-tabs
class InstallAppTab(QWidget):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.app_manager = AppManager()
        self.selected_apps = []  # Our list of selected applications
        # Load any existing apps for this category
        self.load_selected_apps()
        self.initUI()
        self.load_installed_apps()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Show category
        category_label = QLabel(f"Installing Applications for: {self.category}")
        category_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(category_label)
        
        # Application input methods
        input_group = QGroupBox("Add Application")
        input_layout = QVBoxLayout()
        
        # Manual search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for application...")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_application)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        
        # Browse local file
        browse_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Browse application file...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_application)
        browse_layout.addWidget(self.file_path)
        browse_layout.addWidget(browse_btn)
        
        input_layout.addLayout(search_layout)
        input_layout.addLayout(browse_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Results and status
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.MultiSelection)  # Make results list selectable
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        
        # Add selected apps to list button
        add_btn = QPushButton("Add Selected Applications")
        add_btn.clicked.connect(self.add_selected_applications)
        
        # Save button
        save_btn = QPushButton("Save Application Settings")
        save_btn.clicked.connect(self.save_application_settings)
        
        layout.addWidget(self.results_list)
        layout.addWidget(add_btn)
        layout.addWidget(self.status_label)
        layout.addWidget(save_btn)
        
        # Selected applications for categories
        selected_group = QGroupBox("Selected Applications by Category")
        selected_layout = QVBoxLayout()
        # We'll store each selected app row in self.selected_apps_layout
        self.selected_apps_layout = QVBoxLayout()
        selected_layout.addLayout(self.selected_apps_layout)
        selected_group.setLayout(selected_layout)
        layout.addWidget(selected_group)

        # Installed applications section
        installed_group = QGroupBox("Installed Applications")
        installed_layout = QVBoxLayout()
        self.installed_list = QListWidget()  # Create the installed_list here
        installed_layout.addWidget(self.installed_list)
        installed_group.setLayout(installed_layout)
        layout.addWidget(installed_group)
        
        self.setLayout(layout)
        # Refresh display of selected apps
        self.refresh_selected_apps()

    def browse_application(self):
        file_filter = ""
        if platform.system() == "Windows":
            file_filter = "Applications (*.exe)"
        elif platform.system() == "Linux":
            file_filter = "Applications (*.deb *.AppImage *.run)"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "", file_filter)
            
        if file_path:
            if self.validate_application_file(file_path):
                self.file_path.setText(file_path)
                self.status_label.setText("✓ Valid application file selected")
                self.status_label.setStyleSheet("color: green")
            else:
                self.status_label.setText("✗ Invalid application file")
                self.status_label.setStyleSheet("color: red")

    def validate_application_file(self, file_path):
        """Validate application file based on OS"""
        ext = os.path.splitext(file_path)[1].lower()
        valid_extensions = {
            "Windows": [".exe"],
            "Linux": [".deb", ".appimage", ".run"],
            "Darwin": [".app", ".dmg"]
        }
        return ext in valid_extensions.get(platform.system(), [])

    def save_application_settings(self):
        """Save selected applications for this category"""
        if not self.selected_apps:
            QMessageBox.warning(self, "Warning", "No applications selected")
            return
            
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            # Load existing settings
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            # Update settings for this category
            all_settings[self.category] = self.selected_apps
            
            # Save back to file
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
                
            QMessageBox.information(
                self, 
                "Success", 
                f"Applications saved for category {self.category}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

    def update_selected_applications_display(self):
        """Update the display of selected applications by category"""
        self.selected_list.clear()
        for category, apps in self.selected_apps.items():
            self.selected_list.addItem(f"Category: {category}")
            for app in apps:
                self.selected_list.addItem(f"  • {app['name']}")
            self.selected_list.addItem("")

    def save_config(self):
        """Save application settings to configuration file"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(self.selected_apps, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

    def search_application(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.results_list.clear()
        self.status_label.setText("Searching...")
        QApplication.processEvents()
        
        results = self.app_manager.search_application(query)
        
        self.results_list.clear()
        if results:
            for result in results:
                item = QListWidgetItem(
                    f"{result['name']}\n"
                    f"Source: {result['source']}\n"
                    f"{'Free' if result.get('free', False) else 'Paid'}"
                )
                self.results_list.addItem(item)
            self.status_label.setText(f"Found {len(results)} results")
        else:
            self.status_label.setText("No results found")
    
    def load_installed_apps(self):
        """Load list of installed applications"""
        self.installed_list.clear()
        apps = self.app_manager.get_installed_applications()
        for app in apps:
            self.installed_list.addItem(app['name'])

    def load_category_apps(self):
        """Load applications specific to this category"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                return all_settings.get(self.category, {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def add_selected_applications(self):
        """Add selected applications to the list and save immediately."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            app_info = {
                'name': item.text().split('\n')[0],
                'source': item.text().split('\n')[1].replace('Source: ', ''),
                'free': 'Free' in item.text()
            }
            if app_info not in self.selected_apps:
                self.selected_apps.append(app_info)

        # Save and refresh
        self.save_selected_apps()
        self.refresh_selected_apps()

    def remove_application(self, app_info):
        """Remove the given application from the list and save."""
        if app_info in self.selected_apps:
            self.selected_apps.remove(app_info)
            self.save_selected_apps()
            self.refresh_selected_apps()

    def refresh_selected_apps(self):
        """Rebuild the UI showing each app with a Remove button."""
        # Clear current layout
        while self.selected_apps_layout.count():
            child = self.selected_apps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add row for each selected application
        for app in self.selected_apps:
            row = QHBoxLayout()
            label = QLabel(f"{app['name']} ({app['source']}) - {'Free' if app['free'] else 'Paid'}")
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda _, appinfo=app: self.remove_application(appinfo))
            row.addWidget(label)
            row.addWidget(remove_btn)
            
            row_widget = QWidget()
            row_widget.setLayout(row)
            self.selected_apps_layout.addWidget(row_widget)

    def load_selected_apps(self):
        """Load this category's apps from app_settings.json if present."""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
                # Load apps if they exist for this category
                self.selected_apps = all_settings.get(self.category, [])
            except:
                self.selected_apps = []
        else:
            self.selected_apps = []

    def save_selected_apps(self):
        """Save this category's apps to app_settings.json immediately."""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")

        # Load existing data
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            except:
                all_settings = {}
        else:
            all_settings = {}

        # Overwrite this category’s apps
        all_settings[self.category] = self.selected_apps

        try:
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

class UninstallAppTab(QWidget):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.app_manager = AppManager()
        self.selected_apps = []  # List of apps to uninstall
        self.initUI()
        self.load_selected_apps()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Category label
        layout.addWidget(QLabel(f"Uninstalling Applications for: {self.category}"))
        
        # Manual input section
        input_group = QGroupBox("Manual Input")
        input_layout = QHBoxLayout()
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Enter application name to uninstall...")
        add_btn = QPushButton("Add to List")
        add_btn.clicked.connect(self.add_manual_app)
        input_layout.addWidget(self.app_input)
        input_layout.addWidget(add_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Currently installed applications
        installed_group = QGroupBox("Currently Installed Applications")
        installed_layout = QVBoxLayout()
        self.installed_list = QListWidget()
        self.installed_list.setSelectionMode(QListWidget.MultiSelection)
        add_selected_btn = QPushButton("Add Selected to Uninstall List")
        add_selected_btn.clicked.connect(self.add_selected_apps)
        installed_layout.addWidget(self.installed_list)
        installed_layout.addWidget(add_selected_btn)
        installed_group.setLayout(installed_layout)
        layout.addWidget(installed_group)
        
        # Applications to uninstall
        uninstall_group = QGroupBox("Applications to Uninstall")
        self.uninstall_layout = QVBoxLayout()  # Will contain app rows dynamically
        uninstall_group.setLayout(self.uninstall_layout)
        layout.addWidget(uninstall_group)
        
        # Save button
        save_btn = QPushButton("Save Uninstall Settings")
        save_btn.clicked.connect(self.save_uninstall_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
        self.refresh_installed_apps()
        self.refresh_uninstall_list()

    def add_manual_app(self):
        app_name = self.app_input.text().strip()
        if not app_name:
            return
            
        app_info = {
            'name': app_name,
            'source': 'manual'
        }
        
        if app_info not in self.selected_apps:
            self.selected_apps.append(app_info)
            self.app_input.clear()
            self.refresh_uninstall_list()
            self.save_uninstall_settings()

    def add_selected_apps(self):
        for item in self.installed_list.selectedItems():
            app_info = {
                'name': item.text(),
                'source': 'installed'
            }
            if app_info not in self.selected_apps:
                self.selected_apps.append(app_info)
        
        self.refresh_uninstall_list()
        self.save_uninstall_settings()

    def remove_app(self, app_info):
        if app_info in self.selected_apps:
            self.selected_apps.remove(app_info)
            self.refresh_uninstall_list()
            self.save_uninstall_settings()

    def refresh_uninstall_list(self):
        """Update the display of apps to uninstall"""
        # Clear current list
        while self.uninstall_layout.count():
            child = self.uninstall_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add row for each app
        for app in self.selected_apps:
            row = QHBoxLayout()
            label = QLabel(f"{app['name']} ({app['source']})")
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda _, a=app: self.remove_app(a))
            row.addWidget(label)
            row.addWidget(remove_btn)
            
            widget = QWidget()
            widget.setLayout(row)
            self.uninstall_layout.addWidget(widget)

    def refresh_installed_apps(self):
        """Update list of currently installed applications"""
        self.installed_list.clear()
        apps = self.app_manager.get_installed_applications()
        for app in apps:
            self.installed_list.addItem(app['name'])

    def load_selected_apps(self):
        """Load previously saved uninstall list"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                self.selected_apps = all_settings.get(f"{self.category}_uninstall", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.selected_apps = []
        self.refresh_uninstall_list()

    def save_uninstall_settings(self):
        """Save uninstall list to config"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            # Load existing settings
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            # Save uninstall list with unique key for this category
            all_settings[f"{self.category}_uninstall"] = self.selected_apps
            
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
                
            QMessageBox.information(
                self,
                "Success",
                f"Uninstall settings saved for category {self.category}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

class EnableDisableAppTab(QWidget):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.app_manager = AppManager()
        self.disabled_apps = []
        self.disabled_files = {}  # new: mapping app_name -> disabled file path
        self.all_apps = []
        self.initUI()
        self.load_state()  # Load both disabled apps and scan for actually disabled apps

    def initUI(self):
        layout = QVBoxLayout()

        # Search section
        search_group = QGroupBox("Search Applications")
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for applications...")
        self.search_input.textChanged.connect(self.filter_applications)
        search_layout.addWidget(self.search_input)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Lists section
        lists_layout = QHBoxLayout()
        
        # Enabled apps
        enabled_group = QGroupBox("Enabled Applications")
        enabled_layout = QVBoxLayout()
        self.enabled_list = QListWidget()
        self.enabled_list.setSelectionMode(QListWidget.MultiSelection)
        disable_btn = QPushButton("Disable Selected")
        disable_btn.clicked.connect(self.disable_selected)
        enabled_layout.addWidget(self.enabled_list)
        enabled_layout.addWidget(disable_btn)
        enabled_group.setLayout(enabled_layout)
        
        # Disabled apps
        disabled_group = QGroupBox("Disabled Applications")
        disabled_layout = QVBoxLayout()
        self.disabled_list = QListWidget()
        self.disabled_list.setSelectionMode(QListWidget.MultiSelection)
        enable_btn = QPushButton("Enable Selected")
        enable_btn.clicked.connect(self.enable_selected)
        disabled_layout.addWidget(self.disabled_list)
        disabled_layout.addWidget(enable_btn)
        disabled_group.setLayout(disabled_layout)
        
        lists_layout.addWidget(enabled_group)
        lists_layout.addWidget(disabled_group)
        layout.addLayout(lists_layout)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
        self.refresh_lists()

    def load_state(self):
        """Load both saved state and scan for currently disabled apps/files"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                saved_disabled = all_settings.get(f"{self.category}_disabled", [])
                saved_disabled_files = all_settings.get(f"{self.category}_disabled_files", {})
        except (FileNotFoundError, json.JSONDecodeError):
            saved_disabled = []
            saved_disabled_files = {}
        
        self.disabled_files = saved_disabled_files.copy()

        # Then scan for actually disabled apps and update files mapping
        desktop_paths = [
            '/usr/share/applications',
            os.path.expanduser('~/.local/share/applications')
        ]
        actually_disabled = []
        for path in desktop_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.desktop.disabled'):
                        full_path = os.path.join(path, file)
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'Name=' in content:
                                    name = content.split('Name=')[1].split('\n')[0].strip()
                                    actually_disabled.append(name)
                                    if name not in self.disabled_files:
                                        self.disabled_files[name] = full_path
                        except Exception:
                            continue

        # Merge saved and scanned disabled app names
        self.disabled_apps = list(set(saved_disabled + actually_disabled))
        self.all_apps = self.app_manager.get_installed_applications()
        self.refresh_lists()
        print(f"Loaded disabled apps for {self.category}: {self.disabled_apps}")
        print(f"Disabled files mapping: {self.disabled_files}")

    def save_settings(self):
        """Save disabled apps list and disabled files mapping to config"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            all_settings[f"{self.category}_disabled"] = self.disabled_apps
            all_settings[f"{self.category}_disabled_files"] = self.disabled_files
            
            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
            
            print(f"Saved disabled apps for {self.category}: {self.disabled_apps}")
            print(f"Saved disabled files mapping: {self.disabled_files}")
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")
    
    def get_disabled_file(self, app_name: str) -> str:
        """Helper to scan desktop paths for the disabled file corresponding to app_name"""
        desktop_paths = [
            '/usr/share/applications',
            os.path.expanduser('~/.local/share/applications')
        ]
        for path in desktop_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.desktop.disabled'):
                        full_path = os.path.join(path, file)
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'Name=' in content:
                                    name = content.split('Name=')[1].split('\n')[0].strip()
                                    if name == app_name:
                                        return full_path
                        except Exception:
                            continue
        return ""

    def disable_selected(self):
        """Disable selected applications and update the lists and disabled files mapping"""
        for item in self.enabled_list.selectedItems():
            app_name = item.text()
            success, message = self.app_manager.disable_application(app_name)
            if success:
                if app_name not in self.disabled_apps:
                    self.disabled_apps.append(app_name)
                # Update disabled_files mapping
                disabled_path = self.get_disabled_file(app_name)
                if disabled_path:
                    self.disabled_files[app_name] = disabled_path
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Error", message)
        self.refresh_lists()
        self.save_settings()

    def enable_selected(self):
        """Enable selected applications and update the lists and disabled files mapping"""
        for item in self.disabled_list.selectedItems():
            app_name = item.text()
            success, message = self.app_manager.enable_application(app_name)
            if success:
                if app_name in self.disabled_apps:
                    self.disabled_apps.remove(app_name)
                if app_name in self.disabled_files:
                    del self.disabled_files[app_name]
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Error", message)
        self.refresh_lists()
        self.save_settings()

    def load_all_applications(self):
        """Load all applications once at startup"""
        self.all_apps = self.app_manager.get_installed_applications()
        self.refresh_lists()

    def filter_applications(self, text):
        """Filter applications in real-time based on search text"""
        search_text = text.lower()
        
        # Clear both lists
        self.enabled_list.clear()
        self.disabled_list.clear()
        
        # Filter and add apps
        for app in self.all_apps:
            if search_text in app['name'].lower():
                if app['name'] in self.disabled_apps:
                    self.disabled_list.addItem(app['name'])
                else:
                    self.enabled_list.addItem(app['name'])

    def refresh_lists(self):
        """Refresh both lists with current apps ensuring disabled apps are shown"""
        self.enabled_list.clear()
        self.disabled_list.clear()
        
        # Get installed apps and extract names
        installed_apps = self.app_manager.get_installed_applications()
        installed_names = set(app['name'] for app in installed_apps)
        
        # Ensure disabled apps are included even if not in installed apps
        all_app_names = installed_names.union(set(self.disabled_apps))
        
        for name in all_app_names:
            if name in self.disabled_apps:
                self.disabled_list.addItem(name)
            else:
                self.enabled_list.addItem(name)

class LockAppTab(QWidget):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.app_manager = AppManager()
        self.locked_apps = {}  # Dictionary to store locked apps and their hashed PINs
        self.initUI()
        self.load_locked_apps()

    def initUI(self):
        layout = QVBoxLayout()

        # Search section
        search_group = QGroupBox("Search Applications")
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for applications...")
        self.search_input.textChanged.connect(self.filter_applications)
        search_layout.addWidget(self.search_input)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Lists section
        lists_layout = QHBoxLayout()

        # All apps
        all_apps_group = QGroupBox("All Applications")
        all_apps_layout = QVBoxLayout()
        self.all_apps_list = QListWidget()
        self.all_apps_list.setSelectionMode(QListWidget.MultiSelection)
        lock_btn = QPushButton("Lock Selected")
        lock_btn.clicked.connect(self.lock_selected)
        all_apps_layout.addWidget(self.all_apps_list)
        all_apps_layout.addWidget(lock_btn)
        all_apps_group.setLayout(all_apps_layout)

        # Locked apps
        locked_apps_group = QGroupBox("Locked Applications")
        locked_apps_layout = QVBoxLayout()
        self.locked_apps_list = QListWidget()
        self.locked_apps_list.setSelectionMode(QListWidget.MultiSelection)
        unlock_btn = QPushButton("Unlock Selected")
        unlock_btn.clicked.connect(self.unlock_selected)
        locked_apps_layout.addWidget(self.locked_apps_list)
        locked_apps_layout.addWidget(unlock_btn)
        locked_apps_group.setLayout(locked_apps_layout)

        lists_layout.addWidget(all_apps_group)
        lists_layout.addWidget(locked_apps_group)
        layout.addLayout(lists_layout)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        self.setLayout(layout)
        self.refresh_lists()

    def filter_applications(self, text):
        """Filter applications in real-time based on search text"""
        search_text = text.lower()
        self.all_apps_list.clear()
        all_apps = self.app_manager.get_installed_applications()
        for app in all_apps:
            if search_text in app['name'].lower():
                self.all_apps_list.addItem(app['name'])

    def lock_selected(self):
        """Lock selected applications and ask for a PIN"""
        pin, ok = QInputDialog.getText(self, "Lock Application", "Enter PIN:", QLineEdit.Password)
        if ok and pin:
            hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
            for item in self.all_apps_list.selectedItems():
                app_name = item.text()
                if app_name not in self.locked_apps:
                    self.locked_apps[app_name] = hashed_pin
            self.refresh_lists()
            self.save_settings()

    def unlock_selected(self):
        """Unlock selected applications after PIN verification"""
        pin, ok = QInputDialog.getText(self, "Unlock Application", "Enter PIN:", QLineEdit.Password)
        if ok and pin:
            hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
            for item in self.locked_apps_list.selectedItems():
                app_name = item.text()
                if app_name in self.locked_apps and self.locked_apps[app_name] == hashed_pin:
                    del self.locked_apps[app_name]
                else:
                    QMessageBox.warning(self, "Error", "Incorrect PIN")
        self.refresh_lists()
        self.save_settings()

    def refresh_lists(self):
        """Refresh both lists with current apps"""
        self.all_apps_list.clear()
        self.locked_apps_list.clear()

        # Get all installed applications
        all_apps = self.app_manager.get_installed_applications()

        # Add apps to appropriate lists
        for app in all_apps:
            if app['name'] in self.locked_apps:
                self.locked_apps_list.addItem(app['name'])
            else:
                self.all_apps_list.addItem(app['name'])

    def load_locked_apps(self):
        """Load locked apps for this category"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            with open(config_path, 'r') as f:
                all_settings = json.load(f)
                # Ensure it's a dict
                self.locked_apps = all_settings.get(f"{self.category}_locked", {})
                if not isinstance(self.locked_apps, dict):
                    self.locked_apps = {}
        except (FileNotFoundError, json.JSONDecodeError):
            self.locked_apps = {}
        self.refresh_lists()

    def save_settings(self):
        """Save locked apps list to config"""
        config_path = os.path.join(os.path.dirname(__file__), "app_settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}

            # Ensure we save a dict
            all_settings[f"{self.category}_locked"] = self.locked_apps

            with open(config_path, 'w') as f:
                json.dump(all_settings, f, indent=4)
            QMessageBox.information(self, "Success", "Settings saved successfully!")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")

# Folder Management Sub-tabs
class HideFolderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Folder selection
        browse_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder to hide...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        browse_layout.addWidget(self.path_input)
        browse_layout.addWidget(browse_btn)
        
        # Hide button
        hide_btn = QPushButton("Hide Folder")
        
        layout.addLayout(browse_layout)
        layout.addWidget(hide_btn)
        layout.addWidget(QLabel("Hidden Folders:"))
        layout.addWidget(QListWidget())
        
        self.setLayout(layout)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_input.setText(folder)

# Similarly implement UnhideFolderTab, LockFolderTab, UnlockFolderTab
class UnhideFolderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Hidden Folders:"))
        layout.addWidget(QListWidget())
        layout.addWidget(QPushButton("Unhide Selected"))
        self.setLayout(layout)

class LockFolderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        browse_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder to lock...")
        browse_btn = QPushButton("Browse")
        browse_layout.addWidget(self.path_input)
        browse_layout.addWidget(browse_btn)
        
        layout.addLayout(browse_layout)
        layout.addWidget(QPushButton("Lock Folder"))
        layout.addWidget(QLabel("Locked Folders:"))
        layout.addWidget(QListWidget())
        
        self.setLayout(layout)

class UnlockFolderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Locked Folders:"))
        layout.addWidget(QListWidget())
        layout.addWidget(QPushButton("Unlock Selected"))
        self.setLayout(layout)
