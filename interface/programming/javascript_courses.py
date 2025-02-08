from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from .course_viewer import CourseViewer

class JavaScriptCoursesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("JavaScript Learning Path")
        header.setStyleSheet("""
            QLabel {
                color: #f7df1e;
                font-size: 24px;
                font-family: 'Courier New';
                padding: 20px;
            }
        """)
        layout.addWidget(header)
        
        # Courses grid
        courses_layout = QGridLayout()
        
        courses = [
            ("30 Days of JavaScript", True, """
# Master JavaScript
- ES6+ Features
- DOM Manipulation
- Asynchronous JS
- Modern JS Development"""),
            ("JavaScript for Web", False, """
# Web Development
- DOM Projects
- Browser APIs
- Web Storage
- Event Handling"""),
            ("Advanced JavaScript", False, """
# Advanced Concepts
- Closures
- Promises & Async
- Design Patterns
- OOP in JavaScript"""),
            ("JavaScript Testing", False, """
# Testing in JS
- Jest Framework
- Unit Testing
- Integration Tests
- TDD Practices""")
        ]
        
        for i, (course, active, description) in enumerate(courses):
            card = self.create_course_card(course, active, description)
            courses_layout.addWidget(card, i // 2, i % 2)
            
        layout.addLayout(courses_layout)
        self.setLayout(layout)
        
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
        
        # Course header with JS color scheme
        header = QLabel(course)
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #f7df1e;
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
        
        # Action button with JS color scheme
        btn = QPushButton("Start Course" if active else "Coming Soon")
        if active:
            btn.clicked.connect(self.start_course)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f7df1e;
                    color: #000000;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f0d000;
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
        
        # Card styling
        card.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                min-width: 300px;
                border: 1px solid #2d2d2d;
            }
        """)
        
        return card
        
    def start_course(self):
        self.hide()
        self.course_viewer = CourseViewer(
            title="30 Days of JavaScript",
            repo="Asabeneh/30-Days-Of-JavaScript"
        )
        self.course_viewer.show()
