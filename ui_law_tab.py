import os
import time
import re
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
        
        self.left_matches = [] 
        self.left_match_idx = -1
        self.right_matches = []
        self.right_match_idx = -1
        self.third_matches = [] 
        self.third_match_idx = -1
        
        self.sync_lock = False
        self.last_sync_time = 0
        
        self.right_widget_map = {} 
        self.detached_windows = []
        
        # 조항 키 추출용 정규식 (제n조의m 지원)
        self.re_art_key = re.compile(r'.*?(제\s*\d+\s*조(?:\s*의\s*\d+)?)')

        self.setup_ui()

    def setup_ui(self):
        # (기존 UI 레이아웃 코드와 완전히 동일)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top.addWidget(QLabel("법률 선택:"))
        top.addWidget(self.combo, 1)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3) 
        splitter.setStyleSheet("QSplitter::handle { background-color: #BDC3C7; }")

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

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.search_bar_right = LawSearchBar()
        self.search_bar_right.search_requested.connect(self.run_right_search)
        self.search_bar_right.next_clicked.connect(self.next_right_search)
        self.search_bar_right.prev_clicked.connect(self.prev_right_search)
        right_layout.addWidget(self.search_bar_right)
        lbl_ref = QLabel("관련 규정 및 참조 (1차)")
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

        third_widget = QWidget()
        third_layout = QVBoxLayout(third_widget)
        self.search_bar_third = LawSearchBar()
        self.search_bar_third.search_requested.connect(self.run_third_search)
        self.search_bar_third.next_clicked.connect(self.next_third_search)
        self.search_bar_third.prev_clicked.connect(self.prev_third_search)
        third_layout.addWidget(self.search_bar_third)
        lbl_third = QLabel("심화 참조 (조항만 표시)")
        lbl_third.setStyleSheet("background: #2c3e50; color: white; padding: 10px; font-weight: bold;")
        third_layout.addWidget(lbl_third)
        self.third_scroll = QScrollArea()
        self.third_scroll.setWidgetResizable(True)
        self.third_content = QWidget()
        self.third_layout = QVBoxLayout(self.third_content)
        self.third_layout.setAlignment(Qt.AlignTop)
        self.third_scroll.setStyleSheet("background-color: #ECF0F1;") 
        self.third_scroll.setWidget(self.third_content)
        self.third_scroll.verticalScrollBar().valueChanged.connect(self.on_third_scroll)
        third_layout.addWidget(self.third_scroll)
        splitter.addWidget(third_widget)

        splitter.setSizes([500, 400, 400])
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
        law_name = self.combo.currentText()
        if not law_name: return

        self.setUpdatesEnabled(False)

        try:
            self._clear_layout(self.left_layout)
            self._clear_layout(self.right_layout)
            self._clear_layout(self.third_layout)
            self.left_widgets = []
            self.right_widget_map = {} 
            
            for sb in [self.search_bar_left, self.search_bar_right, self.search_bar_third]:
                sb.clear_input()
                sb.set_count_text("0/0")

            data = self.manager.get_parsed_data(law_name)
            if not data: return

            law_code = self.manager.config["DATABASES"].get(law_name)
            img_folder_name = self.manager.config["IMAGE_FOLDERS"].get(law_code)
            img_base_path = os.path.join(self.manager.data_dir, img_folder_name) if img_folder_name else None

            total_steps = len(data) * 3 
            progress = QProgressDialog("법률 데이터를 분석 중입니다...", "취소", 0, total_steps, self)
            progress.setWindowTitle("로딩 중")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0) 
            progress.setValue(0)
            current_step = 0

            # 1. 왼쪽 생성
            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size, image_base_path=img_base_path)
                w.link_clicked.connect(self.open_new_window)
                self.left_layout.addWidget(w)
                self.left_widgets.append(w)
                current_step += 1
                progress.setValue(current_step)
                if i % 10 == 0: QApplication.processEvents()

            # 2. 오른쪽 & 심화 생성
            has_any_ref_right = False
            has_any_ref_third = False

            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                article_key = item['article_key']
                related = self.manager.get_related_articles(article_key)
                
                if related:
                    has_any_ref_right = True
                    sep_right = SectionSeparator(f"■ {item['title']} 관련 규정", article_key)
                    self.right_layout.addWidget(sep_right)

                    order_map = {'I. 시행령': 1, 'II. 시행규칙': 2, 'III. 관련 조항': 3, 'IV. 타법 참조': 4}
                    related.sort(key=lambda x: order_map.get(x['type'], 99))

                    for r in related:
                        r_data = r['data']
                        h_key = r_data.get('article_key')
                        if not h_key:
                            match = self.re_art_key.match(r_data['title'])
                            if match: h_key = match.group(1).replace(" ", "")

                        w_right = ReferenceWidget(
                            r['type'], r_data['title'], r_data['content'], 
                            self.curr_font, self.curr_size, 
                            image_base_path=img_base_path,
                            highlight_key=h_key 
                        )
                        w_right.hover_entered.connect(self.on_ref_hover_enter)
                        w_right.hover_left.connect(self.on_ref_hover_leave)
                        self.right_layout.addWidget(w_right)
                        
                        if w_right.article_key:
                            self.right_widget_map[w_right.article_key] = w_right

                        # 3차 생성
                        if r['type'] in ['III. 관련 조항', 'IV. 타법 참조']:
                            deep_key = w_right.article_key
                            if deep_key:
                                deep_related = self.manager.get_related_articles(deep_key)
                                filtered_deep = [dr for dr in deep_related if dr['type'] in ['III. 관련 조항', 'IV. 타법 참조']]
                                
                                if filtered_deep:
                                    has_any_ref_third = True
                                    sep_third = SectionSeparator(f"→ {r_data['title']}의 참조", deep_key)
                                    self.third_layout.addWidget(sep_third)

                                    for dr in filtered_deep:
                                        dr_data = dr['data']
                                        dh_key = dr_data.get('article_key')
                                        if not dh_key:
                                            match = self.re_art_key.match(dr_data['title'])
                                            if match: dh_key = match.group(1).replace(" ", "")

                                        w_third = ReferenceWidget(
                                            dr['type'], dr_data['title'], dr_data['content'],
                                            self.curr_font, self.curr_size, 
                                            image_base_path=None, 
                                            parent_key=deep_key, 
                                            highlight_key=dh_key 
                                        )
                                        w_third.hover_entered.connect(self.on_third_hover_enter)
                                        w_third.hover_left.connect(self.on_third_hover_leave)
                                        self.third_layout.addWidget(w_third)

                current_step += 1
                progress.setValue(current_step)
                if i % 10 == 0: QApplication.processEvents()

            if not has_any_ref_right: self._add_placeholder(self.right_layout, "관련 참조 내용이 없습니다.")
            if not has_any_ref_third: self._add_placeholder(self.third_layout, "심화 참조(법 조항)가 없습니다.")

            self.right_layout.addStretch(1)
            self.third_layout.addStretch(1)

            progress.setValue(total_steps)
            self.left_scroll.verticalScrollBar().setValue(0)
            self.right_scroll.verticalScrollBar().setValue(0)
            self.third_scroll.verticalScrollBar().setValue(0)
            if data: self.sticky.setText(data[0]['chapter'])

        finally:
            self.setUpdatesEnabled(True)

    def _add_placeholder(self, layout, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: gray; margin-top: 20px;")
        layout.addWidget(lbl)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    # --- [호버 로직] ---

    # 2차 -> 1차 (기존과 동일)
    def on_ref_hover_enter(self, target_text):
        for w in self.left_widgets: 
            w.set_highlight(w.current_search_query, hover_target=target_text)

    def on_ref_hover_leave(self):
        for w in self.left_widgets: 
            w.set_highlight(w.current_search_query, hover_target="")

    # 3차 -> 2차 (수정됨: target_text는 '제10조' 같은 찾을 단어)
    def on_third_hover_enter(self, target_text):
        sender = self.sender()
        if not sender or not isinstance(sender, ReferenceWidget): return
        
        # 3차 창 위젯의 부모 키(예: 제5조)를 가져옴 -> 2차 창의 해당 위젯을 찾기 위함
        parent_key = sender.parent_key 
        
        # 맵에서 2차 창 위젯 검색
        target_widget = self.right_widget_map.get(parent_key)
        
        if target_widget:
            # 2차 창 위젯에게 'target_text(제10조)'를 하이라이트하라고 요청
            target_widget.set_highlight(target_widget.current_query, hover_target=target_text)

    def on_third_hover_leave(self):
        sender = self.sender()
        if not sender or not isinstance(sender, ReferenceWidget): return
        
        parent_key = sender.parent_key
        target_widget = self.right_widget_map.get(parent_key)
        
        if target_widget:
            target_widget.set_highlight(target_widget.current_query, hover_target="")

    # ... (나머지 스크롤 및 검색 함수들은 기존과 동일) ...
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
        target_right_y = -1
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, SectionSeparator) and widget.article_key == curr_left_key:
                target_right_y = widget.y()
                break
        if target_right_y != -1:
            self.sync_lock = True 
            self.right_scroll.verticalScrollBar().setValue(target_right_y)
            self.sync_lock = False

    def on_right_scroll(self):
        if self.sync_lock: return
        sy = self.right_scroll.verticalScrollBar().value()
        visible_ref_key = None
        visible_sep_key = None
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if not widget: continue
            if widget.y() + widget.height() > sy:
                if isinstance(widget, ReferenceWidget): visible_ref_key = widget.article_key
                elif isinstance(widget, SectionSeparator): visible_sep_key = widget.article_key
                break
        if visible_ref_key:
            target_third_y = -1
            for i in range(self.third_layout.count()):
                item = self.third_layout.itemAt(i)
                widget = item.widget()
                if isinstance(widget, SectionSeparator) and widget.article_key == visible_ref_key:
                    target_third_y = widget.y()
                    break
            if target_third_y != -1:
                self.third_scroll.blockSignals(True) 
                self.third_scroll.verticalScrollBar().setValue(target_third_y)
                self.third_scroll.blockSignals(False)
        if time.time() - self.last_sync_time > 10 and visible_sep_key:
            target_left_y = -1
            for w in self.left_widgets:
                if w.article_key == visible_sep_key:
                    target_left_y = w.y()
                    break
            if target_left_y != -1 and abs(self.left_scroll.verticalScrollBar().value() - target_left_y) > 20:
                self.sync_lock = True
                self.left_scroll.verticalScrollBar().setValue(target_left_y)
                self.sync_lock = False
                self.last_sync_time = time.time()

    def on_third_scroll(self):
        if self.sync_lock: return
        sy = self.third_scroll.verticalScrollBar().value()
        visible_sep_key = None
        for i in range(self.third_layout.count()):
            item = self.third_layout.itemAt(i)
            widget = item.widget()
            if not widget: continue
            if widget.y() + widget.height() > sy:
                if isinstance(widget, SectionSeparator): visible_sep_key = widget.article_key
                break
        if visible_sep_key:
            target_right_y = -1
            for i in range(self.right_layout.count()):
                item = self.right_layout.itemAt(i)
                widget = item.widget()
                if isinstance(widget, ReferenceWidget) and widget.article_key == visible_sep_key:
                    target_right_y = widget.y()
                    break
            if target_right_y != -1:
                self.sync_lock = True
                self.right_scroll.verticalScrollBar().setValue(target_right_y)
                self.sync_lock = False

    def run_left_search(self, query=None):
        if query is None: query = self.search_bar_left.get_text()
        self.left_matches = []
        self.left_match_idx = -1
        for i, widget in enumerate(self.left_widgets):
            has_text = query and (query in widget.title_text or query in widget.plain_content)
            if has_text:
                widget.set_highlight(query)
                self.left_matches.append(i)
            else: widget.set_highlight("") 
        if not query: self.search_bar_left.set_count_text("0/0"); return
        if self.left_matches:
            self.left_match_idx = 0
            self.update_left_search_ui()
            self.move_to_left_match(self.left_match_idx)
        else: self.search_bar_left.set_count_text("0/0")
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
    def update_left_search_ui(self): self.search_bar_left.set_count_text(f"{self.left_match_idx + 1}/{len(self.left_matches)}")
    def move_to_left_match(self, idx): self.left_scroll.verticalScrollBar().setValue(self.left_widgets[self.left_matches[idx]].y())

    def run_right_search(self, query=None):
        if query is None: query = self.search_bar_right.get_text()
        self.right_matches = []
        self.right_match_idx = -1
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ReferenceWidget):
                has_text = query and (query in widget.plain_title or query in widget.plain_content)
                if has_text: widget.set_highlight(query); self.right_matches.append(widget)
                else: widget.set_highlight("")
        if not query: self.search_bar_right.set_count_text("0/0"); return
        if self.right_matches:
            self.right_match_idx = 0
            self.update_right_search_ui()
            self.move_to_right_match(self.right_match_idx)
        else: self.search_bar_right.set_count_text("0/0")
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
    def update_right_search_ui(self): self.search_bar_right.set_count_text(f"{self.right_match_idx + 1}/{len(self.right_matches)}")
    def move_to_right_match(self, idx): self.right_scroll.verticalScrollBar().setValue(self.right_matches[idx].y())

    def run_third_search(self, query=None):
        if query is None: query = self.search_bar_third.get_text()
        self.third_matches = []
        self.third_match_idx = -1
        for i in range(self.third_layout.count()):
            item = self.third_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ReferenceWidget):
                has_text = query and (query in widget.plain_title or query in widget.plain_content)
                if has_text: widget.set_highlight(query); self.third_matches.append(widget)
                else: widget.set_highlight("")
        if not query: self.search_bar_third.set_count_text("0/0"); return
        if self.third_matches:
            self.third_match_idx = 0
            self.update_third_search_ui()
            self.move_to_third_match(self.third_match_idx)
        else: self.search_bar_third.set_count_text("0/0")
    def next_third_search(self):
        if not self.third_matches: return
        self.third_match_idx = (self.third_match_idx + 1) % len(self.third_matches)
        self.move_to_third_match(self.third_match_idx)
        self.update_third_search_ui()
    def prev_third_search(self):
        if not self.third_matches: return
        self.third_match_idx = (self.third_match_idx - 1) % len(self.third_matches)
        self.move_to_third_match(self.third_match_idx)
        self.update_third_search_ui()
    def update_third_search_ui(self): self.search_bar_third.set_count_text(f"{self.third_match_idx + 1}/{len(self.third_matches)}")
    def move_to_third_match(self, idx): self.third_scroll.verticalScrollBar().setValue(self.third_matches[idx].y())

    def update_custom_font(self, family, size):
        self.curr_font = family
        self.curr_size = size
        for w in self.left_widgets: w.set_custom_font(family, size)
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ReferenceWidget): item.widget().setFont(QFont(family, size))
        for i in range(self.third_layout.count()):
            item = self.third_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ReferenceWidget): item.widget().setFont(QFont(family, size)) 
        self.load_law() 

    def open_new_window(self, link_text):
        law_name = link_text.replace("「", "").replace("」", "")
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        lbl_title = QLabel(f"{law_name} (상세 보기)")
        lbl_title.setFont(QFont(self.curr_font, 14, QFont.Bold))
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_content = QWidget()
        w_layout = QVBoxLayout(w_content)
        w_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(w_content)
        layout.addWidget(scroll)
        data = self.manager.get_parsed_data(law_name)
        base_name = law_name.replace(" 시행령", "").replace(" 시행규칙", "")
        law_code = self.manager.config["DATABASES"].get(base_name)
        img_base_path = os.path.join(self.manager.data_dir, self.manager.config["IMAGE_FOLDERS"].get(law_code)) if law_code and self.manager.config["IMAGE_FOLDERS"].get(law_code) else None
        if data:
            progress = QProgressDialog(f"{law_name} 불러오는 중...", "취소", 0, len(data), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size, image_base_path=img_base_path)
                w.link_clicked.connect(self.open_new_window)
                w_layout.addWidget(w)
                progress.setValue(i+1)
                QApplication.processEvents()
        else: w_layout.addWidget(QLabel("데이터 없음"))
        new_window = DetachedWindow(law_name, content_widget)
        new_window.resize(600, 800)
        new_window.show()
        self.detached_windows.append(new_window)