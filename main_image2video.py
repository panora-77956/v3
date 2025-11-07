# main_image2video.py
"""
Video Super Ultra V7 - Main Application
Complete with all V5/V7 panels:
- Image2Video V7 (multi-project, modern UI)
- Text2Video V5 (ocean blue tabs, full workflow)
- Video Ads V5 (collapsible sections, character bible)
- Settings Panel

Author: chamnv-dev
Date: 2025-01-05
Version: 7.0.0
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QTabWidget, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Settings Panel
try:
    from ui.settings_panel_v3_compact import SettingsPanelV3Compact as SettingsPanel
except ImportError:
    try:
        from ui.settings_panel import SettingsPanel
    except ImportError:
        print("⚠️ Warning: SettingsPanel not found, using placeholder")
        SettingsPanel = None

# Image2Video V7 - NEW VERSION
try:
    from ui.image2video_panel_v7_complete import Image2VideoPanelV7 as Image2VideoPanel
    print("✓ Loaded Image2Video V7")
except ImportError as e:
    print(f"⚠️ Image2Video V7 not found, falling back to original: {e}")
    try:
        from ui.project_panel import ProjectPanel as Image2VideoPanel
    except ImportError:
        print("❌ Error: No Image2Video panel available")
        Image2VideoPanel = None

# Text2Video V5 - NEW VERSION
try:
    from ui.text2video_panel_v5_complete import Text2VideoPanelV5 as Text2VideoPanel
    print("✓ Loaded Text2Video V5")
except ImportError as e:
    print(f"⚠️ Text2Video V5 not found, falling back to original: {e}")
    try:
        from ui.text2video_panel import Text2VideoPane as Text2VideoPanel
    except ImportError:
        print("❌ Error: No Text2Video panel available")
        Text2VideoPanel = None

# Video Ads V5 - NEW VERSION
try:
    from ui.video_ban_hang_v5_complete import VideoBanHangV5 as VideoAdsPanel
    print("✓ Loaded Video Ads V5")
except ImportError as e:
    print(f"⚠️ Video Ads V5 not found, falling back to original: {e}")
    try:
        from ui.video_ban_hang_panel import VideoBanHangPanel as VideoAdsPanel
    except ImportError:
        print("❌ Error: No Video Ads panel available")
        VideoAdsPanel = None

# Clone Video - NEW FEATURE
try:
    from ui.clone_video_panel import CloneVideoPanel
    print("✓ Loaded Clone Video Panel")
except ImportError as e:
    print(f"⚠️ Clone Video not found: {e}")
    CloneVideoPanel = None

# Utils
try:
    from utils import config as cfg
    from utils.version import get_version
except ImportError as e:
    print(f"⚠️ Utils import warning: {e}")
    cfg = None
    get_version = lambda: "7.0.0"

# Theme
try:
    from ui.styles.light_theme_v2 import apply_light_theme_v2 as apply_theme
except ImportError:
    try:
        from ui.styles.light_theme import apply_light_theme as apply_theme
    except ImportError:
        print("⚠️ Warning: No theme found, using default")
        apply_theme = lambda app: None

# Main tab styling
MAIN_TAB_STYLE = """
QTabWidget::pane {
    border: none;
    background: #FAFAFA;
}

QTabBar::tab {
    background: #E0E0E0;
    color: #616161;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 12px 24px;
    margin-right: 4px;
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 700;
    font-size: 15px;
    min-width: 120px;
}

QTabBar::tab:hover {
    background: #BDBDBD;
}

QTabBar::tab:selected {
    background: #1E88E5;
    color: white;
    font-weight: 700;
    font-size: 16px;
}

