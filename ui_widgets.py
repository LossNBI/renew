from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
import re
import os

# ArticleWidget, SectionSeparator는 기존 코드 유지 (최적화 버전)
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
        final_title = self.base_title_html
        final_content = self.base_content_html

        if search_query:
            span = f'<span style="background-color: #ffd700;">{search_query}</span>'
            final_title = final_title.replace(search_query, span)
            final_content = final_content.replace(search_query, span)

        if hover_target:
            # [핵심] 호버 타겟(예: "제17조")이 있으면 그 부분만 하늘색으로 칠함
            span = f'<span style="background-color: #87CEEB; font-weight: bold;">{hover_target}</span>'
            final_content = final_content.replace(hover_target, span)
            final_title = final_title.replace(hover_target, span)

        self.lbl_t.setText(final_title)
        self.lbl_c.setText(final_content)

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


# --- [수정] ReferenceWidget (하이라이트 키 전달 기능 추가) ---
class ReferenceWidget(QWidget):
    hover_entered = pyqtSignal(str) 
    hover_left = pyqtSignal()
    RE_IMAGE = re.compile(r'\[IMAGE:\s*(.*?)\]')

    # [수정] highlight_key 인자 추가 (이게 있으면 이걸 하이라이트 하라고 신호 보냄)
    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None, parent_key=None, highlight_key=None):
        super().__init__()
        self.target_key = ""
        self.article_key = ""
        self.parent_key = parent_key
        self.highlight_key = highlight_key # 저장
        
        self.plain_title = title
        self.plain_content = content
        self.image_base_path = image_base_path
        
        self.current_query = ""
        self.current_hover_target = ""
        self.is_highlighted = False

        match = re.match(r'.*?(제\d+(?:의\d+)?조)', title)
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

        if query:
            span = f'<span style="background-color: #ffd700;">{query}</span>'
            t_text = t_text.replace(query, span)
            c_text = c_text.replace(query, span)

        if hover_target:
            # 내용에서 타겟 텍스트를 찾아 하이라이트
            span = f'<span style="background-color: #87CEEB; font-weight: bold;">{hover_target}</span>'
            c_text = c_text.replace(hover_target, span)
            t_text = t_text.replace(hover_target, span)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)

    def enterEvent(self, event):
        # [핵심 로직] 우선순위: highlight_key(지정된 텍스트) -> parent_key(부모조항) -> target_key(자기자신)
        key = self.highlight_key
        if not key:
            key = self.parent_key if self.parent_key else self.target_key
            
        if key:
            self.hover_entered.emit(key)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)