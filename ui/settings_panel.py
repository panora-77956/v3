# -*- coding: utf-8 -*-
import datetime

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWidgets import QWidget as _QW

from ui.widgets.key_list import KeyList
from utils import config as cfg
from utils.version import get_version

# Typography
FONT_TITLE = QFont(); FONT_TITLE.setPixelSize(14); FONT_TITLE.setBold(True)     # Section header 14px
FONT_LABEL = QFont(); FONT_LABEL.setPixelSize(13)                               # Labels 13px
FONT_INPUT = QFont(); FONT_INPUT.setPixelSize(12)                               # Inputs 12px
FONT_VALUE_BOLD = QFont(); FONT_VALUE_BOLD.setPixelSize(13); FONT_VALUE_BOLD.setBold(True)  # Bold 13px for content
FONT_BTN_BIG = QFont(); FONT_BTN_BIG.setPixelSize(14); FONT_BTN_BIG.setBold(True)           # Save button

def _ts():
    return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

def _line(ph='', bold=False):
    e = QLineEdit()
    e.setPlaceholderText(ph)
    e.setFont(FONT_VALUE_BOLD if bold else FONT_INPUT)
    return e

def _lab(text):
    l = QLabel(text)
    l.setFont(FONT_LABEL)
    return l

def _decorate_group(gb: QGroupBox):
    # PR#6: Part E #26 - Compact spacing 6px, dark theme styling
    # Styling is now handled by unified theme, so this is optional
    pass

