# -*- coding: utf-8 -*-
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services import key_check_service as kcs

FONT_TITLE = QFont(); FONT_TITLE.setPixelSize(14); FONT_TITLE.setBold(True)
FONT_LABEL = QFont(); FONT_LABEL.setPixelSize(13)
# PR#6: Part E #29 - Use 12px monospace font for keys
FONT_TEXT  = QFont("Courier New", 12); FONT_TEXT.setStyleHint(QFont.Monospace)

def _ts(): return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
def mask_sensitive_text(text: str, show_chars: int = 8) -> str:
    """Mask sensitive text showing only first and last N characters
    
    Args:
        text: Original text to mask
        show_chars: Number of characters to show at start and end
    
    Returns:
        Masked string like "12345678.....xyzabcde"
    """
    if not text or len(text) <= show_chars * 2:
        return text
    
    return f"{text[:show_chars]}.....{text[-show_chars:]}"

def _mask(s:str)->str:
    """Mask API key for display"""
    return mask_sensitive_text((s or '').strip(), show_chars=8)

class _KeyItem(QWidget):
    def __init__(self, kind:str, key:str):
        super().__init__()
        self.kind=kind; self.key=(key or '').strip()
        h=QHBoxLayout(self); h.setContentsMargins(6,4,6,4); h.setSpacing(8)
        # Show masked key with monospace font
        self.lb_key=QLabel(_mask(self.key))
        self.lb_key.setFont(FONT_TEXT)
        self.lb_key.setWordWrap(False)
        # Enable text selection for copying
        self.lb_key.setTextInteractionFlags(self.lb_key.textInteractionFlags() | Qt.TextSelectableByMouse)
        # Store full key in property and show in tooltip
        self.lb_key.setProperty("full_key", self.key)
        self.lb_key.setToolTip(f"Full key (selectable): {self.key}")
        
        self.lb_status=QLabel(''); self.lb_status.setFont(FONT_TEXT)
        self.btn_test=QPushButton('✓'); self.btn_test.setObjectName('btn_check_kiem')
        self.btn_test.setMinimumHeight(32)
        self.btn_test.setMaximumHeight(32)
        self.btn_test.setFixedWidth(40)
        self.btn_test.setStyleSheet("padding: 6px; font-size: 13px;")
        self.btn_test.setToolTip('Kiểm tra key này')
        self.btn_del=QPushButton('🗑'); self.btn_del.setObjectName('btn_delete_xoa')
        self.btn_del.setMinimumHeight(32)
        self.btn_del.setMaximumHeight(32)
        self.btn_del.setFixedWidth(40)
        self.btn_del.setStyleSheet("padding: 6px; font-size: 13px;")
        self.btn_del.setToolTip('Xóa key này')
        h.addWidget(self.lb_key); h.addStretch(1); h.addWidget(self.btn_test); h.addWidget(self.lb_status); h.addWidget(self.btn_del)
        self.btn_test.clicked.connect(self._on_test)
    def _on_test(self):
        ok,msg=kcs.check(self.kind, self.key)
        self.lb_status.setText(('✓ ' if ok else '✗ ')+msg)

class KeyList(QWidget):
    def __init__(self, *, title:str, kind:str, initial=None):
        super().__init__()
        self.kind=kind; initial=initial or []
        v=QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        self.lb_title=QLabel(title); self.lb_title.setFont(FONT_TITLE)
        v.addWidget(self.lb_title)
        # Set list height to show ~3 keys (40px per row), with scroll support
        self.listw=QListWidget()
        self.listw.setMinimumHeight(120)  # Show at least 3 rows
        self.listw.setMaximumHeight(160)  # Max ~4 rows before scrolling
        self.listw.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.listw.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        v.addWidget(self.listw)
        row=QHBoxLayout()
        # Add input field and button with consistent height
        self.ed_new=QLineEdit(); self.ed_new.setFont(FONT_TEXT); self.ed_new.setPlaceholderText('Dán API Key của bạn vào đây')
        self.ed_new.setMinimumHeight(32)
        self.btn_add=QPushButton('Thêm Key'); self.btn_add.setObjectName('btn_primary')
        self.btn_add.setMinimumHeight(32)
        self.btn_add.setMaximumHeight(32)
        self.btn_add.setStyleSheet("padding: 6px 12px; font-size: 13px;")
        self.btn_add.setToolTip('Thêm API key mới')
        self.btn_add.clicked.connect(self._add_from_input)
        row.addWidget(self.ed_new); row.addWidget(self.btn_add); v.addLayout(row)
        actions=QHBoxLayout()
        # Action buttons with consistent styling
        self.btn_import=QPushButton('📁 Nhập từ File (.txt)'); self.btn_import.setObjectName('btn_import_nhap')  # Orange
        self.btn_import.setMinimumHeight(32)
        self.btn_import.setMaximumHeight(32)
        self.btn_import.setStyleSheet("padding: 6px 12px; font-size: 13px;")
        self.btn_import.setToolTip('Import keys from text file')
        self.btn_test_all=QPushButton('✓ Kiểm tra tất cả'); self.btn_test_all.setObjectName('btn_check_kiem')  # Teal
        self.btn_test_all.setMinimumHeight(32)
        self.btn_test_all.setMaximumHeight(32)
        self.btn_test_all.setStyleSheet("padding: 6px 12px; font-size: 13px;")
        self.btn_test_all.setToolTip('Test all API keys')
        self.btn_import.clicked.connect(self._import_txt); self.btn_test_all.clicked.connect(self._test_all)
        actions.addWidget(self.btn_import); actions.addWidget(self.btn_test_all); actions.addStretch(1); v.addLayout(actions)
        self.set_keys(initial)
    def set_keys(self, keys):
        self.listw.clear(); seen=set()
        for k in (keys or []):
            k=(k or '').strip()
            if not k or k in seen: continue
            seen.add(k); self._add_item(k)
    def get_keys(self):
        out=[]
        for i in range(self.listw.count()):
            w=self.listw.itemWidget(self.listw.item(i))
            if w and w.key: out.append(w.key)
        return out
    def _add_item(self, key:str):
        it=QListWidgetItem(self.listw)
        w=_KeyItem(self.kind, key)
        self.listw.setItemWidget(it, w); it.setSizeHint(w.sizeHint())
        def _del(): self.listw.takeItem(self.listw.row(it))
        w.btn_del.clicked.connect(_del)
    def _add_from_input(self):
        key=(self.ed_new.text() or '').strip()
        if key and key not in set(self.get_keys()):
            self._add_item(key)
        self.ed_new.clear()
    def _import_txt(self):
        path,_=QFileDialog.getOpenFileName(self, 'Chọn file .txt', '', 'Text Files (*.txt)')
        if not path: return
        try:
            with open(path,'r',encoding='utf-8') as f:
                lines=[x.strip() for x in f.read().splitlines() if x.strip()]
            cur=set(self.get_keys())
            for k in lines:
                if k not in cur: self._add_item(k); cur.add(k)
        except Exception: pass
    def _test_all(self):
        for i in range(self.listw.count()):
            w=self.listw.itemWidget(self.listw.item(i))
            if w: w._on_test()
