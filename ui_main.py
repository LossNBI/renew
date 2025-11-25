from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QTabWidget, QTextBrowser, QShortcut)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt

# --- 분리한 파일들 임포트 ---
from ui_windows import DetachedWindow
from ui_search_bar import LawSearchBar
# --------------------------

from data_manager import LawDataManager
from ui_widgets import ArticleWidget, ReferenceWidget
from ui_settings import MainSettingsDialog

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.left_widgets = [] 
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.detached_windows = []
        
        # 검색 관련 변수
        self.search_matches = [] 
        self.current_match_idx = -1
        
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro (Expert)")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarDoubleClicked.connect(self.detach_tab)
        self.setCentralWidget(self.tabs)

        self.main_tab = QWidget()
        self.create_main_viewer(self.main_tab)
        self.tabs.addTab(self.main_tab, "법률 뷰어")

    def create_main_viewer(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        
        # --- 상단 바 ---
        top = QHBoxLayout()
        
        self.btn_set = QPushButton(" ⚙ 설정")
        self.btn_set.clicked.connect(self.open_settings)
        top.addWidget(self.btn_set)

        # [수정됨] 검색바 위젯 사용
        self.search_bar = LawSearchBar()
        self.search_bar.search_requested.connect(self.run_search)
        self.search_bar.next_clicked.connect(self.next_search)
        self.search_bar.prev_clicked.connect(self.prev_search)
        top.addWidget(self.search_bar)
        
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top.addWidget(QLabel("  법률 선택:"))
        top.addWidget(self.combo, 1)
        
        layout.addLayout(top)

        # --- 스플리터 ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #CCCCCC; }")

        # [왼쪽 패널]
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.sticky = QLabel("법률을 선택하세요")
        self.sticky.setStyleSheet("background: #4A90E2; color: white; padding: 10px; font-weight: bold;")
        left_layout.addWidget(self.sticky)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_content = QWidget()
        self.left_layout = QVBoxLayout(self.left_content)
        self.left_layout.setAlignment(Qt.AlignTop)
        self.left_scroll.setWidget(self.left_content)
        self.left_scroll.verticalScrollBar().valueChanged.connect(self.on_left_scroll)
        
        left_layout.addWidget(self.left_scroll)
        splitter.addWidget(left_widget)

        # [오른쪽 패널]
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        lbl_ref = QLabel("관련 규정 및 참조")
        lbl_ref.setStyleSheet("background: #505050; color: white; padding: 10px; font-weight: bold;")
        right_layout.addWidget(lbl_ref)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_content = QWidget()
        self.right_layout = QVBoxLayout(self.right_content)
        self.right_layout.setAlignment(Qt.AlignTop)
        self.right_scroll.setWidget(self.right_content)
        
        right_layout.addWidget(self.right_scroll)
        splitter.addWidget(right_widget)

        splitter.setSizes([700, 500])
        layout.addWidget(splitter)
        self.refresh_combo()

    def setup_shortcuts(self):
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        # 검색바 위젯의 포커스 메서드 호출
        self.shortcut_search.activated.connect(self.search_bar.set_focus_input)

    # --- 검색 로직 ---
    def run_search(self, query=None):
        if query is None: 
            query = self.search_bar.get_text()
        
        self.search_matches = []
        self.current_match_idx = -1
        
        if not query:
            self.search_bar.set_count_text("0/0")
            return

        for i, widget in enumerate(self.left_widgets):
            if query in widget.title_text or query in widget.plain_content:
                self.search_matches.append(i)

        if self.search_matches:
            self.current_match_idx = 0
            self.update_search_ui()
            self.move_to_match(self.current_match_idx)
        else:
            self.search_bar.set_count_text("0/0")

    def next_search(self):
        if not self.search_matches: return
        self.current_match_idx += 1
        if self.current_match_idx >= len(self.search_matches):
            self.current_match_idx = 0 
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def prev_search(self):
        if not self.search_matches: return
        self.current_match_idx -= 1
        if self.current_match_idx < 0:
            self.current_match_idx = len(self.search_matches) - 1
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def update_search_ui(self):
        total = len(self.search_matches)
        curr = self.current_match_idx + 1
        self.search_bar.set_count_text(f"{curr}/{total}")

    def move_to_match(self, idx):
        widget_idx = self.search_matches[idx]
        target_widget = self.left_widgets[widget_idx]
        self.left_scroll.verticalScrollBar().setValue(target_widget.y())

    # --- 탭 관리 로직 ---
    def detach_tab(self, index):
        if index < 0: return 
        title = self.tabs.tabText(index)
        widget = self.tabs.widget(index)
        if widget == self.main_tab: return 
        self.tabs.removeTab(index)
        
        new_window = DetachedWindow(title, widget, self)
        new_window.closed_signal.connect(self.reattach_tab)
        new_window.show()
        self.detached_windows.append(new_window)

    def reattach_tab(self, title, widget):
        self.tabs.addTab(widget, title)
        self.tabs.setCurrentWidget(widget)
        self.detached_windows = [w for w in self.detached_windows if w.isVisible()]

    def open_settings(self):
        MainSettingsDialog(self.manager, self).exec_()

    # --- [수정] 폰트 업데이트 함수 추가 ---
    def update_font(self, family, size):
        self.curr_font = family
        self.curr_size = size
        
        # 1. 왼쪽 패널 업데이트
        for w in self.left_widgets:
            w.set_custom_font(family, size)
            
        # 2. 오른쪽 패널 업데이트 (현재 보고있는게 있다면)
        if hasattr(self, 'last_art_key') and self.last_art_key:
            self.update_right_pane(self.last_art_key)

    def refresh_combo(self):
        curr = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        for name in self.manager.config["DATABASES"]:
            self.combo.addItem(name)
        if curr: self.combo.setCurrentText(curr)
        self.combo.blockSignals(False)
        if self.combo.count() > 0 and not self.left_widgets:
            self.load_law()

    def load_law(self):
        for i in reversed(range(self.left_layout.count())):
            widget = self.left_layout.itemAt(i).widget()
            if widget: widget.deleteLater()
        self.left_widgets = []
        self.clear_right_pane()
        
        # 검색 초기화
        self.search_bar.clear_input()
        self.search_bar.set_count_text("0/0")

        law_name = self.combo.currentText()
        if not law_name: return

        data = self.manager.get_parsed_data(law_name)
        for item in data:
            w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
            w.link_clicked.connect(self.open_new_window)
            self.left_layout.addWidget(w)
            self.left_widgets.append(w)

        self.left_scroll.verticalScrollBar().setValue(0)
        if data: 
            self.sticky.setText(data[0]['chapter'])
            self.update_right_pane(data[0]['article_key'])

    def on_left_scroll(self):
        sy = self.left_scroll.verticalScrollBar().value()
        for w in self.left_widgets:
            if w.y() + w.height() > sy:
                if self.sticky.text() != w.chapter:
                    self.sticky.setText(w.chapter)
                if not hasattr(self, 'last_art_key') or self.last_art_key != w.article_key:
                    self.last_art_key = w.article_key
                    self.update_right_pane(w.article_key)
                break

    def clear_right_pane(self):
        for i in reversed(range(self.right_layout.count())):
            widget = self.right_layout.itemAt(i).widget()
            if widget: widget.deleteLater()

    def update_right_pane(self, article_key):
        self.clear_right_pane()
        related = self.manager.get_related_articles(article_key)
        if not related:
            lbl = QLabel("관련 참조 내용이 없습니다.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: gray; margin-top: 20px;")
            self.right_layout.addWidget(lbl)
            return
        
        order_map = {'I. 시행령': 1, 'II. 시행규칙': 2, 'III. 관련 조항': 3}
        related.sort(key=lambda x: order_map.get(x['type'], 99))
        
        for item in related:
            r_data = item['data']
            w = ReferenceWidget(item['type'], r_data['title'], r_data['content'], self.curr_font, self.curr_size)
            self.right_layout.addWidget(w)

    def open_new_window(self, law_name):
        law_name = law_name.replace("「", "").replace("」", "") 
        
        # 1. 보여줄 내용 위젯 생성
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        browser = QTextBrowser()
        browser.setFont(self.font())
        # 나중에 여기에도 실제 법 내용을 불러오는 로직을 넣을 수 있습니다.
        browser.setText(f"<h1>{law_name}</h1><p>내용 준비중입니다.</p>")
        layout.addWidget(browser)

        # 2. 바로 DetachedWindow(새 창) 생성
        new_window = DetachedWindow(law_name, content_widget, self)
        new_window.resize(500, 600) # 창 크기 적절히 조절
        
        # 3. 창이 닫힐 때 메모리 관리 (닫힌 창은 리스트에서 제거)
        new_window.closed_signal.connect(self.cleanup_closed_window)
        
        new_window.show()
        
        # 4. 참조 리스트에 추가 (가비지 컬렉션 방지)
        self.detached_windows.append(new_window)

    def close_tab(self, index):
        if index > 0: self.tabs.removeTab(index)

    def cleanup_closed_window(self, title, widget):
        # 현재 떠있는(isVisible) 창들만 남기고 리스트 갱신
        self.detached_windows = [w for w in self.detached_windows if w.isVisible()]    