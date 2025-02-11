import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt

class AudioRecordingSettings(QWidget):
    def __init__(self, parent=None, audio_record_manager=None):
        super().__init__(parent)
        self.audio_record_manager = audio_record_manager
        self.settings_changed = False
        self.last_saved_settings = None
        self.recording = False
        self._current_category = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Output path selection
        path_layout = QHBoxLayout()
        path_label = QLabel("Recording Output Path:")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter path or browse...")
        self.path_input.textChanged.connect(self.validate_path)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_path)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)
        
        # Duration selection
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Recording Duration:")
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["1 minute", "2 minutes", "5 minutes", "10 minutes", "30 minutes"])
        
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_combo)
        layout.addLayout(duration_layout)
        
        # Add duration change handler
        self.duration_combo.currentTextChanged.connect(self.on_settings_changed)
        # Add path change handler
        self.path_input.textChanged.connect(self.on_settings_changed)
        
        # Recording status
        self.status_label = QLabel("Recording will start when category triggers match")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        # Record button
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setEnabled(False)  # Disabled until path is valid
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("""
            QPushButton {
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.record_btn)
        
        self.setLayout(layout)
        self.recording = False

    def validate_path(self, path):
        """Validate output path in real-time"""
        result = False
        path = os.path.expanduser(path)
        try:
            # Create directory if it doesn't exist
            if not os.path.exists(path):
                os.makedirs(path)
            
            # Check write permissions
            if os.access(path, os.W_OK):
                self.path_input.setStyleSheet("color: black;")
                self.record_btn.setEnabled(True)
                self.settings_changed = True  # Mark settings as changed
                result = True
            else:
                self.path_input.setStyleSheet("color: red;")
                self.record_btn.setEnabled(False)
                result = False
                
        except Exception:
            self.path_input.setStyleSheet("color: red;")
            self.record_btn.setEnabled(False)
            result = False
            
        if result:
            print("\n📁 [AudioRecording] Valid output path:", path)
            self.settings_changed = True  # Mark settings changed on valid path
        return result

    def browse_path(self):
        """Open folder browser dialog"""
        from PyQt5.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.path_input.setText(folder)

    def load_settings(self, settings: dict):
        """Load saved settings for a category"""
        if not settings:
            # Reset to defaults
            self.recording = False
            self.path_input.setText("")
            self.duration_combo.setCurrentText("1 minute")
            self.record_btn.setText("Start Recording")
            self.status_label.setText("Recording will start when category triggers match")
            self.status_label.setStyleSheet("color: gray;")
            self.settings_changed = False
            return

        print("\n📂 [AudioRecording] Loading saved settings:", settings)
        self.path_input.setText(settings.get("output_path", ""))
        self.duration_combo.setCurrentText(settings.get("duration", "1 minute"))
        
        # Restore recording state
        if settings.get("enabled", False):
            self.recording = True
            self.record_btn.setText("Stop Recording")
            self.status_label.setText(f"Recording will start when triggers match ({settings['duration']})")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.validate_path(settings["output_path"])
        else:
            self.recording = False
            self.record_btn.setText("Start Recording")
            self.status_label.setText("Recording will start when category triggers match")
            self.status_label.setStyleSheet("color: gray;")

        # Store last saved settings
        self.last_saved_settings = settings.copy()
        self.settings_changed = False

    def on_settings_changed(self, *args):
        """Called when any setting changes"""
        print("\n⚡ [AudioRecording] Settings changed")
        self.settings_changed = True
        # Get current values
        current = self.get_settings()
        if self.last_saved_settings != current:
            print("  Previous:", self.last_saved_settings)
            print("  Current:", current)

    def toggle_recording(self):
        """Toggle recording state"""
        if not self._current_category:
            QMessageBox.warning(self, "No Category", "Please select a category first")
            return
            
        if not self.recording:
            if not self.validate_path(self.path_input.text()):
                QMessageBox.warning(self, "Invalid Path", "Please specify a valid output path")
                return
                
            self.recording = True
            duration = self.duration_combo.currentText()
            path = self.path_input.text()
            
            print(f"\n🎙️ [AudioRecording] Starting recording configuration:")
            print(f"  Category: {self._current_category}")
            print(f"  Duration: {duration}")
            print(f"  Path: {path}")
            
            # Update UI
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                }
            """)
            self.status_label.setText(f"Recording will start when triggers match ({duration})")
            self.status_label.setStyleSheet("color: #4CAF50;")
            
            # Save settings immediately
            if self.audio_record_manager:
                self.audio_record_manager.set_output_path(path)
                self.audio_record_manager.set_duration(duration)
                print("  ✓ Settings saved to AudioRecordManager")
                
        else:
            self.recording = False
            print(f"\n🛑 [AudioRecording] Stopping recording for {self._current_category}")
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                }
            """)
            self.status_label.setText("Recording stopped")
            self.status_label.setStyleSheet("color: gray;")
            
        self.settings_changed = True
        self.on_settings_changed()

    def get_settings(self):
        """Get current audio recording settings"""
        settings = {
            "output_path": self.path_input.text(),
            "duration": self.duration_combo.currentText(),
            "enabled": self.recording
        }
        print("\n🎙️ [AudioRecording] Current settings:", settings)
        return settings

    def set_category(self, category_name: str):
        """Set current category and load its settings"""
        print(f"\n🎯 [AudioRecording] Setting active category to: {category_name}")
        self._current_category = category_name
        
        # Load category settings from audio_record_manager
        if self.audio_record_manager:
            settings = self.audio_record_manager.get_category_settings(category_name)
            if settings:
                print(f"  Loading saved settings: {settings}")
                self.load_settings(settings)
            else:
                print("  No saved settings found, using defaults")
                self.load_settings({})

    def store_settings(self):
        """Store current settings to manager"""
        if not self._current_category:
            print("  ✗ No category selected, can't store settings")
            return
            
        if self.audio_record_manager:
            settings = self.get_settings()
            print(f"\n💾 [AudioRecording] Storing settings for {self._current_category}: {settings}")
            self.audio_record_manager.set_category_settings(self._current_category, settings)
            self.last_saved_settings = settings.copy()
            self.settings_changed = False
