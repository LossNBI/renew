from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re

# ... (ArticleWidget 클래스는 기존과 동일하므로 생략하거나 그대로 두세요) ...
class ArticleWidget(QWidget):
    link_clicked = pyqtSignal(str) 

    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        self.chapter = chapter
        self.title_text = title
        self.plain_content = content 
        
        self.current_search_query = "" 
        self.current_hover_target = ""
        self.font_family = font_family
        self.font_size = font_size

        self.article_key = title.split('(')[0].strip().replace(" ", "") 

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame)
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #000000;")
        layout.addWidget(line)

        self.lbl_t = QLabel(title)
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # [중요] 제목도 창 크기에 맞춰 줄어들게 설정
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(self.lbl_t)

        self.lbl_c = QLabel()
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setStyleSheet("color: #333333; line-height: 1.6;")
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setTextFormat(Qt.RichText) 
        self.lbl_c.setOpenExternalLinks(False)
        self.lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.lbl_c.linkActivated.connect(self.on_link_click)
        self.lbl_c.setMinimumWidth(100)
        # [중요] 내용도 창 크기에 맞춰 줄어들게 설정
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        
        layout.addWidget(self.lbl_c)
        self.setLayout(layout)
        self.render_content()

    def set_custom_font(self, family, size):
        self.font_family = family
        self.font_size = size
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))

    def render_content(self):
        text = self.plain_content
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if self.current_search_query:
            q = self.current_search_query
            text = text.replace(q, f'<span style="background-color: #ffd700;">{q}</span>')

        if self.current_hover_target:
            t = self.current_hover_target
            text = text.replace(t, f'<span style="background-color: #87CEEB; font-weight: bold;">{t}</span>')

        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        
        re_law = re.compile(r'(「[^」]+」)')
        text = re_law.sub(replace_link, text)

        self.lbl_c.setText(text)

    def set_highlight(self, search_query, hover_target=None):
        self.current_search_query = search_query
        if hover_target is not None:
            self.current_hover_target = hover_target
        self.render_content()

    def on_link_click(self, url):
        self.link_clicked.emit(url)


# --- 섹션 구분선 ---
class SectionSeparator(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 30, 0, 10) 
        
        # 파란색 세로 바
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setFixedHeight(25) # 바 높이 고정
        bar.setStyleSheet("background-color: #2980b9;")
        layout.addWidget(bar)
        
        # 텍스트 라벨
        label = QLabel(title)
        label.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        label.setStyleSheet("color: #2980b9;")
        label.setWordWrap(True) # 줄바꿈 허용
        
        # 가로 정책을 Ignored로 하되...
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum) 
        
        # [핵심 수정] addWidget에 숫자 '1'을 넣어서 
        # "남은 공간을 이 라벨이 전부 다 써라"고 명시합니다.
        layout.addWidget(label, 1)
        
        # layout.addStretch(1)  <-- 이 줄은 삭제! (라벨이 늘어나야 하므로 빈 공간 삭제)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #f0f8ff;")


# --- [핵심 수정] ReferenceWidget ---
class ReferenceWidget(QWidget):
    hover_entered = pyqtSignal(str) 
    hover_left = pyqtSignal()

    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        self.target_key = ""
        match = re.match(r'.*?(제\d+(?:의\d+)?조)', title)
        if match:
            self.target_key = match.group(1).replace(" ", "")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 20)
        
        self.setStyleSheet("background-color: white; border-radius: 5px;")

        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet("color: #d35400; font-weight: bold; font-size: 12px; border: none;")
        layout.addWidget(lbl_cat)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont(font_family, font_size + 1, QFont.Bold))
        lbl_t.setWordWrap(True)
        lbl_t.setStyleSheet("border: none;")
        # [핵심] 가로 사이즈 정책을 Ignored로 설정하여 창 크기에 맞춰 줄어들게 함
        lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(lbl_t)

        self.lbl_c = QLabel(content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setStyleSheet("line-height: 1.5; color: #555555; border: none;")
        # [핵심] 가로 사이즈 정책을 Ignored로 설정
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(self.lbl_c)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(line)
        self.setLayout(layout)

    def enterEvent(self, event):
        if self.target_key: self.hover_entered.emit(self.target_key)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)