# -*- coding: utf-8 -*-
"""
Settings Panel V3 Compact - Super compact, 2-column API
Fits in one screen
"""

import datetime
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton,
    QGroupBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QDialog, QDialogButtonBox, QTextEdit, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer

from ui.widgets.accordion import Accordion, AccordionSection
from ui.widgets.compact_button import CompactButton
from ui.widgets.key_list_v2 import KeyListV2
from utils import config as cfg
from utils.version import get_version
from services.account_manager import get_account_manager, LabsAccount

# Typography
FONT_H2 = QFont("Segoe UI", 14, QFont.Bold)
FONT_BODY = QFont("Segoe UI", 13)
FONT_SMALL = QFont("Segoe UI", 12)
FONT_MONO = QFont("Courier New", 11)

# Default Project ID constant
DEFAULT_PROJECT_ID = '87b19267-13d6-49cd-a7ed-db19a90c9339'

def _ts():
    return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

def _line(placeholder='', read_only=False):
    """Create compact line edit"""
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFont(FONT_BODY)
    e.setMinimumHeight(36)
    e.setMaximumHeight(36)
    e.setReadOnly(read_only)
    
    if not read_only:
        e.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 2px solid #1E88E5;
                background: #F8FCFF;
            }
        """)
    else:
        e.setStyleSheet("""
            QLineEdit {
                background: #F5F5F5;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
    
    return e

def _label(text):
    l = QLabel(text)
    l.setFont(FONT_BODY)
    l.setMinimumHeight(36)
    l.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    return l

class SettingsPanelV3Compact(QWidget):
    """Settings Panel V3 - Super Compact"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = cfg.load()
        self._migrated = False  # Track migration status
        self._build_ui()
    
    def showEvent(self, event):
        """Handle panel show - perform auto-migration on first show"""
        super().showEvent(event)
        # Auto-migrate on first show
        if not self._migrated:
            self._auto_migrate_old_config()
            self._migrated = True
    
    def _auto_migrate_old_config(self):
        """
        Auto-migrate old single-token config to multi-account format
        Called on first Settings panel load
        """
        # Use existing state instead of reloading
        config = self.state
        
        # Check if old 'tokens' or 'labs_tokens' array exists but no 'labs_accounts'
        old_tokens = config.get('tokens', [])
        old_labs_tokens = config.get('labs_tokens', [])
        existing_accounts = config.get('labs_accounts', [])
        
        # Combine all old token sources (preserve order, remove duplicates)
        all_old_tokens = list(dict.fromkeys(old_tokens + old_labs_tokens))
        
        if all_old_tokens and not existing_accounts:
            # Migration needed
            reply = QMessageBox.question(
                self, 
                "Migrate Configuration",
                f"Found {len(all_old_tokens)} old token(s).\n\n"
                "Migrate to multi-account format?\n"
                "(Old tokens will be preserved as backup)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Migrate
                accounts = []
                default_project_id = config.get('flow_project_id', DEFAULT_PROJECT_ID)
                
                for i, token in enumerate(all_old_tokens):
                    accounts.append({
                        'name': f'Account {i+1} (Migrated)',
                        'tokens': [token],
                        'project_id': default_project_id,
                        'enabled': True
                    })
                
                # Save migrated config
                config['labs_accounts'] = accounts
                config['tokens_backup'] = all_old_tokens  # Keep backup
                cfg.save(config)
                
                # Reload state and account table
                self.state = cfg.load()
                if hasattr(self, 'accounts_table') and self.accounts_table is not None:
                    self._load_accounts_table()
                
                QMessageBox.information(
                    self, 
                    "Migration Complete",
                    f"✅ Migrated {len(all_old_tokens)} token(s) to multi-account format.\n\n"
                    "Old tokens backed up as 'tokens_backup' in config."
                )
    
    
    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)  # Compact spacing
        
        # === ACCOUNT INFO ===
        acc_group = QGroupBox("👤 Account Information")
        acc_group.setFont(FONT_H2)
        acc_layout = QGridLayout(acc_group)
        acc_layout.setVerticalSpacing(8)
        acc_layout.setHorizontalSpacing(12)
        acc_layout.setColumnStretch(1, 1)
        acc_layout.setColumnStretch(3, 1)
        
        self.ed_email = _line('Email', read_only=True)
        self.ed_email.setText(self.state.get('account_email', ''))
        
        hwid_text = self.state.get('hardware_id', '')
        self.lb_hwid = _label(hwid_text)
        self.lb_hwid.setFont(FONT_MONO)
        self.lb_hwid.setStyleSheet("background: #F5F5F5; padding: 8px; border-radius: 4px;")
        
        status_text = self.state.get('license_status', 'Kích Hoạt')
        self.lb_status = _label(status_text)
        if 'kích' in status_text.lower() or 'active' in status_text.lower():
            self.lb_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        expiry_text = self.state.get('license_expiry', 'Không có hạn sử dụng')
        self.lb_expiry = _label(expiry_text)
        
        acc_layout.addWidget(_label("Email:"), 0, 0)
        acc_layout.addWidget(self.ed_email, 0, 1)
        acc_layout.addWidget(_label("Hardware ID:"), 0, 2)
        acc_layout.addWidget(self.lb_hwid, 0, 3)
        
        acc_layout.addWidget(_label("Status:"), 1, 0)
        acc_layout.addWidget(self.lb_status, 1, 1)
        acc_layout.addWidget(_label("Expires:"), 1, 2)
        acc_layout.addWidget(self.lb_expiry, 1, 3)
        
        root.addWidget(acc_group)
        
        # === API CREDENTIALS - 2 COLUMNS ===
        api_group = QGroupBox("🔑 API Credentials")
        api_group.setFont(FONT_H2)
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(6)
        
        hint = QLabel("💡 Click sections to expand. Keys are displayed compactly.")
        hint.setFont(FONT_SMALL)
        hint.setStyleSheet("color: #757575; font-style: italic;")
        api_layout.addWidget(hint)
        
        # 2-column grid for accordion sections
        accordion_grid = QGridLayout()
        accordion_grid.setSpacing(8)
        
        # Column 1
        google_section = AccordionSection("Google API Keys")
        g_list = self.state.get('google_api_keys') or []
        self.w_google = KeyListV2(kind='google', initial=g_list)
        google_section.add_content_widget(self.w_google)
        accordion_grid.addWidget(google_section, 0, 0)
        
        # Column 2
        eleven_section = AccordionSection("Elevenlabs API Keys")
        self.w_eleven = KeyListV2(kind='elevenlabs', 
                                  initial=self.state.get('elevenlabs_api_keys') or [])
        eleven_section.add_content_widget(self.w_eleven)
        
        self.ed_voice = _line('Voice ID')
        self.ed_voice.setText(self.state.get('default_voice_id', '3VnrjnYrskPMDsapTr8X'))
        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Voice ID:"))
        voice_row.addWidget(self.ed_voice)
        eleven_section.add_content_layout(voice_row)
        
        accordion_grid.addWidget(eleven_section, 0, 1)
        
        openai_section = AccordionSection("OpenAI API Keys")
        self.w_openai = KeyListV2(kind='openai', 
                                  initial=self.state.get('openai_api_keys') or [])
        openai_section.add_content_widget(self.w_openai)
        accordion_grid.addWidget(openai_section, 1, 1)
        
        # === MULTI-ACCOUNT MANAGEMENT (ISSUE #4) - Now as AccordionSection ===
        multi_acc_section = AccordionSection("🔑 Multi-Account Management")
        
        # Add hint
        hint2 = QLabel(
            "💡 Tip: Use multiple accounts to avoid rate limits and increase processing speed!\n"
            "Each account will process scenes in parallel."
        )
        hint2.setFont(FONT_SMALL)
        hint2.setWordWrap(True)
        hint2.setStyleSheet("color: #666; font-size: 11px; padding: 8px;")
        multi_acc_section.add_content_widget(hint2)
        
        # Account table
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels(["Enabled", "Account Name", "Project ID", "Tokens"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.accounts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.accounts_table.setMaximumHeight(200)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setToolTip(
            "Add multiple Google Labs accounts here.\n"
            "Jobs will be distributed across accounts automatically."
        )
        self.accounts_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        
        # Load accounts from config
        self._load_accounts_table()
        
        multi_acc_section.add_content_widget(self.accounts_table)
        
        # Default Project ID
        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)
        proj_label = QLabel("Default Project ID:")
        proj_label.setFont(FONT_SMALL)
        proj_row.addWidget(proj_label)
        
        self.ed_project = _line('Project ID for new accounts')
        self.ed_project.setText(self.state.get('flow_project_id', DEFAULT_PROJECT_ID))
        self.ed_project.setToolTip(
            "Default Project ID for new accounts.\n"
            "Each account can have its own Project ID in the table above."
        )
        proj_row.addWidget(self.ed_project, 1)
        
        proj_info = QLabel("ℹ️ Used as default for new accounts")
        proj_info.setStyleSheet("color: #666; font-size: 10px;")
        proj_row.addWidget(proj_info)
        
        multi_acc_section.add_content_layout(proj_row)
        
        # Account management buttons
        acc_buttons = QHBoxLayout()
        acc_buttons.setSpacing(8)
        
        self.btn_add_account = CompactButton("➕ Add Account")
        self.btn_add_account.setObjectName("btn_primary")
        self.btn_add_account.clicked.connect(self._add_account)
        acc_buttons.addWidget(self.btn_add_account)
        
        self.btn_edit_account = CompactButton("✏️ Edit Account")
        self.btn_edit_account.clicked.connect(self._edit_account)
        acc_buttons.addWidget(self.btn_edit_account)
        
        self.btn_remove_account = CompactButton("🗑️ Remove Account")
        self.btn_remove_account.clicked.connect(self._remove_account)
        acc_buttons.addWidget(self.btn_remove_account)
        
        acc_buttons.addStretch()
        
        self.lb_account_status = QLabel("")
        self.lb_account_status.setFont(FONT_SMALL)
        self.lb_account_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        acc_buttons.addWidget(self.lb_account_status)
        
        multi_acc_section.add_content_layout(acc_buttons)
        
        # Add Multi-Account section to grid (row 2, spanning both columns)
        accordion_grid.addWidget(multi_acc_section, 2, 0, 1, 2)
        
        api_layout.addLayout(accordion_grid)
        
        # Expand/Collapse buttons
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
        
        btn_expand = CompactButton("📂 Expand All")
        btn_expand.setObjectName("btn_expand")
        btn_expand.clicked.connect(lambda: [
            google_section.set_expanded(True),
            eleven_section.set_expanded(True),
            openai_section.set_expanded(True),
            multi_acc_section.set_expanded(True)
        ])
        toggle_row.addWidget(btn_expand)
        
        btn_collapse = CompactButton("📁 Collapse All")
        btn_collapse.setObjectName("btn_collapse")
        btn_collapse.clicked.connect(lambda: [
            google_section.set_expanded(False),
            eleven_section.set_expanded(False),
            openai_section.set_expanded(False),
            multi_acc_section.set_expanded(False)
        ])
        toggle_row.addWidget(btn_collapse)
        toggle_row.addStretch()
        
        api_layout.addLayout(toggle_row)
        root.addWidget(api_group)
        
        # === STORAGE - ONE LINE ===
        storage_group = QGroupBox("💾 Storage Settings")
        storage_group.setFont(FONT_H2)
        st_layout = QVBoxLayout(storage_group)
        st_layout.setSpacing(6)
        
        # Radio + path in one row
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.rb_local = QRadioButton("📁 Local")
        self.rb_drive = QRadioButton("☁️ Drive")
        storage = (self.state.get('download_storage') or 'local').lower()
        (self.rb_drive if storage == 'gdrive' else self.rb_local).setChecked(True)
        
        row1.addWidget(self.rb_local)
        row1.addWidget(self.rb_drive)
        row1.addWidget(QLabel("Path:"))
        
        self.ed_local = _line('Select folder...')
        self.ed_local.setText(self.state.get('download_root', ''))
        row1.addWidget(self.ed_local, 1)
        
        self.btn_browse = CompactButton("📂 Browse")
        self.btn_browse.setObjectName("btn_browse")
        self.btn_browse.setMinimumHeight(36)
        self.btn_browse.clicked.connect(self._pick_dir)
        row1.addWidget(self.btn_browse)
        
        st_layout.addLayout(row1)
        
        # Drive settings in one row
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(QLabel("Folder ID:"))
        self.ed_gdrive = _line('Folder ID')
        self.ed_gdrive.setText(self.state.get('gdrive_folder_id', ''))
        row2.addWidget(self.ed_gdrive, 1)
        row2.addWidget(QLabel("OAuth:"))
        self.ed_oauth = _line('Token')
        self.ed_oauth.setText(self.state.get('google_workspace_oauth_token', ''))
        row2.addWidget(self.ed_oauth, 1)
        st_layout.addLayout(row2)
        
        self.rb_local.toggled.connect(self._toggle_storage)
        self._toggle_storage()
        
        root.addWidget(storage_group)
        
        # === SYSTEM PROMPTS - ONE LINE ===
        prompts_row = QHBoxLayout()
        prompts_row.setSpacing(8)
        prompts_row.addWidget(QLabel("🔄 Prompts:"))
        self.ed_sheets_url = _line('Google Sheets URL', read_only=False)  # Enhanced: Now editable!
        self.ed_sheets_url.setText(self.state.get('system_prompts_url', 'https://docs.google.com/spreadsheets/d/1ohiL6xOBbjC7La2iUdkjrVjG4IEUnVWhI0fRoarD6P0'))  # Enhanced: Load from config
        prompts_row.addWidget(self.ed_sheets_url, 1)
        self.btn_update_prompts = CompactButton("⬇ Update")
        self.btn_update_prompts.setObjectName("btn_primary")
        self.btn_update_prompts.setMinimumHeight(36)
        self.btn_update_prompts.clicked.connect(self._update_system_prompts)
        prompts_row.addWidget(self.btn_update_prompts)
        root.addLayout(prompts_row)
        
        self.lb_prompts_status = QLabel("")
        self.lb_prompts_status.setFont(FONT_SMALL)
        root.addWidget(self.lb_prompts_status)
        
        # === BOTTOM BAR ===
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        
        self.btn_save = CompactButton("💾 Save Settings")
        self.btn_save.setObjectName("btn_save_luu")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_save.clicked.connect(self._save)
        bottom_row.addWidget(self.btn_save)
        
        self.lb_saved = QLabel("")
        self.lb_saved.setFont(FONT_SMALL)
        self.lb_saved.setStyleSheet("color: #4CAF50; font-weight: bold;")
        bottom_row.addWidget(self.lb_saved)
        bottom_row.addStretch()
        
        self.lb_version = QLabel(f"Video Super Ultra v{get_version()}")
        self.lb_version.setFont(FONT_SMALL)
        bottom_row.addWidget(self.lb_version)
        
        root.addLayout(bottom_row)
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _load_accounts_table(self):
        """Load accounts from config into table"""
        account_mgr = get_account_manager()
        accounts = account_mgr.get_all_accounts()
        
        self.accounts_table.setRowCount(len(accounts))
        
        for row, account in enumerate(accounts):
            # Enabled checkbox
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setChecked(account.enabled)
            checkbox.stateChanged.connect(lambda state, r=row: self._toggle_account(r, state))
            checkbox_layout.addWidget(checkbox)
            self.accounts_table.setCellWidget(row, 0, checkbox_widget)
            
            # Account name
            name_item = QTableWidgetItem(account.name)
            self.accounts_table.setItem(row, 1, name_item)
            
            # Project ID (truncated)
            project_id_display = account.project_id[:16] + "..." if len(account.project_id) > 16 else account.project_id
            project_item = QTableWidgetItem(project_id_display)
            self.accounts_table.setItem(row, 2, project_item)
            
            # Token count
            token_count = QTableWidgetItem(f"{len(account.tokens)} token(s)")
            self.accounts_table.setItem(row, 3, token_count)
    
    def _toggle_account(self, row, state):
        """Toggle account enabled state"""
        account_mgr = get_account_manager()
        if state == Qt.Checked:
            account_mgr.enable_account(row)
        else:
            account_mgr.disable_account(row)
    
    def _add_account(self):
        """Add a new account via dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Google Labs Account")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Account name
        layout.addWidget(_label("Account Name:"))
        ed_name = _line("e.g., Account 1, Production, Testing...")
        layout.addWidget(ed_name)
        
        # Project ID - Pre-fill with default
        layout.addWidget(_label("Project ID:"))
        ed_project_id = _line("9bb9b09b-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        default_project = self.ed_project.text().strip() or DEFAULT_PROJECT_ID
        ed_project_id.setText(default_project)
        layout.addWidget(ed_project_id)
        
        # Tokens
        layout.addWidget(_label("OAuth Tokens (one per line):"))
        ed_tokens = QTextEdit()
        ed_tokens.setPlaceholderText("Paste OAuth tokens here, one per line")
        ed_tokens.setMaximumHeight(120)
        ed_tokens.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Courier New';
                font-size: 11px;
            }
        """)
        layout.addWidget(ed_tokens)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = ed_name.text().strip()
            project_id = ed_project_id.text().strip()
            tokens_text = ed_tokens.toPlainText().strip()
            tokens = [line.strip() for line in tokens_text.split('\n') if line.strip()]
            
            if not name or not project_id or not tokens:
                QMessageBox.warning(self, "Invalid Input", "Please fill all fields")
                return
            
            account = LabsAccount(name=name, project_id=project_id, tokens=tokens, enabled=True)
            
            account_mgr = get_account_manager()
            account_mgr.add_account(account)
            
            self._load_accounts_table()
            self.lb_account_status.setText(f"✓ Added account: {name}")
    
    def _edit_account(self):
        """Edit selected account"""
        row = self.accounts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an account to edit")
            return
        
        account_mgr = get_account_manager()
        account = account_mgr.get_account(row)
        
        if not account:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Google Labs Account")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Account name
        layout.addWidget(_label("Account Name:"))
        ed_name = _line()
        ed_name.setText(account.name)
        layout.addWidget(ed_name)
        
        # Project ID
        layout.addWidget(_label("Project ID:"))
        ed_project_id = _line()
        ed_project_id.setText(account.project_id)
        layout.addWidget(ed_project_id)
        
        # Tokens
        layout.addWidget(_label("OAuth Tokens (one per line):"))
        ed_tokens = QTextEdit()
        ed_tokens.setPlainText('\n'.join(account.tokens))
        ed_tokens.setMaximumHeight(120)
        ed_tokens.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Courier New';
                font-size: 11px;
            }
        """)
        layout.addWidget(ed_tokens)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = ed_name.text().strip()
            project_id = ed_project_id.text().strip()
            tokens_text = ed_tokens.toPlainText().strip()
            tokens = [line.strip() for line in tokens_text.split('\n') if line.strip()]
            
            if not name or not project_id or not tokens:
                QMessageBox.warning(self, "Invalid Input", "Please fill all fields")
                return
            
            # Update account
            account.name = name
            account.project_id = project_id
            account.tokens = tokens
            
            self._load_accounts_table()
            self.lb_account_status.setText(f"✓ Updated account: {name}")
    
    def _remove_account(self):
        """Remove selected account"""
        row = self.accounts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an account to remove")
            return
        
        account_mgr = get_account_manager()
        account = account_mgr.get_account(row)
        
        if not account:
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Removal", 
            f"Remove account '{account.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            account_mgr.remove_account(row)
            self._load_accounts_table()
            self.lb_account_status.setText(f"✓ Removed account: {account.name}")
    
    def _toggle_storage(self):
        is_local = self.rb_local.isChecked()
        self.ed_local.setEnabled(is_local)
        self.btn_browse.setEnabled(is_local)
        self.ed_gdrive.setEnabled(not is_local)
        self.ed_oauth.setEnabled(not is_local)
    
    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, 'Select download folder', '')
        if d:
            self.ed_local.setText(d)
    
    def _save(self):
        storage = 'gdrive' if self.rb_drive.isChecked() else 'local'
        st = {
            **cfg.load(),
            'account_email': self.ed_email.text().strip(),
            'download_storage': storage,
            'download_root': self.ed_local.text().strip(),
            'gdrive_folder_id': self.ed_gdrive.text().strip(),
            'google_workspace_oauth_token': self.ed_oauth.text().strip(),
            'google_api_keys': self.w_google.get_keys(),
            'elevenlabs_api_keys': self.w_eleven.get_keys(),
            'openai_api_keys': self.w_openai.get_keys(),
            'default_voice_id': self.ed_voice.text().strip() or '3VnrjnYrskPMDsapTr8X',
            'flow_project_id': self.ed_project.text().strip() or DEFAULT_PROJECT_ID,
            'system_prompts_url': self.ed_sheets_url.text().strip(),  # Enhanced: Save prompts URL
        }
        
        # ISSUE #4 FIX: Save multi-account manager data
        from services.account_manager import get_account_manager
        account_mgr = get_account_manager()
        account_mgr.save_to_config(st)
        
        cfg.save(st)
        self.lb_saved.setText(f'✓ Saved at {_ts()}')
        
        QTimer.singleShot(5000, lambda: self.lb_saved.setText(''))
    
    def _update_system_prompts(self):
        self.lb_prompts_status.setText('⏳ Updating...')
        self.btn_update_prompts.setEnabled(False)
        QApplication.processEvents()
        
        try:
            from services.prompt_updater import update_prompts_file
            import os
            
            services_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services')
            prompts_file = os.path.join(services_dir, 'domain_prompts.py')
            
            success, message = update_prompts_file(prompts_file)
            
            if success:
                self.lb_prompts_status.setText(f'✅ {message}')
                QMessageBox.information(self, 'Success', message)
            else:
                self.lb_prompts_status.setText(f'❌ {message}')
                QMessageBox.critical(self, 'Error', message)
        
        except Exception as e:
            error_msg = f'❌ Error: {str(e)}'
            self.lb_prompts_status.setText(error_msg)
            QMessageBox.critical(self, 'Error', error_msg)
        
        finally:
            self.btn_update_prompts.setEnabled(True)