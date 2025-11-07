# ui/styles/main_tab_style.py
"""
Modern Tab Bar Styling - Bold, Large, Colorful
"""

MAIN_TAB_STYLE = """
/* ============================================
   MAIN TAB BAR - Modern & Colorful
   ============================================ */

QTabWidget::pane {
    border: none;
    background: #FAFAFA;
}

QTabBar::tab {
    background: #E0E0E0;  /* Gray default */
    color: #616161;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 12px 24px;
    margin-right: 4px;
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 700;  /* BOLD */
    font-size: 15px;   /* LARGE */
    min-width: 120px;
}

QTabBar::tab:hover {
    background: #BDBDBD;
}

QTabBar::tab:selected {
    background: #1E88E5;  /* Blue selected */
    color: white;
    font-weight: 700;
    font-size: 16px;
    padding-bottom: 14px;
}

/* Different colors for each main tab */
QTabBar::tab:nth-child(1):selected {
    background: #5C6BC0;  /* Settings - Indigo */
}

QTabBar::tab:nth-child(2):selected {
    background: #1E88E5;  /* Image2Video - Blue */
}

QTabBar::tab:nth-child(3):selected {
    background: #26A69A;  /* Text2Video - Teal */
}

QTabBar::tab:nth-child(4):selected {
    background: #FF7043;  /* Video Ads - Orange */
}
"""