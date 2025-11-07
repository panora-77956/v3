# -*- coding: utf-8 -*-
# Shim for backward compatibility - re-export ProjectPanel from ui.project_panel
from ui.project_panel import ProjectPanel  # noqa: F401

__all__ = ["ProjectPanel"]
