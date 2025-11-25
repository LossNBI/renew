from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class LawSearchBar(QWidget):
    # 메인 윈도우로 보낼 신호들
    search_requested = pyqtSignal(str) # 검색어 변경 시
    next_clicked = pyqtSignal()        # 다음 버튼 / 엔터 / 아래키
    prev_clicked = pyqtSignal()        # 이전 버튼 / 위키

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("검색:"))

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("검색어 입력 (Ctrl+F)")
        self.inp_search.setFixedWidth(200)
        # 글자가 바뀔 때마다 시그널 발생
        self.inp_search.textChanged.connect(lambda: self.search_requested.emit(self.inp_search.text()))
        # 엔터키 -> 다음 찾기
        self.inp_search.returnPressed.connect(self.next_clicked)
        layout.addWidget(self.inp_search)

        # 결과 개수 표시 (예: 1/5)
        self.lbl_count = QLabel("0/0")
        self.lbl_count.setFixedWidth(60)
        self.lbl_count.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_count)

        # 버튼들
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.clicked.connect(self.prev_clicked)
        layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("▼")
        self.btn_next.setFixedWidth(30)
        self.btn_next.clicked.connect(self.next_clicked)
        layout.addWidget(self.btn_next)

    def get_text(self):
        return self.inp_search.text().strip()

    def set_count_text(self, text):
        self.lbl_count.setText(text)

    def set_focus_input(self):
        self.inp_search.setFocus()
        self.inp_search.selectAll()

    def clear_input(self):
        self.inp_search.clear()

    # 입력창에서 위/아래 키 누르면 바로 이동하도록 처리
    def keyPressEvent(self, event):
        if self.inp_search.hasFocus():
            if event.key() == Qt.Key_Down:
                self.next_clicked.emit()
                return
            elif event.key() == Qt.Key_Up:
                self.prev_clicked.emit()
                return
        super().keyPressEvent(event)