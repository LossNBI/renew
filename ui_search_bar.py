from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class LawSearchBar(QWidget):
    # 메인 윈도우로 보낼 신호들
    search_requested = pyqtSignal(str) # 검색 요청 (Enter 또는 버튼 클릭 시)
    next_clicked = pyqtSignal()        # 다음 찾기 (▼ 버튼)
    prev_clicked = pyqtSignal()        # 이전 찾기 (▲ 버튼)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("검색:"))

        # 1. 검색어 입력창
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("검색어 (Enter)")
        self.inp_search.setFixedWidth(200)
        
        # [변경 1] textChanged 연결 삭제 (입력 중 자동 검색 방지)
        # self.inp_search.textChanged.connect(...) <- 삭제됨
        
        # [변경 2] Enter키 누르면 검색 실행
        self.inp_search.returnPressed.connect(self.execute_search)
        layout.addWidget(self.inp_search)

        # [변경 3] 돋보기(검색) 버튼 추가
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedWidth(30)
        self.btn_search.setToolTip("검색 실행")
        self.btn_search.clicked.connect(self.execute_search)
        layout.addWidget(self.btn_search)

        # 2. 결과 개수 표시
        self.lbl_count = QLabel("0/0")
        self.lbl_count.setFixedWidth(60)
        self.lbl_count.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_count)

        # 3. 위/아래 이동 버튼
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.setToolTip("이전 결과")
        self.btn_prev.clicked.connect(self.prev_clicked)
        layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("▼")
        self.btn_next.setFixedWidth(30)
        self.btn_next.setToolTip("다음 결과")
        self.btn_next.clicked.connect(self.next_clicked)
        layout.addWidget(self.btn_next)

    # [추가] 검색 실행 함수
    def execute_search(self):
        text = self.inp_search.text().strip()
        # 텍스트를 담아 메인 윈도우에 "검색해줘!"라고 신호 보냄
        self.search_requested.emit(text)

    def get_text(self):
        return self.inp_search.text().strip()

    def set_count_text(self, text):
        self.lbl_count.setText(text)

    def set_focus_input(self):
        self.inp_search.setFocus()
        self.inp_search.selectAll()

    def clear_input(self):
        self.inp_search.clear()

    # 입력창에서 위/아래 방향키 누르면 다음/이전 결과로 이동
    def keyPressEvent(self, event):
        if self.inp_search.hasFocus():
            if event.key() == Qt.Key_Down:
                self.next_clicked.emit()
                return
            elif event.key() == Qt.Key_Up:
                self.prev_clicked.emit()
                return
        super().keyPressEvent(event)