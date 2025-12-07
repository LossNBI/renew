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
        self.image_base_path = image_base_path
        
        self.current_search_query = "" 
        self.current_hover_target = ""
        self.font_family = font_family
        self.font_size = font_size

        # [최적화 1] 상태 추적 변수 (불필요한 렌더링 방지)
        self.is_highlighted = False 

        self.article_key = title.split('(')[0].strip().replace(" ", "") 

        # [최적화 2] 기본 HTML 미리 계산 (이미지/링크 처리된 버전)
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
        self.lbl_t.setText(self.base_title_html) # 초기값 설정
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
        self.lbl_c.setText(self.base_content_html) # 초기값 설정
        
        layout.addWidget(self.lbl_c)
        self.setLayout(layout)

    # [최적화] 내용을 미리 가공하여 저장하는 함수 (1회만 실행됨)
    def _process_base_content(self, text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 이미지 처리
        if self.image_base_path:
            def replace_img(match):
                filename = match.group(1).strip()
                full_path = os.path.join(self.image_base_path, filename)
                full_path = full_path.replace("\\", "/")
                return f'<br><img src="{full_path}" width="600"><br>'
            text = re.sub(r'\[IMAGE:\s*(.*?)\]', replace_img, text)

        # 링크 처리
        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        re_law = re.compile(r'(「[^」]+」)')
        text = re_law.sub(replace_link, text)
        return text

    def _process_base_title(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def set_custom_font(self, family, size):
        self.font_family = family
        self.font_size = size
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))

    # [최적화] 하이라이트 적용 함수 (가벼워짐)
    def set_highlight(self, search_query, hover_target=None):
        # 변경 사항이 없으면 리턴 (매우 중요)
        if self.current_search_query == search_query and self.current_hover_target == hover_target:
            return

        self.current_search_query = search_query
        self.current_hover_target = hover_target

        # 검색어도 없고 호버도 없으면 -> 원본(Base) 상태로 복구
        if not search_query and not hover_target:
            if self.is_highlighted: # 이미 원본 상태라면 건너뜀
                self.lbl_t.setText(self.base_title_html)
                self.lbl_c.setText(self.base_content_html)
                self.is_highlighted = False
            return

        self.is_highlighted = True
        
        # 원본(Base)을 가져와서 거기다 색칠만 함 (정규식 재연산 X)
        final_title = self.base_title_html
        final_content = self.base_content_html

        # 1. 검색어 하이라이트
        if search_query:
            span = f'<span style="background-color: #ffd700;">{search_query}</span>'
            final_title = final_title.replace(search_query, span)
            final_content = final_content.replace(search_query, span)

        # 2. 호버 하이라이트
        if hover_target:
            # 호버는 보통 "제5조" 같은 것이므로 정확한 매칭이 필요할 수 있으나 단순 치환
            span = f'<span style="background-color: #87CEEB; font-weight: bold;">{hover_target}</span>'
            final_content = final_content.replace(hover_target, span)

        self.lbl_t.setText(final_title)
        self.lbl_c.setText(final_content)

    def on_link_click(self, url):
        self.link_clicked.emit(url)


# SectionSeparator는 그대로 유지
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


# [최적화] ReferenceWidget도 동일하게 캐싱 적용
class ReferenceWidget(QWidget):
    hover_entered = pyqtSignal(str) 
    hover_left = pyqtSignal()

    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10, image_base_path=None):
        super().__init__()
        self.target_key = ""
        self.plain_title = title
        self.plain_content = content
        self.image_base_path = image_base_path
        
        self.current_query = ""
        self.is_highlighted = False

        match = re.match(r'.*?(제\d+(?:의\d+)?조)', title)
        if match:
            self.target_key = match.group(1).replace(" ", "")

        # [최적화] 미리 가공
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
            text = re.sub(r'\[IMAGE:\s*(.*?)\]', replace_img, text)
        return text

    def _process_base_title(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def set_highlight(self, query):
        if self.current_query == query: return
        self.current_query = query
        
        if not query:
            if self.is_highlighted:
                self.lbl_t.setText(self.base_title_html)
                self.lbl_c.setText(self.base_content_html)
                self.is_highlighted = False
            return

        self.is_highlighted = True
        span = f'<span style="background-color: #ffd700;">{query}</span>'
        
        self.lbl_t.setText(self.base_title_html.replace(query, span))
        self.lbl_c.setText(self.base_content_html.replace(query, span))

    def enterEvent(self, event):
        if self.target_key: self.hover_entered.emit(self.target_key)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)