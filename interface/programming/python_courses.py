from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from .course_viewer import CourseViewer

class PythonCoursesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Python Learning Paths")
        header.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-size: 24px;
                font-family: 'Courier New';
                padding: 20px;
            }
        """)
        layout.addWidget(header)
        
        # Courses grid
        courses_layout = QGridLayout()
        
        courses = [
            ("30 Days of Python", True, """
# Comprehensive Python Course
- 30 daily lessons
- Hands-on exercises
- From basics to advanced
- Real-world projects"""),
            ("Python for Data Science", False, """
# Data Science Path
- NumPy & Pandas
- Data Analysis
- Visualization
- Machine Learning"""),
            ("Python Web Dev", False, """
# Web Development
- Django & Flask
- REST APIs
- Database Design
- Deployment"""),
            ("Python Automation", False, """
# Automation & Scripts
- Task Automation
- Web Scraping
- File Processing
- System Scripts""")
        ]
        
        for i, (course, active, description) in enumerate(courses):
            card = self.create_course_card(course, active, description)
            courses_layout.addWidget(card, i // 2, i % 2)
            
        layout.addLayout(courses_layout)
        self.setLayout(layout)
        
        # Window styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        
    def create_course_card(self, course, active, description):
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card_layout = QVBoxLayout()
        
        # Course header
        header = QLabel(course)
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #61afef;
            }
        """)
        
        # Description
        desc = QLabel(description)
        desc.setStyleSheet("""
            QLabel {
                font-family: 'Courier New';
                background-color: #2d2d2d;
                padding: 15px;
                border-radius: 5px;
                color: #98c379;
                text-align: left;
                qproperty-alignment: AlignLeft;
            }
        """)
        
        # Action button
        btn = QPushButton("Start Course" if active else "Coming Soon")
        if active:
            btn.clicked.connect(self.start_course)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #198754;
                    color: white;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #157347;
                }
            """)
        else:
            btn.setEnabled(False)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #343a40;
                    color: #6c757d;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                }
            """)
        
        card_layout.addWidget(header)
        card_layout.addWidget(desc)
        card_layout.addWidget(btn)
        card.setLayout(card_layout)
        
        card.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                min-width: 300px;
            }
        """)
        
        return card
        
    def start_course(self):
        self.hide()
        self.course_viewer = CourseViewer()
        self.course_viewer.show()
