from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QTabWidget, QTextBrowser, QShortcut,
                             QProgressDialog, QApplication) # QProgressDialog, QApplication 추가
from PyQt5.QtGui import QKeySequence, QFont
from PyQt5.QtCore import Qt

from ui_windows import DetachedWindow
from ui_search_bar import LawSearchBar
from data_manager import LawDataManager
from ui_widgets import ArticleWidget, ReferenceWidget, SectionSeparator # SectionSeparator 추가
from ui_settings import MainSettingsDialog

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.left_widgets = [] 
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.detached_windows = []
        
        self.search_matches = [] 
        self.current_match_idx = -1
        
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro (Expert)")
        self.resize(1400, 900) # 창 크기 조금 키움

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
        splitter.setHandleWidth(3) # 핸들 조금 더 두껍게
        splitter.setStyleSheet("QSplitter::handle { background-color: #BDC3C7; }")

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
        lbl_ref = QLabel("관련 규정 및 참조 (전체)")
        lbl_ref.setStyleSheet("background: #505050; color: white; padding: 10px; font-weight: bold;")
        right_layout.addWidget(lbl_ref)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_content = QWidget()
        self.right_layout = QVBoxLayout(self.right_content)
        self.right_layout.setAlignment(Qt.AlignTop)
        # 우측 배경색을 약간 회색조로 주어 구분감 향상
        self.right_scroll.setStyleSheet("background-color: #F9F9F9;") 
        self.right_scroll.setWidget(self.right_content)
        right_layout.addWidget(self.right_scroll)
        splitter.addWidget(right_widget)

        splitter.setSizes([700, 700])
        layout.addWidget(splitter)
        self.refresh_combo()

    def setup_shortcuts(self):
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self.search_bar.set_focus_input)

    # --- [핵심 수정] 법률 로드 (로딩바 + 전체 로드) ---
    def load_law(self):
        law_name = self.combo.currentText()
        if not law_name: return

        # UI 초기화
        self._clear_layout(self.left_layout)
        self._clear_layout(self.right_layout)
        self.left_widgets = []
        self.search_bar.clear_input()
        self.search_bar.set_count_text("0/0")

        # 데이터 가져오기
        data = self.manager.get_parsed_data(law_name)
        if not data: return

        total_steps = len(data) * 2 # 왼쪽 생성 + 오른쪽 검사
        
        # [4. 로딩 다이얼로그 생성]
        progress = QProgressDialog("법률 데이터를 불러오는 중입니다...", "취소", 0, total_steps, self)
        progress.setWindowTitle("로딩 중")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0) # 즉시 표시
        progress.setValue(0)

        # 1. 왼쪽 패널 생성
        for i, item in enumerate(data):
            if progress.wasCanceled(): break
            
            w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
            w.link_clicked.connect(self.open_new_window)
            self.left_layout.addWidget(w)
            self.left_widgets.append(w)
            
            progress.setValue(i)

        # 2. 오른쪽 패널 전체 생성 (순서대로)
        # 왼쪽 위젯들을 순회하며 관련된게 있으면 구분선 넣고 추가
        current_step = len(data)
        has_any_ref = False

        for item in data:
            if progress.wasCanceled(): break
            
            article_key = item['article_key']
            related = self.manager.get_related_articles(article_key)
            
            if related:
                has_any_ref = True
                # [3. 확실한 구분선 추가]
                sep = SectionSeparator(f"■ {item['title']} 관련 규정")
                self.right_layout.addWidget(sep)

                # 우선순위 정렬
                order_map = {'I. 시행령': 1, 'II. 시행규칙': 2, 'III. 관련 조항': 3, 'IV. 타법 참조': 4}
                related.sort(key=lambda x: order_map.get(x['type'], 99))

                for r in related:
                    r_data = r['data']
                    w = ReferenceWidget(r['type'], r_data['title'], r_data['content'], self.curr_font, self.curr_size)
                    w.hover_entered.connect(self.on_ref_hover_enter)
                    w.hover_left.connect(self.on_ref_hover_leave)
                    self.right_layout.addWidget(w)
            
            current_step += 1
            progress.setValue(current_step)

        if not has_any_ref:
            lbl = QLabel("관련 참조 내용이 없습니다.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: gray; margin-top: 20px;")
            self.right_layout.addWidget(lbl)
        
        # 마무리
        progress.setValue(total_steps)
        
        self.left_scroll.verticalScrollBar().setValue(0)
        self.right_scroll.verticalScrollBar().setValue(0)
        if data: self.sticky.setText(data[0]['chapter'])

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    # --- [수정] 링크 클릭 시 실제 데이터 연동 ---
    def open_new_window(self, link_text):
        # 링크 텍스트: "「소득세법」" -> "소득세법"
        law_name = link_text.replace("「", "").replace("」", "")
        
        # 1. 컨텐츠 위젯 준비 (메인 윈도우와 비슷한 스크롤 구조)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # 제목 표시
        lbl_title = QLabel(f"{law_name} (참조 뷰어)")
        lbl_title.setFont(QFont(self.curr_font, 14, QFont.Bold))
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("background-color: #ecf0f1; padding: 10px;")
        layout.addWidget(lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 2. 데이터 로드 (로딩바 포함)
        # 새 창 로딩을 위한 ProgressDialog
        data = self.manager.get_parsed_data(law_name)
        
        if not data:
            # 데이터가 없거나 DB에 없는 법인 경우
            lbl_err = QLabel(f"'{law_name}' 데이터를 찾을 수 없습니다.\n(설정에서 해당 법률을 등록해주세요)")
            lbl_err.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(lbl_err)
        else:
            # 로딩바 표시 (부모는 None으로 해서 화면 중앙에)
            progress = QProgressDialog(f"{law_name} 불러오는 중...", "취소", 0, len(data), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                # 링크 안에서도 또 링크를 탈 수 있게 ArticleWidget 재사용
                w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
                w.link_clicked.connect(self.open_new_window) # 재귀적 링크 열기 지원
                scroll_layout.addWidget(w)
                progress.setValue(i+1)
                
                # UI 반응성 확보
                QApplication.processEvents()

        # 3. 새 창 띄우기
        new_window = DetachedWindow(law_name, content_widget, self)
        new_window.resize(600, 800)
        new_window.closed_signal.connect(self.cleanup_closed_window)
        new_window.show()
        self.detached_windows.append(new_window)

    # --- 스크롤 이벤트 (우측 패널 갱신 로직 제거됨) ---
    def on_left_scroll(self):
        sy = self.left_scroll.verticalScrollBar().value()
        for w in self.left_widgets:
            if w.y() + w.height() > sy:
                if self.sticky.text() != w.chapter:
                    self.sticky.setText(w.chapter)
                break
    
    # ... (run_search, next_search, prev_search 등 검색 로직은 기존 유지) ...
    def run_search(self, query=None):
        if query is None: query = self.search_bar.get_text()
        self.search_matches = []
        self.current_match_idx = -1
        for w in self.left_widgets: w.set_highlight(query)
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
        if self.current_match_idx >= len(self.search_matches): self.current_match_idx = 0
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def prev_search(self):
        if not self.search_matches: return
        self.current_match_idx -= 1
        if self.current_match_idx < 0: self.current_match_idx = len(self.search_matches) - 1
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def update_search_ui(self):
        self.search_bar.set_count_text(f"{self.current_match_idx + 1}/{len(self.search_matches)}")

    def move_to_match(self, idx):
        widget_idx = self.search_matches[idx]
        target = self.left_widgets[widget_idx]
        self.left_scroll.verticalScrollBar().setValue(target.y())

    # --- 호버 이벤트 ---
    def on_ref_hover_enter(self, target_text):
        for w in self.left_widgets:
            w.set_highlight(w.current_search_query, hover_target=target_text)

    def on_ref_hover_leave(self):
        for w in self.left_widgets:
            w.set_highlight(w.current_search_query, hover_target="")
            
    # ... (나머지 탭, 설정 관련 함수 유지) ...
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

    def update_font(self, family, size):
        self.curr_font = family
        self.curr_size = size
        for w in self.left_widgets: w.set_custom_font(family, size)
        # 우측 패널도 갱신 필요 (전체 로드된 위젯 순회)
        # QVBoxLayout에는 children() 대신 itemAt으로 접근해야 함
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ReferenceWidget):
                item.widget().setFont(QFont(family, size)) 
                # ReferenceWidget 내부에 set_custom_font가 없으므로 setFont 사용 혹은 별도 구현 필요
                # 간단하게는 다시 로드(load_law)를 호출하는게 가장 깔끔함
        self.load_law() # 폰트 변경 시 전체 리로딩 (안전함)

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

    def cleanup_closed_window(self, title, widget):
        self.detached_windows = [w for w in self.detached_windows if w.isVisible()]
        
    def close_tab(self, index):
        if index > 0: self.tabs.removeTab(index)