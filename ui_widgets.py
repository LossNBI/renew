from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re
import os

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
        self.article_key = title.split('(')[0].strip().replace(" ", "") 

        self.base_content_html = self._process_base_content(content)
        self.base_title_html = self._process_base_title(title)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame)
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: #000000;")
        layout.addWidget(line)

        self.lbl_t = QLabel()
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_t.setTextFormat(Qt.RichText) 
        self.lbl_t.setText(self.base_title_html)
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
        self.lbl_c.setText(self.base_content_html)
        
        layout.addWidget(self.lbl_c)
        self.setLayout(layout)

    def _process_base_content(self, text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if self.image_base_path:
            def replace_img(match):
                filename = match.group(1).strip()
                full_path = os.path.join(self.image_base_path, filename)
                full_path = full_path.replace("\\", "/")
                return f'<br><img src="{full_path}" width="600"><br>'
            text = self.RE_IMAGE.sub(replace_img, text)
        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        text = self.RE_LINK.sub(replace_link, text)
        return text

    def _process_base_title(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def set_custom_font(self, family, size):
        self.font_family = family
        self.font_size = size
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))

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

        # [수정] 띄어쓰기 무시 매칭 함수
        def apply_highlight(text, pattern_str, color, bold=False):
            if not pattern_str: return text
            # 글자 사이사이에 \s* (0개 이상의 공백) 패턴을 삽입
            # 예: "제5조" -> "제\s*5\s*조"
            flexible_pattern = r"\s*".join([re.escape(char) for char in pattern_str])
            style = f'background-color: {color};'
            if bold: style += ' font-weight: bold;'
            replacement = f'<span style="{style}">\\g<0></span>'
            
            # 대소문자 무시, HTML 태그 훼손 방지는 복잡하므로 단순 텍스트 매칭 시도
            # 여기서는 본문 내용 내에서의 매칭을 우선합니다.
            return re.sub(f'({flexible_pattern})', replacement, text)

        # 1. 검색어 (노란색)
        if search_query:
            t_text = apply_highlight(t_text, search_query, "#ffd700")
            c_text = apply_highlight(c_text, search_query, "#ffd700")

        # 2. 호버 타겟 (하늘색)
        if hover_target:
            t_text = apply_highlight(t_text, hover_target, "#87CEEB", bold=True)
            c_text = apply_highlight(c_text, hover_target, "#87CEEB", bold=True)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)


    def on_link_click(self, url):
        self.link_clicked.emit(url)

class SectionSeparator(QWidget):
    def __init__(self, title, article_key):
        super().__init__()
        self.article_key = article_key 
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

class ReferenceWidget(QWidget):
    hover_entered = pyqtSignal(str) 
    hover_left = pyqtSignal()
    RE_IMAGE = re.compile(r'\[IMAGE:\s*(.*?)\]')

    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None, parent_key=None, highlight_key=None):
        super().__init__()
        self.target_key = ""
        self.article_key = ""
        self.parent_key = parent_key
        self.highlight_key = highlight_key 
        
        self.plain_title = title
        self.plain_content = content
        self.image_base_path = image_base_path
        
        self.current_query = ""
        self.current_hover_target = ""
        self.is_highlighted = False

        if highlight_key:
            self.target_key = highlight_key
            self.article_key = highlight_key
        else:
            match = re.match(r'.*?(제\s*\d+\s*조(?:\s*의\s*\d+)?)', title)
            if match:
                clean_key = match.group(1).replace(" ", "")
                self.target_key = clean_key
                self.article_key = clean_key

        self.base_content_html = self._process_base_content(content)
        self.base_title_html = self._process_base_title(title)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 20)
        self.setStyleSheet("background-color: white; border-radius: 5px;")

        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet("color: #d35400; font-weight: bold; font-size: 12px; border: none;")
        layout.addWidget(lbl_cat)

        self.lbl_t = QLabel()
        self.lbl_t.setFont(QFont(font_family, font_size + 1, QFont.Bold))
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setStyleSheet("border: none;")
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.MinimumExpanding)
        self.lbl_t.setTextFormat(Qt.RichText)
        self.lbl_t.setText(self.base_title_html)
        layout.addWidget(self.lbl_t)

        self.lbl_c = QLabel()
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setStyleSheet("line-height: 1.5; color: #555555; border: none;")
        self.lbl_c.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.MinimumExpanding)
        self.lbl_c.setTextFormat(Qt.RichText)
        self.lbl_c.setText(self.base_content_html)
        layout.addWidget(self.lbl_c)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(line)
        self.setLayout(layout)

    def _process_base_content(self, text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if self.image_base_path:
            def replace_img(match):
                filename = match.group(1).strip()
                full_path = os.path.join(self.image_base_path, filename)
                full_path = full_path.replace("\\", "/")
                return f'<br><img src="{full_path}" width="600"><br>'
            text = self.RE_IMAGE.sub(replace_img, text)
        return text

    def _process_base_title(self, text):
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

        # [수정] 띄어쓰기 허용 하이라이트 로직
        def apply_highlight(text, pattern_str, color, bold=False):
            if not pattern_str: return text
            # "제5조" -> "제\s*5\s*조" 패턴 생성
            flexible_pattern = r"\s*".join([re.escape(char) for char in pattern_str])
            style = f'background-color: {color};'
            if bold: style += ' font-weight: bold;'
            replacement = f'<span style="{style}">\\g<0></span>'
            return re.sub(f'({flexible_pattern})', replacement, text)

        # 1. 검색어 (노란색)
        if query:
            t_text = apply_highlight(t_text, query, "#ffd700")
            c_text = apply_highlight(c_text, query, "#ffd700")

        # 2. 호버 타겟 (하늘색)
        if hover_target:
            t_text = apply_highlight(t_text, hover_target, "#87CEEB", bold=True)
            c_text = apply_highlight(c_text, hover_target, "#87CEEB", bold=True)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)

    def enterEvent(self, event):
        key_to_emit = self.highlight_key if self.highlight_key else self.target_key
        if key_to_emit: 
            self.hover_entered.emit(key_to_emit)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)