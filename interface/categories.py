from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QSlider,
    QScrollArea,
    QFrame,
    QRadioButton,
    QMessageBox,
    QApplication,
    QDialog,  # Added QDialog for the preview window
    QLineEdit,  # Add this import
)
from PyQt5.QtCore import Qt, QSize, pyqtSlot, QObject, QThread, pyqtSignal  # Added QObject, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap  # Add this import
import json
import os  # Added import os
from utils.wallpaper_manager import WallpaperManager
from interface.app_folder import AppFolderManager
from utils.folder_manager import FolderManager
from utils.sudo_helper import SudoHelper  # Add this import
from utils.sound_manager import SoundManager  # Add this import at the top with other imports
from .audio_recording import AudioRecordingSettings
from utils.audio_record_manager import AudioRecordManager  # Add this import

class PreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wallpaper Preview")
        layout = QVBoxLayout()
        
        # Create image label
        image_label = QLabel()
        pixmap = QPixmap(image_path)
        # Scale pixmap to reasonable size while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        
        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        layout.addWidget(image_label)
        layout.addWidget(close_btn)
        self.setLayout(layout)

class SaveWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, category_states, category_states_file):
        super().__init__()
        self.category_states = category_states
        self.category_states_file = category_states_file

    def run(self):
        try:
            with open(self.category_states_file, "w") as f:
                json.dump(self.category_states, f, indent=4)
            self.finished.emit()
        except OSError as e:
            self.error.emit(str(e))

class CategoriesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.tag_checkboxes = {}  # Initialize tag_checkboxes here
        # Initialize managers first
        self.audio_record_manager = AudioRecordManager()
        self.sound_manager = SoundManager()
        
        # First create and configure SudoHelper
        self.sudo_helper = SudoHelper()
        # Load sudo password from settings
        settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                if "sudo_password" in settings:
                    self.sudo_helper.set_sudo_password(settings["sudo_password"])
        except Exception as e:
            print(f"Error loading sudo password: {e}")

        # Create FolderManager with configured SudoHelper
        self.folder_manager = FolderManager(sudo_helper=self.sudo_helper)
        
        self.tags_data_file = os.path.join(os.path.dirname(__file__), "tags.json")  # Updated path
        self.category_states_file = os.path.join(os.path.dirname(__file__), "category_states.json")
        self.tags = {}  # Initialize tags attribute
        self.category_states = {}  # Holds trigger check states, etc. by category
        self.current_category = None  # Track which category is active
        self.load_category_states_from_file()  # Load saved states from file
        self.initUI()
        self.set_initial_category()  # Set the initial category to ensure settings can be saved immediately
        self.wallpaper_manager = WallpaperManager()
        self.audio_settings = None  # Will be initialized in initUI
        self.tag_checkboxes = {}  # Initialize this dictionary appropriately

    def initUI(self):
        layout = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Category selector section at top
        category_frame = QFrame()
        category_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        category_layout = QHBoxLayout()  # Changed to QHBoxLayout for horizontal placement
        
        header_label = QLabel("Current Category")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        categories = ["Home", "School", "Work", "Partner", "Private", "Custom"]
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("QComboBox { padding: 5px; min-width: 200px; }")
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        
        # Add Save Settings button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(lambda: self.store_category_settings(self.current_category))
        category_layout.addWidget(header_label)
        category_layout.addWidget(self.category_combo)
        category_layout.addWidget(save_button)  # Add button to the layout
        
        category_frame.setLayout(category_layout)
        
        # Add some spacing around the category selector
        scroll_layout.addWidget(category_frame)
        scroll_layout.addSpacing(20)  # Add space between category and other sections

        # Triggers section
        self.triggers_group = QGroupBox("Triggers")  # Changed to instance variable
        self.triggers_layout = QVBoxLayout()        # Changed to instance variable
        
        # Load saved tags from tags.json
        try:
            with open(self.tags_data_file, "r") as f:
                tags = json.load(f)
        except FileNotFoundError:
            tags = {}
            print("tags.json not found. No tags loaded.")
        except json.JSONDecodeError:
            tags = {}
            print("tags.json is not a valid JSON file. No tags loaded.")
        
        # Iterate through each trigger type and create checkboxes for tags
        for trigger_type, tag_list in tags.items():
            # Create a label for the trigger type
            trigger_label = QLabel(f"{trigger_type} Tags")
            trigger_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            self.triggers_layout.addWidget(trigger_label)
            
            # Create a group box for each trigger's tags
            tags_group = QGroupBox()
            tags_layout = QVBoxLayout()
            
            for tag in tag_list:
                checkbox = QCheckBox(tag["name"])
                tags_layout.addWidget(checkbox)
                self.tag_checkboxes[tag["name"]] = checkbox
            
            tags_group.setLayout(tags_layout)
            self.triggers_layout.addWidget(tags_group)
        
        self.triggers_group.setLayout(self.triggers_layout)
        scroll_layout.addWidget(self.triggers_group)

        # Settings section
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()

        # Wallpaper section with preview
        wallpaper_layout = QHBoxLayout()
        wallpaper_btn = QPushButton("Change Wallpaper")
        preview_btn = QPushButton("Preview Wallpaper")
        wallpaper_btn.clicked.connect(self.change_wallpaper)
        preview_btn.clicked.connect(self.preview_wallpaper)
        wallpaper_layout.addWidget(wallpaper_btn)
        wallpaper_layout.addWidget(preview_btn)
        settings_layout.addLayout(wallpaper_layout)

        # Application and Folder Management
        manage_layout = QHBoxLayout()
        apps_btn = QPushButton("Manage Applications")
        folders_btn = QPushButton("Manage Folders")
        apps_btn.clicked.connect(lambda: self.open_app_folder_manager("applications"))
        folders_btn.clicked.connect(lambda: self.open_app_folder_manager("folders"))
        manage_layout.addWidget(apps_btn)
        manage_layout.addWidget(folders_btn)
        settings_layout.addLayout(manage_layout)
        
        settings_group.setLayout(settings_layout)
        scroll_layout.addWidget(settings_group)

        # 1. Audio & Sound Management
        audio_group = QGroupBox("Audio & Sound Management")
        audio_layout = QVBoxLayout()

        # Volume Control with memory of last state
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        # Default to last saved volume or 50%
        last_volume = self.category_states.get(self.current_category, {}).get("sound", {}).get("volume", 50)
        self.volume_slider.setValue(last_volume)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(10)
        self.volume_value = QLabel(f"{last_volume}%")
        self.volume_slider.valueChanged.connect(self.update_volume_display)
        self.mute_checkbox = QCheckBox("Mute")
        # Default to last saved mute state
        last_mute = self.category_states.get(self.current_category, {}).get("sound", {}).get("muted", False)
        self.mute_checkbox.setChecked(last_mute)
        self.mute_checkbox.stateChanged.connect(self.on_mute_changed)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value)
        volume_layout.addWidget(self.mute_checkbox)
        audio_layout.addLayout(volume_layout)

        # Audio Recording section - pass manager when creating
        self.audio_settings = AudioRecordingSettings(audio_record_manager=self.audio_record_manager)
        audio_layout.addWidget(self.audio_settings)

        audio_group.setLayout(audio_layout)
        scroll_layout.addWidget(audio_group)

        # 2. Camera & Video Settings
        camera_group = QGroupBox("Camera & Video Settings")
        camera_layout = QVBoxLayout()

        # Camera controls
        camera_controls = QHBoxLayout()
        self.camera_checkbox = QCheckBox("Enable Camera")
        self.camera_checkbox.setChecked(True)
        self.camera_checkbox.stateChanged.connect(self.toggle_camera)
        camera_controls.addWidget(self.camera_checkbox)
        camera_layout.addLayout(camera_controls)

        # Photo capture section
        photo_group = QGroupBox("Photo Capture")
        photo_layout = QVBoxLayout()
        
        # Interval selection
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Capture Interval:")
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["10 seconds", "20 seconds", "30 seconds", "60 seconds"])
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_combo)
        photo_layout.addLayout(interval_layout)

        # Output folder for photos
        photo_folder_layout = QHBoxLayout()
        self.photo_path = QLineEdit()
        self.photo_path.setPlaceholderText("Select output folder for photos...")
        photo_browse_btn = QPushButton("Browse")
        photo_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.photo_path))
        photo_folder_layout.addWidget(self.photo_path)
        photo_folder_layout.addWidget(photo_browse_btn)
        photo_layout.addLayout(photo_folder_layout)

        # Photo capture button
        self.photo_btn = QPushButton("Start Photo Capture")
        self.photo_btn.setCheckable(True)
        self.photo_btn.clicked.connect(self.toggle_photo_capture)
        photo_layout.addWidget(self.photo_btn)

        photo_group.setLayout(photo_layout)
        camera_layout.addWidget(photo_group)

        # Video recording section
        video_group = QGroupBox("Video Recording")
        video_layout = QVBoxLayout()
        
        # Duration selection
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Recording Duration:")
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["1 minute", "2 minutes", "5 minutes", "10 minutes", "30 minutes"])
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_combo)
        video_layout.addLayout(duration_layout)

        # Output folder for videos
        video_folder_layout = QHBoxLayout()
        self.video_path = QLineEdit()
        self.video_path.setPlaceholderText("Select output folder for videos...")
        video_browse_btn = QPushButton("Browse")
        video_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.video_path))
        video_folder_layout.addWidget(self.video_path)
        video_folder_layout.addWidget(video_browse_btn)
        video_layout.addLayout(video_folder_layout)

        # Record button
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.toggle_video_recording)
        video_layout.addWidget(self.record_btn)

        video_group.setLayout(video_layout)
        camera_layout.addWidget(video_group)

        camera_group.setLayout(camera_layout)
        scroll_layout.addWidget(camera_group)

        # 3. Power & Device Management with Display & Screen Capture
        power_group = QGroupBox("Power & Device Management")
        power_layout = QVBoxLayout()

        # Power control buttons in two rows
        power_row1 = QHBoxLayout()
        power_row2 = QHBoxLayout()

        # First row buttons
        poweroff_btn = QPushButton("Power Off")
        lock_btn = QPushButton("Lock")
        
        # Second row buttons
        sleep_btn = QPushButton("Sleep")
        restart_btn = QPushButton("Restart")

        # Set button styles
        button_style = """
            QPushButton {
                padding: 10px;
                min-width: 100px;
            }
            QPushButton:checked {
                background-color: #ff4444;
                color: white;
            }
        """
        for btn in [poweroff_btn, lock_btn, sleep_btn, restart_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet(button_style)

        # Connect signals
        poweroff_btn.clicked.connect(self.toggle_poweroff)
        lock_btn.clicked.connect(self.toggle_lock)
        sleep_btn.clicked.connect(self.toggle_sleep)
        restart_btn.clicked.connect(self.toggle_restart)

        # Add buttons to rows
        power_row1.addWidget(poweroff_btn)
        power_row1.addWidget(lock_btn)
        power_row2.addWidget(sleep_btn)
        power_row2.addWidget(restart_btn)

        # Add rows to layout
        power_layout.addLayout(power_row1)
        power_layout.addLayout(power_row2)

        # Display & Screen Capture section
        display_group = QGroupBox("Display & Screen Capture")
        display_layout = QVBoxLayout()

        # Display controls
        display_controls = QGroupBox("Display Controls")
        display_controls_layout = QVBoxLayout()

        # Brightness Control
        brightness_layout = QHBoxLayout()
        brightness_label = QLabel("Brightness:")
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.set_brightness)
        brightness_layout.addWidget(brightness_label)
        brightness_layout.addWidget(self.brightness_slider)
        display_controls_layout.addLayout(brightness_layout)

        # Screensaver Settings
        screensaver_layout = QHBoxLayout()
        self.screensaver_checkbox = QCheckBox("Enable Screensaver")
        self.screensaver_checkbox.setChecked(False)
        self.screensaver_checkbox.stateChanged.connect(self.toggle_screensaver)
        screensaver_layout.addWidget(self.screensaver_checkbox)
        display_controls_layout.addLayout(screensaver_layout)

        display_controls.setLayout(display_controls_layout)
        display_layout.addWidget(display_controls)

        # Screenshot section
        screenshot_group = QGroupBox("Screenshot Capture")
        screenshot_layout = QVBoxLayout()
        
        # Interval selection for screenshots
        screenshot_interval_layout = QHBoxLayout()
        screenshot_interval_label = QLabel("Capture Interval:")
        self.screenshot_interval_combo = QComboBox()
        self.screenshot_interval_combo.addItems(["10 seconds", "20 seconds", "30 seconds", "60 seconds"])
        screenshot_interval_layout.addWidget(screenshot_interval_label)
        screenshot_interval_layout.addWidget(self.screenshot_interval_combo)
        screenshot_layout.addLayout(screenshot_interval_layout)

        # Output folder for screenshots
        screenshot_folder_layout = QHBoxLayout()
        self.screenshot_path = QLineEdit()
        self.screenshot_path.setPlaceholderText("Select output folder for screenshots...")
        screenshot_browse_btn = QPushButton("Browse")
        screenshot_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.screenshot_path))
        screenshot_folder_layout.addWidget(self.screenshot_path)
        screenshot_folder_layout.addWidget(screenshot_browse_btn)
        screenshot_layout.addLayout(screenshot_folder_layout)

        # Screenshot capture button
        self.screenshot_btn = QPushButton("Start Screenshot Capture")
        self.screenshot_btn.setCheckable(True)
        self.screenshot_btn.clicked.connect(self.toggle_screenshot_capture)
        screenshot_layout.addWidget(self.screenshot_btn)

        screenshot_group.setLayout(screenshot_layout)
        display_layout.addWidget(screenshot_group)

        # Screen recording section
        screen_recording_group = QGroupBox("Screen Recording")
        screen_layout = QVBoxLayout()
        
        # Duration selection for screen recording
        screen_duration_layout = QHBoxLayout()
        screen_duration_label = QLabel("Recording Duration:")
        self.screen_duration_combo = QComboBox()
        self.screen_duration_combo.addItems(["1 minute", "2 minutes", "5 minutes", "10 minutes", "30 minutes"])
        screen_duration_layout.addWidget(screen_duration_label)
        screen_duration_layout.addWidget(self.screen_duration_combo)
        screen_layout.addLayout(screen_duration_layout)

        # Output folder for screen recordings
        screen_folder_layout = QHBoxLayout()
        self.screen_path = QLineEdit()
        self.screen_path.setPlaceholderText("Select output folder for screen recordings...")
        screen_browse_btn = QPushButton("Browse")
        screen_browse_btn.clicked.connect(lambda: self.browse_output_folder(self.screen_path))
        screen_folder_layout.addWidget(self.screen_path)
        screen_folder_layout.addWidget(screen_browse_btn)
        screen_layout.addLayout(screen_folder_layout)

        # Screen recording button
        self.screen_record_btn = QPushButton("Start Screen Recording")
        self.screen_record_btn.setCheckable(True)
        self.screen_record_btn.clicked.connect(self.toggle_screen_recording)
        screen_layout.addWidget(self.screen_record_btn)

        screen_recording_group.setLayout(screen_layout)
        display_layout.addWidget(screen_recording_group)

        display_group.setLayout(display_layout)
        power_layout.addWidget(display_group)

        power_group.setLayout(power_layout)
        scroll_layout.addWidget(power_group)

        # 5. Network & Connectivity Settings
        network_group = QGroupBox("Network & Connectivity Settings")
        network_layout = QVBoxLayout()

        # Simple network controls
        wifi_layout = QHBoxLayout()
        wifi_btn = QPushButton("Turn Off Wi-Fi")
        wifi_btn.setCheckable(True)
        wifi_btn.clicked.connect(self.toggle_wifi)
        
        bluetooth_btn = QPushButton("Turn Off Bluetooth")
        bluetooth_btn.setCheckable(True)
        bluetooth_btn.clicked.connect(self.toggle_bluetooth)
        
        wifi_layout.addWidget(wifi_btn)
        wifi_layout.addWidget(bluetooth_btn)
        network_layout.addLayout(wifi_layout)

        network_group.setLayout(network_layout)
        scroll_layout.addWidget(network_group)

        # 6. Notification Settings
        notification_group = QGroupBox("Notification Settings")
        notification_layout = QVBoxLayout()

        # Do Not Disturb mode
        dnd_layout = QHBoxLayout()
        self.dnd_checkbox = QCheckBox("Do Not Disturb")
        self.dnd_checkbox.stateChanged.connect(self.toggle_do_not_disturb)
        dnd_layout.addWidget(self.dnd_checkbox)
        notification_layout.addLayout(dnd_layout)

        # Basic notification toggle
        self.notifications_checkbox = QCheckBox("Enable Notifications")
        self.notifications_checkbox.setChecked(True)
        self.notifications_checkbox.stateChanged.connect(self.toggle_notifications)
        notification_layout.addWidget(self.notifications_checkbox)

        notification_group.setLayout(notification_layout)
        scroll_layout.addWidget(notification_group)

        # 7. Browser Controls
        browser_group = QGroupBox("Browser Controls")
        browser_layout = QVBoxLayout()

        # Browser selection
        browser_select = QHBoxLayout()
        browser_label = QLabel("Select Browser:")
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome", "Firefox", "Safari", "Edge"])
        browser_select.addWidget(browser_label)
        browser_select.addWidget(self.browser_combo)
        browser_layout.addLayout(browser_select)

        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to open...")
        go_btn = QPushButton("Go")
        go_btn.clicked.connect(self.open_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(go_btn)
        browser_layout.addLayout(url_layout)

        # Browser actions
        actions_layout = QHBoxLayout()
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.clicked.connect(self.clear_browser_history)
        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.clicked.connect(self.clear_browser_cache)
        
        actions_layout.addWidget(clear_history_btn)
        actions_layout.addWidget(clear_cache_btn)
        browser_layout.addLayout(actions_layout)

        browser_group.setLayout(browser_layout)
        scroll_layout.addWidget(browser_group)

        self.scroll.setWidget(scroll_content)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def set_initial_category(self):
        # Set the initial category to "Home"
        initial_category = "Home"
        if self.category_combo.findText(initial_category) != -1:
            self.category_combo.setCurrentText(initial_category)
            self.current_category = initial_category  # Ensure current_category is set
            self.load_category_settings(initial_category)

    def on_category_changed(self, new_category):
        """Handle category changes - only load settings, don't save"""
        print(f"\n📂 [CategoriesTab] Switching to category: {new_category}")
        self.current_category = new_category
        self.load_category_settings(new_category)

    def store_category_settings(self, category):
        """Store updated tag states for a given category"""
        if not category or category.strip().lower() == "none":
            QMessageBox.warning(self, "Error", "Please select a category first")
            return

        try:
            # Load existing states or create new
            cat_file = os.path.join(os.path.dirname(__file__), "category_states.json")
            if os.path.exists(cat_file):
                with open(cat_file, 'r') as f:
                    cat_states = json.load(f)
            else:
                cat_states = {}

            # Initialize or update the category
            if category not in cat_states:
                cat_states[category] = {}

            # Save checkbox states
            for tag_name, checkbox in self.tag_checkboxes.items():
                cat_states[category][tag_name] = checkbox.isChecked()
            
            # Save audio and sound settings
            if self.audio_settings:
                cat_states[category]["audio_recording"] = self.audio_settings.get_settings()

            cat_states[category]["sound"] = {
                "muted": self.mute_checkbox.isChecked(),
                "volume": self.volume_slider.value()
            }

            self.category_states = cat_states

            # Write to file
            os.makedirs(os.path.dirname(cat_file), exist_ok=True)
            with open(cat_file, 'w') as f:
                json.dump(cat_states, f, indent=4)
            
            QMessageBox.information(self, "Success", f"Settings for category '{category}' saved successfully!")
            print(f"\n💾 Category '{category}' settings saved to {cat_file}")
            print(f"Saved states: {cat_states[category]}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            print(f"Error saving category settings: {e}")

    def save_settings_async(self):
        self.thread = QThread()
        self.worker = SaveWorker(self.category_states, self.category_states_file)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.handle_save_error)
        self.worker.finished.connect(self.handle_save_success)  # Connect finished to success handler
        self.thread.start()

    def handle_save_success(self):
        pass

    def handle_save_error(self, error_message):
        print(f"  ✗ Error saving settings: {error_message}")
        QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n{error_message}")

    def load_category_settings(self, category):
        """Load all settings for a category"""
        print(f"\n📂 [CategoriesTab] Loading settings for category: {category}")

        # Load saved settings
        saved = self.category_states.get(category, {})

        # Load audio settings
        if self.audio_settings:
            saved_audio = saved.get("audio_recording", {})
            print(f"  Loading audio settings: {saved_audio}")
            self.audio_settings.load_settings(saved_audio)
            
            # Set the loaded settings to the audio record manager
            self.audio_record_manager.set_category_settings(category, saved_audio)

        # Load sound settings
        sound_settings = saved.get("sound", {"muted": False, "volume": 50})
        self.mute_checkbox.setChecked(sound_settings.get("muted", False))
        self.volume_slider.setValue(sound_settings.get("volume", 50))

        audio_settings = saved.get("audio_settings", {})
        if "volume" in audio_settings:
            self.volume_slider.setValue(audio_settings["volume"])
            self.mute_checkbox.setChecked(audio_settings["mute"])

        # Immediately refresh the UI with brand-new triggers
        self.refresh_categories_ui()
        # Then apply previously saved checks, if any
        saved = self.category_states.get(category, {})
        idx = 0
        while idx < self.triggers_layout.count():
            item = self.triggers_layout.itemAt(idx)
            if item and item.widget():
                widget = item.widget()
                # Only proceed if it's a QGroupBox with a valid layout
                if isinstance(widget, QGroupBox) and widget.layout() is not None:
                    for cb_idx in range(widget.layout().count()):
                        w = widget.layout().itemAt(cb_idx).widget()
                        if isinstance(w, QCheckBox) and w.text() in saved:
                            w.setChecked(saved[w.text()])
                            # print(f" - {w.text()}: {'Checked' if saved[w.text()] else 'Unchecked'}")
            idx += 1
        # print(f"Category settings for '{category}' have been loaded.")

        # Load and apply audio recording settings if they exist
        if self.audio_settings:
            saved_audio = self.category_states.get(category, {}).get("audio_recording", {})
            if saved_audio:
                print(f"\n📂 [CategoriesTab] Loading audio settings for {category}:")
                print(f"  Settings: {saved_audio}")
                self.audio_settings.load_settings(saved_audio)
            else:
                print(f"\n📂 [CategoriesTab] No saved audio settings for {category}")
                self.audio_settings.load_settings({})  # Reset to defaults

    def refresh_categories_ui(self):
        # Clear existing widgets in the triggers_layout
        while self.triggers_layout.count():
            child = self.triggers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Reload tags from file
        try:
            with open(self.tags_data_file, "r") as f:
                tags = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            tags = {}
            print("tags.json not found or is invalid. No tags loaded.")

        # Re-populate the triggers_layout with updated tags
        for trigger_type, tag_list in tags.items():
            # Create a label for the trigger type
            trigger_label = QLabel(f"{trigger_type} Tags")
            trigger_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            self.triggers_layout.addWidget(trigger_label)
            
            # Create a group box for each trigger's tags
            tags_group = QGroupBox()
            tags_layout = QVBoxLayout()
            
            for tag in tag_list:
                checkbox = QCheckBox(tag["name"])
                tags_layout.addWidget(checkbox)
                self.tag_checkboxes[tag["name"]] = checkbox
            
            tags_group.setLayout(tags_layout)
            self.triggers_layout.addWidget(tags_group)

        # Ensure the layout is updated
        self.triggers_layout.update()

    def load_category_states_from_file(self):
        if os.path.isfile(self.category_states_file):
            try:
                with open(self.category_states_file, "r") as f:
                    self.category_states = json.load(f)
                # print(f"Loaded category states from {self.category_states_file}")
            except (json.JSONDecodeError, OSError) as e:
                # print(f"Error loading category_states.json: {e}. Resetting category states.")
                self.reset_category_states()
        else:
            # print("category_states.json not found. Initializing default categories.")
            self.reset_category_states()

    def save_category_states_to_file(self):
        try:
            with open(self.category_states_file, "w") as f:
                json.dump(self.category_states, f, indent=4)
            # print(f"Category states saved to {self.category_states_file}")
        except OSError as e:
            # print(f"Error writing to category_states.json: {e}.")
            pass

    def reset_category_states(self):
        default_categories = ["Home", "School", "Work", "Partner", "Private", "Custom"]
        self.category_states = {category: {} for category in default_categories}
        self.save_category_states_to_file()
        # print("Default category states have been initialized.")

    def change_wallpaper(self):
        if not self.current_category:
            QMessageBox.warning(self, "Error", "Please select a category first")
            return
            
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wallpaper",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_name:
            success, result = self.wallpaper_manager.save_wallpaper(
                self.current_category, 
                file_name
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Wallpaper saved for category {self.current_category}"
                )
            else:
                QMessageBox.warning(self, "Error", f"Failed to save wallpaper: {result}")

    def preview_wallpaper(self):
        """Show preview of current category's wallpaper"""
        if not self.current_category:
            QMessageBox.warning(self, "Error", "Please select a category first")
            return
            
        wallpaper_path = self.wallpaper_manager.get_category_wallpaper(self.current_category)
        if (wallpaper_path and os.path.exists(wallpaper_path)):
            preview_dialog = PreviewDialog(wallpaper_path, self)
            preview_dialog.exec_()
        else:
            QMessageBox.information(
                self,
                "No Wallpaper",
                f"No wallpaper set for category {self.current_category}"
            )

    # Example handler methods (implementations needed)
    def set_volume(self, value):
        # Implement volume adjustment logic
        pass

    def toggle_mute(self, state):
        # Implement mute/unmute logic
        pass

    def toggle_microphone(self, state):
        # Implement microphone enable/disable
        pass

    def change_playback_device(self, device):
        # Implement playback device selection
        pass

    def change_recording_device(self, device):
        # Implement recording device selection
        pass

    def toggle_camera(self, state):
        # Implement camera enable/disable
        pass

    def set_resolution(self, resolution):
        # Implement resolution setting
        pass

    def set_frame_rate(self, rate):
        # Implement frame rate setting
        pass

    def shutdown_device(self):
        # Implement device shutdown
        pass

    def restart_device(self):
        # Implement device restart
        pass

    def sleep_device(self):
        # Implement device sleep
        pass

    def toggle_auto_lock(self, state):
        # Implement auto-lock toggle
        pass

    def install_application(self):
        # Implement application installation
        pass

    def uninstall_application(self):
        # Implement application uninstallation
        pass

    def enable_application(self):
        # Implement enabling an application
        pass

    def disable_application(self):
        # Implement disabling an application
        pass

    def lock_application(self):
        # Implement locking an application
        pass

    def hide_folder(self):
        # Implement hiding a folder
        pass

    def unhide_folder(self):
        # Implement unhiding a folder
        pass

    def lock_folder(self):
        # Implement locking a folder
        pass

    def unlock_folder(self):
        # Implement unlocking a folder
        pass

    def toggle_wifi(self, checked):
        """Toggle Wi-Fi on/off"""
        sender = self.sender()
        if checked:
            sender.setText("Turn On Wi-Fi")
            # Implement Wi-Fi disable
        else:
            sender.setText("Turn Off Wi-Fi")
            # Implement Wi-Fi enable

    def toggle_bluetooth(self, checked):
        """Toggle Bluetooth on/off"""
        sender = self.sender()
        if checked:
            sender.setText("Turn On Bluetooth")
            # Implement Bluetooth disable
        else:
            sender.setText("Turn Off Bluetooth")
            # Implement Bluetooth enable

    def toggle_do_not_disturb(self, state):
        """Toggle Do Not Disturb mode"""
        if state:
            self.notifications_checkbox.setEnabled(False)
            # Implement DND enable
        else:
            self.notifications_checkbox.setEnabled(True)
            # Implement DND disable

    def toggle_notifications(self, state):
        """Toggle system notifications"""
        # Implement notification toggle
        pass

    def open_url(self):
        """Open URL in selected browser"""
        browser = self.browser_combo.currentText()
        url = self.url_input.text()
        if url:
            # Implement URL opening in selected browser
            pass

    def clear_browser_history(self):
        """Clear history of selected browser"""
        browser = self.browser_combo.currentText()
        # Implement history clearing for selected browser
        QMessageBox.information(self, "Success", f"Cleared {browser} history")

    def clear_browser_cache(self):
        """Clear cache of selected browser"""
        browser = self.browser_combo.currentText()
        # Implement cache clearing for selected browser
        QMessageBox.information(self, "Success", f"Cleared {browser} cache")

    def set_brightness(self, value):
        # Implement brightness adjustment
        pass

    def toggle_screensaver(self, state):
        # Implement screensaver enable/disable
        pass

    def toggle_screen_recording(self, state):
        # Implement screen recording enable/disable
        pass

    def toggle_screenshot_capture(self, checked):
        """Toggle screenshot capture"""
        if checked:
            if not self.screenshot_path.text():
                QMessageBox.warning(self, "Error", "Please select output folder first")
                self.screenshot_btn.setChecked(False)
                return
            self.screenshot_btn.setText("Stop Screenshot Capture")
            # Screenshot capture functionality will be implemented later
        else:
            self.screenshot_btn.setText("Start Screenshot Capture")
            # Stop screenshot functionality will be implemented later

    def toggle_poweroff(self, checked):
        """Toggle power off state"""
        sender = self.sender()
        if checked:
            sender.setText("Power Off (Armed)")
        else:
            sender.setText("Power Off")

    def toggle_lock(self, checked):
        """Toggle lock state"""
        sender = self.sender()
        if checked:
            sender.setText("Lock (Armed)")
        else:
            sender.setText("Lock")

    def toggle_sleep(self, checked):
        """Toggle sleep state"""
        sender = self.sender()
        if checked:
            sender.setText("Sleep (Armed)")
        else:
            sender.setText("Sleep")

    def toggle_restart(self, checked):
        """Toggle restart state"""
        sender = self.sender()
        if checked:
            sender.setText("Restart (Armed)")
        else:
            sender.setText("Restart")

    def closeEvent(self, event):
        if self.current_category:
            self.store_category_settings(self.current_category)
            # Wait for the save thread to finish
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.wait()
        event.accept()

    def open_app_folder_manager(self, active_tab):
        """Open the App & Folder Manager dialog for current category"""
        if not self.current_category:
            QMessageBox.warning(self, "Error", "Please select a category first")
            return
            
        dialog = AppFolderManager(
            active_tab=active_tab,
            category=self.current_category,
            parent=self
        )
        dialog.exec_()

    def update_volume_display(self, value):
        """Update the display and apply the volume"""
        self.volume_value.setText(f"{value}%")
        print(f"\n📢 [CategoriesTab] Setting volume to {value}%")
        self.sound_manager.set_volume(value)

    def browse_recording_folder(self):
        """Open folder browser for recording output"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def toggle_recording(self, checked):
        """Toggle recording state"""
        if checked:
            self.record_btn.setText("Stop Recording")
            # Recording functionality will be implemented later
        else:
            self.record_btn.setText("Start Recording")
            # Stop recording functionality will be implemented later

    def browse_output_folder(self, line_edit):
        """Browse for output folder and set it in the given line edit"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            line_edit.setText(folder)

    def toggle_photo_capture(self, checked):
        """Toggle interval photo capture"""
        if checked:
            if not self.photo_path.text():
                QMessageBox.warning(self, "Error", "Please select output folder first")
                self.photo_btn.setChecked(False)
                return
            self.photo_btn.setText("Stop Photo Capture")
            # Photo capture functionality will be implemented later
        else:
            self.photo_btn.setText("Start Photo Capture")
            # Stop photo capture functionality will be implemented later

    def toggle_video_recording(self, checked):
        """Toggle video recording"""
        if checked:
            if not self.video_path.text():
                QMessageBox.warning(self, "Error", "Please select output folder first")
                self.record_btn.setChecked(False)
                return
            self.record_btn.setText("Stop Recording")
            # Video recording functionality will be implemented later
        else:
            self.record_btn.setText("Start Recording")
            # Stop video recording functionality will be implemented later

    @pyqtSlot(str, list)
    def update_categories(self, trigger_type, tags):
        """Update UI with new trigger tags and save to file"""
        try:
            # Load current tags
            with open(self.tags_data_file, "r") as f:
                current_tags = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            current_tags = {}

        # Update tags for this trigger type
        current_tags[trigger_type] = [
            tag.to_dict() if hasattr(tag, 'to_dict') else tag
            for tag in tags
        ]

        # Save updated tags
        with open(self.tags_data_file, "w") as f:
            json.dump(current_tags, f, indent=4)

        # Refresh UI
        self.refresh_categories_ui()

    def on_mute_changed(self, state):
        """Update UI state and apply mute setting"""
        self.volume_slider.setEnabled(not state)
        self.volume_value.setEnabled(not state)
        print(f"\n📢 [CategoriesTab] Setting mute state to {state}")
        self.sound_manager.toggle_mute(state)
