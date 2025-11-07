# Hướng dẫn thêm ảnh báo lỗi (Error Image Guide)

## Tổng quan (Overview)

Hệ thống đã được nâng cấp để hỗ trợ hiển thị **ảnh icon báo lỗi** thay vì chỉ sử dụng emoji. Điều này giúp giao diện chuyên nghiệp và nhất quán hơn.

### Các tính năng chính:
- ✅ Hỗ trợ 4 loại icon: Error, Warning, Success, Info
- ✅ Tự động fallback sang emoji nếu không có file ảnh
- ✅ Widget có thể tái sử dụng cho toàn bộ ứng dụng
- ✅ Kích thước icon có thể điều chỉnh
- ✅ Layout linh hoạt (vertical/horizontal)

---

## Cấu trúc thư mục (Directory Structure)

```
v3/
├── resources/
│   └── icons/
│       ├── error.png       # Icon lỗi (màu đỏ)
│       ├── warning.png     # Icon cảnh báo (màu cam)
│       ├── success.png     # Icon thành công (màu xanh lá)
│       └── info.png        # Icon thông tin (màu xanh dương)
├── utils/
│   └── icon_utils.py       # Tiện ích load icon
└── ui/
    └── widgets/
        ├── error_display.py    # Widget hiển thị lỗi
        └── status_label.py     # Label có icon
```

---

## Cách sử dụng (How to Use)

### 1. Sử dụng Icon Utilities (Cách đơn giản nhất)

```python
from utils.icon_utils import get_error_icon, get_warning_icon

# Load error icon với kích thước 64x64
error_pixmap = get_error_icon(size=(64, 64))

# Hiển thị trong QLabel
if error_pixmap:
    label = QLabel()
    label.setPixmap(error_pixmap)
```

### 2. Sử dụng ErrorDisplayWidget (Recommended)

Widget chuyên dụng để hiển thị lỗi với icon và text:

```python
from ui.widgets.error_display import create_error_display

# Tạo error display widget
error_widget = create_error_display(
    title="Connection Failed",
    message="Could not connect to the server. Please check your network.",
    compact=False  # False = vertical layout, True = horizontal
)

# Thêm vào layout
layout.addWidget(error_widget)
```

**Các loại display có sẵn:**
```python
from ui.widgets.error_display import (
    create_error_display,    # Hiển thị lỗi (đỏ)
    create_warning_display,  # Hiển thị cảnh báo (cam)
    create_success_display,  # Hiển thị thành công (xanh lá)
    create_info_display      # Hiển thị thông tin (xanh dương)
)
```

### 3. Sử dụng StatusLabel (Cho status inline)

Label có icon nhỏ ở bên cạnh text, phù hợp cho status messages:

```python
from ui.widgets.status_label import create_error_label

# Tạo status label với icon
status = create_error_label(
    text="5 videos failed to process",
    icon_size=20  # Kích thước icon (px)
)

# Hoặc tạo trực tiếp
from ui.widgets.status_label import StatusLabel

status = StatusLabel(
    text="Processing...",
    icon_type="info",  # error, warning, success, info
    icon_size=16
)
```

---

## Ví dụ thực tế (Real Examples)

### Ví dụ 1: Hiển thị lỗi trong Panel

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from ui.widgets.error_display import create_error_display

class MyPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Hiển thị lỗi khi load thất bại
        error = create_error_display(
            title="Module Not Found",
            message="Please install required dependencies:\n"
                   "pip install -r requirements.txt",
            compact=False
        )
        layout.addWidget(error)
```

### Ví dụ 2: Status label trong danh sách video

```python
from ui.widgets.status_label import StatusLabel

