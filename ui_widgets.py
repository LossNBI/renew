from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re
import os

class ArticleWidget(QWidget):
    link_clicked = pyqtSignal(str) 

    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None):
        super().__init__()
        self.chapter = chapter
        self.title_text = title
        self.plain_content = content 
        
        self.current_search_query = "" 
        self.current_hover_target = ""
        self.font_family = font_family
        self.font_size = font_size
        self.image_base_path = image_base_path

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
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        
        # [중요] 제목도 HTML 처리를 위해 RichText 포맷 설정
        self.lbl_t.setTextFormat(Qt.RichText) 
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
        # 1. 본문 처리
        content_html = self.plain_content
        content_html = content_html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 이미지 처리
        if self.image_base_path:
            def replace_img(match):
                filename = match.group(1).strip()
                full_path = os.path.join(self.image_base_path, filename)
                full_path = full_path.replace("\\", "/")
                return f'<br><img src="{full_path}" width="600"><br>'
            content_html = re.sub(r'\[IMAGE:\s*(.*?)\]', replace_img, content_html)

        # 2. 제목 처리 (하이라이트를 위해 원본 복사)
        title_html = self.title_text
        title_html = title_html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 3. 검색어 하이라이트 (본문 + 제목)
        if self.current_search_query:
            q = self.current_search_query
            # 노란색 하이라이트
            highlight_span = f'<span style="background-color: #ffd700;">{q}</span>'
            content_html = content_html.replace(q, highlight_span)
            title_html = title_html.replace(q, highlight_span) # [추가] 제목에도 적용

        # 4. 호버 하이라이트 (본문만)
        if self.current_hover_target:
            t = self.current_hover_target
            content_html = content_html.replace(t, f'<span style="background-color: #87CEEB; font-weight: bold;">{t}</span>')

        # 5. 링크 처리 (본문만)
        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        re_law = re.compile(r'(「[^」]+」)')
        content_html = re_law.sub(replace_link, content_html)

        self.lbl_c.setText(content_html)
        self.lbl_t.setText(title_html) # [추가] 제목 설정

    def set_highlight(self, search_query, hover_target=None):
        self.current_search_query = search_query
        if hover_target is not None:
            self.current_hover_target = hover_target
        self.render_content()

    def on_link_click(self, url):
        self.link_clicked.emit(url)


# --- 섹션 구분선 ---
class SectionSeparator(QWidget):
    # [수정] 구분선이 어떤 조항("제5조")을 나타내는지 키를 받음
    def __init__(self, title, article_key):
        super().__init__()
        self.article_key = article_key # 키 저장

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 30, 0, 10) 
        
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setFixedHeight(25) 
        bar.setStyleSheet("background-color: #2980b9;")
        layout.addWidget(bar)
        
        label = QLabel(title)
        label.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        label.setStyleSheet("color: #2980b9;")
        label.setWordWrap(True) 
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum) 
        layout.addWidget(label, 1)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #f0f8ff;")

# ReferenceWidget은 변경 없음 (기존 코드 유지)
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
        lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(lbl_t)

        self.lbl_c = QLabel(content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setStyleSheet("line-height: 1.5; color: #555555; border: none;")
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