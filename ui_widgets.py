from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re
import os

# =========================================================
# 1. 법률창 위젯 (ArticleWidget)
# =========================================================
class ArticleWidget(QWidget):
    link_clicked = pyqtSignal(str) 
    RE_IMAGE = re.compile(r'\[IMAGE:\s*(.*?)\]')
    RE_LINK = re.compile(r'(「[^」]+」)')

    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None):
        super().__init__()
        self.chapter = chapter
        self.title_text = title
        self.plain_content = content 
        self.image_base_path = image_base_path
        
        self.current_search_query = "" 
        self.current_hover_target = ""
        self.font_family = font_family
        self.font_size = font_size
        self.is_highlighted = False 
        
        # [핵심] 조항 키 생성 (예: "제1조")
        self.article_key = title.split('(')[0].strip().replace(" ", "") 

        self.base_content_html = self._process_content(content)
        self.base_title_html = self._process_title(title)

        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 20) 
        layout.setSpacing(10) 

        # 상단 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #333333;") 
        line.setFixedHeight(2)
        layout.addWidget(line)

        # 제목
        self.lbl_t = QLabel()
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50; margin-top: 5px;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextFormat(Qt.RichText) 
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_t.setText(self.base_title_html)
        layout.addWidget(self.lbl_t)

        # 본문
        self.lbl_c = QLabel()
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setStyleSheet("color: #333333; line-height: 1.6;") 
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setTextFormat(Qt.RichText) 
        self.lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.lbl_c.linkActivated.connect(self.on_link_click)
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_c.setText(self.base_content_html)
        layout.addWidget(self.lbl_c)
        
        self.setLayout(layout)

    def _process_content(self, text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if self.image_base_path:
            def replace_img(match):
                filename = match.group(1).strip()
                path = os.path.join(self.image_base_path, filename).replace("\\", "/")
                return f'<br><img src="{path}" width="600"><br>'
            text = self.RE_IMAGE.sub(replace_img, text)
        
        def replace_link(match):
            name = match.group(1)
            return f'<a href="{name}" style="color: #2980b9; text-decoration: none; font-weight: bold;">{name}</a>'
        return self.RE_LINK.sub(replace_link, text)

    def _process_title(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def on_link_click(self, url):
        self.link_clicked.emit(url)

    def set_highlight(self, search_query, hover_target=None):
        if self.current_search_query == search_query and self.current_hover_target == hover_target:
            return
        self.current_search_query = search_query
        self.current_hover_target = hover_target

        if not search_query and not hover_target:
            if self.is_highlighted:
                self.lbl_t.setText(self.base_title_html)
                self.lbl_c.setText(self.base_content_html)
                self.is_highlighted = False
            return

        self.is_highlighted = True
        t_text = self.base_title_html
        c_text = self.base_content_html

        def apply(text, pat, color, bold=False):
            if not pat: return text
            chars = [re.escape(c) for c in pat]
            pattern = r"\s*".join(chars)
            style = f'background-color: {color};'
            if bold: style += ' font-weight: bold;'
            def cb(m): return f'<span style="{style}">{m.group(0)}</span>'
            return re.sub(f'({pattern})', cb, text)

        if search_query:
            t_text = apply(t_text, search_query, "#ffd700")
            c_text = apply(c_text, search_query, "#ffd700")
        if hover_target:
            t_text = apply(t_text, hover_target, "#87CEEB", bold=True)
            c_text = apply(c_text, hover_target, "#87CEEB", bold=True)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)


# =========================================================
# 2. 구분선 위젯 (SectionSeparator)
# =========================================================
class SectionSeparator(QWidget):
    def __init__(self, title, article_key):
        super().__init__()
        self.article_key = article_key 
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 20, 0, 5) 
        
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setFixedHeight(18) 
        bar.setStyleSheet("background-color: #d35400;") 
        layout.addWidget(bar)
        
        label = QLabel(title)
        label.setFont(QFont("Malgun Gothic", 10, QFont.Bold))
        label.setStyleSheet("color: #d35400;")
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        layout.addWidget(label, 1)
        
        self.setLayout(layout)

