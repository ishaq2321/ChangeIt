from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from .course_viewer import CourseViewer

class ReactCoursesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("React Learning Path")
        header.setStyleSheet("""
            QLabel {
                color: #61dafb;
                font-size: 24px;
                font-family: 'Courier New';
                padding: 20px;
            }
        """)
        layout.addWidget(header)
        
        # Courses grid
        courses_layout = QGridLayout()
        
        courses = [
            ("30 Days of React", True, """
# Comprehensive React Course
- 30 daily lessons
- Component-based UI
- State management
- Modern React features"""),
            ("React Hooks", False, """
# React Hooks
- useState
- useEffect
- Custom Hooks
- Context API"""),
            ("React Router", False, """
# Routing in React
- Route setup
- Navigation
- Protected routes
- Route parameters"""),
            ("React Testing", False, """
# Testing React Apps
- Component Testing
- Integration Tests
- React Testing Library
- Jest""")
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
        
        # Course header
        header = QLabel(course)
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #61dafb;
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
                    background-color: #61dafb;
                    color: #282c34;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #4fa8c7;
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
        self.course_viewer = CourseViewer("30 Days of React", 
                                        "Asabeneh/30-Days-Of-React")
        self.course_viewer.show()
