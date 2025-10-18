import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QLineEdit, QVBoxLayout, QHBoxLayout, QStackedLayout, QFileDialog,
    QScrollArea, QSpacerItem, QSizePolicy, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import re
import json
import os

# Google Gemini API imports
from google.genai import Client 
from google.genai import types

# ======================================================================
# --- 1. Data Reading Function (Numerical Time Extraction for Split) ---
# ======================================================================
def read_data(data):
    """
    Parses the model response string into a dictionary, extracting 
    the total duration as a numerical value (time_min) for splitting among subjects.
    """
    parsed_data = {}
    lined_data = data.strip().split("\n")
    
    for line in lined_data:
        if line.startswith("!") and line.count(":") >= 2:
            try:
                content = line[1:].strip()
                day_subjects_part, time_str = content.rsplit(":", 1)
                day, subjects_str = day_subjects_part.split(":", 1)
                
                day = day.strip()
                time_str = time_str.strip()
                subjects_list = [item.strip() for item in subjects_str.split(",") if item.strip()]
                
                time_min = 0
                match = re.search(r'(\d+)\s*(hour|hr|min|minute)', time_str, re.IGNORECASE)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2).lower()
                    if 'hour' in unit or 'hr' in unit:
                        time_min = value * 60
                    elif 'min' in unit or 'minute' in unit:
                        time_min = value
                elif re.search(r'(\d+)', time_str):
                    time_min = int(re.search(r'(\d+)', time_str).group(1))
                
                if day and subjects_list:
                    parsed_data[day] = {
                        "subjects": subjects_list,
                        "time_str": time_str, 
                        "time_min": time_min   
                    }
            except ValueError:
                continue
                
    return parsed_data

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # --- SESSION AND FILE PATH STATE ---
        self.current_user = None # NEW: Stores the current username
        self.USER_DIR = "users" # NEW: Directory for user save files
        # SHOP_FILE is now generated dynamically in load/save methods

        # Initialize data holders
        self.ref_file_path = None
        self.response = None
        self.days_data = {}
        self.current_day = None

        # --- POINT SYSTEM STATE ---
        # NOTE: Initialized to 0/empty, but loaded based on user later
        self.total_points = 0
        self.subject_status = {}
        # --- END POINT SYSTEM ---
        
        # --- SHOP SYSTEM STATE ---
        self.shop_items = {
            # ID: (Cost, Image Path, Name)
            "char_1": (100, "assets/1.png", "Birdieboy"), 
            "char_2": (250, "assets/2.png", "Dino"),
            "char_3": (500, "assets/3.png", "Lazydog"),
            "char_4": (750, "assets/4.png", "Musicalmouse"),
            "char_5": (1000, "assets/5.png", "Pengy"),
            "char_6": (1500, "assets/6.png", "Sadbear"),
            "char_7": (2000, "assets/7.png", "Seabro"),
            "char_8": (2500, "assets/8.png", "sheep"),
            "char_9": (3000, "assets/9.png", "singingcat"),
            "char_10": (5000, "assets/10.png", "WIN")
        }
        self.unlocked_items = []
        # Progress loading is now deferred to the show_imageloader method
        # --- END SHOP SYSTEM ---

        self.setWindowTitle("A Study Tracker, totally rad")
        self.setGeometry(100, 100, 800, 600)

        # Global stylesheet (Black and White Paper Style) - UNCHANGED
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                color: #000000;
                font-family: Arial, sans-serif;
            }

            QLabel {
                color: #000000;
                font-weight: bold;
            }
            
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border: 2px solid #000000;
                border-radius: 0px; 
                font-size: 16px;
                padding: 6px 14px;
            }

            QPushButton:hover {
                background-color: #EEEEEE;
            }
            
            QPushButton.day_button {
                border-radius: 5px;
            }
            
            QPushButton.day_button:checked, 
            .shop_unlocked, 
            QPushButton:disabled[text*="(DONE)"] {
                background-color: #333333;
                color: #FFFFFF;
                border-color: #333333;
            }

            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
                border-color: #666666;
            }
            
            .shop_buy_btn {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #000000;
                border-radius: 0px;
                font-size: 12px;
            }
            
            .time_label {
                color: #000000;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #333333;
                border-radius: 0px;
                background-color: #F8F8F8;
            }
            
            .subject_duration_label {
                background-color: #CCCCCC;
                color: #000000;
                padding: 4px 8px;
                border-radius: 0px;
                font-weight: bold;
                border: 1px solid #333333;
                text-align: center;
                min-width: 60px;
            }
            
            .points_display {
                background-color: #FFFFFF;
                color: #000000;
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border: 2px solid #000000;
                border-radius: 0px;
                margin-bottom: 20px;
            }

            QLineEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #000000;
                border-radius: 0px;
                font-size: 14px;
                color: black;
                padding: 5px;
            }
            
            QScrollArea {
                border: none;
            }
        """)

        # ===== Stacked layout for screens =====
        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)

        # ------------------------------------
        # --- Welcome Screen Setup ---
        # ------------------------------------
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_layout.setAlignment(Qt.AlignCenter)
        self.welcome_widget.setLayout(welcome_layout)
        
        self.welcome_label = QLabel("CTRL+STUDY")
        self.welcome_label.setStyleSheet("font-size: 48px;")
        welcome_layout.addWidget(self.welcome_label, alignment=Qt.AlignCenter)
        
        self.start_btn = QPushButton("Start?")
        self.start_btn.setFixedSize(150, 50)
        self.start_btn.clicked.connect(self.show_startup)
        welcome_layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        
        self.stacked_layout.addWidget(self.welcome_widget)
        
        # ------------------------------------
        # --- Startup Screen Setup ---
        # ------------------------------------
        self.startup_widget = QWidget()
        startup_layout = QVBoxLayout(self.startup_widget) 

        startup_layout.setAlignment(Qt.AlignCenter)
        startup_layout.setContentsMargins(0, 0, 0, 0)
        startup_layout.setSpacing(0)

        content_group_widget = QWidget()
        content_group_layout = QVBoxLayout(content_group_widget)
        content_group_layout.setSpacing(10) 
        content_group_layout.setContentsMargins(50, 50, 50, 50) 
        
        self.startup_label = QLabel("Enter Your Name") # Updated Label
        self.startup_label.setStyleSheet("font-size: 24px;")
        content_group_layout.addWidget(self.startup_label, alignment=Qt.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your unique username...")
        self.name_input.setFixedWidth(300)
        content_group_layout.addWidget(self.name_input, alignment=Qt.AlignCenter)
        
        startup_layout.addWidget(content_group_widget, alignment=Qt.AlignCenter)
        
        startup_layout.addStretch(1)
        
        # Next button layout (forced right)
        self.startup_next_btn = QPushButton("Load Progress ->") # Updated Button Text
        self.startup_next_btn.setFixedSize(180, 40)
        self.startup_next_btn.clicked.connect(self.load_user_and_show_imageloader) # UPDATED CONNECT
        btn_h_layout = QHBoxLayout()
        btn_h_layout.addStretch(1)
        btn_h_layout.addWidget(self.startup_next_btn)
        startup_layout.addLayout(btn_h_layout)

        self.stacked_layout.addWidget(self.startup_widget)

        # ------------------------------------
        # --- Image Loader Screen Setup (UNCHANGED) ---
        # ------------------------------------
        self.image_loader_widget = QWidget()
        image_loader_layout = QVBoxLayout(self.image_loader_widget)

        image_loader_layout.setAlignment(Qt.AlignCenter)
        image_loader_layout.setContentsMargins(0, 0, 0, 0)
        image_loader_layout.setSpacing(0)
        
        content_group_widget_img = QWidget()
        content_group_layout_img = QVBoxLayout(content_group_widget_img)
        content_group_layout_img.setSpacing(20) 
        content_group_layout_img.setContentsMargins(0, 0, 0, 0) 

        self.open_btn = QPushButton("Open Timetable Image")
        self.open_btn.setFixedSize(200, 40)
        self.open_btn.clicked.connect(self.open_image)
        content_group_layout_img.addWidget(self.open_btn, alignment=Qt.AlignCenter)
        
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #000000; min-height: 200px;")
        content_group_layout_img.addWidget(self.image_label)

        image_loader_layout.addWidget(content_group_widget_img, alignment=Qt.AlignCenter)
        
        image_loader_layout.addStretch(1)
        
        self.image_next_btn = QPushButton("Process Timetable ->")
        self.image_next_btn.setFixedSize(200, 40)
        self.image_next_btn.clicked.connect(self.work_up_google)
        btn_h_layout_img = QHBoxLayout()
        btn_h_layout_img.addStretch(1)
        btn_h_layout_img.addWidget(self.image_next_btn)
        image_loader_layout.addLayout(btn_h_layout_img)

        self.stacked_layout.addWidget(self.image_loader_widget)

        # ------------------------------------
        # --- To-Do List Layout Setup (UNCHANGED) ---
        # ------------------------------------
        self.todo_widget = QWidget()
        main_todo_v_layout = QVBoxLayout() 
        main_todo_v_layout.setContentsMargins(30, 30, 30, 30)
        self.todo_widget.setLayout(main_todo_v_layout)
        
        header_h_layout = QHBoxLayout()
        
        self.points_label = QLabel(f"Score: {self.total_points} Points")
        self.points_label.setProperty("class", "points_display")
        self.points_label.setAlignment(Qt.AlignCenter)
        header_h_layout.addWidget(self.points_label)
        
        self.shop_btn = QPushButton("Visit Shop 🛒")
        self.shop_btn.setFixedSize(120, 40)
        self.shop_btn.clicked.connect(self.show_shop)
        header_h_layout.addWidget(self.shop_btn)
        
        main_todo_v_layout.addLayout(header_h_layout)
        
        todo_layout = QHBoxLayout() 
        todo_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        todo_layout.setSpacing(20)
        
        main_todo_v_layout.addLayout(todo_layout, stretch=1) 

        days_container = QWidget()
        self.dayslayout = QVBoxLayout(days_container)
        self.dayslayout.setAlignment(Qt.AlignTop)
        self.dayslayout.setContentsMargins(10, 10, 10, 10)
        
        days_scroll = QScrollArea()
        days_scroll.setWidgetResizable(True)
        days_scroll.setWidget(days_container)
        days_scroll.setFixedWidth(250)
        days_scroll.setStyleSheet("border: 1px solid #000000;")
        todo_layout.addWidget(days_scroll)

        subjects_container = QWidget()
        self.subjectlayout = QVBoxLayout(subjects_container)
        self.subjectlayout.setAlignment(Qt.AlignTop) 
        self.subjectlayout.setContentsMargins(10, 10, 10, 10)
        
        subjects_scroll = QScrollArea()
        subjects_scroll.setWidgetResizable(True)
        subjects_scroll.setWidget(subjects_container)
        subjects_scroll.setMinimumWidth(400)
        subjects_scroll.setStyleSheet("border: 1px solid #000000;")
        todo_layout.addWidget(subjects_scroll)

        self.stacked_layout.addWidget(self.todo_widget)
        
        # ------------------------------------
        # --- Shop Area Screen Setup (UNCHANGED) ---
        # ------------------------------------
        self.shop_widget = QWidget()
        shop_v_layout = QVBoxLayout(self.shop_widget)
        shop_v_layout.setContentsMargins(30, 30, 30, 30)
        
        shop_header_layout = QHBoxLayout()
        self.shop_back_btn = QPushButton("<- Back to To-Do")
        self.shop_back_btn.setFixedSize(150, 40)
        self.shop_back_btn.clicked.connect(self.show_todo)
        shop_header_layout.addWidget(self.shop_back_btn)
        
        shop_header_layout.addStretch(1)
        
        shop_title = QLabel("Gift Shop")
        shop_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        shop_header_layout.addWidget(shop_title)
        
        shop_header_layout.addStretch(1)
        
        self.shop_points_label = QLabel(f"Points: {self.total_points}")
        self.shop_points_label.setStyleSheet("font-size: 18px; color: #000000; font-weight: bold;")
        shop_header_layout.addWidget(self.shop_points_label)
        
        shop_v_layout.addLayout(shop_header_layout)
        
        shop_scroll_area = QScrollArea()
        shop_scroll_area.setWidgetResizable(True)
        shop_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        shop_scroll_area.setStyleSheet("border: none;")

        self.shop_grid_container = QWidget()
        self.shop_grid_layout = QGridLayout(self.shop_grid_container)
        self.shop_grid_layout.setSpacing(25)
        self.shop_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter) 
        self.shop_grid_layout.setContentsMargins(0, 10, 0, 0)
        
        shop_scroll_area.setWidget(self.shop_grid_container)
        shop_v_layout.addWidget(shop_scroll_area, stretch=1)
        
        self.stacked_layout.addWidget(self.shop_widget)
        
        self.stacked_layout.setCurrentWidget(self.welcome_widget)
        
        self.create_shop_items()
        
    # ======================================================================
    # --- Progress Saving/Loading Methods (MODIFIED) ---
    # ======================================================================
    def get_user_file_path(self):
        """Generates the save file path based on the current user."""
        if not self.current_user:
            return None
        
        # Sanitize username for file path
        safe_username = re.sub(r'[^\w\-_\.]', '_', self.current_user).lower()
        
        # Ensure the user directory exists
        if not os.path.exists(self.USER_DIR):
            os.makedirs(self.USER_DIR)
            
        return os.path.join(self.USER_DIR, f"{safe_username}_progress.json")


    def load_progress(self):
        """Loads total points and unlocked items for the current user."""
        file_path = self.get_user_file_path()
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.total_points = data.get("total_points", 0)
                    self.subject_status = data.get("subject_status", {})
                    self.unlocked_items = data.get("unlocked_items", [])
                
                # Update display if elements exist
                if hasattr(self, 'points_label'):
                    self.update_points_display()
                
                QMessageBox.information(self, "Progress Loaded", 
                                        f"Welcome back, {self.current_user}! Your progress has been loaded.", 
                                        QMessageBox.Ok)
            except Exception as e:
                # If loading fails, start with fresh data (0 points, no status)
                self.total_points = 0
                self.subject_status = {}
                self.unlocked_items = []
                QMessageBox.warning(self, "Load Error", 
                                    f"Could not load progress for {self.current_user}. Starting fresh session.", 
                                    QMessageBox.Ok)
        else:
            # New user or no save file found
            self.total_points = 0
            self.subject_status = {}
            self.unlocked_items = []
            QMessageBox.information(self, "New Session", 
                                    f"Welcome, {self.current_user}! Starting a new session.", 
                                    QMessageBox.Ok)


    def save_progress(self):
        """Saves total points and unlocked items for the current user."""
        if not self.current_user:
            print("Error: Cannot save progress without a set username.")
            return

        file_path = self.get_user_file_path()
        data = {
            "total_points": self.total_points,
            "subject_status": self.subject_status,
            "unlocked_items": self.unlocked_items
        }
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving progress for {self.current_user}: {e}")

    # ======================================================================
    # --- Screen Switch and Session Management (MODIFIED) ---
    # ======================================================================
    def load_user_and_show_imageloader(self):
        """Validates username, loads progress, and switches to the image loader."""
        username = self.name_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Input Required", "Please enter a username to proceed.", QMessageBox.Ok)
            return

        if len(username) < 3:
            QMessageBox.warning(self, "Input Error", "Username must be at least 3 characters long.", QMessageBox.Ok)
            return
            
        # Set the current user and load their progress
        self.current_user = username
        self.load_progress()
        
        # Now switch the screen
        self.show_imageloader()


    def show_startup(self):
        """Switches to the Startup screen (user entry)."""
        self.stacked_layout.setCurrentWidget(self.startup_widget)
        
    def show_imageloader(self):
        """Switches to the Image Loader screen."""
        self.stacked_layout.setCurrentWidget(self.image_loader_widget)

    # --- Other Methods (Same as before, ensure they call save_progress) ---

    def update_points_display(self):
        """Updates the text of the main score labels."""
        self.points_label.setText(f"Score: {self.total_points} Points")
        if hasattr(self, 'shop_points_label'):
            self.shop_points_label.setText(f"Points: {self.total_points}")

    def subject_clicked(self, button, subject_id, points):
        """
        Marks a subject as done, updates the score, disables the button, and saves progress.
        """
        if self.subject_status.get(subject_id) is not True:
            self.subject_status[subject_id] = True
            
            self.total_points += points
            self.update_points_display()
            
            button.setEnabled(False)
            original_text = button.text().replace(" (DONE)", "")
            button.setText(f"{original_text} (DONE)") 
            
            self.save_progress() # Saves for the current user

    def buy_item(self, item_id, cost, button):
        """Handles the purchase of an item."""
        if item_id in self.unlocked_items:
            return

        if self.total_points >= cost:
            self.total_points -= cost
            self.unlocked_items.append(item_id)
            self.update_points_display()
            
            button.setEnabled(False)
            button.setText("UNLOCKED")
            button.setProperty("class", "shop_unlocked")
            button.setStyleSheet("background-color: #333333; color: white; border-color: #333333;")
            
            self.update_shop_item_display(item_id, button.parent()) 
            
            self.save_progress() # Saves for the current user
            
        else:
            button.setText("Not Enough!")

    def update_shop_item_display(self, item_id, container_widget):
        """Updates the image and button state for a single shop item."""
        cost, path, name = self.shop_items[item_id]
        is_unlocked = item_id in self.unlocked_items
        
        image_label = None
        for child in container_widget.findChildren(QLabel):
            if child.property("is_image_holder"):
                image_label = child
                break
        
        if not image_label:
            return

        if is_unlocked:
            image_path = path
        else:
            image_path = "assets/locked.png"
            
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            image_label.setText("")
            image_label.setStyleSheet("border: none;")
            image_label.setPixmap(pixmap.scaled(
                100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            image_label.setText("LOCKED")
            image_label.setStyleSheet("color: #FFFFFF; background-color: #333333; border: 1px solid #000000;")
            image_label.setFixedSize(100, 100)

    def create_shop_items(self):
        """Generates the unlockable character buttons and display."""
        
        for i in reversed(range(self.shop_grid_layout.count())):
            widget_item = self.shop_grid_layout.itemAt(i)
            if widget_item:
                widget = widget_item.widget()
                if widget:
                    widget.deleteLater()
        
        col_count = 0
        row_count = 0
        MAX_COLS = 4 
        
        for item_id, (cost, path, name) in self.shop_items.items():
            item_container = QWidget()
            item_v_layout = QVBoxLayout(item_container)
            item_v_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
            item_container.setFixedSize(150, 200) 
            item_container.setStyleSheet("border: 1px solid #000000;")
            
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
            item_v_layout.addWidget(name_label, alignment=Qt.AlignCenter)

            image_label = QLabel()
            image_label.setProperty("is_image_holder", True)
            image_label.setFixedSize(100, 100)
            image_label.setAlignment(Qt.AlignCenter)
            item_v_layout.addWidget(image_label, alignment=Qt.AlignCenter)
            
            buy_btn = QPushButton(f"Unlock: {cost} Pts")
            buy_btn.setProperty("class", "shop_buy_btn")
            buy_btn.setFixedSize(100, 30)
            
            if item_id in self.unlocked_items:
                buy_btn.setEnabled(False)
                buy_btn.setText("UNLOCKED")
                buy_btn.setProperty("class", "shop_unlocked")
                buy_btn.setStyleSheet("background-color: #333333; color: white; border-color: #333333; font-size: 12px;")
            else:
                buy_btn.clicked.connect(lambda checked, i=item_id, c=cost, b=buy_btn: self.buy_item(i, c, b))
                
            item_v_layout.addWidget(buy_btn, alignment=Qt.AlignCenter)
            
            self.update_shop_item_display(item_id, item_container) 
            
            self.shop_grid_layout.addWidget(item_container, row_count, col_count)
            
            col_count += 1
            if col_count >= MAX_COLS: 
                col_count = 0
                row_count += 1
        
        if col_count > 0:
            self.shop_grid_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), row_count, col_count)


    def show_todo(self):
        self.update_points_display()
        self.stacked_layout.setCurrentWidget(self.todo_widget)

    def show_shop(self):
        self.update_points_display()
        self.create_shop_items()
        self.stacked_layout.setCurrentWidget(self.shop_widget)
    
    def open_image(self):
        self.ref_file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.bmp *.gif)"
        )
        if self.ref_file_path:
            pixmap = QPixmap(self.ref_file_path)
            self.image_label.setText("") 
            self.image_label.setPixmap(pixmap.scaled(
                500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            self.image_label.setText("No image loaded")

    def create_day_buttons(self):
        for i in reversed(range(self.dayslayout.count())): 
            widget = self.dayslayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        title = QLabel("Select a Day:")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #000000;")
        self.dayslayout.addWidget(title)

        for day in self.days_data.keys():
            btn = QPushButton(day)
            btn.setProperty("class", "day_button")
            btn.setCheckable(True) 
            btn.clicked.connect(lambda checked, d=day: self.day_button_clicked(d))
            self.dayslayout.addWidget(btn)
        
        self.dayslayout.addStretch(1) 
        
        if self.days_data:
            first_day = list(self.days_data.keys())[0]
            first_btn_item = self.dayslayout.itemAt(1) 
            if first_btn_item and first_btn_item.widget():
                first_btn = first_btn_item.widget()
                first_btn.setChecked(True)
                self.day_button_clicked(first_day)


    def create_subject_buttons(self, day):
        while self.subjectlayout.count():
            item = self.subjectlayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.current_day = day
        day_data = self.days_data.get(day, {"subjects": [], "time_str": "N/A", "time_min": 0})
        
        title = QLabel(f"Subjects for {day}:")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px; color: #000000;")
        self.subjectlayout.addWidget(title)
        
        time_label = QLabel(f"Total Study Time: {day_data['time_str']}")
        time_label.setProperty("class", "time_label")
        time_label.setAlignment(Qt.AlignCenter)
        self.subjectlayout.addWidget(time_label)
        
        subjects = day_data['subjects']
        total_time = day_data['time_min']
        num_subjects = len(subjects)
        
        if subjects and num_subjects > 0 and total_time > 0:
            time_per_subject = round(total_time / num_subjects) 
            points_value = time_per_subject 
            
            instruction_label = QLabel(f"\nTime per subject (approx. {time_per_subject} min): Click to complete and earn points!")
            instruction_label.setStyleSheet("font-size: 14px; font-weight: normal; margin-top: 10px; margin-bottom: 5px; color: #000000;")
            self.subjectlayout.addWidget(instruction_label)
            
            for subject in subjects:
                subject_id = f"{day}:{subject}"
                
                h_layout = QHBoxLayout()
                h_layout.setSpacing(0) 
                
                btn = QPushButton(subject)
                
                is_done = self.subject_status.get(subject_id, False)
                if is_done:
                    btn.setEnabled(False)
                    btn.setText(f"{subject} (DONE)")
                
                btn.clicked.connect(lambda checked, b=btn, sid=subject_id, p=points_value: self.subject_clicked(b, sid, p))
                
                duration_label = QLabel(f"{time_per_subject} min\n({points_value} pts)")
                duration_label.setProperty("class", "subject_duration_label")
                duration_label.setAlignment(Qt.AlignCenter)
                
                h_layout.addWidget(btn, 3) 
                h_layout.addWidget(duration_label, 1) 
                
                subject_widget = QWidget()
                subject_widget.setLayout(h_layout)
                self.subjectlayout.addWidget(subject_widget)
        
        else:
            no_subjects = QLabel("No subjects or valid time found for this day.")
            no_subjects.setStyleSheet("color: #888; margin-top: 20px;")
            self.subjectlayout.addWidget(no_subjects)

        self.subjectlayout.addStretch(1) 


    def day_button_clicked(self, day):
        for i in range(self.dayslayout.count()):
            item = self.dayslayout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QPushButton):
                button = item.widget()
                if button.text() != day and button.isChecked():
                    button.setChecked(False)
        
        self.create_subject_buttons(day)


    def work_up_google(self):
        if not self.ref_file_path:
            QMessageBox.warning(self, "Image Required", "Please load an image first.", QMessageBox.Ok)
            return
        
        if not self.current_user:
            QMessageBox.critical(self, "User Error", "Username not set. Please restart and enter your name.", QMessageBox.Ok)
            return

        # NOTE: You must replace this with a valid, secure API key!
        API_KEY = "api key here for now" 

        try:
            client = Client(api_key=API_KEY) 
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Error initializing client: {e}", QMessageBox.Ok)
            return

        IMAGE_PATH = self.ref_file_path 

        try:
            with open(IMAGE_PATH, 'rb') as f:
                image_bytes = f.read()
        except FileNotFoundError:
            QMessageBox.critical(self, "File Error", f"Error: Image file not found at {IMAGE_PATH}", QMessageBox.Ok)
            return
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Error reading image file: {e}", QMessageBox.Ok)
            return

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=f'image/jpeg',
        )

        text_prompt = "provide me the data given in this image of a time table and give me a detailed routine i should follow for each subject to study after school, in the format !<day>:subject1,subject2,.. :<amount of time to study in a format like '90 minutes' or '1 hour'>, excluding pt or pe, please dont use any fancy text enchancements as i just need raw data"

        contents = [
            image_part,
            text_prompt
        ]

        try:
            self.response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents
            )
            
            self.days_data = read_data(self.response.text)
            
            if self.days_data:
                self.create_day_buttons()
                self.stacked_layout.setCurrentWidget(self.todo_widget)
            else:
                self.image_label.setText("Error: Could not process timetable data. Check console for details.")
                QMessageBox.warning(self, "Processing Failed", "Could not extract valid timetable data from the image.", QMessageBox.Ok)


        except Exception as e:
            QMessageBox.critical(self, "API Call Error", f"An error occurred during API call: {e}", QMessageBox.Ok)


if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())