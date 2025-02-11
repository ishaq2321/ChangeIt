from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QCheckBox, QPushButton, QGroupBox, QMessageBox,
                           QInputDialog, QLineEdit)
from PyQt5.QtCore import pyqtSignal
from utils.sudo_helper import SudoHelper
import json
import os

class SettingsTab(QWidget):
    settings_changed = pyqtSignal(dict)  # Signal when settings are changed

    def __init__(self):
        super().__init__()
        self.settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        self.sudo_helper = SudoHelper()
        # self.website_blocker = WebsiteBlocker()
        self.settings = self.load_settings()
        self.initUI()
        self.add_sudo_settings()
        
        # Don't auto-verify password at startup
        if "sudo_password" in self.settings:
            self.sudo_password.setText(self.settings["sudo_password"])
            # Don't auto-verify: self.verify_sudo_password()

    def initUI(self):
        layout = QVBoxLayout()

        # Monitoring Settings Group
        monitoring_group = QGroupBox("Background Monitoring Settings")
        monitoring_layout = QVBoxLayout()

        # Create checkboxes for each monitoring type
        self.location_cb = QCheckBox("Enable Location Monitoring")
        self.wifi_cb = QCheckBox("Enable WiFi Monitoring")
        self.bluetooth_cb = QCheckBox("Enable Bluetooth Monitoring")
        self.camera_cb = QCheckBox("Enable Camera Monitoring")
        
        # Mic monitoring (disabled)
        self.mic_cb = QCheckBox("Enable Microphone Monitoring")
        self.mic_cb.setEnabled(False)
        self.mic_cb.setToolTip("Coming soon in future updates")

        # New keyboard monitoring checkbox
        self.keyboard_cb = QCheckBox("Enable Keyboard Monitoring")

        # Add checkboxes to layout
        monitoring_layout.addWidget(self.location_cb)
        monitoring_layout.addWidget(self.wifi_cb)
        monitoring_layout.addWidget(self.bluetooth_cb)
        monitoring_layout.addWidget(self.camera_cb)
        monitoring_layout.addWidget(self.mic_cb)
        monitoring_layout.addWidget(self.keyboard_cb)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        
        # Apply settings from saved state
        self.apply_settings()

        monitoring_group.setLayout(monitoring_layout)
        layout.addWidget(monitoring_group)
        layout.addWidget(save_btn)

        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)

    def add_sudo_settings(self):
        """Add sudo authentication section"""
        sudo_group = QGroupBox("System Administration")
        sudo_layout = QVBoxLayout()

        # Password input
        password_layout = QHBoxLayout()
        self.sudo_password = QLineEdit()
        self.sudo_password.setEchoMode(QLineEdit.Password)
        self.sudo_password.setPlaceholderText("Enter sudo password")
        
        auth_btn = QPushButton("Authenticate")
        auth_btn.clicked.connect(self.verify_sudo_password)
        
        password_layout.addWidget(self.sudo_password)
        password_layout.addWidget(auth_btn)

        # Status indicator
        self.auth_status = QLabel("Not authenticated")
        self.auth_status.setStyleSheet("color: #666;")

        sudo_layout.addLayout(password_layout)
        sudo_layout.addWidget(self.auth_status)
        sudo_group.setLayout(sudo_layout)

        # Add to main layout after monitoring settings
        self.layout().insertWidget(1, sudo_group)

        # Load saved password if exists
        if "sudo_password" in self.settings:
            self.sudo_password.setText(self.settings["sudo_password"])
            # Don't auto-verify: self.verify_sudo_password()

    def verify_sudo_password(self):
        """Verify and save sudo password"""
        password = self.sudo_password.text()
        if not password:
            self.auth_status.setText("Please enter password")
            self.auth_status.setStyleSheet("color: #666;")
            return

        # First verify with sudo helper
        if self.sudo_helper.set_sudo_password(password):
            self.settings["sudo_password"] = password
            self.save_settings()
            self.auth_status.setText("✓ Authentication successful")
            self.auth_status.setStyleSheet("color: green;")
            # Update other components
            # self.website_blocker.set_sudo_password(password)
        else:
            self.auth_status.setText("✗ Invalid password")
            self.auth_status.setStyleSheet("color: red;")

    def load_settings(self):
        default_settings = {
            "monitoring": {
                "location": True,
                "wifi": True,
                "bluetooth": True,
                "camera": False,
                "mic": False,
                "keyboard": False
            }
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            return default_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return default_settings

    def apply_settings(self):
        monitoring = self.settings.get("monitoring", {})
        self.location_cb.setChecked(monitoring.get("location", True))
        self.wifi_cb.setChecked(monitoring.get("wifi", True))
        self.bluetooth_cb.setChecked(monitoring.get("bluetooth", True))
        self.camera_cb.setChecked(monitoring.get("camera", False))
        self.mic_cb.setChecked(monitoring.get("mic", False))
        self.keyboard_cb.setChecked(monitoring.get("keyboard", False))

    def save_settings(self):
        """Save settings including sudo password"""
        self.settings["monitoring"] = {
            "location": self.location_cb.isChecked(),
            "wifi": self.wifi_cb.isChecked(),
            "bluetooth": self.bluetooth_cb.isChecked(),
            "camera": self.camera_cb.isChecked(),
            "mic": self.mic_cb.isChecked(),
            "keyboard": self.keyboard_cb.isChecked()
        }
        self.settings["sudo_password"] = self.settings.get("sudo_password", "")
        
        # Ensure the directory for settings exists
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            self.settings_changed.emit(self.settings)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.print_monitoring_status()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def print_monitoring_status(self):
        """Print the current monitoring status to the terminal"""
        monitoring = self.settings["monitoring"]
        
        print("\nMonitoring Status:")
        print("------------------")
        print(f"Location Monitoring: {'Enabled' if monitoring['location'] else 'Disabled'}")
        print(f"WiFi Monitoring: {'Enabled' if monitoring['wifi'] else 'Disabled'}")
        print(f"Bluetooth Monitoring: {'Enabled' if monitoring['bluetooth'] else 'Disabled'}")
        print(f"Camera Monitoring: {'Enabled' if monitoring['camera'] else 'Disabled'}")
        print("Microphone Monitoring: Will be implemented in future updates")
        print(f"Keyboard Monitoring: {'Enabled' if monitoring['keyboard'] else 'Disabled'}")
        print("------------------")
