# ui/image2video_panel_v7_complete.py
"""
Image2Video V7 - Complete Implementation (Improved Layout)
- Sidebar 40% smaller (180-240px instead of 300-400px)
- Consistent button styling across all panels
- Larger fonts for labels (15px, bold)
- Right column 40% larger
- Video thumbnails in result table
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

# === IMPROVED V7 STYLING - CONSISTENT ACROSS ALL PANELS ===
BUTTON_SMALL = """
    QPushButton {
        background: #1E88E5;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        font-size: 13px;
        font-family: "Segoe UI", Arial, sans-serif;
        padding: 6px 12px;
    }
    QPushButton:hover { background: #2196F3; }
    QPushButton:pressed { background: #1565C0; }
    QPushButton:disabled {
        background: #CCCCCC;
        color: #888888;
    }
"""

BUTTON_MEDIUM = """
    QPushButton {
        background: #1E88E5;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14px;
        font-family: "Segoe UI", Arial, sans-serif;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #2196F3; }
    QPushButton:pressed { background: #1565C0; }
"""

BUTTON_WARNING = """
    QPushButton {
        background: #FF6B35;
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        font-size: 13px;
        font-family: "Segoe UI", Arial, sans-serif;
        padding: 8px;
        text-align: center;
    }
    QPushButton:hover { background: #FF8555; }
    QPushButton:pressed { background: #FF5722; }
    QPushButton:disabled {
        background: #CCCCCC;
        color: #888888;
    }
"""

LIST_STYLE = """
    QListWidget {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 6px;
        padding: 6px;
        font-size: 13px;
        font-family: "Segoe UI", Arial, sans-serif;
    }
    QListWidget::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px 0px;
    }
    QListWidget::item:hover {
        background: #F5F5F5;
    }
    QListWidget::item:selected {
        background: #1E88E5;
        color: white;
        font-weight: 600;
    }
"""

class Image2VideoPanelV7(QWidget):
    """Image2Video V7 - Improved layout"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.config = load_cfg()
        self.base_dir = self.config.get('download_root', 'D:/Tiktok/projects')
        self.project_panels = {}
        self.run_all_queue = []
        self.is_running_all = False
        
        self._build_ui()
        self._load_initial_projects()
    
    def _build_ui(self):
        """Build UI with improved proportions"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT SIDEBAR (40% smaller: 180-240px)
        left = self._build_left_sidebar()
        splitter.addWidget(left)
        
        # RIGHT CONTENT (40% larger)
        right = self._build_right_content()
        splitter.addWidget(right)
        
        # New proportions: 200px left, 1200px right (instead of 300/1100)
        splitter.setSizes([200, 1200])
        
        main_layout.addWidget(splitter)
    
    def _build_left_sidebar(self):
        """Build compact left sidebar"""
        left = QWidget()
        left.setStyleSheet("""
            QWidget {
                background: #FAFAFA;
                border-right: 2px solid #E0E0E0;
            }
        """)
        
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        
        # Title - smaller font
        title = QLabel("📁 Dự án")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #1E88E5; background: transparent; border: none;")
        left_layout.addWidget(title)
        
        # Compact buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        
        self.btn_add = QPushButton("+ Thêm")
        self.btn_add.setMinimumHeight(32)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet(BUTTON_SMALL)
        self.btn_add.clicked.connect(self._add_project)
        btn_row.addWidget(self.btn_add)
        
        self.btn_delete = QPushButton("− Xóa")
        self.btn_delete.setMinimumHeight(32)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet(BUTTON_SMALL)
        self.btn_delete.clicked.connect(self._delete_project)
        btn_row.addWidget(self.btn_delete)
        
        left_layout.addLayout(btn_row)
        
        # Compact project list
        self.project_list = QListWidget()
        self.project_list.setStyleSheet(LIST_STYLE)
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        left_layout.addWidget(self.project_list)
        
        # Compact run all button
        self.btn_run_all = QPushButton("🔥 CHẠY TẤT CẢ\n(TUẦN TỰ)")
        self.btn_run_all.setMinimumHeight(50)
        self.btn_run_all.setCursor(Qt.PointingHandCursor)
        self.btn_run_all.setStyleSheet(BUTTON_WARNING)
        self.btn_run_all.clicked.connect(self._run_all_projects)
        left_layout.addWidget(self.btn_run_all)
        
        # Compact info label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setFont(QFont("Segoe UI", 10))
        self.info_label.setStyleSheet("color: #757575; background: transparent; border: none;")
        self.info_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.info_label)
        
        left_layout.addStretch()
        
        # Smaller size constraints
        left.setMinimumWidth(180)
        left.setMaximumWidth(240)
        
        return left
    
    def _build_right_content(self):
        """Build right content with enhanced ProjectPanel"""
        self.stacked = QStackedWidget()
        
        # Placeholder
        placeholder = QWidget()
        ph_layout = QVBoxLayout(placeholder)
        
        ph_label = QLabel("← Chọn dự án")
        ph_label.setAlignment(Qt.AlignCenter)
        ph_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        ph_label.setStyleSheet("color: #BDBDBD;")
        ph_layout.addWidget(ph_label)
        
        self.stacked.addWidget(placeholder)
        
        return self.stacked
    
    def _load_initial_projects(self):
        """Load projects from config"""
        saved = self.config.get('image2video_projects', [])
        if not saved:
            saved = ['Project_1']
        
        for name in saved:
            self._add_project_to_list(name)
        
        if self.project_list.count() > 0:
            self.project_list.setCurrentRow(0)
        
        self._update_info()
    
    def _add_project(self):
        """Add new project"""
        name, ok = QInputDialog.getText(
            self, "Thêm Dự Án", "Tên dự án:",
            text=f"Project_{self.project_list.count() + 1}"
        )
        if not ok or not name.strip():
            return
        
        name = name.strip()
        for i in range(self.project_list.count()):
            if self.project_list.item(i).data(Qt.UserRole) == name:
                QMessageBox.warning(self, "Trùng tên", f"Dự án '{name}' đã tồn tại!")
                return
        
        self._add_project_to_list(name)
        self.project_list.setCurrentRow(self.project_list.count() - 1)
        self._save_projects()
        self._update_info()
    
    def _add_project_to_list(self, name):
        """Add project to list"""
        item = QListWidgetItem(f"📋 {name}")
        item.setData(Qt.UserRole, name)
        self.project_list.addItem(item)
    
    def _delete_project(self):
        """Delete project"""
        current = self.project_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn dự án!")
            return
        
        name = current.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Xác nhận",
            f"Xóa dự án '{name}'?\n(Chỉ xóa khỏi danh sách)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        row = self.project_list.row(current)
        self.project_list.takeItem(row)
        
        if name in self.project_panels:
            panel = self.project_panels[name]
            self.stacked.removeWidget(panel)
            panel.deleteLater()
            del self.project_panels[name]
        
        if self.project_list.count() == 0:
            self.stacked.setCurrentIndex(0)
        
        self._save_projects()
        self._update_info()
    
    def _on_project_selected(self, current, previous):
        """Handle project selection with enhanced styling"""
        if not current:
            self.stacked.setCurrentIndex(0)
            return
        
        name = current.data(Qt.UserRole)
        
        if name in self.project_panels:
            panel = self.project_panels[name]
        else:
            panel = ProjectPanel(
                project_name=name,
                base_dir=self.base_dir,
                settings_provider=lambda: load_cfg(),
                parent=self
            )
            
            # Apply enhanced styling to ProjectPanel labels
            self._enhance_project_panel_styling(panel)
            
            panel.project_completed.connect(self._on_project_completed)
            panel.run_all_requested.connect(self._run_all_projects)
            
            self.stacked.addWidget(panel)
            self.project_panels[name] = panel
        
        self.stacked.setCurrentWidget(panel)
    
    def _enhance_project_panel_styling(self, panel):
        """Enhance ProjectPanel with larger, bold labels"""
        # Find all QLabel widgets and make them larger + bold
        for label in panel.findChildren(QLabel):
            text = label.text()
            # Check if it's a section label (contains keywords)
            if any(keyword in text for keyword in [
                "Model", "Tỉ lệ", "Số video", "Prompt", "Ảnh tham chiếu",
                "Dự án", "video"
            ]):
                font = label.font()
                font.setPointSize(15)  # +2px from original
                font.setBold(True)
                label.setFont(font)
                label.setStyleSheet("font-weight: 700;")
    
    def _run_all_projects(self):
        """Run all projects"""
        count = self.project_list.count()
        if count == 0:
            QMessageBox.warning(self, "Không có dự án", "Chưa có dự án!")
            return
        
        reply = QMessageBox.question(
            self, "Xác nhận",
            f"Chạy {count} dự án?\n⚠️ Có thể mất nhiều thời gian.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        self.run_all_queue = [
            self.project_list.item(i).data(Qt.UserRole)
            for i in range(count)
        ]
        
        self.is_running_all = True
        self.btn_run_all.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.btn_delete.setEnabled(False)
        
        self._update_info(f"Đang chạy: 0/{count}")
        self._run_next()
    
    def _run_next(self):
        """Run next project"""
        if not self.run_all_queue:
            self._all_done()
            return
        
        name = self.run_all_queue.pop(0)
        total = self.project_list.count()
        current = total - len(self.run_all_queue)
        
        self._update_info(f"Đang chạy: {name} ({current}/{total})")
        
        for i in range(self.project_list.count()):
            if self.project_list.item(i).data(Qt.UserRole) == name:
                self.project_list.setCurrentRow(i)
                if name in self.project_panels:
                    QTimer.singleShot(500, self.project_panels[name]._run_seq)
                break
    
    def _on_project_completed(self, name):
        """Handle completion"""
        print(f"✅ Project '{name}' completed!")
        if self.is_running_all:
            QTimer.singleShot(2000, self._run_next)
    
    def _all_done(self):
        """All done"""
        self.is_running_all = False
        self.btn_run_all.setEnabled(True)
        self.btn_add.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self._update_info()
        QMessageBox.information(self, "Hoàn tất", "✅ Xong tất cả!")
    
    def _save_projects(self):
        """Save projects"""
        projects = [
            self.project_list.item(i).data(Qt.UserRole)
            for i in range(self.project_list.count())
        ]
        config = load_cfg()
        config['image2video_projects'] = projects
        save_cfg(config)
    
    def _update_info(self, text=""):
        """Update info"""
        if text:
            self.info_label.setText(text)
        else:
            self.info_label.setText(f"📊 {self.project_list.count()} dự án")