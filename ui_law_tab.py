import os
import time
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QProgressDialog, QApplication)
from PyQt5.QtGui import QFont 
from PyQt5.QtCore import Qt, QEventLoop

from ui_windows import DetachedWindow
from ui_search_bar import LawSearchBar
from ui_widgets import ArticleWidget, ReferenceWidget, SectionSeparator

class LawViewerWidget(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
        # 데이터 관리용
        self.left_widgets = [] 
        self.right_widget_map = {}   
        self.right_sep_map = {}      
        self.third_sep_map = {}      
        
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.sync_lock = False
        self.last_sync_time = 0
        
        self.left_matches = [] 
        self.left_match_idx = -1
        self.right_matches = []
        self.right_match_idx = -1
        self.third_matches = [] 
        self.third_match_idx = -1
        
        self.detached_windows = []
        self.re_art_key = re.compile(r'.*?(제\s*\d+\s*조(?:\s*의\s*\d+)?)')

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top_bar.addWidget(QLabel("법률 선택:"))
        top_bar.addWidget(self.combo, 1)
        main_layout.addLayout(top_bar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3) 
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #BDC3C7; }")

        # 🚀 수정 포인트: _create_column이 컨테이너 자체를 반환하고, 바로 splitter에 추가합니다.
        self.left_container, self.left_scroll, self.left_layout, self.search_bar_left, self.sticky = self._create_column("#4A90E2", "법률을 선택하세요")
        self.right_container, self.right_scroll, self.right_layout, self.search_bar_right, _ = self._create_column("#505050", "관련 규정 및 참조 (1차)")
        self.third_container, self.third_scroll, self.third_layout, self.search_bar_third, _ = self._create_column("#2c3e50", "심화 참조 (조항만 표시)")

        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.right_container)
        self.splitter.addWidget(self.third_container)

        # 스크롤 이벤트 연결 (이제 객체가 삭제되지 않아 안전합니다)
        self.left_scroll.verticalScrollBar().valueChanged.connect(self.on_left_scroll)
        self.right_scroll.verticalScrollBar().valueChanged.connect(self.on_right_scroll)
        self.third_scroll.verticalScrollBar().valueChanged.connect(self.on_third_scroll)

        self._connect_search(self.search_bar_left, self.run_left_search, self.next_left_search, self.prev_left_search)
        self._connect_search(self.search_bar_right, self.run_right_search, self.next_right_search, self.prev_right_search)
        self._connect_search(self.search_bar_third, self.run_third_search, self.next_third_search, self.prev_third_search)

        self.splitter.setSizes([500, 400, 400])
        main_layout.addWidget(self.splitter)
        self.refresh_combo()

    def _create_column(self, color, title):
        # 🚀 수정 포인트: 컨테이너에 self(부모)를 명시하여 메모리 삭제 방지
        container = QWidget(self) 
        lay = QVBoxLayout(container)
        
        sb = LawSearchBar()
        lay.addWidget(sb)
        
        sticky = QLabel(title)
        sticky.setStyleSheet(f"background: {color}; color: white; padding: 10px; font-weight: bold;")
        lay.addWidget(sticky)
        
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setAlignment(Qt.AlignTop)
        sc.setWidget(content)
        lay.addWidget(sc)
        
        return container, sc, content_lay, sb, sticky

    def load_law(self):
        law_name = self.combo.currentText()
        if not law_name: return

        self.setUpdatesEnabled(False)
        self.combo.setEnabled(False)

        try:
            self._clear_layouts()
            data = self.manager.get_parsed_data(law_name)
            if not data: return

            law_code = self.manager.config["DATABASES"].get(law_name)
            img_folder = self.manager.config["IMAGE_FOLDERS"].get(law_code)
            img_base_path = os.path.join(self.manager.data_dir, img_folder) if img_folder else None

            progress = QProgressDialog("데이터를 로드 중입니다...", "취소", 0, len(data), self)
            progress.setWindowModality(Qt.WindowModal)

            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                
                curr_chapter = item['chapter']
                art_key = item['article_key']
                # 🚀 1번창 고유 ID: "제1장_제1조"
                u_id = f"{curr_chapter}_{art_key}".replace(" ", "")

                # 1. 1번창 위젯 생성
                w_left = ArticleWidget(curr_chapter, item['title'], item['content'], 
                                       self.curr_font, self.curr_size, image_base_path=img_base_path)
                w_left.unique_id = u_id 
                w_left.link_clicked.connect(self.open_new_window)
                self.left_layout.addWidget(w_left)
                self.left_widgets.append(w_left)

                # 2. 2번창 구분선 및 내용 생성
                related = self.manager.get_related_articles(art_key)
                if related:
                    sep_right = SectionSeparator(f"■ {item['title']} 관련 규정", u_id)
                    self.right_layout.addWidget(sep_right)
                    self.right_sep_map[u_id] = sep_right 

                    for r in related:
                        r_data = r['data']
                        h_key = r_data.get('article_key') or self._extract_key(r_data['title'])
                        
                        # 🚀 2번창 위젯 고유 ID: "제1장_제1조_시행령_제3조" (중복 방지용)
                        r_u_id = f"{u_id}_{r['type']}_{h_key}".replace(" ", "")
                        
                        w_right = ReferenceWidget(r['type'], r_data['title'], r_data['content'], 
                                                 self.curr_font, self.curr_size, 
                                                 image_base_path=img_base_path, highlight_key=h_key)
                        w_right.unique_id = r_u_id      # 자기 자신의 ID
                        w_right.parent_unique_id = u_id # 1번창의 누구에게 속하는지
                        
                        w_right.hover_entered.connect(self.on_ref_hover_enter)
                        w_right.hover_left.connect(self.on_ref_hover_leave)
                        self.right_layout.addWidget(w_right)
                        self.right_widget_map[r_u_id] = w_right

                        # 3. 3번창 심화 참조 생성
                        if r['type'] in ['III. 관련 조항', 'IV. 타법 참조']:
                            deep_key = w_right.article_key
                            if deep_key:
                                d_related = self.manager.get_related_articles(deep_key)
                                filtered = [dr for dr in d_related if dr['type'] in ['III. 관련 조항', 'IV. 타법 참조']]
                                if filtered:
                                    # 3번창 구분선은 2번창 위젯의 고유 ID(r_u_id)를 참조함
                                    sep_third = SectionSeparator(f"→ {r_data['title']} 참조", r_u_id)
                                    self.third_layout.addWidget(sep_third)
                                    self.third_sep_map[r_u_id] = sep_third
                                    
                                    for dr in filtered:
                                        dr_data = dr['data']
                                        dh_key = dr_data.get('article_key') or self._extract_key(dr_data['title'])
                                        w_third = ReferenceWidget(dr['type'], dr_data['title'], dr_data['content'], 
                                                                 self.curr_font, self.curr_size, 
                                                                 parent_key=r_u_id, highlight_key=dh_key)
                                        w_third.hover_entered.connect(self.on_third_hover_enter)
                                        w_third.hover_left.connect(self.on_third_hover_leave)
                                        self.third_layout.addWidget(w_third)

                if i % 20 == 0:
                    progress.setValue(i)
                    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

            self.right_layout.addStretch(1)
            self.third_layout.addStretch(1)
            progress.close()
            if self.left_widgets: self.sticky.setText(self.left_widgets[0].chapter)

        finally:
            self.setUpdatesEnabled(True)
            self.combo.setEnabled(True)

    def on_left_scroll(self):
        """1번 -> 2번 연동 (unique_id 기준)"""
        if self.sync_lock: return
        sy = self.left_scroll.verticalScrollBar().value()
        
        for w in self.left_widgets:
            if w.y() + w.height() > sy + 10:
                # 🚀 조항번호가 아닌 고유 ID로 2번창 검색
                target_id = w.unique_id 
                if target_id in self.right_sep_map:
                    self._sync_to_target(self.right_scroll, self.right_sep_map[target_id])
                break

    def on_right_scroll(self):
        """2번 -> 3번 연동 (unique_id 기준)"""
        if self.sync_lock: return
        sy = self.right_scroll.verticalScrollBar().value()
        
        for i in range(self.right_layout.count()):
            w = self.right_layout.itemAt(i).widget()
            if not w or getattr(w, 'is_placeholder', False): continue

            if w.y() + w.height() > sy + 20:
                # 🚀 현재 2번창 맨 위 위젯의 고유 ID 추출
                target_id = getattr(w, 'unique_id', None)
                if target_id in self.third_sep_map:
                    self._sync_to_target(self.third_scroll, self.third_sep_map[target_id])
                break

    def on_third_scroll(self):
        """[Step 3] 3번(심화) -> 2번(참조) 연동"""
        if self.sync_lock: return
        
        sy = self.third_scroll.verticalScrollBar().value()
        threshold = sy + 20

        target_key = None
        for i in range(self.third_layout.count()):
            w = self.third_layout.itemAt(i).widget()
            if not w or getattr(w, 'is_placeholder', False): continue

            if w.y() + w.height() > threshold:
                # 3번 창 위젯은 parent_key(2번창의 키)를 가지고 있음
                target_key = getattr(w, 'parent_key', None)
                break

        if target_key and target_key in self.right_widget_map:
            target_w = self.right_widget_map[target_key]
            # 2번 창의 해당 위젯이 이미 보이고 있다면 굳이 움직이지 않음 (무한루프 방지)
            curr_2_y = self.right_scroll.verticalScrollBar().value()
            if abs(curr_2_y - target_w.y()) > 50:
                self._sync_to_target(self.right_scroll, target_w)

    def _sync_to_target(self, scroll_area, target_widget):
        """공통: target_widget을 scroll_area의 최상단으로 정밀 이동"""
        if not target_widget: return
        
        # 이동할 목표 좌표
        target_y = target_widget.y()
        
        # 현재 스크롤 위치와 거의 같다면 무시 (성능 및 떨림 방지)
        if abs(scroll_area.verticalScrollBar().value() - target_y) < 5:
            return

        self.sync_lock = True
        scroll_area.verticalScrollBar().blockSignals(True)
        
        # 🎯 최상단으로 붙이기
        scroll_area.verticalScrollBar().setValue(target_y)
        
        scroll_area.verticalScrollBar().blockSignals(False)
        self.sync_lock = False

    def _add_placeholder(self, layout, txt):
        """플레이스홀더 추가 시 속성 부여"""
        l = QLabel(txt)
        l.is_placeholder = True # 이제 이 속성이 안전하게 체크됩니다.
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("color: gray; margin: 20px;")
        layout.addWidget(l)

    def on_ref_hover_enter(self, target):
        """참조창 호버 시 본문 하이라이트 (성능 개선)"""
        if not target: return
        # 현재 화면에 보이는 위젯들 위주로만 먼저 체크하도록 설계하는 것이 좋으나, 
        # 일단은 텍스트 변경 여부를 위젯 내부(ArticleWidget)에서 체크하도록 맡깁니다.
        for w in self.left_widgets:
            # target이 바뀔 때만 호출되도록 ArticleWidget.set_highlight 내부 수정 권장
            w.set_highlight(getattr(w, 'current_search_query', ""), hover_target=target)

    def on_ref_hover_leave(self):
        for w in self.left_widgets:
            w.set_highlight(getattr(w, 'current_search_query', ""), hover_target="")

    def on_third_hover_enter(self, target):
        s = self.sender()
        if s and (target_w := self.right_widget_map.get(s.parent_key)):
            target_w.set_highlight(getattr(target_w, 'current_query', ""), hover_target=target)
            self.right_scroll.ensureWidgetVisible(target_w, 0, 150)
    def on_third_hover_leave(self):
        s = self.sender()
        if s and (target_w := self.right_widget_map.get(s.parent_key)):
            target_w.set_highlight(getattr(target_w, 'current_query', ""), hover_target="")

    def run_left_search(self, q=None):
        """1번 창 검색 (렉 최적화 버전)"""
        if q is None: q = self.search_bar_left.get_text()
        
        # 🚀 최적화: 모든 화면 업데이트 중지
        self.left_scroll.setUpdatesEnabled(False)
        
        self.left_matches = []
        for i, w in enumerate(self.left_widgets):
            # 1. 검색어가 있는 경우에만 처리
            if q and (q in w.title_text or q in w.plain_content):
                # 이미 같은 쿼리로 하이라이트 되어 있다면 건너뜀 (렉 방지 핵심)
                if getattr(w, 'last_query', "") != q:
                    w.set_highlight(q)
                self.left_matches.append(i)
            else:
                # 검색어가 없는데 하이라이트가 남아있는 경우에만 리셋
                if getattr(w, 'last_query', "") != "":
                    w.set_highlight("")
        
        self.left_scroll.setUpdatesEnabled(True)
        
        self.left_match_idx = 0 if self.left_matches else -1
        self._update_search_ui(self.search_bar_left, self.left_matches, self.left_match_idx, self.left_scroll, self.left_widgets)

    def next_left_search(self):
        if not self.left_matches: return
        self.left_match_idx = (self.left_match_idx + 1) % len(self.left_matches)
        self._update_search_ui(self.search_bar_left, self.left_matches, self.left_match_idx, self.left_scroll, self.left_widgets)

    def prev_left_search(self):
        if not self.left_matches: return
        self.left_match_idx = (self.left_match_idx - 1) % len(self.left_matches)
        self._update_search_ui(self.search_bar_left, self.left_matches, self.left_match_idx, self.left_scroll, self.left_widgets)

    def run_right_search(self, q=None):
        if q is None: q = self.search_bar_right.get_text()
        self.right_matches = []
        for i in range(self.right_layout.count()):
            w = self.right_layout.itemAt(i).widget()
            if isinstance(w, ReferenceWidget):
                if q and (q in w.plain_title or q in w.plain_content):
                    w.set_highlight(q); self.right_matches.append(w)
                else: w.set_highlight("")
        self.right_match_idx = 0 if self.right_matches else -1
        self._update_search_ui_widget(self.search_bar_right, self.right_matches, self.right_match_idx, self.right_scroll)

    def next_right_search(self):
        if not self.right_matches: return
        self.right_match_idx = (self.right_match_idx + 1) % len(self.right_matches)
        self._update_search_ui_widget(self.search_bar_right, self.right_matches, self.right_match_idx, self.right_scroll)

    def prev_right_search(self):
        if not self.right_matches: return
        self.right_match_idx = (self.right_match_idx - 1) % len(self.right_matches)
        self._update_search_ui_widget(self.search_bar_right, self.right_matches, self.right_match_idx, self.right_scroll)

    def run_third_search(self, q=None):
        if q is None: q = self.search_bar_third.get_text()
        self.third_matches = []
        for i in range(self.third_layout.count()):
            w = self.third_layout.itemAt(i).widget()
            if isinstance(w, ReferenceWidget):
                if q and (q in w.plain_title or q in w.plain_content):
                    w.set_highlight(q); self.third_matches.append(w)
                else: w.set_highlight("")
        self.third_match_idx = 0 if self.third_matches else -1
        self._update_search_ui_widget(self.search_bar_third, self.third_matches, self.third_match_idx, self.third_scroll)

    def next_third_search(self):
        if not self.third_matches: return
        self.third_match_idx = (self.third_match_idx + 1) % len(self.third_matches)
        self._update_search_ui_widget(self.search_bar_third, self.third_matches, self.third_match_idx, self.third_scroll)

    def prev_third_search(self):
        if not self.third_matches: return
        self.third_match_idx = (self.third_match_idx - 1) % len(self.third_matches)
        self._update_search_ui_widget(self.search_bar_third, self.third_matches, self.third_match_idx, self.third_scroll)

    def _update_search_ui(self, bar, matches, idx, scroll, widgets):
        if not matches: bar.set_count_text("0/0"); return
        bar.set_count_text(f"{idx+1}/{len(matches)}")
        scroll.verticalScrollBar().setValue(widgets[matches[idx]].y())

    def _update_search_ui_widget(self, bar, matches, idx, scroll):
        if not matches: bar.set_count_text("0/0"); return
        bar.set_count_text(f"{idx+1}/{len(matches)}")
        scroll.verticalScrollBar().setValue(matches[idx].y())

    def _clear_layouts(self):
        for l in [self.left_layout, self.right_layout, self.third_layout]:
            while l.count():
                it = l.takeAt(0)
                if it.widget(): it.widget().deleteLater()
        self.left_widgets.clear()
        self.right_widget_map.clear()
        self.right_sep_map.clear()
        self.third_sep_map.clear()

    def _extract_key(self, txt):
        m = self.re_art_key.match(txt)
        return m.group(1).replace(" ", "") if m else ""

    def _connect_search(self, bar, run, nxt, prv):
        bar.search_requested.connect(run); bar.next_clicked.connect(nxt); bar.prev_clicked.connect(prv)

    def refresh_combo(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(self.manager.config["DATABASES"].keys())
        self.combo.blockSignals(False)
        if self.combo.count() > 0: self.load_law()

    def update_custom_font(self, family, size):
        self.curr_font, self.curr_size = family, size
        self.load_law()

    def open_new_window(self, link):
        law_name = link.replace("「", "").replace("」", "")
        content = QWidget()
        lay = QVBoxLayout(content)
        data = self.manager.get_parsed_data(law_name)
        if data:
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            inner = QWidget(); in_lay = QVBoxLayout(inner); in_lay.setAlignment(Qt.AlignTop)
            scroll.setWidget(inner); lay.addWidget(scroll)
            for item in data:
                in_lay.addWidget(ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size))
            win = DetachedWindow(law_name, content)
            win.resize(600, 800); win.show()
            self.detached_windows.append(win)