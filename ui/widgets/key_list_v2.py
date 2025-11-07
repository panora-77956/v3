# -*- coding: utf-8 -*-
"""
KeyList V2 - Fixed Version
- Proper spacing (no huge gaps)
- Highlighted input fields
- Better visual hierarchy
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class KeyListV2(QWidget):
    """Improved KeyList with compact layout and prominent inputs"""

    def __init__(self, title="", kind="default", initial=None, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.keys = initial or []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Keys display area - with better styling
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(120)
        self.list_widget.setMaximumHeight(180)
        self.list_widget.setFont(QFont("Courier New", 11))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #FAFAFA;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget::item {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: #F5F5F5;
                border-color: #BDBDBD;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                border-color: #1E88E5;
                color: #1565C0;
            }
        """)
        layout.addWidget(self.list_widget)

        # Populate existing keys
        for key in self.keys:
            self._add_key_item(key)

        # Input area - PROMINENT & CLEAR
        input_label = QLabel(f"➕ Paste {self.kind.upper()} API Key:")
        input_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        input_label.setStyleSheet("color: #424242; margin-top: 4px;")
        layout.addWidget(input_label)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"Enter your {self.kind} API key here...")
        self.input_field.setMinimumHeight(40)
        self.input_field.setFont(QFont("Segoe UI", 13))
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 3px solid #BDBDBD;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
                color: #212121;
            }
            QLineEdit:focus {
                border: 3px solid #1E88E5;
                background: #F8FCFF;
            }
            QLineEdit::placeholder {
                color: #9E9E9E;
                font-style: italic;
            }
        """)
        self.input_field.returnPressed.connect(self._add_key)
        input_row.addWidget(self.input_field, 1)

        # Add button - prominent
        self.btn_add = QPushButton("➕ Add")
        self.btn_add.setObjectName("btn_primary")
        self.btn_add.setMinimumHeight(40)
        self.btn_add.setMinimumWidth(100)
        self.btn_add.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._add_key)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: #008080;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #009999;
            }
        """)
        input_row.addWidget(self.btn_add)

        layout.addLayout(input_row)

        # Action buttons row - compact
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_import = QPushButton("📁 Import File")
        self.btn_import.setObjectName("btn_import")
        self.btn_import.setMinimumHeight(32)
        self.btn_import.setFont(QFont("Segoe UI", 12))
        self.btn_import.clicked.connect(self._import_file)
        actions_row.addWidget(self.btn_import)

        self.btn_validate = QPushButton("✓ Validate All")
        self.btn_validate.setObjectName("btn_check")
        self.btn_validate.setMinimumHeight(32)
        self.btn_validate.setFont(QFont("Segoe UI", 12))
        self.btn_validate.clicked.connect(self._validate_all)
        actions_row.addWidget(self.btn_validate)

        actions_row.addStretch()
        layout.addLayout(actions_row)

    def _add_key_item(self, key_text):
        """Add key item with COMPACT spacing - NO HUGE GAPS"""
        item = QListWidgetItem()

        # Custom widget for item
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(6, 4, 6, 4)
        item_layout.setSpacing(8)  # ONLY 8px - not huge gap

        # Key text (monospace, selectable)
        key_label = QLabel(self._truncate_key(key_text))
        key_label.setFont(QFont("Courier New", 11))
        key_label.setStyleSheet("color: #424242; padding: 4px;")
        key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        key_label.setToolTip(key_text)  # Full key on hover
        item_layout.addWidget(key_label, 1)  # stretch=1 takes remaining space

        # Check button - RIGHT NEXT to text (NO gap)
        btn_check = QPushButton("✓")
        btn_check.setFixedSize(32, 32)
        btn_check.setObjectName("btn_check")
        btn_check.setToolTip("Validate this key")
        btn_check.setCursor(Qt.PointingHandCursor)
        btn_check.setFont(QFont("Segoe UI", 14))
        btn_check.clicked.connect(lambda: self._validate_key(key_text))
        item_layout.addWidget(btn_check)

        # Delete button - RIGHT NEXT to check button
        btn_delete = QPushButton("🗑")
        btn_delete.setFixedSize(32, 32)
        btn_delete.setObjectName("btn_danger")
        btn_delete.setToolTip("Delete this key")
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setFont(QFont("Segoe UI", 14))
        btn_delete.clicked.connect(lambda: self._delete_key_item(item))
        item_layout.addWidget(btn_delete)

        # NO addStretch() here - that's what caused huge gap!

        # Set item
        item.setSizeHint(item_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)

    def _truncate_key(self, key):
        """Truncate key for display: show first 24 and last 12 chars"""
        if len(key) > 40:
            return f"{key[:24]}...{key[-12:]}"
        return key

    def _add_key(self):
        """Add key from input"""
        key = self.input_field.text().strip()
        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key!")
            return

        if key in self.keys:
            QMessageBox.warning(self, "Duplicate", "This key already exists!")
            return

        self._add_key_item(key)
        self.keys.append(key)
        self.input_field.clear()
        self.input_field.setFocus()

    def _delete_key_item(self, item):
        """Delete key item"""
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        if 0 <= row < len(self.keys):
            self.keys.pop(row)

    def _import_file(self):
        """Import keys from text file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import API Keys", "", "Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                count = 0
                for line in f:
                    key = line.strip()
                    if key and key not in self.keys:
                        self._add_key_item(key)
                        self.keys.append(key)
                        count += 1

            QMessageBox.information(self, "Import Success", f"Imported {count} keys!")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Error: {str(e)}")

    def _validate_key(self, key):
        """Validate single key (placeholder)"""
        QMessageBox.information(self, "Validate", f"Validating key: {self._truncate_key(key)}\n\n(Validation logic not implemented)")

    def _validate_all(self):
        """Validate all keys (placeholder)"""
        if not self.keys:
            QMessageBox.warning(self, "No Keys", "No keys to validate!")
            return

        QMessageBox.information(self, "Validate All", f"Validating {len(self.keys)} keys...\n\n(Validation logic not implemented)")

    def get_keys(self):
        """Get all keys as list"""
        return self.keys.copy()