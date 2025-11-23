from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt5.QtGui import QFont

class ArticleWidget(QWidget):
    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        self.chapter = chapter
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 15, 5, 15)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #B0B0B0; margin-bottom: 10px;")
        layout.addWidget(line)

        # 제목
        self.lbl_t = QLabel(title)
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50;")
        self.lbl_t.setWordWrap(True)
        layout.addWidget(self.lbl_t)

        # 내용 (자동 줄바꿈 설정됨)
        self.lbl_c = QLabel(content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setStyleSheet("color: #333333; line-height: 1.6;")
        self.lbl_c.setWordWrap(True)

        self.lbl_c.setMinimumWidth(200)
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        
        layout.addWidget(self.lbl_c)
        self.setLayout(layout)

    def set_custom_font(self, family, size):
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))