/* Different colors for each tab when selected */
QTabBar::tab:nth-child(1):selected { background: #5C6BC0; }  /* Settings - Purple */
QTabBar::tab:nth-child(2):selected { background: #1E88E5; }  /* Image2Video - Blue */
QTabBar::tab:nth-child(3):selected { background: #26A69A; }  /* Text2Video - Teal */
QTabBar::tab:nth-child(4):selected { background: #FF7043; }  /* Video Ads - Orange */
QTabBar::tab:nth-child(5):selected { background: #7C4DFF; }  /* Clone Video - Deep Purple */
"""


class PlaceholderPanel(QWidget):
    """Placeholder panel when a module is not available"""
    
    def __init__(self, panel_name, error_msg="", parent=None):
        super().__init__(parent)
        from PyQt5.QtWidgets import QVBoxLayout, QLabel
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Segoe UI", 48))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        title_label = QLabel(f"{panel_name} Not Available")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FF5722;")
        layout.addWidget(title_label)
        
        if error_msg:
            error_label = QLabel(f"Error: {error_msg}")
            error_label.setFont(QFont("Segoe UI", 12))
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: #666;")
            layout.addWidget(error_label)
        
        help_label = QLabel(
            "Please ensure all required files are in place:\n"
            "- ui/image2video_panel_v7_complete.py\n"
            "- ui/text2video_panel_v5_complete.py\n"
            "- ui/video_ban_hang_v5_complete.py"
        )
        help_label.setFont(QFont("Courier New", 10))
        help_label.setAlignment(Qt.AlignCenter)
        help_label.setStyleSheet("color: #888; margin-top: 20px;")
        layout.addWidget(help_label)


class MainWindow(QTabWidget):
    """Main application window with all panels"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowTitle(f"Video Super Ultra v{get_version()}")
        self.setMinimumSize(1280, 720)
        self.resize(1440, 860)
        
        # Apply main tab styling
        self.setStyleSheet(MAIN_TAB_STYLE)
        
        # Initialize tabs
        self._init_tabs()
        
        # Load state
        self._load_state()
        
        # Print initialization info
        self._print_init_info()
    
    def _init_tabs(self):
        """Initialize all tabs"""
        try:
            # Tab 1: Settings
            if SettingsPanel:
                self.settings = SettingsPanel(self)
            else:
                self.settings = PlaceholderPanel("Settings Panel")
            self.addTab(self.settings, "⚙️ Cài đặt")
            
            # Tab 2: Image2Video V7
            if Image2VideoPanel:
                try:
                    self.image2video = Image2VideoPanel(self)
                except Exception as e:
                    print(f"❌ Error creating Image2Video panel: {e}")
                    self.image2video = PlaceholderPanel("Image2Video V7", str(e))
            else:
                self.image2video = PlaceholderPanel("Image2Video V7")
            self.addTab(self.image2video, "🖼️ Image2Video")
            
            # Tab 3: Text2Video V5
            if Text2VideoPanel:
                try:
                    self.text2video = Text2VideoPanel(self)
                except Exception as e:
                    print(f"❌ Error creating Text2Video panel: {e}")
                    self.text2video = PlaceholderPanel("Text2Video V5", str(e))
            else:
                self.text2video = PlaceholderPanel("Text2Video V5")
            self.addTab(self.text2video, "📝 Text2Video")
            
            # Tab 4: Video Ads V5
            if VideoAdsPanel:
                try:
                    self.video_ads = VideoAdsPanel(self)
                except Exception as e:
                    print(f"❌ Error creating Video Ads panel: {e}")
                    self.video_ads = PlaceholderPanel("Video Ads V5", str(e))
            else:
                self.video_ads = PlaceholderPanel("Video Ads V5")
            self.addTab(self.video_ads, "🛒 Video bán hàng")
            
            # Tab 5: Clone Video
            if CloneVideoPanel:
                try:
                    self.clone_video = CloneVideoPanel(self)
                except Exception as e:
                    print(f"❌ Error creating Clone Video panel: {e}")
                    self.clone_video = PlaceholderPanel("Clone Video", str(e))
            else:
                self.clone_video = PlaceholderPanel("Clone Video")
            self.addTab(self.clone_video, "🎬 Clone Video")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize application:\n\n{e}\n\n"
                "Please check console for details."
            )
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _print_init_info(self):
        """Print initialization information"""
        print("\n" + "=" * 70)
        print("📊 PANEL STATUS")
        print("=" * 70)
        
        panels = [
            ("⚙️  Settings", self.settings),
            ("🖼️  Image2Video", self.image2video),
            ("📝 Text2Video", self.text2video),
            ("🛒 Video Ads", self.video_ads),
            ("🎬 Clone Video", self.clone_video)
        ]
        
        for name, panel in panels:
            panel_type = type(panel).__name__
            status = "✓" if not isinstance(panel, PlaceholderPanel) else "✗"
            print(f"{status} {name:15} {panel_type}")
        
        print("=" * 70)
        print(f"📅 Version: {get_version()}")
        print(f"👤 User: chamnv-dev")
        print(f"📆 Date: 2025-01-05")
        print("=" * 70 + "\n")
    
    def _load_state(self):
        """Load saved application state"""
        try:
            if cfg:
                state = cfg.load()
                last_tab = state.get('last_active_tab', 0)
                
                # Validate tab index
                if 0 <= last_tab < self.count():
                    self.setCurrentIndex(last_tab)
                    print(f"✓ Restored last tab: {last_tab}")
                else:
                    print(f"⚠️ Invalid tab index: {last_tab}, using default")
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")
    
    def closeEvent(self, event):
        """Save state when closing"""
        try:
            if cfg:
                state = cfg.load()
                state['last_active_tab'] = self.currentIndex()
                cfg.save(state)
                print(f"✓ Saved state: tab {self.currentIndex()}")
        except Exception as e:
            print(f"⚠️ Could not save state: {e}")
        
        event.accept()


def setup_application():
    """Setup QApplication with proper settings"""
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Video Super Ultra")
    app.setApplicationDisplayName("Video Super Ultra V7")
    app.setOrganizationName("chamnv-dev")
    app.setOrganizationDomain("github.com/chamnv-dev")
    
    # Set default font
    app.setFont(QFont("Segoe UI", 10))
    
    # Set application icon (if available)
    try:
        icon_path = os.path.join(
            os.path.dirname(__file__),
            "resources", "icon.png"
        )
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except:
        pass
    
    return app


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("🚀 VIDEO SUPER ULTRA V7 - STARTING")
    print("=" * 70)
    print(f"📅 Version: {get_version()}")
    print(f"👤 User: chamnv-dev")
    print(f"📆 Date: 2025-01-05 02:37:13 UTC")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📂 Working Directory: {os.getcwd()}")
    print("=" * 70 + "\n")
    
    # Setup application
    app = setup_application()
    
    # Apply theme
    try:
        apply_theme(app)
        print("✓ Applied theme\n")
    except Exception as e:
        print(f"⚠️ Could not apply theme: {e}\n")
    
    # Create and show main window
    try:
        window = MainWindow()
        window.show()
        
        print("=" * 70)
        print("✅ APPLICATION STARTED SUCCESSFULLY!")
        print("=" * 70 + "\n")
        
        # Start event loop
        exit_code = app.exec_()
        
        print("\n" + "=" * 70)
        print("👋 APPLICATION CLOSED")
        print("=" * 70 + "\n")
        
        sys.exit(exit_code)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ CRITICAL ERROR")
        print("=" * 70)
        print(f"Error: {e}\n")
        
        import traceback
        traceback.print_exc()
        
        QMessageBox.critical(
            None,
            "Critical Error",
            f"Application failed to start:\n\n{e}\n\n"
            "Please check console for details."
        )
        
        sys.exit(1)


if __name__ == "__main__":
    main()