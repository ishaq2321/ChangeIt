from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QScrollArea, QGridLayout, QSplitter,
                            QTextBrowser, QFrame)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
import requests
import os
import git
import markdown
import shutil
import re

class CourseViewer(QWidget):
    def __init__(self, title="30 Days of Python", repo="Asabeneh/30-Days-Of-Python"):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(1200, 700)
        self.repo_url = f"https://github.com/{repo}.git"
        self.repo_name = repo.split('/')[1]
        self.repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'resources', self.repo_name.lower())
        self.clone_or_update_repo()
        self.day_titles = self.load_day_titles()
        self.course_title = title
        self.initUI()
        
    def clone_or_update_repo(self):
        """Clone or update the course repository"""
        try:
            if not os.path.exists(self.repo_path):
                os.makedirs(os.path.dirname(self.repo_path), exist_ok=True)
                print(f"Cloning repository to {self.repo_path}")
                git.Repo.clone_from(
                    self.repo_url,
                    self.repo_path
                )
                print("Repository cloned successfully")
            else:
                print("Updating existing repository")
                repo = git.Repo(self.repo_path)
                origin = repo.remotes.origin
                origin.fetch()
                origin.pull()
                print("Repository updated successfully")
        except Exception as e:
            print(f"Repository error: {str(e)}")
            # Try to remove and clone again if there's an error
            if os.path.exists(self.repo_path):
                try:
                    shutil.rmtree(self.repo_path)
                    os.makedirs(self.repo_path, exist_ok=True)
                    git.Repo.clone_from(
                        self.repo_url,
                        self.repo_path
                    )
                    print("Repository re-cloned successfully")
                except Exception as e2:
                    print(f"Error during re-cloning: {str(e2)}")
    
    def load_day_titles(self):
        """Load all day titles from the repository"""
        titles = {}
        try:
            for day in range(1, 31):
                readme_path = os.path.join(self.repo_path, f'Day {day}', 'README.md')
                if os.path.exists(readme_path):
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract first heading
                        match = re.search(r'# (.*)', content)
                        if match:
                            titles[day] = match.group(1).strip()
                        else:
                            titles[day] = f"Day {day}"
        except Exception as e:
            print(f"Error loading titles: {e}")
        return titles

    def initUI(self):
        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        
        # Days panel (left side)
        days_widget = QWidget()
        days_layout = QVBoxLayout()
        
        # Add course title and description
        course_header = QLabel(self.course_title)
        course_header.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-size: 24px;
                font-family: 'Courier New';
                padding: 10px;
            }
        """)
        # Set color based on course type
        if "JavaScript" in self.course_title:
            course_header.setStyleSheet("""
                QLabel {
                    color: #f7df1e;
                    font-size: 24px;
                    font-family: 'Courier New';
                    padding: 10px;
                }
            """)
        elif "React" in self.course_title:
            course_header.setStyleSheet("""
                QLabel {
                    color: #61dafb;
                    font-size: 24px;
                    font-family: 'Courier New';
                    padding: 10px;
                }
            """)
        days_layout.addWidget(course_header)
        
        days_scroll = QScrollArea()
        days_content = QWidget()
        days_grid = QVBoxLayout()  # Changed to VBoxLayout for better organization
        
        # Create day buttons with titles
        for day in range(1, 31):
            day_frame = QFrame()
            day_layout = QVBoxLayout()
            
            # Day button with number
            btn = QPushButton(f"Day {day}")
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _, d=day: self.load_day_content(d))
            
            # Day title
            title = QLabel(self.day_titles.get(day, f"Day {day}"))
            title.setWordWrap(True)
            title.setStyleSheet("""
                QLabel {
                    color: #98c379;
                    font-size: 12px;
                    padding-left: 5px;
                }
            """)
            
            day_layout.addWidget(btn)
            day_layout.addWidget(title)
            day_frame.setLayout(day_layout)
            day_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border-radius: 5px;
                    margin: 2px;
                    padding: 5px;
                }
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
            
            days_grid.addWidget(day_frame)
        
        days_grid.addStretch()
        days_content.setLayout(days_grid)
        days_scroll.setWidget(days_content)
        days_scroll.setWidgetResizable(True)
        days_layout.addWidget(days_scroll)
        days_widget.setLayout(days_layout)

        # Content panel (right side)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        
        # Add navigation bar
        nav_bar = QHBoxLayout()
        self.current_day_label = QLabel("Select a day to start")
        nav_bar.addWidget(self.current_day_label)
        nav_bar.addStretch()
        
        # Add navigation buttons
        self.prev_btn = QPushButton("← Previous")
        self.next_btn = QPushButton("Next →")
        self.prev_btn.clicked.connect(self.load_previous_day)
        self.next_btn.clicked.connect(self.load_next_day)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        nav_bar.addWidget(self.prev_btn)
        nav_bar.addWidget(self.next_btn)
        
        content_layout.addLayout(nav_bar)
        
        # Content browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.anchorClicked.connect(self.handle_link_click)
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                color: #24292e;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                padding: 20px;
            }
        """)
        
        content_layout.addWidget(self.content_browser)
        self.content_widget.setLayout(content_layout)
        
        # Add widgets to splitter
        splitter.addWidget(days_widget)
        splitter.addWidget(self.content_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QScrollArea {
                border: none;
            }
        """)
        
    def find_day_content(self, day):
        """Find the content file for a given day"""
        print(f"\nSearching for Day {day} content")
        print(f"Repository path: {self.repo_path}")
        
        try:
            # List all files and folders
            all_items = []
            for root, dirs, files in os.walk(self.repo_path):
                for item in dirs + files:
                    if item.endswith(('.md', '.MD')):
                        all_items.append(os.path.join(root, item))
            
            print(f"Found {len(all_items)} markdown files")
            
            # JavaScript specific patterns (day folders might be named differently)
            js_day_patterns = [
                f'{day:02d}_Day',           # matches "01_Day"
                f'day_{day:02d}',           # matches "day_01"
                f'{day:02d}-Day',           # matches "01-Day"
                f'Day_{day:02d}',           # matches "Day_01"
                f'day{day:02d}',            # matches "day01"
                f'day-{day:02d}',           # matches "day-01"
            ]
            
            # Check for exact day folder matches first
            for pattern in js_day_patterns:
                # Look for README.md in day folder
                for day_path in [p for p in all_items if pattern.lower() in p.lower()]:
                    folder = os.path.dirname(day_path)
                    readme = os.path.join(folder, 'README.md')
                    if os.path.exists(readme):
                        print(f"Found day content: {readme}")
                        return readme
                    
                    # Try alternate filenames
                    alternates = [
                        os.path.join(folder, f'{pattern}.md'),
                        os.path.join(folder, 'note.md'),
                        os.path.join(folder, 'readme.MD'),
                        day_path  # Use the found file if no readme exists
                    ]
                    
                    for alt in alternates:
                        if os.path.exists(alt):
                            print(f"Found alternate content: {alt}")
                            return alt
            
            # Special case for day 1
            if day == 1:
                readme_variants = [
                    os.path.join(self.repo_path, 'readme.md'),
                    os.path.join(self.repo_path, 'README.md'),
                    os.path.join(self.repo_path, 'Introduction', 'README.md'),
                    os.path.join(self.repo_path, '01_Day_Introduction', 'README.md'),
                ]
                for readme in readme_variants:
                    if os.path.exists(readme):
                        return readme
            
            # If no content is found, create a placeholder
            print("No matching content found, creating placeholder")
            return self.create_placeholder_content(day)
            
        except Exception as e:
            print(f"Error searching for content: {str(e)}")
            return self.create_placeholder_content(day)

    def create_placeholder_content(self, day):
        """Create a temporary file with placeholder content for days without .md files"""
        try:
            placeholder_dir = os.path.join(self.repo_path, 'placeholders')
            os.makedirs(placeholder_dir, exist_ok=True)
            
            placeholder_file = os.path.join(placeholder_dir, f'day_{day:02d}_placeholder.md')
            
            if not os.path.exists(placeholder_file):
                with open(placeholder_file, 'w', encoding='utf-8') as f:
                    f.write(f"""# Day {day}

Content for this day is being processed. Please check:

1. The original repository at: {self.repo_url}
2. Or come back later when the content is available.

## Topics covered in Day {day}:

- Check the repository for the latest updates
- Content will be available soon
""")
            
            return placeholder_file
            
        except Exception as e:
            print(f"Error creating placeholder: {str(e)}")
            return None

    def load_day_content(self, day):
        """Load content from local repository"""
        self.current_day = day
        self.prev_btn.setEnabled(day > 1)
        self.next_btn.setEnabled(day < 30)
        
        try:
            # Find the content file
            content_path = self.find_day_content(day)
            print(f"Content path: {content_path}")
            
            if content_path and os.path.exists(content_path):
                with open(content_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"Content loaded successfully for day {day}")
                html_content = self.process_markdown(content, os.path.dirname(content_path))
                self.content_browser.setHtml(html_content)
                self.current_day_label.setText(f"Day {day}: {self.day_titles.get(day, '')}")
            else:
                error_msg = f"Could not find content for Day {day}"
                print(error_msg)
                self.content_browser.setPlainText(error_msg)
                
        except Exception as e:
            error_msg = f"Error loading content for Day {day}: {str(e)}"
            print(error_msg)
            self.content_browser.setPlainText(error_msg)
    
    def load_previous_day(self):
        if hasattr(self, 'current_day') and self.current_day > 1:
            self.load_day_content(self.current_day - 1)
    
    def load_next_day(self):
        if hasattr(self, 'current_day') and self.current_day < 30:
            self.load_day_content(self.current_day + 1)
    
    def process_markdown(self, content, day_folder):
        """Convert markdown to HTML with proper image paths"""
        try:
            # Configure markdown extensions
            md = markdown.Markdown(extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.attr_list',
                'markdown.extensions.def_list',
                'markdown.extensions.abbr',
                'markdown.extensions.footnotes',
                'markdown.extensions.md_in_html',
                'markdown.extensions.toc'
            ])
            
            # Update paths for navigation links
            content = self.fix_navigation_links(content)
            
            # Update image and other asset paths
            repo_root = self.repo_path
            base_path = f'file://{os.path.join(repo_root, day_folder)}'
            root_path = f'file://{repo_root}'
            
            # Fix various path patterns
            content = content.replace('](./images/', f']({base_path}/images/')
            content = content.replace('](images/', f']({base_path}/images/')
            content = content.replace('](../images/', f']({root_path}/images/')
            content = content.replace('](./readme.md)', f']({root_path}/readme.md)')
            
            # Convert to HTML
            html = md.convert(content)
            
            # Add GitHub-style CSS
            return f"""
            <html>
            <head>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.5;
                    color: #24292e;
                    background-color: #ffffff;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 6px;
                    padding: 16px;
                    overflow: auto;
                }}
                code {{
                    font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                    font-size: 85%;
                    background-color: #f6f8fa;
                    padding: 0.2em 0.4em;
                    border-radius: 3px;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                table {{
                    border-spacing: 0;
                    border-collapse: collapse;
                    margin-top: 0;
                    margin-bottom: 16px;
                }}
                table th, table td {{
                    padding: 6px 13px;
                    border: 1px solid #dfe2e5;
                }}
                table tr:nth-child(2n) {{
                    background-color: #f6f8fa;
                }}
            </style>
            </head>
            <body>
            {html}
            </body>
            </html>
            """
        except Exception as e:
            print(f"Error processing markdown: {str(e)}")
            return f"<html><body><pre>{content}</pre></body></html>"

    def fix_navigation_links(self, content):
        """Fix navigation links in markdown content"""
        # Fix different types of navigation links
        replacements = [
            # Fix relative readme links
            (r'\[.*?\]\(./readme\.md\)', lambda m: m.group().replace('./readme.md', '../readme.md')),
            (r'\[.*?\]\(readme\.md\)', lambda m: m.group().replace('readme.md', '../readme.md')),
            
            # Fix day navigation links
            (r'\[.*?\]\((\.\./)?\d+_Day_.*?/.*?\.md\)', lambda m: self.convert_to_local_link(m.group())),
            (r'\[.*?\]\((\.\./)Day_\d+.*?\.md\)', lambda m: self.convert_to_local_link(m.group())),
            (r'\[.*?\]\((\.\./)readme\.md\)', lambda m: self.convert_to_local_link(m.group())),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content

    def convert_to_local_link(self, markdown_link):
        """Convert repository links to local application links"""
        # Extract URL part from markdown link [text](url)
        url_match = re.search(r'\((.*?)\)', markdown_link)
        if url_match:
            url = url_match.group(1)
            # Convert to local application URL scheme
            return markdown_link.replace(url, f'file:///{url}')
        return markdown_link

    def handle_link_click(self, url):
        """Handle clicking on links"""
        url_str = url.toString()
        print(f"Clicked link: {url_str}")
        
        # Handle relative paths
        if url_str.startswith('./') or not url_str.startswith(('http://', 'https://', 'file://')):
            # Convert relative path to absolute
            current_dir = os.path.dirname(self.find_day_content(self.current_day))
            absolute_path = os.path.normpath(os.path.join(current_dir, url_str))
            url = QUrl.fromLocalFile(absolute_path)
            url_str = url.toString()
            print(f"Converted to absolute path: {url_str}")
        
        # Check for day navigation links
        day_patterns = [
            r".*?(\d+)_Day_.*?/.*?\.md",     # matches 01_Day_.../file.md
            r"Day_(\d+).*?\.md",              # matches Day_1.md
            r"day_(\d+).*?\.md",              # matches day_1.md
            r"Day (\d+)",                     # matches Day 1
            r".*?readme\.md"                  # matches readme.md (any path)
        ]
        
        # Check if it's a day navigation link
        for pattern in day_patterns:
            match = re.search(pattern, url_str, re.IGNORECASE)
            if match:
                if "readme.md" in url_str.lower():
                    self.load_day_content(1)
                else:
                    day = int(match.group(1))
                    self.load_day_content(day)
                return
        
        # Handle other links
        if url.isLocalFile():
            local_path = url.toLocalFile()
            if os.path.exists(local_path):
                if local_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(local_path))
                else:
                    try:
                        with open(local_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        self.content_browser.setHtml(
                            self.process_markdown(content, os.path.dirname(local_path))
                        )
                    except Exception as e:
                        print(f"Error loading file: {e}")
                        self.content_browser.setPlainText(f"Error loading file: {str(e)}")
            else:
                print(f"File not found: {local_path}")
        else:
            QDesktopServices.openUrl(url)
