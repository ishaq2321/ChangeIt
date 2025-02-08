from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from .python_courses import PythonCoursesView
from .javascript_courses import JavaScriptCoursesView
from .react_courses import ReactCoursesView

class ProgrammingLanguagesSection(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Programming Language")
        self.setMinimumSize(1200, 700)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Choose Your Path")
        header.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-size: 24px;
                font-family: 'Courier New';
                padding: 20px;
            }
        """)
        layout.addWidget(header)
        
        # Create scrollable area for cards
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QGridLayout()
        
        # Language configurations
        languages = [
            ("Python", "🐍", True, """
def why_python():
    return [
        "Simple & Powerful",
        "AI & Data Science",
        "Web Development",
        "Automation"
    ]"""),
            ("JavaScript", "⚡", True, """
function whyJavaScript() {
    return [
        "Web Development",
        "Frontend & Backend",
        "Cross-platform Apps",
        "Modern Frameworks"
    ];
}"""),
            ("React", "⚛️", True, """
function WhyReact() {
    return (
        <div>
            {"Component-Based"}
            {"Virtual DOM"}
            {"Rich Ecosystem"}
            {"Industry Standard"}
        </div>
    );
}"""),
            ("Java", "☕", False, """
public static void main() {
    // Coming soon...
}"""),
            ("Ruby", "💎", False, """
def coming_soon
    puts "Under development"
end"""),
            ("Go", "🔵", False, """
package main

func main() {
    println("Under development")
}"""),
            ("C++", "⚔️", False, """
#include <iostream>

int main() {
    std::cout << "Under development" << std::endl;
    return 0;
}""")
        ]
        
        for i, (lang, icon, active, sample_code) in enumerate(languages):
            card = self.create_language_card(lang, icon, active, sample_code)
            scroll_layout.addWidget(card, i // 3, i % 3)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        
    def create_language_card(self, lang, icon, active, sample_code):
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card_layout = QVBoxLayout()
        
        # Language header
        header = QLabel(f"{icon} {lang}")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #61afef;
            }
        """)
        
        # Code sample
        code = QLabel(sample_code)
        code.setStyleSheet("""
            QLabel {
                font-family: 'Courier New';
                background-color: #2d2d2d;
                padding: 10px;
                border-radius: 5px;
                color: #98c379;
            }
        """)
        
        # Status/Action button
        btn = QPushButton("Start Learning" if active else "Coming Soon")
        if active:
            if lang == "Python":
                btn.clicked.connect(self.show_python_courses)
            elif lang == "JavaScript":
                btn.clicked.connect(self.show_javascript_courses)
            elif lang == "React":
                btn.clicked.connect(self.show_react_courses)
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
        card_layout.addWidget(code)
        card_layout.addWidget(btn)
        card.setLayout(card_layout)
        
        card.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
            }
        """)
        
        return card
        
    def show_python_courses(self):
        self.hide()
        self.python_courses = PythonCoursesView()
        self.python_courses.show()

    def show_javascript_courses(self):
        self.hide()
        self.javascript_courses = JavaScriptCoursesView()
        self.javascript_courses.show()

    def show_react_courses(self):
        self.hide()
        self.react_courses = ReactCoursesView()
        self.react_courses.show()
