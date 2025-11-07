# ui/multi_project_panel.py
"""
Multi-Project Manager V5 - Beautiful GUI + Original Logic
Combines:
- Modern V5 styling (rounded buttons, blue theme)
- Original ProjectPanel logic (100% working)
- Multi-project management (add, delete, run all)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QPushButton, QLabel, QInputDialog,
    QMessageBox, QListWidgetItem, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from ui.project_panel import ProjectPanel
from utils.config import load as load_cfg, save as save_cfg

class MultiProjectPanel(QWidget):
    """Multi-project manager with V5 styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.config = load_cfg()
        self.base_dir = self.config.get('download_root', 'D:/Tiktok/projects')
        self.project_panels = {}  # name -> ProjectPanel
        self.run_all_queue = []
        self.is_running_all = False
        
        self._build_ui()
        self._load_initial_projects()
    
    def _build_ui(self):
        """Build UI with V5 styling"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # === LEFT SIDEBAR (300px) - V5 Style ===
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget {
                background: #FAFAFA;
                border-right: 2px solid #E0E0E0;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # Title - V5 Style
        title = QLabel("📁 Dự án")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #1E88E5; background: transparent; border: none;")
        left_layout.addWidget(title)
        
        # Add/Delete buttons - V5 Rounded Style
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self.btn_add = QPushButton("+ Thêm")
        self.btn_add.setMinimumHeight(40)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: #1E88E5;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: 700;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QPushButton:hover {
                background: #2196F3;
            }
            QPushButton:pressed {
                background: #1565C0;
            }
        """)
        self.btn_add.clicked.connect(self._add_project)
        btn_row.addWidget(self.btn_add, 1)
        
        self.btn_delete = QPushButton("− Xóa")
        self.btn_delete.setMinimumHeight(40)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet(self.btn_add.styleSheet())
        self.btn_delete.clicked.connect(self._delete_project)
        btn_row.addWidget(self.btn_delete, 1)
        
        left_layout.addLayout(btn_row)
        
        # Project list - V5 Style
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 6px;
                margin: 3px 0px;
            }
            QListWidget::item:hover {
                background: #F5F5F5;
            }
            QListWidget::item:selected {
                background: #1E88E5;
                color: white;
                font-weight: 600;
            }
        """)
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        left_layout.addWidget(self.project_list)
        
        # Run all button - V5 Big Rounded Button
        self.btn_run_all = QPushButton("🔥 CHẠY TOÀN BỘ CÁC DỰ ÁN\n(THEO THỨ TỰ)")
        self.btn_run_all.setMinimumHeight(60)
        self.btn_run_all.setCursor(Qt.PointingHandCursor)
        self.btn_run_all.setStyleSheet("""
            QPushButton {
                background: #FF6B35;
                color: white;
                border: none;
                border-radius: 30px;
                font-weight: 700;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
                text-align: center;
                padding: 10px;
            }
            QPushButton:hover {
                background: #FF8555;
            }
            QPushButton:pressed {
                background: #FF5722;
            }
            QPushButton:disabled {
                background: #CCCCCC;
                color: #888888;
            }
        """)
        self.btn_run_all.clicked.connect(self._run_all_projects)
        left_layout.addWidget(self.btn_run_all)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setFont(QFont("Segoe UI", 11))
        self.info_label.setStyleSheet("color: #757575; background: transparent; border: none;")
        self.info_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.info_label)
        
        left_layout.addStretch()
        
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        splitter.addWidget(left_panel)
        
        # === RIGHT PANEL - Stacked Widget for Projects ===
        self.stacked_widget = QStackedWidget()
        
        # Placeholder page
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_label = QLabel("← Chọn hoặc tạo dự án bên trái")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        placeholder_label.setStyleSheet("color: #BDBDBD;")
        placeholder_layout.addWidget(placeholder_label)
        
        self.stacked_widget.addWidget(placeholder)  # Index 0
        
        splitter.addWidget(self.stacked_widget)
        
        # Set initial sizes (300px left, rest right)
        splitter.setSizes([300, 1100])
        
        main_layout.addWidget(splitter)
    
    def _load_initial_projects(self):
        """Load initial projects from config"""
        # Load saved projects
        saved_projects = self.config.get('image2video_projects', [])
        
        if not saved_projects:
            # Create default project
            saved_projects = ['Project_1']
        
        # Add to list
        for proj_name in saved_projects:
            self._add_project_to_list(proj_name)
        
        # Select first
        if self.project_list.count() > 0:
            self.project_list.setCurrentRow(0)
        
        self._update_info_label()
    
    def _add_project(self):
        """Add new project"""
        default_name = f"Project_{self.project_list.count() + 1}"
        name, ok = QInputDialog.getText(
            self, 
            "Thêm Dự Án Mới", 
            "Tên dự án:",
            text=default_name
        )
        
        if not ok or not name.strip():
            return
        
        name = name.strip()
        
        # Check duplicate
        for i in range(self.project_list.count()):
            if self.project_list.item(i).text() == name:
                QMessageBox.warning(self, "Trùng tên", f"Dự án '{name}' đã tồn tại!")
                return
        
        # Add to list
        self._add_project_to_list(name)
        
        # Select new project
        self.project_list.setCurrentRow(self.project_list.count() - 1)
        
        # Save
        self._save_projects()
        self._update_info_label()
    
    def _add_project_to_list(self, name):
        """Add project to list widget"""
        item = QListWidgetItem(f"📋 {name}")
        item.setData(Qt.UserRole, name)  # Store actual name
        self.project_list.addItem(item)
    
    def _delete_project(self):
        """Delete selected project"""
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn dự án cần xóa!")
            return
        
        name = current_item.data(Qt.UserRole)
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa dự án '{name}'?\n\n"
            "(Chỉ xóa khỏi danh sách, không xóa files trên ổ đĩa)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Remove from list
        row = self.project_list.row(current_item)
        self.project_list.takeItem(row)
        
        # Remove panel if loaded
        if name in self.project_panels:
            panel = self.project_panels[name]
            self.stacked_widget.removeWidget(panel)
            panel.deleteLater()
            del self.project_panels[name]
        
        # Show placeholder if empty
        if self.project_list.count() == 0:
            self.stacked_widget.setCurrentIndex(0)
        
        # Save
        self._save_projects()
        self._update_info_label()
    
    def _on_project_selected(self, current, previous):
        """Handle project selection"""
        if not current:
            self.stacked_widget.setCurrentIndex(0)
            return
        
        project_name = current.data(Qt.UserRole)
        
        # Check if panel already exists
        if project_name in self.project_panels:
            panel = self.project_panels[project_name]
        else:
            # Create new ProjectPanel
            panel = ProjectPanel(
                project_name=project_name,
                base_dir=self.base_dir,
                settings_provider=lambda: load_cfg(),
                parent=self
            )
            
            # Connect signals
            panel.project_completed.connect(self._on_project_completed)
            panel.run_all_requested.connect(self._run_all_projects)
            
            # Add to stack
            self.stacked_widget.addWidget(panel)
            self.project_panels[project_name] = panel
        
        # Show panel
        self.stacked_widget.setCurrentWidget(panel)
    
    def _run_all_projects(self):
        """Run all projects sequentially"""
        count = self.project_list.count()
        
        if count == 0:
            QMessageBox.warning(self, "Không có dự án", "Chưa có dự án nào để chạy!")
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Xác nhận chạy tất cả",
            f"Bạn có chắc muốn chạy {count} dự án theo thứ tự?\n\n"
            "⚠️ Quá trình này có thể mất nhiều thời gian.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Build queue
        self.run_all_queue = []
        for i in range(count):
            item = self.project_list.item(i)
            project_name = item.data(Qt.UserRole)
            self.run_all_queue.append(project_name)
        
        # Start
        self.is_running_all = True
        self.btn_run_all.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.btn_delete.setEnabled(False)
        
        self._update_info_label(f"Đang chạy tuần tự: 0/{count}")
        
        # Run first project
        self._run_next_in_queue()
    
    def _run_next_in_queue(self):
        """Run next project in queue"""
        if not self.run_all_queue:
            # Done
            self._on_all_projects_completed()
            return
        
        # Get next project
        project_name = self.run_all_queue.pop(0)
        remaining = len(self.run_all_queue)
        total = self.project_list.count()
        current_index = total - remaining - 1
        
        self._update_info_label(f"Đang chạy: {project_name} ({current_index + 1}/{total})")
        
        # Select and run
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.UserRole) == project_name:
                self.project_list.setCurrentRow(i)
                
                # Get or create panel
                if project_name in self.project_panels:
                    panel = self.project_panels[project_name]
                    
                    # Trigger run
                    QTimer.singleShot(500, panel._run_seq)
                
                break
    
    def _on_project_completed(self, project_name):
        """Handle single project completion"""
        print(f"✅ Project '{project_name}' completed!")
        
        # If running all, continue to next
        if self.is_running_all:
            QTimer.singleShot(2000, self._run_next_in_queue)
    
    def _on_all_projects_completed(self):
        """Handle all projects completion"""
        self.is_running_all = False
        self.btn_run_all.setEnabled(True)
        self.btn_add.setEnabled(True)
        self.btn_delete.setEnabled(True)
        
        self._update_info_label()
        
        QMessageBox.information(
            self,
            "Hoàn tất",
            "✅ Đã chạy xong tất cả các dự án!"
        )
    
    def _save_projects(self):
        """Save project list to config"""
        projects = []
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            projects.append(item.data(Qt.UserRole))
        
        config = load_cfg()
        config['image2video_projects'] = projects
        save_cfg(config)
    
    def _update_info_label(self, text=""):
        """Update info label"""
        if text:
            self.info_label.setText(text)
        else:
            count = self.project_list.count()
            self.info_label.setText(f"📊 Tổng số: {count} dự án")