from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QTabWidget, QTextBrowser, QLineEdit, QShortcut)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal
from data_manager import LawDataManager
from ui_widgets import ArticleWidget, ReferenceWidget
from ui_settings import MainSettingsDialog

class DetachedWindow(QMainWindow):
    closed_signal = pyqtSignal(str, QWidget) 
    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 800)
        self.content_widget = content_widget
        self.setCentralWidget(self.content_widget)

    def closeEvent(self, event):
        self.closed_signal.emit(self.windowTitle(), self.content_widget)
        event.accept()

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.left_widgets = [] 
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.detached_windows = []
        
        # 검색 관련 변수
        self.search_matches = [] # 검색된 위젯의 인덱스들
        self.current_match_idx = -1
        
        self.setup_ui()
        self.setup_shortcuts() # 단축키 설정

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

        # [검색창 UI 구성]
        self.search_container = QWidget()
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(0,0,0,0)
        
        search_layout.addWidget(QLabel("검색:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색어 입력 (Ctrl+F)")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.run_search) # 글자 칠 때마다 검색
        self.search_input.returnPressed.connect(self.next_search) # 엔터 치면 다음
        search_layout.addWidget(self.search_input)

        # 결과 개수 라벨 (예: 1/5)
        self.lbl_search_count = QLabel("0/0")
        self.lbl_search_count.setFixedWidth(60)
        self.lbl_search_count.setAlignment(Qt.AlignCenter)
        search_layout.addWidget(self.lbl_search_count)

        # 위/아래 버튼
        btn_prev = QPushButton("▲")
        btn_prev.setFixedWidth(30)
        btn_prev.clicked.connect(self.prev_search)
        search_layout.addWidget(btn_prev)

        btn_next = QPushButton("▼")
        btn_next.setFixedWidth(30)
        btn_next.clicked.connect(self.next_search)
        search_layout.addWidget(btn_next)
        
        top.addWidget(self.search_container)
        
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top.addWidget(QLabel("  법률 선택:"))
        top.addWidget(self.combo, 1)
        
        layout.addLayout(top)

        # --- 스플리터 ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #CCCCCC; }")

        # [왼쪽]
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

        # [오른쪽]
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
        # Ctrl+F 단축키 연결
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self.focus_search)

        # 검색창에서 위/아래 화살표 키 이벤트 처리는 keyPressEvent 오버라이딩 대신
        # QLineEdit에 이벤트 필터를 설치하는게 좋지만, 간단하게 버튼 클릭으로 유도
        # (아래 검색창 이벤트 처리 함수에서 키 입력 처리)

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    # --- [검색 로직 구현] ---
    def run_search(self):
        query = self.search_input.text().strip()
        self.search_matches = []
        self.current_match_idx = -1
        
        if not query:
            self.lbl_search_count.setText("0/0")
            return

        # 모든 조항을 순회하며 검색
        for i, widget in enumerate(self.left_widgets):
            # 제목이나 본문에 검색어가 포함되어 있는지 확인
            if query in widget.title_text or query in widget.plain_content:
                self.search_matches.append(i)

        if self.search_matches:
            self.current_match_idx = 0
            self.update_search_ui()
            self.move_to_match(self.current_match_idx)
        else:
            self.lbl_search_count.setText("0/0")

    def next_search(self):
        if not self.search_matches: return
        self.current_match_idx += 1
        if self.current_match_idx >= len(self.search_matches):
            self.current_match_idx = 0 # 루프
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def prev_search(self):
        if not self.search_matches: return
        self.current_match_idx -= 1
        if self.current_match_idx < 0:
            self.current_match_idx = len(self.search_matches) - 1 # 루프
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def update_search_ui(self):
        total = len(self.search_matches)
        curr = self.current_match_idx + 1
        self.lbl_search_count.setText(f"{curr}/{total}")

    def move_to_match(self, idx):
        widget_idx = self.search_matches[idx]
        target_widget = self.left_widgets[widget_idx]
        
        # 스크롤 이동
        self.left_scroll.verticalScrollBar().setValue(target_widget.y())
        
        # (선택 사항) 해당 위젯을 잠시 강조할 수도 있음
        # 여기서는 스크롤 이동만 수행

    # 검색창에서 키 입력 가로채기 (위/아래 방향키)
    def keyPressEvent(self, event):
        # 포커스가 검색창에 있을 때만 작동
        if self.search_input.hasFocus():
            if event.key() == Qt.Key_Down:
                self.next_search()
                return
            elif event.key() == Qt.Key_Up:
                self.prev_search()
                return
        super().keyPressEvent(event)

    # --- (이하 기존 로직 유지) ---
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
            self.left_layout.itemAt(i).widget().deleteLater()
        self.left_widgets = []
        self.clear_right_pane()
        # 검색 초기화
        self.search_input.clear()
        self.lbl_search_count.setText("0/0")

        law_name = self.combo.currentText()
        if not law_name: return

        data = self.manager.get_parsed_data(law_name)
        for item in data:
            w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
            w.link_clicked.connect(self.open_new_tab)
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
            self.right_layout.itemAt(i).widget().deleteLater()

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

    def open_new_tab(self, law_name):
        law_name = law_name.replace("「", "").replace("」", "") 
        new_tab = QWidget()
        layout = QVBoxLayout(new_tab)
        browser = QTextBrowser()
        browser.setFont(self.font())
        browser.setText(f"<h1>{law_name}</h1><p>내용 준비중입니다.</p>")
        layout.addWidget(browser)
        idx = self.tabs.addTab(new_tab, law_name)
        self.tabs.setCurrentIndex(idx)

    def close_tab(self, index):
        if index > 0: self.tabs.removeTab(index)