from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QMainWindow,
                             QLabel, QPushButton, QComboBox, QScrollArea, QFrame,
                             QListWidget, QGroupBox, QFormLayout, QLineEdit, 
                             QMessageBox, QFileDialog, QDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from data_manager import LawDataManager

# --- [작은 부품] 설정 팝업창 ---
class SettingsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.resize(400, 300)
        self.setWindowTitle("설정")
        
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("등록된 법 목록:"))
        layout.addWidget(self.list_widget)

        # 삭제 버튼
        btn_del = QPushButton("선택 삭제")
        btn_del.setStyleSheet("color: red")
        btn_del.clicked.connect(self.del_law)
        layout.addWidget(btn_del)

        # 추가 입력칸
        form = QFormLayout()
        self.inp_name = QLineEdit()
        self.inp_code = QLineEdit()
        self.btn_file = QPushButton("파일 찾기")
        self.btn_file.clicked.connect(self.find_file)
        self.f_path = None
        
        form.addRow("이름:", self.inp_name)
        form.addRow("코드:", self.inp_code)
        form.addRow("파일:", self.btn_file)
        layout.addLayout(form)

        btn_add = QPushButton("추가하기")
        btn_add.clicked.connect(self.add_law)
        layout.addWidget(btn_add)
        
        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for k in self.manager.config["DATABASES"]:
            self.list_widget.addItem(k)

    def find_file(self):
        f, _ = QFileDialog.getOpenFileName(self, '파일 선택', '', '*.txt')
        if f: self.f_path = f

    def add_law(self):
        if not self.inp_name.text(): return
        self.manager.add_law(self.inp_name.text(), self.inp_code.text(), self.f_path)
        self.refresh()
        self.inp_name.clear(); self.inp_code.clear(); self.f_path = None

    def del_law(self):
        curr = self.list_widget.currentItem()
        if curr:
            self.manager.delete_law(curr.text())
            self.refresh()

# --- [작은 부품] 조(Article) 하나를 보여주는 위젯 ---
class ArticleWidget(QWidget):
    def __init__(self, chapter, title, content):
        super().__init__()
        self.chapter = chapter # 현재 조가 속한 장(Sticky Header용)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 10)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #CCCCCC; margin-bottom: 10px;")
        layout.addWidget(line)

        # 조 제목 (굵게)
        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        lbl_t.setStyleSheet("color: #222;")
        layout.addWidget(lbl_t)

        # 조 내용
        lbl_c = QLabel(content)
        lbl_c.setFont(QFont("Malgun Gothic", 10))
        lbl_c.setWordWrap(True)
        lbl_c.setStyleSheet("color: #444; line-height: 1.5;")
        layout.addWidget(lbl_c)
        
        self.setLayout(layout)

# --- [메인] 전체 뷰어 화면 ---
class LawViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = LawDataManager()
        self.widgets_list = [] # 스크롤 위치 계산용
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("법률 뷰어")
        self.resize(600, 800)
        
        # 전체 틀
        container = QWidget()
        main_layout = QVBoxLayout(container)

        # 1. 상단 바 (설정버튼 + 콤보박스)
        top_bar = QHBoxLayout()
        btn_set = QPushButton("설정")
        btn_set.clicked.connect(self.open_settings)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.load_law)
        
        top_bar.addWidget(btn_set)
        top_bar.addWidget(self.combo, 1)
        main_layout.addLayout(top_bar)

        # 2. 스티키 헤더 (고정된 장 제목)
        self.sticky_header = QLabel("법률을 선택하세요")
        self.sticky_header.setAlignment(Qt.AlignCenter)
        self.sticky_header.setStyleSheet("background: #4A90E2; color: white; padding: 8px; font-weight: bold;")
        main_layout.addWidget(self.sticky_header)

        # 3. 스크롤 영역
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_widget)
        # 스크롤 움직일 때마다 함수 호출
        self.scroll.verticalScrollBar().valueChanged.connect(self.check_header)
        main_layout.addWidget(self.scroll)

        self.setCentralWidget(container)
        self.refresh_combo()

    def open_settings(self):
        dlg = SettingsDialog(self.manager, self)
        dlg.exec_()
        self.refresh_combo()

    def refresh_combo(self):
        curr = self.combo.currentText()
        self.combo.clear()
        for name in self.manager.config["DATABASES"]:
            self.combo.addItem(name)
        if curr: self.combo.setCurrentText(curr)

    def load_law(self):
        # 기존 내용 지우기
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()
        self.widgets_list = []

        law_name = self.combo.currentText()
        if not law_name: return

        # 데이터 매니저에게 파싱된 데이터 요청
        data = self.manager.get_parsed_data(law_name)
        
        for item in data:
            w = ArticleWidget(item['chapter'], item['title'], item['content'])
            self.scroll_layout.addWidget(w)
            self.widgets_list.append(w) # 리스트에 저장해둬야 위치 계산 가능

        # 로드 후 맨 위로
        self.scroll.verticalScrollBar().setValue(0)
        if data: self.sticky_header.setText(data[0]['chapter'])

    def check_header(self):
        # 현재 스크롤 위치
        scroll_y = self.scroll.verticalScrollBar().value()
        
        # 화면 맨 위에 있는 위젯 찾기
        for w in self.widgets_list:
            # 위젯의 바닥이 스크롤보다 아래에 있으면 (=화면에 보이면)
            if w.y() + w.height() > scroll_y:
                if self.sticky_header.text() != w.chapter:
                    self.sticky_header.setText(w.chapter)
                break