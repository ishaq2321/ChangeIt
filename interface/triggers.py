from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                           QLabel, QGroupBox, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
                           QInputDialog, QMessageBox, QDialog, QFormLayout,
                           QProgressBar, QSpinBox, QFileDialog, QTextBrowser,
                           QScrollArea, QWidget, QGridLayout, QFrame, 
                           QToolButton, QSizePolicy, QApplication)  # Added QApplication
from PyQt5.QtCore import Qt, QSize, pyqtSignal  # Added pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QIcon  # Added QIcon
import os  # Add this import
import re
import requests
from triggers.wifi import WiFiScanner, WiFiTag
from triggers.location import LocationFetcher, LocationTag
from triggers.bluetooth import BluetoothScanner, BluetoothTag
from triggers.camera import ImageProcessor, CameraTag, get_image_guidelines
from triggers.mic import AudioRecorder, AudioProcessor, MicTag
from triggers.keyboard import KeyboardTag
import numpy as np  # Add this import
import scipy.io.wavfile as wav  # Add this import
import sounddevice as sd  # Add this import
import json  # Add this import
from settings.monitor import BackgroundMonitor

class ImagePreviewWidget(QFrame):
    def __init__(self, image_path, grid_widget):
        super().__init__()
        self.image_path = image_path
        self.grid_widget = grid_widget  # Store reference to grid widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Remove button
        remove_btn = QToolButton(self)
        remove_btn.setText("×")
        remove_btn.setStyleSheet("""
            QToolButton {
                color: red;
                font-weight: bold;
                border: none;
                background: white;
                border-radius: 10px;
            }
            QToolButton:hover {
                background: #ffeeee;
            }
        """)
        remove_btn.clicked.connect(self.remove_image)
        
        # Image preview
        image_label = QLabel()
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            QSize(150, 150),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px;
                border-radius: 3px;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(remove_btn, alignment=Qt.AlignRight)
        layout.addWidget(image_label)
        layout.addWidget(self.status_label)
        
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("background-color: white;")

    def remove_image(self):
        # Call remove_image on the grid widget instead of parent
        self.grid_widget.remove_image(self.image_path)

    def update_status(self, message, style='normal'):
        styles = {
            'success': """
                color: #28a745;
                background-color: #f0fff0;
            """,
            'error': """
                color: #dc3545;
                background-color: #fff3f3;
            """,
            'normal': """
                color: #666666;
                background-color: #f8f9fa;
            """
        }
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 2px;
                border-radius: 3px;
                font-size: 11px;
                {styles.get(style, styles['normal'])}
            }}
        """)

    def disconnect(self):
        """Disconnect all signals before deletion"""
        try:
            self.findChild(QToolButton).clicked.disconnect()
        except:
            pass

    def remove_image(self):
        """Safely trigger image removal"""
        try:
            if hasattr(self, 'grid_widget') and self.grid_widget:
                self.grid_widget.remove_image(self.image_path)
        except Exception as e:
            print(f"Error in remove_image: {str(e)}")

class ImageGridWidget(QScrollArea):
    image_removed = pyqtSignal(int)  # New signal for image count updates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent  # Store reference to parent widget
        self.main_widget = QWidget()
        self.grid_layout = QGridLayout(self.main_widget)
        self.setWidget(self.main_widget)
        self.setWidgetResizable(True)
        self.image_widgets = {}
        
    def add_image(self, image_path):
        row = len(self.image_widgets) // 3
        col = len(self.image_widgets) % 3
        preview = ImagePreviewWidget(image_path, self)  # Pass self as grid_widget
        self.grid_layout.addWidget(preview, row, col)
        self.image_widgets[image_path] = preview
        
    def remove_image(self, image_path):
        """Safely remove an image widget"""
        try:
            if image_path in self.image_widgets:
                widget = self.image_widgets[image_path]
                # Disconnect any signals/slots first
                widget.disconnect()
                # Remove from layout
                self.grid_layout.removeWidget(widget)
                # Schedule widget for deletion
                widget.setParent(None)
                widget.deleteLater()
                # Remove from our tracking dict
                self.image_widgets.pop(image_path)
                # Emit count update
                self.image_removed.emit(len(self.image_widgets))
                # Schedule grid rearrangement
                QApplication.processEvents()
                self.rearrange_grid()
        except Exception as e:
            print(f"Error safely removing image: {str(e)}")
    
    def rearrange_grid(self):
        """Safely rearrange the grid"""
        try:
            # Store current widgets
            current_widgets = [(path, widget) for path, widget in self.image_widgets.items()]
            
            # Clear all items from grid
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item and item.widget():
                    item.widget().hide()
            
            # Re-add widgets to their new positions
            self.image_widgets.clear()
            for idx, (path, widget) in enumerate(current_widgets):
                row, col = divmod(idx, 3)
                self.grid_layout.addWidget(widget, row, col)
                widget.show()
                self.image_widgets[path] = widget
            
        except Exception as e:
            print(f"Error rearranging grid: {str(e)}")

    def clear(self):
        """Safely clear all widgets"""
        try:
            for widget in self.image_widgets.values():
                widget.disconnect()
                widget.setParent(None)
                widget.deleteLater()
            self.image_widgets.clear()
            QApplication.processEvents()
        except Exception as e:
            print(f"Error clearing grid: {str(e)}")

class TagDialog(QDialog):
    def __init__(self, tag_name="", selected_items=None, tag_data=None):
        super().__init__()
        self.setWindowTitle("Tag Details")
        layout = QVBoxLayout()  # Changed to VBoxLayout
        
        # Name input section
        name_layout = QFormLayout()
        self.name_input = QLineEdit(tag_name)
        name_layout.addRow("Tag Name:", self.name_input)
        layout.addLayout(name_layout)
        
        # Add image preview for camera tags
        if tag_data and isinstance(tag_data, CameraTag):
            preview_scroll = QScrollArea()
            preview_widget = QWidget()
            preview_layout = QGridLayout(preview_widget)
            
            for i, image_path in enumerate(tag_data.image_paths):
                if os.path.exists(image_path):
                    img_label = QLabel()
                    pixmap = QPixmap(image_path)
                    scaled_pixmap = pixmap.scaled(
                        QSize(150, 150),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    img_label.setPixmap(scaled_pixmap)
                    row, col = i // 3, i % 3
                    preview_layout.addWidget(img_label, row, col)
            
            preview_scroll.setWidget(preview_widget)
            preview_scroll.setWidgetResizable(True)
            preview_scroll.setMinimumHeight(200)
            layout.addWidget(QLabel("Saved Images:"))
            layout.addWidget(preview_scroll)
        
        self.setLayout(layout)
        self.setMinimumWidth(500)

class TriggersTab(QWidget):
    tag_changed = pyqtSignal(str, list)  # Signal: trigger type, list of tags

    def __init__(self):
        super().__init__()
        self.tags = {}  # Dictionary to store tags for each trigger type
        self.wifi_scanner = WiFiScanner()
        self.location_fetcher = LocationFetcher()
        self.location_fetcher.location_found.connect(self.on_location_found)
        self.location_fetcher.error_occurred.connect(self.on_location_error)
        self.bluetooth_scanner = BluetoothScanner()
        self.bluetooth_scanner.devices_found.connect(self.update_bluetooth_list)
        self.bluetooth_scanner.status_update.connect(self.update_bluetooth_status)
        self.current_trigger = None  # Track current trigger
        self.current_scanner = None  # Track current active scanner
        self._scanner_active = False
        self.network_list = None  # Initialize network_list to None
        self.bluetooth_list = None  # Initialize bluetooth_list to None
        self.tags_data_file = os.path.join(os.path.dirname(__file__), "tags.json")
        self.load_tags_from_file()  # Load stored tags at startup
        self.initUI()
        self.background_monitor = BackgroundMonitor()
        self.background_monitor.start_monitoring()

    def initUI(self):
        layout = QVBoxLayout()

        # Trigger type dropdown
        triggers = ["Location", "Wifi", "Bluetooth", "Camera", "Mic", "Keyboard"]
        trigger_combo = QComboBox()
        trigger_combo.addItems(triggers)
        trigger_combo.currentTextChanged.connect(self.update_trigger_interface)
        layout.addWidget(QLabel("Select Trigger:"))
        layout.addWidget(trigger_combo)

        # Tags list section with management buttons
        tags_group = QGroupBox("Saved Tags")
        tags_layout = QVBoxLayout()

        self.tags_list = QListWidget()
        tags_layout.addWidget(self.tags_list)

        # Add management buttons
        buttons_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit Tag")
        delete_btn = QPushButton("Delete Tag")
        edit_btn.clicked.connect(self.edit_tag)
        delete_btn.clicked.connect(self.delete_tag)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        tags_layout.addLayout(buttons_layout)

        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        # Dynamic trigger content
        self.trigger_content = QGroupBox("Trigger Settings")
        self.trigger_layout = QVBoxLayout()
        self.trigger_content.setLayout(self.trigger_layout)
        layout.addWidget(self.trigger_content)
        
        self.setLayout(layout)
        self.update_trigger_interface("Location")  # Default view

    def cleanup_scanners(self):
        """Stop any active scanners before switching interfaces"""
        self._scanner_active = False
        if self.wifi_scanner and self.wifi_scanner.isRunning():
            self.wifi_scanner.stop()
            self.wifi_scanner.wait()  # Wait for thread to finish
        if self.bluetooth_scanner and self.bluetooth_scanner.isRunning():
            self.bluetooth_scanner.stop()
            self.bluetooth_scanner.wait()  # Wait for thread to finish
        self.current_scanner = None

    def update_trigger_interface(self, trigger_type):
        # First, stop any running scanners and wait for them to finish
        self.cleanup_scanners()
        
        # Store current trigger type
        self.current_trigger = trigger_type
        
        # Clear existing layout with safety checks
        if hasattr(self, 'trigger_layout'):
            def clear_layout(layout):
                if layout is not None:
                    while layout.count():
                        item = layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                        elif item.layout():
                            clear_layout(item.layout())
                            item.layout().deleteLater()
            clear_layout(self.trigger_layout)
        
        # Update tags list
        if hasattr(self, 'tags_list'):
            self.tags_list.clear()
        for tag in self.tags.get(trigger_type, []):
            self.tags_list.addItem(tag.name)
        
        # Setup specific trigger interface
        if trigger_type == "Location":
            self.setup_location_interface()
        elif trigger_type == "Wifi":
            self.setup_wifi_interface()
        elif trigger_type == "Bluetooth":
            self.setup_bluetooth_interface()
        elif trigger_type == "Camera":
            self.setup_camera_interface()
        elif trigger_type == "Mic":
            self.setup_mic_interface()
        elif trigger_type == "Keyboard":
            self.setup_keyboard_interface()

    def create_standard_tag_input(self):
        """Create standard tag input layout used across all triggers"""
        tag_layout = QHBoxLayout()
        
        self.tag_name = QLineEdit()
        self.tag_name.setPlaceholderText("Enter tag name")
        self.tag_name.setMinimumWidth(200)
        
        save_btn = QPushButton("Save Tag")
        save_btn.clicked.connect(lambda: self.save_tag(self.current_trigger))
        
        tag_layout.addWidget(self.tag_name)
        tag_layout.addWidget(save_btn)
        
        return tag_layout

    def setup_location_interface(self):
        layout = QVBoxLayout()
        
        # Tag name input at top
        layout.addLayout(self.create_standard_tag_input())
        
        # Status label for real-time feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Location input methods
        methods_group = QGroupBox("Location Input Methods")
        methods_layout = QVBoxLayout()
        
        # 1. Current Location
        current_loc_btn = QPushButton("Use Current Location")
        current_loc_btn.clicked.connect(self.fetch_current_location)
        methods_layout.addWidget(current_loc_btn)
        
        # 2. Google Maps Link
        maps_layout = QHBoxLayout()
        self.maps_input = QLineEdit()
        self.maps_input.setPlaceholderText("Paste Google Maps link")
        verify_maps_btn = QPushButton("Verify Link")
        verify_maps_btn.clicked.connect(self.verify_google_link)
        maps_layout.addWidget(self.maps_input)
        maps_layout.addWidget(verify_maps_btn)
        methods_layout.addLayout(maps_layout)
        
        # 3. Manual Coordinates
        coords_layout = QHBoxLayout()
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        self.lat_input.setPlaceholderText("Latitude")
        self.lon_input.setPlaceholderText("Longitude")
        verify_coords_btn = QPushButton("Verify Coordinates")
        verify_coords_btn.clicked.connect(self.verify_coordinates)
        
        coords_layout.addWidget(QLabel("Lat:"))
        coords_layout.addWidget(self.lat_input)
        coords_layout.addWidget(QLabel("Lon:"))
        coords_layout.addWidget(self.lon_input)
        coords_layout.addWidget(verify_coords_btn)
        methods_layout.addLayout(coords_layout)
        
        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)
        
        # Radius selection
        radius_group = QGroupBox("Coverage Radius")
        radius_layout = QHBoxLayout()
        self.radius_combo = QComboBox()
        self.radius_combo.addItems(['10m', '20m', '50m', '100m'])
        self.radius_combo.setCurrentText('50m')  # Default selection
        radius_layout.addWidget(QLabel("Select radius:"))
        radius_layout.addWidget(self.radius_combo)
        radius_group.setLayout(radius_layout)
        layout.addWidget(radius_group)
        
        # Location display
        self.location_label = QLabel("No location selected")
        self.location_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.location_label)
        
        self.trigger_layout.addLayout(layout)

    def fetch_current_location(self):
        self.status_label.setText("Fetching current location...")
        self.status_label.setStyleSheet("color: #666;")
        self.location_fetcher.get_current_location()

    def verify_google_link(self):
        link = self.maps_input.text().strip()
        if not link:
            self.status_label.setText("Please enter a Google Maps link")
            self.status_label.setStyleSheet("color: red;")
            return
            
        try:
            # Handle short URLs and app links
            if 'goo.gl' in link or 'maps.app' in link:
                # Follow redirect to get the full URL
                response = requests.get(link, allow_redirects=True)
                link = response.url
            
            # Try different patterns
            patterns = [
                r'@(-?\d+\.\d+),(-?\d+\.\d+)',  # Pattern: @lat,lng
                r'll=(-?\d+\.\d+),(-?\d+\.\d+)',  # Pattern: ll=lat,lng
                r'q=(-?\d+\.\d+),(-?\d+\.\d+)',   # Pattern: q=lat,lng
                r'center=(-?\d+\.\d+),(-?\d+\.\d+)'  # Pattern: center=lat,lng
            ]
            
            for pattern in patterns:
                match = re.search(pattern, link)
                if match:
                    lat, lon = float(match.group(1)), float(match.group(2))
                    self.lat_input.setText(str(lat))
                    self.lon_input.setText(str(lon))
                    self.verify_coordinates()
                    return
                    
            self.status_label.setText("Could not extract coordinates from link")
            self.status_label.setStyleSheet("color: red;")
            
        except requests.exceptions.RequestException:
            self.status_label.setText("Error accessing the link")
            self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.status_label.setText(f"Error processing link: {str(e)}")
            self.status_label.setStyleSheet("color: red;")

    def verify_coordinates(self):
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                self.location_fetcher.get_location_from_address(f"{lat}, {lon}")
                self.status_label.setText("Verifying coordinates...")
                self.status_label.setStyleSheet("color: #666;")
            else:
                self.status_label.setText("Invalid coordinate range")
                self.status_label.setStyleSheet("color: red;")
        except ValueError:
            self.status_label.setText("Invalid coordinate format")
            self.status_label.setStyleSheet("color: red;")

    def on_location_found(self, location):
        self.current_location = location
        self.location_label.setText(
            f"📍 Location: {location['address']}\n"
            f"📌 Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}\n"
            f"⭕ Radius: {self.radius_combo.currentText()}"
        )
        self.status_label.setText("Location verified ✓")
        self.status_label.setStyleSheet("color: green;")

    def on_location_error(self, error_message):
        QMessageBox.warning(self, "Location Error", error_message)

    def setup_wifi_interface(self):
        main_layout = QVBoxLayout()
        
        # Add tag name input at top
        main_layout.addLayout(self.create_standard_tag_input())
        
        # Scanning section
        scan_btn = QPushButton("Start Scanning")
        scan_btn.clicked.connect(self.toggle_wifi_scan)
        
        self.network_list = QListWidget()  # Assign network_list
        self.network_list.setSelectionMode(QListWidget.MultiSelection)
        
        main_layout.addWidget(scan_btn)
        main_layout.addWidget(self.network_list)
        
        self.trigger_layout.addLayout(main_layout)
        
        # Connect WiFi scanner signals after network_list is initialized
        self.wifi_scanner.wifi_list_updated.connect(self.update_wifi_list)

    def setup_bluetooth_interface(self):
        layout = QVBoxLayout()
        
        # Add tag name input at top
        layout.addLayout(self.create_standard_tag_input())
        
        # Status label
        self.bt_status_label = QLabel("")
        self.bt_status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.bt_status_label)
        
        # Scanning controls
        scan_btn = QPushButton("Start Scanning")
        scan_btn.clicked.connect(self.toggle_bluetooth_scan)
        layout.addWidget(scan_btn)
        
        # Devices list
        self.bluetooth_list = QListWidget()  # Assign bluetooth_list
        self.bluetooth_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.bluetooth_list)
        
        self.trigger_layout.addLayout(layout)

    def setup_camera_interface(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Reduce spacing
        
        # Add tag name input at top
        input_layout = self.create_standard_tag_input()
        input_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(input_layout)
        
        # Create horizontal layout
        main_content = QHBoxLayout()
        main_content.setSpacing(10)  # Reduce spacing between panels
        
        # Left side: Guidelines
        left_panel = QVBoxLayout()
        left_panel.setSpacing(2)  # Minimal spacing
        
        # Guidelines text directly in the layout
        guidelines_text = QTextBrowser()
        guidelines_text.setHtml(get_image_guidelines())
        guidelines_text.setOpenExternalLinks(True)
        guidelines_text.setMaximumWidth(250)
        guidelines_text.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: transparent;
                padding: 0px;
            }
        """)
        left_panel.addWidget(guidelines_text)
        main_content.addLayout(left_panel)
        
        # Right side: Image upload section
        upload_group = QGroupBox("Image Upload")
        upload_layout = QVBoxLayout()
        upload_layout.setSpacing(5)  # Reduce spacing
        
        # Upload controls
        controls_layout = QHBoxLayout()
        upload_btn = QPushButton("📸 Select Image(s)")
        upload_btn.clicked.connect(self.upload_images)
        self.image_counter = QLabel("No images selected")
        controls_layout.addWidget(upload_btn)
        controls_layout.addWidget(self.image_counter)
        upload_layout.addLayout(controls_layout)
        
        # Image grid
        self.image_grid = ImageGridWidget(self)
        self.image_grid.setMinimumHeight(400)
        self.image_grid.image_removed.connect(self.update_image_count)
        upload_layout.addWidget(self.image_grid, 1)
        
        # Processing indicator and status
        self.processing_bar = QProgressBar()
        self.processing_bar.setTextVisible(False)
        self.processing_bar.hide()
        upload_layout.addWidget(self.processing_bar)
        
        self.camera_status = QLabel("")
        self.camera_status.setWordWrap(True)
        self.camera_status.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
        """)
        upload_layout.addWidget(self.camera_status)
        
        upload_group.setLayout(upload_layout)
        main_content.addWidget(upload_group, 2)
        
        layout.addLayout(main_content, 1)
        self.trigger_layout.addLayout(layout)
        
        # Initialize image processor
        self.image_processor = ImageProcessor()
        self.image_processor.processing_complete.connect(self.on_processing_complete)
        self.image_processor.processing_error.connect(self.on_processing_error)
        self.image_processor.status_update.connect(self.update_camera_status)
        self.image_processor.image_processed.connect(self.on_image_processed)
        
        self.current_images = []

    def upload_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image(s)",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_names:
            self.current_images = file_names
            
            # Show processing indicator
            self.processing_bar.setMaximum(0)  # Indeterminate mode
            self.processing_bar.show()
            self.camera_status.setText("Processing images...")
            
            # Update image grid
            self.image_grid.clear()
            for path in file_names:
                self.image_grid.add_image(path)
            
            # Update counter
            count = len(file_names)
            self.image_counter.setText(f"Selected {count} image{'s' if count > 1 else ''}")
            
            # Process images
            self.image_processor.process_images(file_names)

    def on_image_removed(self, image_path):
        try:
            if image_path in self.current_images:
                self.current_images.remove(image_path)
                count = len(self.current_images)
                self.image_counter.setText(f"Selected {count} image{'s' if count > 1 else ''}")
        except Exception as e:
            print(f"Error removing image: {str(e)}")

    def setup_mic_interface(self):
        layout = QVBoxLayout()
        layout.addLayout(self.create_standard_tag_input())
        
        # Record button
        self.record_btn = QPushButton("Record Audio")
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)
        
        # Audio level indicator
        self.audio_level = QProgressBar()
        layout.addWidget(self.audio_level)
        
        # Status label
        self.mic_status = QLabel("")
        self.mic_status.setStyleSheet("color: #666;")
        layout.addWidget(self.mic_status)
        
        # Test audio button
        self.test_audio_btn = QPushButton("Test Audio")
        self.test_audio_btn.clicked.connect(self.test_audio)
        self.test_audio_btn.setEnabled(False)
        layout.addWidget(self.test_audio_btn)
        
        # Duration label
        self.duration_label = QLabel("Duration: 0 seconds")
        layout.addWidget(self.duration_label)
        
        # Guidelines
        guidelines_text = QTextBrowser()
        guidelines_text.setHtml("""
            <h3>🎤 Audio Recording Guidelines</h3>
            <ul>
                <li>Ensure a quiet environment</li>
                <li>Speak clearly and at a moderate volume</li>
                <li>Avoid background noise</li>
                <li>Keep the microphone at a consistent distance</li>
            </ul>
        """)
        layout.addWidget(guidelines_text)
        
        self.trigger_layout.addLayout(layout)
        
        # Initialize audio recorder and processor
        self.audio_recorder = AudioRecorder()
        self.audio_processor = AudioProcessor()
        
        self.audio_recorder.recording_complete.connect(self.on_recording_complete)
        self.audio_recorder.recording_error.connect(self.on_recording_error)
        self.audio_recorder.status_update.connect(self.update_mic_status)
        self.audio_recorder.audio_signal.connect(self.update_audio_level)
        
        self.audio_processor.processing_complete.connect(self.on_processing_complete)
        self.audio_processor.processing_error.connect(self.on_processing_error)
        self.audio_processor.status_update.connect(self.update_mic_status)
        
        # Store current audio path
        self.current_audio_path = None

    def toggle_recording(self):
        if self.audio_recorder.isRunning():
            self.audio_recorder.stop_recording()
            self.record_btn.setText("Record Audio")
        else:
            self.audio_recorder.start()
            self.record_btn.setText("Stop Recording")

    def on_recording_complete(self, message):
        self.update_mic_status(message)
        self.record_btn.setText("Record Audio")
        self.test_audio_btn.setEnabled(True)
        # Save the recorded audio temporarily
        temp_audio_path = os.path.join('data', 'temp_audio.wav')
        self.current_audio_path = self.audio_recorder.save_audio(temp_audio_path)
        # Analyze the recorded audio
        self.audio_processor.analyze_audio(self.current_audio_path)
        # Update duration label
        duration = self.audio_recorder.duration
        self.duration_label.setText(f"Duration: {duration:.2f} seconds")

    def on_recording_error(self, error_message):
        self.update_mic_status(error_message)
        self.record_btn.setText("Record Audio")

    def update_mic_status(self, message):
        self.mic_status.setText(message)

    def update_audio_level(self, signal):
        level = int(np.abs(signal).mean() * 100)
        self.audio_level.setValue(level)

    def test_audio(self):
        if self.current_audio_path:
            self.play_audio(self.current_audio_path)

    def play_audio(self, audio_path):
        try:
            # Play the audio using sounddevice
            data, fs = wav.read(audio_path)
            print(f"Audio data type before playing: {data.dtype}")  # Debugging statement
            if isinstance(data, np.ndarray):
                data = data.astype(np.int16)  # Convert to supported datatype
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to play audio: {str(e)}")

    def toggle_wifi_scan(self):
        if self.wifi_scanner.isRunning():
            self._scanner_active = False
            self.wifi_scanner.stop()
            self.sender().setText("Start Scanning")
            self.current_scanner = None
        else:
            self.cleanup_scanners()  # Stop other scanners first
            self._scanner_active = True
            self.wifi_scanner.start()
            self.sender().setText("Stop Scanning")
            self.current_scanner = self.wifi_scanner

    def toggle_bluetooth_scan(self):
        sender = self.sender()
        if self.bluetooth_scanner.isRunning():
            self._scanner_active = False
            self.bluetooth_scanner.stop()
            sender.setText("Start Scanning")
            self.current_scanner = None
        else:
            self.cleanup_scanners()  # Stop other scanners first
            self._scanner_active = True
            self.bluetooth_scanner.start()
            sender.setText("Stop Scanning")
            self.current_scanner = self.bluetooth_scanner

    def closeEvent(self, event):
        """Handle cleanup when widget is closed"""
        self.cleanup_scanners()
        super().closeEvent(event)

    def update_wifi_list(self, networks):
        # print("update_wifi_list called with networks:", networks)  # Debugging statement
        if not self._scanner_active:
            # print("Scanner is not active. Exiting update_wifi_list.")  # Debugging statement
            return
            
        try:
            if self.network_list is None:
                print("network_list widget not initialized.")
                return
                
            if self.current_trigger != "Wifi":
                print(f"Current trigger is {self.current_trigger}, not Wifi.")
                return
                
            self.network_list.clear()
            if not networks:
                self.network_list.addItem("No networks found.")
            for network in networks:
                self.network_list.addItem(f"{network['ssid']} ({network['signal']}%)")
        except RuntimeError:
            # print("RuntimeError encountered in update_wifi_list.")  # Debugging statement
            self.cleanup_scanners()
        except Exception as e:
            # print(f"Error updating wifi list: {str(e)}")  # Debugging statement
            self.cleanup_scanners()

    def update_bluetooth_list(self, devices):
        # Update the Bluetooth devices list in the UI
        self.bluetooth_list.clear()
        for addr, name in devices:
            item = QListWidgetItem(f"{name} ({addr})")
            self.bluetooth_list.addItem(item)
        self.tag_changed.emit("Bluetooth", self.tags.get("Bluetooth", []))

    def update_bluetooth_status(self, message):
        self.bt_status_label.setText(message)

    def save_tag(self, trigger_type):
        tag_name = self.tag_name.text().strip()
        if not tag_name:
            QMessageBox.warning(self, "Invalid Tag", "Tag name cannot be empty.")
            return
        
        # Create appropriate tag object based on trigger_type
        if trigger_type == "Location":
            if hasattr(self, 'current_location'):
                location_tag = LocationTag(tag_name, self.current_location['latitude'], self.current_location['longitude'], self.radius_combo.currentText())
                self.tags.setdefault(trigger_type, []).append(location_tag)
            else:
                QMessageBox.warning(self, "Location Error", "No location selected.")
                return
        elif trigger_type == "Wifi":
            selected_networks = [item.text() for item in self.network_list.selectedItems()]
            wifi_tag = WiFiTag(tag_name, selected_networks)
            self.tags.setdefault(trigger_type, []).append(wifi_tag)
        elif trigger_type == "Bluetooth":
            selected_devices = [item.text() for item in self.bluetooth_list.selectedItems()]
            bluetooth_tag = BluetoothTag(tag_name, selected_devices)
            self.tags.setdefault(trigger_type, []).append(bluetooth_tag)
        elif trigger_type == "Camera":
            if hasattr(self, 'image_grid') and self.image_grid.image_widgets:
                selected_images = list(self.image_grid.image_widgets.keys())
                camera_tag = CameraTag(tag_name, selected_images)
                self.tags.setdefault(trigger_type, []).append(camera_tag)
            else:
                QMessageBox.warning(self, "Camera Error", "No images selected.")
                return
        elif trigger_type == "Mic":
            if hasattr(self, 'current_audio_path') and self.current_audio_path:
                mic_tag = MicTag(tag_name, self.current_audio_path)
                self.tags.setdefault(trigger_type, []).append(mic_tag)
            else:
                QMessageBox.warning(self, "Mic Error", "No audio recorded.")
                return
        elif trigger_type == "Keyboard":
            code = self.keyboard_code_input.text().strip()
            keyboard_tag = KeyboardTag(tag_name, code)
            self.tags.setdefault(trigger_type, []).append(keyboard_tag)
        
        # Emit signal to update CategoriesTab
        self.tag_changed.emit(trigger_type, [tag.to_dict() for tag in self.tags[trigger_type]])
        
        # Save to tags.json
        self.save_tags_to_file()
        
        # Update the tags list UI
        self.tags_list.addItem(tag_name)
        QMessageBox.information(self, "Tag Saved", f"Tag '{tag_name}' saved successfully.")

    def edit_tag(self):
        selected_items = self.tags_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a tag to edit.")
            return
        item = selected_items[0]
        tag_name = item.text()
        trigger_type = self.current_trigger
        tag_list = self.tags.get(trigger_type, [])
        tag = next((t for t in tag_list if t.name == tag_name), None)
        if not tag:
            QMessageBox.warning(self, "Tag Not Found", "Selected tag does not exist.")
            return
        
        # Open TagDialog with existing tag data
        dialog = TagDialog(tag_name=tag.name, tag_data=tag)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.name_input.text().strip()
            if not new_name:
                QMessageBox.warning(self, "Invalid Name", "Tag name cannot be empty.")
                return
            tag.name = new_name
            # Update UI
            item.setText(new_name)
            # Save changes
            self.save_tags_to_file()
            self.tag_changed.emit(trigger_type, [t.to_dict() for t in self.tags[trigger_type]])
            QMessageBox.information(self, "Tag Edited", f"Tag '{new_name}' edited successfully.")

    def delete_tag(self):
        selected_items = self.tags_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a tag to delete.")
            return
        item = selected_items[0]
        tag_name = item.text()
        trigger_type = self.current_trigger
        tag_list = self.tags.get(trigger_type, [])
        tag = next((t for t in tag_list if t.name == tag_name), None)
        if tag:
            reply = QMessageBox.question(self, "Delete Tag", f"Are you sure you want to delete tag '{tag_name}'?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                tag_list.remove(tag)
                self.tags_list.takeItem(self.tags_list.row(item))
                self.save_tags_to_file()
                self.tag_changed.emit(trigger_type, [t.to_dict() for t in self.tags[trigger_type]])
                QMessageBox.information(self, "Tag Deleted", f"Tag '{tag_name}' deleted successfully.")

    def current_trigger_type(self):
        # Helper method to get current trigger type
        return self.findChild(QComboBox).currentText()

    def on_processing_complete(self, result):
        self.processing_bar.hide()
        if result['valid']:
            count = result['total_processed']
            message = f"✓ Processed {count} image{'s' if count > 1 else ''}"
            self.camera_status.setText(message)
            self.camera_status.setStyleSheet("""
                QLabel {
                    color: #28a745;
                    background-color: #f0fff0;
                    padding: 5px;
                    border-radius: 5px;
                }
            """)

    def on_processing_error(self, error_message):
        # Hide processing indicator
        self.processing_bar.hide()
        """Handle processing errors"""
        self.camera_status.setText(f"❌ {error_message}")
        self.camera_status.setStyleSheet("""
            QLabel {
                color: #dc3545;
                background-color: #fff3f3;
                padding: 10px;
                border-radius: 5px;
            }
        """)

    def on_image_processed(self, result):
        """Handle individual image processing results"""
        if hasattr(self, 'image_grid'):
            image_path = result.get('path')
            if image_path not in self.image_grid.image_widgets:
                return  # Image was removed before processing finished
            widget = self.image_grid.image_widgets[image_path]
            widget.update_status(result['message'], result.get('style', 'normal'))
        
        # Update progress bar
        if hasattr(self, 'processing_bar'):
            self.processing_bar.setMaximum(result['total'])
            self.processing_bar.setValue(result['index'])
            if result['index'] == result['total']:
                self.processing_bar.hide()

        QApplication.processEvents()  # Process events to prevent UI freeze

    def update_camera_status(self, message):
        """Update camera processing status"""
        if hasattr(self, 'camera_status'):
            self.camera_status.setText(message)
            if "Error" in message:
                self.camera_status.setStyleSheet("""
                    QLabel {
                        color: #dc3545;
                        background-color: #fff3f3;
                        padding: 10px;
                        border-radius: 5px;
                    }
                """)
            elif "Success" in message or "Complete" in message:
                self.camera_status.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        background-color: #f0fff0;
                        padding: 10px;
                        border-radius: 5px;
                    }
                """)
            else:
                self.camera_status.setStyleSheet("""
                    QLabel {
                        color: #666;
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 5px;
                    }
                """)

    def play_audio(self, audio_path):
        try:
            # Play the audio using sounddevice
            data, fs = wav.read(audio_path)
            if isinstance(data, np.ndarray):
                data = data.astype(np.int16)  # Convert to supported datatype
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to play audio: {str(e)}")

    def _get_bluetooth_icon(self, device_type):
        # Define a mapping from device types to icon paths
        icon_mapping = {
            'phone': QIcon('resources/icons/phone_icon.png'),
            'computer': QIcon('resources/icons/computer_icon.png'),
            'headphones': QIcon('resources/icons/headphones_icon.png'),
            'other': QIcon('resources/icons/other_icon.png'),
        }
        # Return the corresponding icon or a default icon if type not found
        return icon_mapping.get(device_type, QIcon('resources/icons/default_bluetooth_icon.png'))

    def load_tags_from_file(self):
        try:
            with open(self.tags_data_file, "r") as f:
                tags_data = json.load(f)
            # Ensure all trigger types are present
            all_trigger_types = ["Location", "Wifi", "Bluetooth", "Camera", "Mic"]
            for trigger_type in all_trigger_types:
                if trigger_type not in tags_data:
                    tags_data[trigger_type] = []
            
            self.tags = {}
            for trigger_type in all_trigger_types:
                self.tags[trigger_type] = []
                for tag in tags_data.get(trigger_type, []):
                    try:
                        if trigger_type == "Location":
                            self.tags[trigger_type].append(LocationTag.from_dict(tag))
                        elif trigger_type == "Wifi":
                            self.tags[trigger_type].append(WiFiTag.from_dict(tag))
                        elif trigger_type == "Bluetooth":
                            self.tags[trigger_type].append(BluetoothTag.from_dict(tag))
                        elif trigger_type == "Camera":
                            self.tags[trigger_type].append(CameraTag.from_dict(tag))
                        elif trigger_type == "Mic":
                            self.tags[trigger_type].append(MicTag.from_dict(tag))
                    except Exception as e:
                        print(f"Error loading {trigger_type} tag: {str(e)}")
                        continue
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading tags file: {str(e)}")
            self.tags = {type_: [] for type_ in all_trigger_types}

    def save_tags_to_file(self):
        tags_data = {}
        for trigger_type, tag_list in self.tags.items():
            tags_data[trigger_type] = []
            for tag in tag_list:
                if hasattr(tag, 'to_dict'):
                    tags_data[trigger_type].append(tag.to_dict())
                else:
                    tags_data[trigger_type].append(tag)  # Assuming it's already a dict
        with open(self.tags_data_file, "w") as f:
            json.dump(tags_data, f, indent=4)

    def remove_image(self, image_path):
        self.image_grid.remove_image(image_path)
        self.tags.pop(image_path, None)
        self.save_tags_to_file()
        self.image_grid.rearrange_grid()

    def update_image_count(self, count):
        """Update the UI when images are removed"""
        self.image_counter.setText(f"Selected {count} image{'s' if count > 1 else ''}")
        if count > 0:
            self.camera_status.setText(f"✓ Processed {count} image{'s' if count > 1 else ''}")
        else:
            self.camera_status.setText("")
            self.processing_bar.hide()

    def rearrange_grid(self):
        self.image_grid.rearrange_grid()

    def setup_keyboard_interface(self):
        layout = QVBoxLayout()
        layout.addLayout(self.create_standard_tag_input())

        self.keyboard_code_input = QLineEdit()
        self.keyboard_code_input.setPlaceholderText("Enter numeric code (e.g., 2321)")
        layout.addWidget(QLabel("Keyboard activation code:"))
        layout.addWidget(self.keyboard_code_input)

        # Display keyboard trigger guidelines as bullets
        guidelines = (
            "Keyboard Trigger Guidelines:\n"
            "• Use numeric keys only for activation code.\n"
            "• Activation code must be a four-digit number (e.g., 2321).\n"
            "• On key press matching the code, the corresponding category settings activate.\n"
            "• Tags are saved in real time and immediately appear in the Categories tab."
        )
        guidelines_label = QLabel(guidelines)
        guidelines_label.setWordWrap(True)
        layout.addWidget(guidelines_label)

        self.trigger_layout.addLayout(layout)

    # ...rest of existing code...

