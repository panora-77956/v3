# -*- coding: utf-8 -*-
"""
Button utilities for easy RippleButton usage
"""

from ui.widgets.ripple_button import RippleButton

def create_ripple_button(text, object_name=None, parent=None):
    """
    Create a RippleButton with common settings
    
    Args:
        text: Button text
        object_name: Optional objectName for styling
        parent: Parent widget
    
    Returns:
        RippleButton instance
    """
    btn = RippleButton(text, parent)
    if object_name:
        btn.setObjectName(object_name)
    btn.setMinimumHeight(28)
    btn.setMaximumHeight(32)
    return btn

# Example usage:
# from ui.widgets.button_utils import create_ripple_button
# 
# btn_save = create_ripple_button("💾 Lưu", "btn_save")
# btn_delete = create_ripple_button("🗑️ Xóa", "btn_danger")