# =========================================================
# 3. 참조/심화참조 위젯 (ReferenceWidget)
# =========================================================
class ReferenceWidget(QWidget):
    hover_entered = pyqtSignal(str) 
    hover_left = pyqtSignal()
    RE_IMAGE = re.compile(r'\[IMAGE:\s*(.*?)\]')

    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None, parent_key=None, highlight_key=None):
        super().__init__()
        
        # [핵심] 마우스 추적 활성화 (호버 반응 속도 향상)
        self.setMouseTracking(True)
        
        self.parent_key = parent_key
        self.highlight_key = highlight_key 
        
        # 키 초기화 (안전장치)
        self.target_key = ""
        # 기본 키 생성 로직 (제목에서 "제1조" 등 추출)
        clean_title_key = title.split('(')[0].strip().replace(" ", "")
        self.article_key = clean_title_key
        
        if highlight_key:
            self.target_key = highlight_key
            self.article_key = highlight_key
        else:
            # 제목에서 정규식으로 정확한 조항 키 추출 시도
            match = re.match(r'.*?(제\s*\d+\s*조(?:\s*의\s*\d+)?)', title)
            if match:
                clean_key = match.group(1).replace(" ", "")
                self.target_key = clean_key
                self.article_key = clean_key

        self.current_query = ""
        self.current_hover_target = ""
        self.is_highlighted = False
        
        self.base_content_html = self._process_content(content, image_base_path)
        self.base_title_html = self._process_title(title)

        # 디자인 통일 (ArticleWidget 스타일)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 20)
        layout.setSpacing(8)
        self.setStyleSheet("background-color: white; border-bottom: 1px solid #E0E0E0;") 

        if category:
            lbl_cat = QLabel(category)
            lbl_cat.setFont(QFont(font_family, 9, QFont.Bold))
            lbl_cat.setStyleSheet("color: #e67e22; margin-bottom: 2px;")
            layout.addWidget(lbl_cat)

        self.lbl_t = QLabel()
        self.lbl_t.setFont(QFont(font_family, font_size + 1, QFont.Bold)) 
        self.lbl_t.setStyleSheet("color: #2c3e50;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextFormat(Qt.RichText)
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_t.setText(self.base_title_html)
        layout.addWidget(self.lbl_t)

        self.lbl_c = QLabel()
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setStyleSheet("color: #333333; line-height: 1.6;") 
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setTextFormat(Qt.RichText)
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.lbl_c.setText(self.base_content_html)
        layout.addWidget(self.lbl_c)

        self.setLayout(layout)

    def _process_content(self, text, img_path):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if img_path:
            def replace_img(match):
                filename = match.group(1).strip()
                path = os.path.join(img_path, filename).replace("\\", "/")
                return f'<br><img src="{path}" width="600"><br>'
            text = self.RE_IMAGE.sub(replace_img, text)
        return text

    def _process_title(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def set_highlight(self, query, hover_target=None):
        if self.current_query == query and self.current_hover_target == hover_target:
            return
        self.current_query = query
        self.current_hover_target = hover_target
        
        if not query and not hover_target:
            if self.is_highlighted:
                self.lbl_t.setText(self.base_title_html)
                self.lbl_c.setText(self.base_content_html)
                self.is_highlighted = False
            return

        self.is_highlighted = True
        t_text = self.base_title_html
        c_text = self.base_content_html

        def apply(text, pat, color, bold=False):
            if not pat: return text
            chars = [re.escape(c) for c in pat]
            pattern = r"\s*".join(chars)
            style = f'background-color: {color};'
            if bold: style += ' font-weight: bold;'
            def cb(m): return f'<span style="{style}">{m.group(0)}</span>'
            return re.sub(f'({pattern})', cb, text)

        if query:
            t_text = apply(t_text, query, "#ffd700")
            c_text = apply(c_text, query, "#ffd700")
        if hover_target:
            t_text = apply(t_text, hover_target, "#87CEEB", bold=True)
            c_text = apply(c_text, hover_target, "#87CEEB", bold=True)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)

    # [핵심] 호버 이벤트 강화: 어떤 키라도 반드시 찾아내어 신호를 보냄
    def enterEvent(self, event):
        # 1순위: 명시적 키, 2순위: 제목에서 추출한 키, 3순위: 기본 생성 키
        key = self.highlight_key or self.target_key or self.article_key
        if key: 
            self.hover_entered.emit(key)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)