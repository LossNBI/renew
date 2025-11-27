import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QShortcut
from PyQt5.QtGui import QKeySequence

# 분리된 모듈들
from data_manager import LawDataManager
from ui_search_bar import LawSearchBar
from ui_viewer import LawViewerWidget  # 새로 만든 뷰어 위젯
from ui_settings import MainSettingsDialog
from ui_windows import DetachedWindow

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.detached_windows = []
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro")
        self.resize(1200, 800)

        # 1. 상단 툴바 (설정 + 검색바)
        toolbar = QWidget()
        top_layout = QHBoxLayout(toolbar)
        top_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_set = QPushButton(" ⚙ 설정")
        self.btn_set.clicked.connect(self.open_settings)
        top_layout.addWidget(self.btn_set)

        self.search_bar = LawSearchBar()
        top_layout.addWidget(self.search_bar)
        
        # 2. 메인 탭 영역
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarDoubleClicked.connect(self.detach_tab)

        # 3. 메인 뷰어 생성 및 검색바 연결
        self.main_viewer = LawViewerWidget(self.manager, self.search_bar)
        self.tabs.addTab(self.main_viewer, "메인 뷰어")
        
        # 검색바 시그널 -> 뷰어 슬롯 연결
        self.search_bar.search_requested.connect(self.main_viewer.run_search)
        self.search_bar.next_clicked.connect(self.main_viewer.next_search)
        self.search_bar.prev_clicked.connect(self.main_viewer.prev_search)

        # 레이아웃 조립
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(toolbar)
        layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

    

    def setup_shortcuts(self):
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self.search_bar.set_focus_input)

    def open_settings(self):
        MainSettingsDialog(self.manager, self).exec_()

    def update_font(self, family, size):
        # 현재 탭이 뷰어라면 폰트 적용
        curr = self.tabs.currentWidget()
        if isinstance(curr, LawViewerWidget):
            curr.set_font_style(family, size)

    def refresh_combo(self):
        self.main_viewer.refresh_combo()

    # --- 탭/창 관리 ---
    def detach_tab(self, index):
        if index < 0: return
        widget = self.tabs.widget(index)
        # 메인 뷰어는 떼어내지 않음 (선택사항)
        if widget == self.main_viewer: return 
        
        title = self.tabs.tabText(index)
        self.tabs.removeTab(index)
        
        new_win = DetachedWindow(title, widget, self)
        new_win.closed_signal.connect(self.reattach_tab)
        new_win.show()
        self.detached_windows.append(new_win)

    def reattach_tab(self, title, widget):
        self.tabs.addTab(widget, title)
        self.tabs.setCurrentWidget(widget)
        self.detached_windows = [w for w in self.detached_windows if w.isVisible()]

    def close_tab(self, index):
        if self.tabs.widget(index) != self.main_viewer:
            self.tabs.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LawViewerWindow()
    ex.show()
    sys.exit(app.exec_())