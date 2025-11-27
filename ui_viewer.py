from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                             QLabel, QSplitter, QComboBox)
from PyQt5.QtCore import Qt
from ui_widgets import ArticleWidget, ReferenceWidget
from ui_windows import DetachedWindow

class LawViewerWidget(QWidget):
    def __init__(self, manager, search_bar=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.search_bar = search_bar # 메인에서 넘겨받은 검색바
        self.left_widgets = []
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        
        # 검색 상태
        self.search_matches = []
        self.current_match_idx = -1

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 상단 (법률 선택 콤보박스만 여기 남김, 검색바는 메인 윈도우에 있음)
        top_layout = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top_layout.addWidget(QLabel("법률 선택:"))
        top_layout.addWidget(self.combo, 1)
        layout.addLayout(top_layout)

        # 스플리터
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #CCCCCC; }")

        # 왼쪽 (본문)
        left_cont = QWidget()
        left_vbox = QVBoxLayout(left_cont)
        self.sticky = QLabel("법률을 선택하세요")
        self.sticky.setStyleSheet("background: #4A90E2; color: white; padding: 10px; font-weight: bold;")
        left_vbox.addWidget(self.sticky)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_inner = QWidget()
        self.left_layout = QVBoxLayout(self.left_inner)
        self.left_layout.setAlignment(Qt.AlignTop)
        self.left_scroll.setWidget(self.left_inner)
        self.left_scroll.verticalScrollBar().valueChanged.connect(self.on_left_scroll)
        left_vbox.addWidget(self.left_scroll)
        splitter.addWidget(left_cont)

        # 오른쪽 (참조)
        right_cont = QWidget()
        right_vbox = QVBoxLayout(right_cont)
        lbl_ref = QLabel("관련 규정 및 참조")
        lbl_ref.setStyleSheet("background: #505050; color: white; padding: 10px; font-weight: bold;")
        right_vbox.addWidget(lbl_ref)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_inner = QWidget()
        self.right_layout = QVBoxLayout(self.right_inner)
        self.right_layout.setAlignment(Qt.AlignTop)
        self.right_scroll.setWidget(self.right_inner)
        right_vbox.addWidget(self.right_scroll)
        splitter.addWidget(right_cont)

        splitter.setSizes([700, 500])
        layout.addWidget(splitter)
        
        self.refresh_combo()

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
        # 초기화
        for i in reversed(range(self.left_layout.count())):
            w = self.left_layout.itemAt(i).widget()
            if w: w.deleteLater()
        self.left_widgets = []
        self.clear_right_pane()
        
        if self.search_bar:
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
            w = self.right_layout.itemAt(i).widget()
            if w: w.deleteLater()

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
        # 링크 클릭 시 새 창 (메인 윈도우의 메서드가 아니므로 독립적으로 처리)
        from PyQt5.QtWidgets import QTextBrowser
        law_name = law_name.replace("「", "").replace("」", "")
        
        content = QWidget()
        lay = QVBoxLayout(content)
        browser = QTextBrowser()
        browser.setText(f"<h1>{law_name}</h1><p>내용 준비중...</p>")
        lay.addWidget(browser)
        
        # 부모가 없으면 가비지 컬렉션 될 수 있으므로 전역 리스트나 메인에 위임해야 함
        # 여기서는 편의상 자신(Widget)을 부모로 하여 띄움
        self.popup = DetachedWindow(law_name, content, self) 
        self.popup.show()

    # --- 폰트 변경 ---
    def set_font_style(self, family, size):
        self.curr_font = family
        self.curr_size = size
        for w in self.left_widgets:
            w.set_custom_font(family, size)
        if hasattr(self, 'last_art_key') and self.last_art_key:
            self.update_right_pane(self.last_art_key)

    # --- 검색 로직 ---
    def run_search(self, query=None):
        if query is None: 
            query = self.search_bar.get_text()
        
        self.search_matches = []
        self.current_match_idx = -1
        
        # 1. 모든 위젯에 검색어 하이라이트 전파
        for w in self.left_widgets:
            w.set_highlight(query) # 검색어 전달

        if not query:
            self.search_bar.set_count_text("0/0")
            return

        # 2. 매칭된 위치 찾기
        for i, widget in enumerate(self.left_widgets):
            # 렌더링된 plain_text 기준으로 검색
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
        self.current_match_idx = (self.current_match_idx + 1) % len(self.search_matches)
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def prev_search(self):
        if not self.search_matches: return
        self.current_match_idx = (self.current_match_idx - 1) % len(self.search_matches)
        self.move_to_match(self.current_match_idx)
        self.update_search_ui()

    def update_search_ui(self):
        if self.search_bar:
            self.search_bar.set_count_text(f"{self.current_match_idx + 1}/{len(self.search_matches)}")

    def update_right_pane(self, article_key):
        self.clear_right_pane()
        related = self.manager.get_related_articles(article_key)
        if not related:
            # ... (없음 표시 로직 동일)
            return
        
        order_map = {'I. 시행령': 1, 'II. 시행규칙': 2, 'III. 관련 조항': 3, 'IV. 타법 참조': 4}
        related.sort(key=lambda x: order_map.get(x['type'], 99))
        
        for item in related:
            r_data = item['data']
            w = ReferenceWidget(item['type'], r_data['title'], r_data['content'], self.curr_font, self.curr_size)
            
            # [추가] 호버 시그널 연결
            w.hover_entered.connect(self.on_ref_hover_enter)
            w.hover_left.connect(self.on_ref_hover_leave)
            
            self.right_layout.addWidget(w)

    # [추가] 호버 진입 시 처리
    def on_ref_hover_enter(self, target_text):
        # 왼쪽 패널의 모든 위젯에게 "이 텍스트 하이라이트 해!" 라고 명령
        # target_text는 공백 없는 "제5조" 형태이므로, 
        # ArticleWidget에서 이를 처리할 때 공백 유무를 고려해야 할 수도 있지만
        # 일단 정확한 매칭을 시도합니다.
        
        # 팁: 정확성을 위해 target_text를 좀 더 유연하게 매칭하고 싶다면
        # ArticleWidget의 render_content를 정교하게 다듬어야 합니다.
        for w in self.left_widgets:
            # 검색어는 유지하고(None이 아니므로), 호버 타겟만 업데이트
            w.set_highlight(w.current_search_query, hover_target=target_text)

    # [추가] 호버 해제 시 처리
    def on_ref_hover_leave(self):
        for w in self.left_widgets:
            # 호버 타겟을 빈 문자열("")로 설정하여 제거
            w.set_highlight(w.current_search_query, hover_target="")

    def move_to_match(self, idx):
        target = self.left_widgets[self.search_matches[idx]]
        self.left_scroll.verticalScrollBar().setValue(target.y())