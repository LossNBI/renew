from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re

class ArticleWidget(QWidget):
    link_clicked = pyqtSignal(str) 

    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        self.chapter = chapter
        self.title_text = title
        self.plain_content = content 
        
        self.article_key = title.split('(')[0].strip()
        if ' ' in self.article_key: self.article_key = self.article_key.split(' ')[0]

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        
        # --- [수정] 구분선 안 보이는 문제 해결 ---
        # HLine 속성 대신, 높이를 강제로 지정한 박스로 만듭니다.
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame) # 테두리 없음
        line.setFixedHeight(2)             # 높이 2px (두께)
        line.setStyleSheet("background-color: #000000;") # 완전 검정
        layout.addWidget(line)

        # 제목
        self.lbl_t = QLabel(title)
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.lbl_t)

        # 내용
        processed_content = self.process_links(content)
        self.lbl_c = QLabel(processed_content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setStyleSheet("color: #333333; line-height: 1.6;")
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setTextFormat(Qt.RichText) 
        self.lbl_c.setOpenExternalLinks(False)
        self.lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.lbl_c.linkActivated.connect(self.on_link_click)
        self.lbl_c.setMinimumWidth(100)
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        
        layout.addWidget(self.lbl_c)
        self.setLayout(layout)

    def set_custom_font(self, family, size):
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))

    def process_links(self, text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        re_law = re.compile(r'(「[^」]+」)')
        return re_law.sub(replace_link, text)

    def on_link_click(self, url):
        self.link_clicked.emit(url)

# ReferenceWidget은 변경 없음 (이전과 동일하게 유지)
class ReferenceWidget(QWidget):
    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 20)
        
        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet("color: #d35400; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl_cat)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont(font_family, font_size + 1, QFont.Bold))
        lbl_t.setWordWrap(True)
        lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl_t.setMinimumWidth(50)
        lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(lbl_t)

        self.lbl_c = QLabel(content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_c.setStyleSheet("line-height: 1.5; color: #555555;")
        self.lbl_c.setMinimumWidth(50)
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        
        layout.addWidget(self.lbl_c)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(line)
        self.setLayout(layout)