class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = cfg.load()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12)
        root.setSpacing(4)  # Compact spacing between GroupBoxes

        # Section: Thông tin tài khoản
        acc = QGroupBox('Thông tin tài khoản'); _decorate_group(acc)
        g = QGridLayout(acc); g.setVerticalSpacing(6)
        self.ed_email = _line('Email', bold=True); self.ed_email.setText(self.state.get('account_email',''))
        self.lb_hwid = QLabel(self.state.get('hardware_id','')); self.lb_hwid.setFont(FONT_VALUE_BOLD)
        self.ed_status = _line('Trạng thái', bold=True); self.ed_status.setText(self.state.get('license_status','active'))
        self.ed_expiry = _line('Thời hạn sử dụng (yyyy/mm/dd)', bold=True); self.ed_expiry.setText(self.state.get('license_expiry',''))
        g.addWidget(_lab('Email:'),0,0); g.addWidget(self.ed_email,0,1)
        g.addWidget(_lab('Mã hardwave-id:'),0,2); g.addWidget(self.lb_hwid,0,3)
        g.addWidget(_lab('Trạng thái:'),1,0); g.addWidget(self.ed_status,1,1)
        g.addWidget(_lab('Thời hạn sử dụng:'),1,2); g.addWidget(self.ed_expiry,1,3)
        root.addWidget(acc)

        # Dòng 2: Labs + ProjectID | ElevenLabs + VoiceID (Equal width - FORCED)
        row2 = _QW()
        grid2 = QHBoxLayout(row2)  # Use HBoxLayout for true 50-50 split
        grid2.setSpacing(12)

        # Left column (50%)
        left_col = _QW()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        labs_init = self.state.get('labs_tokens') or self.state.get('tokens') or []
        self.w_labs = KeyList(title='Google Labs Token (OAuth)', kind='labs', initial=labs_init)
        left_layout.addWidget(self.w_labs)

        self.ed_project = _line('Project ID')
        self.ed_project.setText(self.state.get('flow_project_id','87b19267-13d6-49cd-a7ed-db19a90c9339'))
        proj_box = _QW()
        hp = QHBoxLayout(proj_box)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.addWidget(_lab('Project ID cho Flow:'))
        hp.addWidget(self.ed_project)
        left_layout.addWidget(proj_box)

        grid2.addWidget(left_col, 1)  # stretch factor = 1

        # Right column (50%)
        right_col = _QW()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self.w_eleven = KeyList(title='Elevenlabs API Keys', kind='elevenlabs', initial=self.state.get('elevenlabs_api_keys') or [])
        right_layout.addWidget(self.w_eleven)

        self.ed_voice = _line('Voice ID')
        self.ed_voice.setText(self.state.get('default_voice_id','3VnrjnYrskPMDsapTr8X'))
        voice_box = _QW()
        hv = QHBoxLayout(voice_box)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.addWidget(_lab('Voice ID (Elevenlabs):'))
        hv.addWidget(self.ed_voice)
        right_layout.addWidget(voice_box)

        grid2.addWidget(right_col, 1)  # stretch factor = 1

        root.addWidget(row2)

        # Dòng 3: Google API | OpenAI API (Equal width - FORCED)
        row3 = _QW()
        grid3 = QHBoxLayout(row3)  # Use HBoxLayout for true 50-50 split
        grid3.setSpacing(12)

        # Left column (50%)
        g_list = self.state.get('google_api_keys') or ([] if not self.state.get('google_api_key') else [self.state.get('google_api_key')])
        self.w_google = KeyList(title='Google API Keys', kind='google', initial=g_list)
        grid3.addWidget(self.w_google, 1)  # stretch factor = 1

        # Right column (50%)
        self.w_openai = KeyList(title='OpenAI API Keys', kind='openai', initial=self.state.get('openai_api_keys') or [])
        grid3.addWidget(self.w_openai, 1)  # stretch factor = 1

        root.addWidget(row3)


        # Dòng 4: Download Directory + System Prompts Updater (same row)
        row4 = _QW()
        grid4 = QGridLayout(row4)
        grid4.setHorizontalSpacing(12)
        grid4.setVerticalSpacing(4)

        # Left: Download Directory (50% width)
        st = QGroupBox('Thư mục tải về'); _decorate_group(st)
        gs = QGridLayout(st); gs.setVerticalSpacing(6)
        self.rb_local = QRadioButton('Lưu tại Local'); self.rb_drive = QRadioButton('Google Drive')
        storage = (self.state.get('download_storage') or 'local').lower()
        (self.rb_drive if storage=='gdrive' else self.rb_local).setChecked(True)
        gs.addWidget(self.rb_local, 0, 0); gs.addWidget(self.rb_drive, 0, 1)
        self.ed_local = _line('Chọn thư mục...'); self.ed_local.setText(self.state.get('download_root',''))
        self.btn_browse = QPushButton('Chọn...'); self.btn_browse.setObjectName('btn_browse')
        self.btn_browse.setMinimumHeight(32)
        self.btn_browse.clicked.connect(self._pick_dir)
        gs.addWidget(_lab('Đường dẫn (Local):'), 1, 0); gs.addWidget(self.ed_local, 1, 1, 1, 2); gs.addWidget(self.btn_browse, 1, 3)
        self.ed_gdrive = _line('Google Drive Folder ID'); self.ed_gdrive.setText(self.state.get('gdrive_folder_id',''))
        self.ed_oauth  = _line('Google Workspace OAuth Token'); self.ed_oauth.setText(self.state.get('google_workspace_oauth_token',''))
        gs.addWidget(_lab('Folder ID (Drive):'), 2, 0); gs.addWidget(self.ed_gdrive, 2, 1, 1, 3)
        gs.addWidget(_lab('OAuth Token:'), 3, 0); gs.addWidget(self.ed_oauth, 3, 1, 1, 3)
        grid4.addWidget(st, 0, 0, 1, 1)

        # Right: System Prompts Updater (50% width)
        prompts_group = QGroupBox('🔄 System Prompts Updater'); _decorate_group(prompts_group)
        gp = QGridLayout(prompts_group); gp.setVerticalSpacing(6)

        # Description
        lbl_desc = QLabel('Cập nhật system prompts từ Google Sheets mà không cần khởi động lại ứng dụng')
        lbl_desc.setWordWrap(True)
        lbl_desc.setFont(FONT_LABEL)
        gp.addWidget(lbl_desc, 0, 0, 1, 2)

        # Google Sheets URL (read-only)
        self.ed_sheets_url = _line('Google Sheets URL', bold=True)
        self.ed_sheets_url.setText('https://docs.google.com/spreadsheets/d/1ohiL6xOBbjC7La2iUdkjrVjG4IEUnVWhI0fRoarD6P0')
        self.ed_sheets_url.setReadOnly(True)
        gp.addWidget(_lab('URL:'), 1, 0); gp.addWidget(self.ed_sheets_url, 1, 1)

        # Update button + Status (same row)
        self.btn_update_prompts = QPushButton('⬇️ Cập nhật System Prompts')
        self.btn_update_prompts.setObjectName('btn_primary')
        self.btn_update_prompts.setMinimumHeight(40)
        self.btn_update_prompts.clicked.connect(self._update_system_prompts)
        gp.addWidget(self.btn_update_prompts, 2, 0, 1, 1)

        # Status label
        self.lb_prompts_status = QLabel('')
        self.lb_prompts_status.setFont(FONT_LABEL)
        self.lb_prompts_status.setWordWrap(True)
        gp.addWidget(self.lb_prompts_status, 3, 0, 1, 2)

        grid4.addWidget(prompts_group, 0, 1, 1, 1)

        root.addWidget(row4)

        self.rb_local.toggled.connect(self._toggle_storage_fields)
        self.rb_drive.toggled.connect(self._toggle_storage_fields)
        self._toggle_storage_fields()

        # Dòng 5: Lưu + Info app ở bên phải
        row5 = QHBoxLayout()
        self.btn_save = QPushButton('💾 Lưu cấu hình'); self.btn_save.setFont(FONT_BTN_BIG)
        self.btn_save.setObjectName('btn_save_luu')  # Green color (using both keywords for theme matching)
        self.btn_save.setMinimumHeight(40)  # Consistent height
        self.lb_saved = QLabel(''); self.lb_saved.setFont(FONT_BTN_BIG)
        row5.addWidget(self.btn_save); row5.addWidget(self.lb_saved); row5.addStretch(1)

        # Block thông tin ứng dụng (bên phải)
        self.lb_appname = QLabel('Video Super Ultra')
        self.lb_version = QLabel(f'Version: V{get_version()}')
        self.lb_author  = QLabel('Phát triển bởi Châm Bầu @2025')
        app_font = QFont(); app_font.setPixelSize(14); app_font.setBold(True)
        ver_font = QFont(); ver_font.setPixelSize(14)
        auth_font = QFont(); auth_font.setPixelSize(14)
        self.lb_appname.setFont(app_font); self.lb_version.setFont(ver_font); self.lb_author.setFont(auth_font)
        info_box = _QW(); vbox = QVBoxLayout(info_box); vbox.setContentsMargins(0,0,0,0); vbox.setSpacing(0)
        vbox.addWidget(self.lb_appname); vbox.addWidget(self.lb_version); vbox.addWidget(self.lb_author)
        row5.addWidget(info_box)
        root.addLayout(row5)

        self.btn_save.clicked.connect(self._save)

    def _toggle_storage_fields(self):
        is_local = self.rb_local.isChecked()
        self.ed_local.setEnabled(is_local); self.btn_browse.setEnabled(is_local)
        self.ed_gdrive.setEnabled(not is_local); self.ed_oauth.setEnabled(not is_local)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, 'Chọn thư mục tải về', '')
        if d: self.ed_local.setText(d)

    def _save(self):
        storage = 'gdrive' if self.rb_drive.isChecked() else 'local'
        st = {
            **cfg.load(),
            'account_email': self.ed_email.text().strip(),
            'license_status': self.ed_status.text().strip() or 'active',
            'license_expiry': self.ed_expiry.text().strip(),
            'download_storage': storage,
            'download_root': self.ed_local.text().strip(),
            'gdrive_folder_id': self.ed_gdrive.text().strip(),
            'google_workspace_oauth_token': self.ed_oauth.text().strip(),
            'labs_tokens': self.w_labs.get_keys(),
            'tokens': self.w_labs.get_keys(),
            'google_api_keys': self.w_google.get_keys(),
            'elevenlabs_api_keys': self.w_eleven.get_keys(),
            'openai_api_keys': self.w_openai.get_keys(),
            'default_voice_id': self.ed_voice.text().strip() or '3VnrjnYrskPMDsapTr8X',
            'flow_project_id': self.ed_project.text().strip() or '87b19267-13d6-49cd-a7ed-db19a90c9339',
            'prompts_sheet_url': self.ed_sheets_url.text().strip(),
        }
        cfg.save(st)
        self.lb_saved.setText('Đã lưu: ' + _ts())

    def _update_system_prompts(self):
        """Update system prompts from Google Sheets with hot reload"""
        import os
        from PyQt5.QtWidgets import QMessageBox

        # Get URL from input
        sheet_url = self.ed_sheets_url.text().strip()
        if not sheet_url:
            QMessageBox.warning(
                self, 
                'Thiếu URL',
                'Vui lòng nhập URL Google Sheets trước khi cập nhật!'
            )
            return

        # Show progress
        self.lb_prompts_status.setText('Đang tải dữ liệu từ Google Sheets...')
        self.btn_update_prompts.setEnabled(False)

        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            from services.prompt_updater import update_prompts_file

            # Get path to domain_prompts.py
            services_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services')
            prompts_file = os.path.join(services_dir, 'domain_prompts.py')

            # Update file with custom URL
            success, message = update_prompts_file(prompts_file, sheet_url=sheet_url)

            if success:
                # Hot reload the prompts
                from services.domain_prompts import reload_prompts
                reload_success, reload_msg = reload_prompts()

                if reload_success:
                    status_text = message + chr(10) + reload_msg + chr(10) + 'Hot reload thành công!'
                    self.lb_prompts_status.setText(status_text)
                    msg_text = message + chr(10) + chr(10) + 'Các prompts mới đã được tải và sẵn sàng sử dụng ngay!'
                    QMessageBox.information(self, 'Thành công', msg_text)
                else:
                    status_text = message + chr(10) + reload_msg
                    self.lb_prompts_status.setText(status_text)
                    msg_text = message + chr(10) + chr(10) + 'Nhưng reload không thành công: ' + reload_msg + chr(10) + chr(10) + 'Vui lòng khởi động lại ứng dụng.'
                    QMessageBox.warning(self, 'Cảnh báo', msg_text)
            else:
                self.lb_prompts_status.setText(message)
                QMessageBox.critical(self, 'Lỗi', message)

        except Exception as e:
            error_msg = 'Lỗi không xác định: ' + str(e)
            self.lb_prompts_status.setText(error_msg)
            QMessageBox.critical(self, 'Lỗi', error_msg)

        finally:
            self.btn_update_prompts.setEnabled(True)
