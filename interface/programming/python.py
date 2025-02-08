from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QPushButton, QScrollArea, QFrame)
from PyQt5.QtCore import Qt
import requests

class PythonCoursesSection(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Course Title
        title = QLabel("30 Days of Python")
        title.setStyleSheet("font-weight: bold; font-size: 18px;")
        layout.addWidget(title)
        
        # Days List
        days_group = QGroupBox("Course Content")
        days_layout = QGridLayout()
        
        for day in range(1, 31):
            day_btn = QPushButton(f"Day {day}")
            day_btn.clicked.connect(lambda _, d=day: self.show_day_content(d))
            days_layout.addWidget(day_btn, (day-1)//5, (day-1)%5)
        
        days_group.setLayout(days_layout)
        layout.addWidget(days_group)
        
        self.setLayout(layout)
    
    def show_day_content(self, day):
        url = f"https://raw.githubusercontent.com/Asabeneh/30-Days-Of-Python/master/Day%20{day}/README.md"
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            self.display_content(content)
        else:
            self.display_content("Content not available.")
    
    def display_content(self, content):
        content_window = QWidget()
        content_layout = QVBoxLayout()
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_label)
        scroll_area.setWidgetResizable(True)
        
        content_layout.addWidget(scroll_area)
        content_window.setLayout(content_layout)
        content_window.setWindowTitle("Course Content")
        content_window.resize(800, 600)
        content_window.show()