# Trong _create_scene_card method
status_label = StatusLabel(
    text=f"{failed} failed, {completed}/{total} OK",
    icon_type="error" if failed > 0 else "success",
    icon_size=16
)
status_label.setStyleSheet("color: #E53935; font-weight: bold;")
card_layout.addWidget(status_label)
```

### Ví dụ 3: Cập nhật PlaceholderPanel

```python
# main_image2video.py đã được update
class PlaceholderPanel(QWidget):
    def __init__(self, panel_name, error_msg="", parent=None):
        super().__init__(parent)
        # ...
        
        # Load warning icon
        from utils.icon_utils import get_warning_icon
        icon_pixmap = get_warning_icon(size=(96, 96))
        
        if icon_pixmap:
            icon_label.setPixmap(icon_pixmap)
        else:
            icon_label.setText("⚠️")  # Fallback
```

---

## API Reference

### icon_utils.py

#### Functions:
```python
# Load icon as QPixmap
get_error_icon(size=(w, h)) -> QPixmap or None
get_warning_icon(size=(w, h)) -> QPixmap or None
get_success_icon(size=(w, h)) -> QPixmap or None
get_info_icon(size=(w, h)) -> QPixmap or None

# Load icon as QIcon (for buttons, windows)
load_icon(icon_type: str) -> QIcon

# Get icon with emoji fallback
get_icon_or_emoji(icon_type: str) -> (QPixmap or None, str)

# Check if icons are available
has_icon_support() -> bool
get_icon_status() -> dict  # {'error': True, 'warning': True, ...}
```

#### Icon Types:
```python
from utils.icon_utils import IconType

IconType.ERROR    # "error"
IconType.WARNING  # "warning"
IconType.SUCCESS  # "success"
IconType.INFO     # "info"
```

### ErrorDisplayWidget

#### Constructor:
```python
ErrorDisplayWidget(
    title: str,              # Tiêu đề chính
    message: str = "",       # Thông báo chi tiết (optional)
    icon_type: str = "error", # error/warning/success/info
    icon_size: int = 64,     # Kích thước icon (px)
    compact: bool = False,   # True = horizontal, False = vertical
    parent = None
)
```

#### Methods:
```python
update_message(title: str, message: str)  # Cập nhật nội dung
```

### StatusLabel

#### Constructor:
```python
StatusLabel(
    text: str = "",          # Text hiển thị
    icon_type: str = None,   # error/warning/success/info hoặc None
    icon_size: int = 16,     # Kích thước icon (px)
    parent = None
)
```

#### Methods:
```python
setText(text: str)           # Đặt text
text() -> str                # Lấy text
setIcon(icon_type: str)      # Thay đổi icon
setStyleSheet(style: str)    # Áp dụng style
setFont(font: QFont)         # Đặt font
```

---

## Thêm icon tùy chỉnh (Custom Icons)

### Cách 1: Thay thế file hiện có

1. Tạo file PNG với kích thước 128x128 px
2. Đặt tên: `error.png`, `warning.png`, `success.png`, hoặc `info.png`
3. Copy vào thư mục `resources/icons/`
4. Restart ứng dụng

**Khuyến nghị:**
- Format: PNG với transparent background
- Size: 128x128 px (sẽ được scale tự động)
- Style: Simple, flat design với màu rõ ràng

### Cách 2: Thêm icon mới

1. Thêm file PNG vào `resources/icons/`
2. Cập nhật `utils/icon_utils.py`:

```python
# Thêm vào ICON_FILES dict
ICON_FILES = {
    IconType.ERROR: 'icons/error.png',
    IconType.WARNING: 'icons/warning.png',
    IconType.SUCCESS: 'icons/success.png',
    IconType.INFO: 'icons/info.png',
    'custom_type': 'icons/custom.png',  # THÊM MỚI
}

