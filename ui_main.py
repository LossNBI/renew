import os
import time
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, 
                             QSplitter, QTabWidget, QTextBrowser, QShortcut,
                             QProgressDialog, QApplication)
from PyQt5.QtGui import QKeySequence, QFont 
from PyQt5.QtCore import Qt

from ui_windows import DetachedWindow
from ui_search_bar import LawSearchBar
from data_manager import LawDataManager
from ui_widgets import ArticleWidget, ReferenceWidget, SectionSeparator
from ui_settings import MainSettingsDialog

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.left_widgets = [] 
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.detached_windows = []
        
        # 좌측 검색용
        self.left_matches = [] 
        self.left_match_idx = -1

        # 우측 검색용
        self.right_matches = [] # ReferenceWidget 객체를 저장
        self.right_match_idx = -1
        
        self.sync_lock = False       
        self.last_sync_time = 0      
        
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro (Expert)")
        self.resize(1400, 900)

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
        
        # --- 상단 바 (설정, 법률선택) ---
        top = QHBoxLayout()
        self.btn_set = QPushButton(" ⚙ 설정")
        self.btn_set.clicked.connect(self.open_settings)
        top.addWidget(self.btn_set)
        
        # *기존 중앙 검색창 제거됨*

        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        top.addWidget(QLabel("  법률 선택:"))
        top.addWidget(self.combo, 1)
        layout.addLayout(top)

        # --- 스플리터 ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3) 
        splitter.setStyleSheet("QSplitter::handle { background-color: #BDC3C7; }")

        # ================= [왼쪽 패널] =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # [왼쪽 검색창]
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

        # [오른쪽 검색창]
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
        # Ctrl+F : 왼쪽 검색
        self.shortcut_left = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_left.activated.connect(self.search_bar_left.set_focus_input)
        
        # Ctrl+G : 오른쪽 검색
        self.shortcut_right = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_right.activated.connect(self.search_bar_right.set_focus_input)

    # --- [왼쪽] 검색 로직 ---
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

    # --- [오른쪽] 검색 로직 ---
    def run_right_search(self, query=None):
        if query is None: query = self.search_bar_right.get_text()
        self.right_matches = []
        self.right_match_idx = -1

        # 1. 모든 ReferenceWidget을 순회하며 하이라이트 & 매칭 확인
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ReferenceWidget):
                widget.set_highlight(query) # 하이라이트 적용
                
                if query and (query in widget.plain_title or query in widget.plain_content):
                    self.right_matches.append(widget) # 위젯 객체 자체를 저장
        
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
        target_widget = self.right_matches[idx]
        # 스크롤 이동 (잠금 걸어서 좌측 이동 방지할 수도 있지만, 검색 이동은 자연스럽게 두어도 됨)
        # 만약 검색 이동 시 좌측이 움직이는게 싫다면 여기서 sync_lock 사용
        self.sync_lock = True
        self.right_scroll.verticalScrollBar().setValue(target_widget.y())
        self.sync_lock = False

    # --- 스크롤 및 기타 로직 (이전과 동일) ---
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

    def load_law(self):
        law_name = self.combo.currentText()
        if not law_name: return

        self._clear_layout(self.left_layout)
        self._clear_layout(self.right_layout)
        self.left_widgets = []
        
        # 검색창 초기화
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

    def open_new_window(self, link_text):
        law_name = link_text.replace("「", "").replace("」", "")
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
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

        data = self.manager.get_parsed_data(law_name)
        if not data:
            lbl_err = QLabel(f"'{law_name}' 데이터를 찾을 수 없습니다.")
            lbl_err.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(lbl_err)
        else:
            progress = QProgressDialog(f"{law_name} 불러오는 중...", "취소", 0, len(data), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            for i, item in enumerate(data):
                if progress.wasCanceled(): break
                w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
                w.link_clicked.connect(self.open_new_window) 
                scroll_layout.addWidget(w)
                progress.setValue(i+1)
                QApplication.processEvents()
        
        new_window = DetachedWindow(law_name, content_widget, self)
        new_window.resize(600, 800)
        new_window.closed_signal.connect(self.cleanup_closed_window)
        new_window.show()
        self.detached_windows.append(new_window)

    def on_ref_hover_enter(self, target_text):
        for w in self.left_widgets:
            w.set_highlight(w.current_search_query, hover_target=target_text)
    
    def on_ref_hover_leave(self):
        for w in self.left_widgets:
            w.set_highlight(w.current_search_query, hover_target="")
    
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
        for i in range(self.right_layout.count()):
            item = self.right_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), ReferenceWidget):
                item.widget().setFont(QFont(family, size)) 
        self.load_law() 
    
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