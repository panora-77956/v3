# Error Image Support - Quick Start

## Question: "làm sao để tôi thêm ảnh báo lỗi vào đây?"

## Answer: ✅ IMPLEMENTED!

---

## Quick Usage

### 1. Display Error with Icon

```python
from ui.widgets.error_display import create_error_display

error = create_error_display(
    title="Connection Failed",
    message="Could not connect to server"
)
layout.addWidget(error)
```

### 2. Status Label with Icon

```python
from ui.widgets.status_label import create_error_label

status = create_error_label("5 videos failed")
layout.addWidget(status)
```

### 3. Use Icon Directly

```python
from utils.icon_utils import get_error_icon

icon = get_error_icon(size=(64, 64))
label.setPixmap(icon)
```

---

## Available Icons

- 🔴 Error (`error.png`) - Red
- 🟠 Warning (`warning.png`) - Orange
- 🟢 Success (`success.png`) - Green
- 🔵 Info (`info.png`) - Blue

All icons are in `resources/icons/`

---

## Features

✅ Automatic emoji fallback  
✅ Configurable sizes  
✅ Reusable widgets  
✅ Both vertical and horizontal layouts  
✅ Full documentation

---

## Documentation

📖 **Full Guide:** `docs/ERROR_IMAGE_GUIDE.md` (Vietnamese)  
🎮 **Demo:** `python examples/error_image_demo.py`  
🔧 **Regenerate Icons:** `python docs/create_icons.py`

---

## Files Created

- `resources/icons/*.png` - Icon images
- `utils/icon_utils.py` - Loading utilities
- `ui/widgets/error_display.py` - ErrorDisplayWidget
- `ui/widgets/status_label.py` - StatusLabel
- `docs/ERROR_IMAGE_GUIDE.md` - Complete guide
- `examples/error_image_demo.py` - Demo app

---

**Status:** Production Ready ✅  
**Version:** 1.0.0  
**Date:** 2025-11-07
