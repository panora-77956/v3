# ui/workers/script_worker.py - PATCH
"""
Enhanced error handling for script generation
Fix for Issue #7: Better error messages
"""
import json
import sys
import traceback
from PyQt5.QtCore import QThread, pyqtSignal

from PyQt5.QtCore import QThread, pyqtSignal
import traceback
import json

class ScriptWorker(QThread):
    progress = pyqtSignal(str)
    done = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.should_stop = False

    def run(self):
        try:
            self.progress.emit("Đang tạo kịch bản...")

            from services.sales_script_service import build_outline

            result = build_outline(self.config)

            self.progress.emit("Hoàn thành!")
            self.done.emit(result)

        except json.JSONDecodeError as e:
            # Enhanced JSON error handling with detailed info
            error_msg = (
                f"JSONDecodeError: Không thể phân tích phản hồi từ LLM.\n"
                f"Lỗi tại dòng {e.lineno}, cột {e.colno}: {e.msg}\n\n"
                f"Khắc phục:\n"
                f"1. Thử lại (LLM có thể tạo phản hồi hợp lệ lần sau)\n"
                f"2. Giảm độ dài nội dung hoặc ý tưởng\n"
                f"3. Đơn giản hóa yêu cầu\n"
                f"4. Kiểm tra kết nối mạng"
            )
            self.error.emit(error_msg)
            # Log full traceback for debugging
            print("[ERROR] JSONDecodeError in ScriptWorker:", file=sys.stderr)
            traceback.print_exc()

        except ValueError as e:
            # Handle empty or invalid responses
            error_msg = f"ValueError: {str(e)}\n\nKhắc phục: Kiểm tra API key và kết nối mạng."
            self.error.emit(error_msg)
            print("[ERROR] ValueError in ScriptWorker:", file=sys.stderr)
            traceback.print_exc()

        except Exception as e:
            # Include exception type name for better error classification
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)}"
            self.error.emit(error_msg)
            # Log full traceback for debugging
            print(f"[ERROR] {error_type} in ScriptWorker:", file=sys.stderr)
            traceback.print_exc()
