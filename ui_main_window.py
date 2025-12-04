from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTabWidget, QShortcut)
from PyQt5.QtGui import QKeySequence
from ui_windows import DetachedWindow
from data_manager import LawDataManager
from ui_settings import MainSettingsDialog
from ui_law_tab import LawViewerWidget # 위에서 만든 클래스 임포트

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.detached_windows = []
        
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro (Expert)")
        self.resize(1400, 900)

        # 메인 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 상단 설정 버튼 (공통)
        top_bar = QHBoxLayout()
        btn_set = QPushButton(" ⚙ 설정")
        btn_set.clicked.connect(self.open_settings)
        top_bar.addWidget(btn_set)
        top_bar.addStretch(1)
        main_layout.addLayout(top_bar)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarDoubleClicked.connect(self.detach_tab)
        main_layout.addWidget(self.tabs)

        # 첫 번째 탭 생성
        self.add_new_tab("법률 뷰어")

    def add_new_tab(self, title):
        # LawViewerWidget 인스턴스 생성
        viewer = LawViewerWidget(self.manager, self)
        self.tabs.addTab(viewer, title)

    def setup_shortcuts(self):
        # 탭 내의 위젯에 포커스 전달
        self.shortcut_left = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_left.activated.connect(self.focus_current_left_search)
        
        self.shortcut_right = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_right.activated.connect(self.focus_current_right_search)

    def focus_current_left_search(self):
        widget = self.tabs.currentWidget()
        if isinstance(widget, LawViewerWidget):
            widget.search_bar_left.set_focus_input()

    def focus_current_right_search(self):
        widget = self.tabs.currentWidget()
        if isinstance(widget, LawViewerWidget):
            widget.search_bar_right.set_focus_input()

    def open_settings(self):
        # 설정 다이얼로그 실행
        dlg = MainSettingsDialog(self.manager, self)
        dlg.exec_()

    # 설정창에서 호출하는 함수 (폰트 변경)
    def update_font(self, family, size):
        self.curr_font = family # LawViewerWindow에도 변수 저장 (설정창용)
        self.curr_size = size
        
        # 현재 열려있는 모든 탭의 폰트 업데이트
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, LawViewerWidget):
                widget.update_custom_font(family, size)

    # 설정창에서 호출하는 함수 (데이터 변경 시 콤보박스 갱신)
    def refresh_combo(self):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, LawViewerWidget):
                widget.refresh_combo()

    # --- 탭 분리/닫기 로직 ---
    def detach_tab(self, index):
        if index < 0: return
        title = self.tabs.tabText(index)
        widget = self.tabs.widget(index)
        
        # 탭이 1개뿐이면 분리 안 함 (선택사항)
        if self.tabs.count() == 1: return 

        self.tabs.removeTab(index)
        new_window = DetachedWindow(title, widget, self)
        new_window.closed_signal.connect(self.reattach_tab)
        new_window.show()
        self.detached_windows.append(new_window)

    def reattach_tab(self, title, widget):
        self.tabs.addTab(widget, title)
        self.tabs.setCurrentWidget(widget)
        # 닫힌 윈도우 정리
        self.detached_windows = [w for w in self.detached_windows if w.isVisible()]

    def close_tab(self, index):
        # 마지막 탭은 닫지 않기 (혹은 닫으면 종료)
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)