# Thêm emoji fallback
EMOJI_FALLBACKS = {
    IconType.ERROR: '❌',
    IconType.WARNING: '⚠️',
    IconType.SUCCESS: '✅',
    IconType.INFO: 'ℹ️',
    'custom_type': '🎯',  # THÊM MỚI
}
```

3. Sử dụng:
```python
from utils.icon_utils import load_icon_pixmap
custom_icon = load_icon_pixmap('custom_type', size=(64, 64))
```

---

## Màu sắc chuẩn (Standard Colors)

```python
ERROR_COLOR   = "#E53935"  # Đỏ (Red)
WARNING_COLOR = "#FF8F00"  # Cam (Orange)
SUCCESS_COLOR = "#4CAF50"  # Xanh lá (Green)
INFO_COLOR    = "#1E88E5"  # Xanh dương (Blue)
```

Sử dụng trong stylesheet:
```python
label.setStyleSheet(f"color: {ERROR_COLOR}; font-weight: bold;")
```

---

## Troubleshooting

### Vấn đề: Icon không hiển thị, chỉ thấy emoji

**Nguyên nhân:**
- File icon không tồn tại trong `resources/icons/`
- Path không đúng
- File bị corrupt

**Giải pháp:**
1. Kiểm tra file tồn tại:
```bash
ls -la resources/icons/
```

2. Test icon loading:
```python
from utils.icon_utils import get_icon_status
print(get_icon_status())
# Expected: {'error': True, 'warning': True, 'success': True, 'info': True}
```

3. Tạo lại icons:
```bash
python3 -c "exec(open('docs/create_icons.py').read())"
```

### Vấn đề: QPixmap error khi test

**Nguyên nhân:** QPixmap yêu cầu QApplication

**Giải pháp:** Chỉ test trong context của QApplication:
```python
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
# Now can test icon loading
from utils.icon_utils import get_error_icon
icon = get_error_icon()
print(f"Icon loaded: {icon is not None}")
```

---

## Migration Guide (Nâng cấp code hiện có)

### Trước (Old):
```python
icon_label = QLabel("❌")
icon_label.setFont(QFont("Segoe UI", 48))
```

### Sau (New):
```python
from utils.icon_utils import get_error_icon

icon_label = QLabel()
error_icon = get_error_icon(size=(64, 64))
if error_icon:
    icon_label.setPixmap(error_icon)
else:
    icon_label.setText("❌")  # Fallback
    icon_label.setFont(QFont("Segoe UI", 48))
```

### Hoặc đơn giản hơn với ErrorDisplayWidget:
```python
from ui.widgets.error_display import create_error_display

# Thay vì tự tạo layout với QLabel
error_widget = create_error_display(
    title="Error Title",
    message="Error details here"
)
```

---

## Best Practices

1. **Luôn có fallback:** Đảm bảo emoji fallback hoạt động khi không có icon
2. **Kích thước nhất quán:** Sử dụng kích thước chuẩn (16px, 24px, 48px, 64px, 96px)
3. **Màu sắc chuẩn:** Sử dụng màu đã định nghĩa (ERROR_COLOR, WARNING_COLOR, v.v.)
4. **Tái sử dụng widgets:** Dùng ErrorDisplayWidget và StatusLabel thay vì tự tạo
5. **Test fallback:** Đảm bảo app vẫn hoạt động khi xóa thư mục resources/

---

## Changelog

### Version 1.0.0 (2025-11-07)
- ✅ Tạo thư mục resources/icons/ với 4 icon chuẩn
- ✅ Tạo utils/icon_utils.py để load icons
- ✅ Tạo ErrorDisplayWidget widget
- ✅ Tạo StatusLabel widget  
- ✅ Cập nhật PlaceholderPanel sử dụng icon
- ✅ Documentation đầy đủ

---

## Câu hỏi thường gặp (FAQ)

**Q: Tôi có thể dùng SVG thay vì PNG không?**
A: Có, nhưng cần cập nhật code để load SVG. Hiện tại chỉ support PNG.

**Q: Làm sao tạo icon với style khác?**
A: Có thể dùng tool thiết kế (Figma, Photoshop) hoặc edit code tạo icon trong create_icons.py

**Q: Icon có tự động scale theo DPI không?**
A: Có, QPixmap tự động handle High DPI nếu Qt High DPI scaling được bật.

**Q: Có thể dùng emoji mà không cần icon không?**
A: Có, chỉ cần xóa thư mục resources/icons/ là app tự động fallback sang emoji.

---

**Tác giả:** chamnv-dev  
**Ngày:** 2025-11-07  
**Version:** 1.0.0
