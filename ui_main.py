from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QScrollArea, QLabel, QMessageBox)
from PyQt5.QtCore import Qt
from data_manager import LawDataManager
from ui_widgets import ArticleWidget
from ui_settings import MainSettingsDialog

class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.widgets_list = []
        self.curr_font = "Malgun Gothic"
        self.curr_size = 11
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어 Pro")
        self.resize(600, 800)
        
        container = QWidget()
        main_layout = QVBoxLayout(container)

        # 상단 바
        top_bar = QHBoxLayout()
        
        # [핵심 수정] 톱니바퀴 아이콘 변경 (유니코드 문자 사용)
        self.btn_set = QPushButton(" ⚙ 설정") 
        self.btn_set.setFont(self.font()) # 폰트 크기 맞춤
        self.btn_set.setFixedWidth(80)
        self.btn_set.clicked.connect(self.open_settings)
        
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        
        top_bar.addWidget(self.btn_set)
        top_bar.addWidget(self.combo, 1)
        main_layout.addLayout(top_bar)

        # 스티키 헤더
        self.sticky = QLabel("법률을 선택하세요")
        self.sticky.setAlignment(Qt.AlignCenter)
        self.sticky.setStyleSheet("background: #4A90E2; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        main_layout.addWidget(self.sticky)

        # 스크롤
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.s_widget = QWidget()
        self.s_layout = QVBoxLayout(self.s_widget)
        self.s_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.s_widget)
        self.scroll.verticalScrollBar().valueChanged.connect(self.check_header)
        main_layout.addWidget(self.scroll)

        self.setCentralWidget(container)
        self.refresh_combo()

    def open_settings(self):
        MainSettingsDialog(self.manager, self).exec_()

    def update_font(self, family, size):
        self.curr_font = family
        self.curr_size = size
        for w in self.widgets_list:
            w.set_custom_font(family, size)
        QMessageBox.information(self, "완료", "글씨 설정 변경됨")

    def refresh_combo(self):
        curr = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        for name in self.manager.config["DATABASES"]:
            self.combo.addItem(name)
        if curr: self.combo.setCurrentText(curr)
        self.combo.blockSignals(False)
        if self.combo.count() > 0 and not self.widgets_list:
            self.load_law()

    def load_law(self):
        for i in reversed(range(self.s_layout.count())):
            self.s_layout.itemAt(i).widget().deleteLater()
        self.widgets_list = []

        law_name = self.combo.currentText()
        if not law_name: return

        data = self.manager.get_parsed_data(law_name)
        
        for item in data:
            w = ArticleWidget(item['chapter'], item['title'], item['content'], self.curr_font, self.curr_size)
            self.s_layout.addWidget(w)
            self.widgets_list.append(w)

        self.scroll.verticalScrollBar().setValue(0)
        if data: self.sticky.setText(data[0]['chapter'])

    def check_header(self):
        sy = self.scroll.verticalScrollBar().value()
        for w in self.widgets_list:
            if w.y() + w.height() > sy:
                if self.sticky.text() != w.chapter:
                    self.sticky.setText(w.chapter)
                break