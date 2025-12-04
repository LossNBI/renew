import os
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QProgressDialog, QApplication)
from PyQt5.QtGui import QFont 
from PyQt5.QtCore import Qt

from ui_windows import DetachedWindow
from ui_search_bar import LawSearchBar
from data_manager import LawDataManager
from ui_widgets import ArticleWidget, ReferenceWidget, SectionSeparator

class LawViewerWidget(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.left_widgets = [] 
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        
        # 검색 관련
        self.left_matches = [] 
        self.left_match_idx = -1
        self.right_matches = []
        self.right_match_idx = -1
        
        # 동기화 관련
        self.sync_lock = False
        self.last_sync_time = 0
        self.detached_windows = []

        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- 상단 바 ---
        top = QHBoxLayout()
        # (설정 버튼은 메인 윈도우에 있으므로 여기선 제외하거나 필요시 추가)
        
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top.addWidget(QLabel("법률 선택:"))
        top.addWidget(self.combo, 1)
        layout.addLayout(top)

        # --- 스플리터 ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3) 
        splitter.setStyleSheet("QSplitter::handle { background-color: #BDC3C7; }")

        # ================= [왼쪽 패널] =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.search_bar_left = LawSearchBar()
        self.search_bar_left.search_requested.connect(self.run_left_search)
        self.search_bar_left.next_clicked.connect(self.next_left_search)
        self.search_bar_left.prev_clicked.connect(self.prev_left_search)
        left_layout.addWidget(self.search_bar_left)

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

        # ================= [오른쪽 패널] =================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.search_bar_right = LawSearchBar()
        self.search_bar_right.search_requested.connect(self.run_right_search)
        self.search_bar_right.next_clicked.connect(self.next_right_search)
        self.search_bar_right.prev_clicked.connect(self.prev_right_search)
        right_layout.addWidget(self.search_bar_right)

        lbl_ref = QLabel("관련 규정 및 참조 (전체)")
        lbl_ref.setStyleSheet("background: #505050; color: white; padding: 10px; font-weight: bold;")
        right_layout.addWidget(lbl_ref)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_content = QWidget()
        self.right_layout = QVBoxLayout(self.right_content)
        self.right_layout.setAlignment(Qt.AlignTop)
        self.right_scroll.setStyleSheet("background-color: #F9F9F9;") 
        self.right_scroll.setWidget(self.right_content)
        self.right_scroll.verticalScrollBar().valueChanged.connect(self.on_right_scroll)
        right_layout.addWidget(self.right_scroll)
        
        splitter.addWidget(right_widget)

        splitter.setSizes([700, 700])
        layout.addWidget(splitter)
        
        self.refresh_combo()

    def setup_shortcuts(self):
        # 단축키는 메인 윈도우 레벨에서 처리하거나 여기서 포커스 정책 설정
        pass 

    # ---------------- 로직 함수들 ----------------

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
        law_name = self.combo.currentText()
        if not law_name: return

        self._clear_layout(self.left_layout)
        self._clear_layout(self.right_layout)
        self.left_widgets = []
        
        self.search_bar_left.clear_input()
        self.search_bar_left.set_count_text("0/0")
        self.search_bar_right.clear_input()
        self.search_bar_right.set_count_text("0/0")

        data = self.manager.get_parsed_data(law_name)
        if not data: return

        law_code = self.manager.config["DATABASES"].get(law_name)
        img_folder_name = self.manager.config["IMAGE_FOLDERS"].get(law_code)
        img_base_path = os.path.join(self.manager.data_dir, img_folder_name) if img_folder_name else None

        total_steps = len(data) * 2 
        progress = QProgressDialog("법률 데이터를 불러오는 중입니다...", "취소", 0, total_steps, self)
        progress.setWindowTitle("로딩 중")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0) 
        progress.setValue(0)

        for i, item in enumerate(data):
            if progress.wasCanceled(): break
            w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size, image_base_path=img_base_path)
            w.link_clicked.connect(self.open_new_window)
            self.left_layout.addWidget(w)
            self.left_widgets.append(w)
            progress.setValue(i)

        current_step = len(data)
        has_any_ref = False

        for item in data:
            if progress.wasCanceled(): break
            article_key = item['article_key']
            related = self.manager.get_related_articles(article_key)
            if related:
                has_any_ref = True
                sep = SectionSeparator(f"■ {item['title']} 관련 규정", article_key)
                self.right_layout.addWidget(sep)
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
        
        progress.setValue(total_steps)
        self.left_scroll.verticalScrollBar().setValue(0)
        self.right_scroll.verticalScrollBar().setValue(0)
        if data: self.sticky.setText(data[0]['chapter'])

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    # --- [검색] 왼쪽 ---
    def run_left_search(self, query=None):
        if query is None: query = self.search_bar_left.get_text()
        self.left_matches = []
        self.left_match_idx = -1
        for w in self.left_widgets: w.set_highlight(query)
        
        if not query:
            self.search_bar_left.set_count_text("0/0")
            return
        
        for i, widget in enumerate(self.left_widgets):
            if query in widget.title_text or query in widget.plain_content:
                self.left_matches.append(i)
        
        if self.left_matches:
            self.left_match_idx = 0
            self.update_left_search_ui()
            self.move_to_left_match(self.left_match_idx)
        else:
            self.search_bar_left.set_count_text("0/0")

    def next_left_search(self):
        if not self.left_matches: return
        self.left_match_idx = (self.left_match_idx + 1) % len(self.left_matches)
        self.move_to_left_match(self.left_match_idx)
        self.update_left_search_ui()

    def prev_left_search(self):
        if not self.left_matches: return
        self.left_match_idx = (self.left_match_idx - 1) % len(self.left_matches)
        self.move_to_left_match(self.left_match_idx)
        self.update_left_search_ui()

    def update_left_search_ui(self):
        self.search_bar_left.set_count_text(f"{self.left_match_idx + 1}/{len(self.left_matches)}")

    def move_to_left_match(self, idx):
        widget_idx = self.left_matches[idx]
        target = self.left_widgets[widget_idx]
        self.left_scroll.verticalScrollBar().setValue(target.y())

    # --- [검색] 오른쪽 ---
    def run_right_search(self, query=None):
        if query is None: query = self.search_bar_right.get_text()
        self.right_matches = []
        self.right_match_idx = -1

        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ReferenceWidget):
                widget.set_highlight(query)
                if query and (query in widget.plain_title or query in widget.plain_content):
                    self.right_matches.append(widget)
        
        if not query:
            self.search_bar_right.set_count_text("0/0")
            return

        if self.right_matches:
            self.right_match_idx = 0
            self.update_right_search_ui()
            self.move_to_right_match(self.right_match_idx)
        else:
            self.search_bar_right.set_count_text("0/0")

    def next_right_search(self):
        if not self.right_matches: return
        self.right_match_idx = (self.right_match_idx + 1) % len(self.right_matches)
        self.move_to_right_match(self.right_match_idx)
        self.update_right_search_ui()

    def prev_right_search(self):
        if not self.right_matches: return
        self.right_match_idx = (self.right_match_idx - 1) % len(self.right_matches)
        self.move_to_right_match(self.right_match_idx)
        self.update_right_search_ui()

    def update_right_search_ui(self):
        self.search_bar_right.set_count_text(f"{self.right_match_idx + 1}/{len(self.right_matches)}")

    def move_to_right_match(self, idx):
        target = self.right_matches[idx]
        self.sync_lock = True
        self.right_scroll.verticalScrollBar().setValue(target.y())
        self.sync_lock = False

    # --- [스크롤 동기화] ---
    def on_left_scroll(self):
        sy = self.left_scroll.verticalScrollBar().value()
        curr_left_key = None
        for w in self.left_widgets:
            if w.y() + w.height() > sy:
                if self.sticky.text() != w.chapter: self.sticky.setText(w.chapter)
                curr_left_key = w.article_key
                break
        
        if self.sync_lock: return
        if not curr_left_key: return

        target_y = -1
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, SectionSeparator) and widget.article_key == curr_left_key:
                target_y = widget.y()
                break
        
        if target_y != -1:
            self.sync_lock = True 
            self.right_scroll.verticalScrollBar().setValue(target_y)
            self.sync_lock = False

    def on_right_scroll(self):
        if self.sync_lock: return
        if time.time() - self.last_sync_time < 10: return

        sy = self.right_scroll.verticalScrollBar().value()
        active_key = None
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if not widget: continue
            if isinstance(widget, SectionSeparator): active_key = widget.article_key
            if widget.y() + widget.height() > sy + 10: break
        
        if not active_key: return

        target_y = -1
        for w in self.left_widgets:
            if w.article_key == active_key:
                target_y = w.y()
                break
        
        if target_y != -1:
            if abs(self.left_scroll.verticalScrollBar().value() - target_y) > 20:
                self.sync_lock = True
                self.left_scroll.verticalScrollBar().setValue(target_y)
                self.sync_lock = False
                self.last_sync_time = time.time()

    # --- [폰트/호버/새창] ---
    def update_custom_font(self, family, size):
        self.curr_font = family
        self.curr_size = size
        for w in self.left_widgets: w.set_custom_font(family, size)
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ReferenceWidget):
                item.widget().setFont(QFont(family, size)) 
        self.load_law() # 레이아웃 재계산을 위해 리로드

    def on_ref_hover_enter(self, target_text):
        for w in self.left_widgets: w.set_highlight(w.current_search_query, hover_target=target_text)
    
    def on_ref_hover_leave(self):
        for w in self.left_widgets: w.set_highlight(w.current_search_query, hover_target="")

    def open_new_window(self, link_text):
        law_name = link_text.replace("「", "").replace("」", "")
        # 여기서 LawViewerWidget을 재귀적으로 사용할 수도 있지만, 
        # 간단하게 하려면 기존처럼 QScrollArea만 띄워도 됩니다.
        # 기능의 일관성을 위해 LawViewerWidget을 새 창에 띄우는 것이 베스트입니다.
        
        # 단순 뷰어 모드 (좌측 내용만 있는 형태)로 구현
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        lbl = QLabel(f"{law_name} (상세 보기)")
        lbl.setFont(QFont(self.curr_font, 14, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_content = QWidget()
        w_layout = QVBoxLayout(w_content)
        w_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(w_content)
        layout.addWidget(scroll)

        data = self.manager.get_parsed_data(law_name)
        if data:
            for item in data:
                w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
                w.link_clicked.connect(self.open_new_window)
                w_layout.addWidget(w)
        else:
            w_layout.addWidget(QLabel("데이터 없음"))

        new_window = DetachedWindow(law_name, content_widget)
        new_window.resize(600, 800)
        # cleanup은 상위 윈도우에서 관리하기 어려우므로 자체 처리하거나 생략
        new_window.show()
        # 참조 유지를 위해 리스트에 추가
        self.detached_windows.append(new_window)