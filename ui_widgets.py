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
        
        self._last_state = None # 🚀 렉 방지용 상태 저장
        self.font_family = font_family
        self.font_size = font_size
        
        # [핵심] 조항 키 생성 (예: "제1조")
        self.article_key = title.split('(')[0].strip().replace(" ", "")

        self.unique_id = f"{chapter}_{self.article_key}"

        # 원본 HTML 미리 생성 (이걸 재사용해서 렉을 줄입니다)
        self.base_content_html = self._process_content(content)
        self.base_title_html = self._process_title(title)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 20) 
        layout.setSpacing(10) 

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #333333;") 
        line.setFixedHeight(2)
        layout.addWidget(line)

        # 제목 레이블
        self.lbl_t = QLabel()
        self.lbl_t.setFont(QFont(font_family, font_size + 2, QFont.Bold))
        self.lbl_t.setStyleSheet("color: #2c3e50; margin-top: 5px;")
        self.lbl_t.setWordWrap(True)
        self.lbl_t.setTextFormat(Qt.RichText) 
        self.lbl_t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.lbl_t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_t.setText(self.base_title_html)
        layout.addWidget(self.lbl_t)

        # 본문 레이블
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

    def set_highlight(self, query, hover_target=""):
        """ArticleWidget 하이라이트 (렉 최적화)"""
        # 🚀 1. 이전 상태와 같으면 아무것도 안 함 (렉 방지 핵심)
        current_state = f"Q:{query}_H:{hover_target}"
        if self._last_state == current_state:
            return 
        self._last_state = current_state

        # 🚀 2. 하이라이트 대상이 없으면 원본 HTML로 복구
        if not query and not hover_target:
            self.lbl_t.setText(self.base_title_html)
            self.lbl_c.setText(self.base_content_html)
            return

        t_text = self.base_title_html
        c_text = self.base_content_html

        # 🚀 3. 하이라이트 처리 (기존 base_html 위에서 글자만 바꿈)
        if query:
            q_style = 'background-color: #FFFF00; color: black;'
            t_text = t_text.replace(query, f'<span style="{q_style}">{query}</span>')
            c_text = c_text.replace(query, f'<span style="{q_style}">{query}</span>')
            
        if hover_target:
            h_style = 'background-color: #D1F2EB; font-weight: bold; color: #1B4F72;'
            t_text = t_text.replace(hover_target, f'<span style="{h_style}">{hover_target}</span>')
            c_text = c_text.replace(hover_target, f'<span style="{h_style}">{hover_target}</span>')

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)

# =========================================================
# 2. 구분선 위젯 (SectionSeparator)
# =========================================================
class SectionSeparator(QWidget):
    def __init__(self, title, unique_id): # 두 번째 인자로 unique_id를 받음
        super().__init__()
        self.unique_id = unique_id
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

    def __init__(self, category, title, content, font_family, font_size, image_base_path=None, parent_key=None, highlight_key=None):
        super().__init__()
        self.parent_key = parent_key # 3번창에서 2번창 찾을 때 사용
        self.unique_id = ""          # 나중에 외부에서 할당됨
        self.article_key = highlight_key # 조항 추출값
        self.setMouseTracking(True)
        self.parent_key = parent_key
        self.highlight_key = highlight_key 
        self._last_state = None
        
        clean_title_key = title.split('(')[0].strip().replace(" ", "")
        self.article_key = highlight_key if highlight_key else clean_title_key
        
        self.base_content_html = self._process_content(content, image_base_path)
        self.base_title_html = self._process_title(title)

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

    def set_highlight(self, query, hover_target=""):
        """ReferenceWidget 하이라이트 (렉 최적화)"""
        current_state = f"Q:{query}_H:{hover_target}"
        if self._last_state == current_state:
            return
        self._last_state = current_state
        
        if not query and not hover_target:
            self.lbl_t.setText(self.base_title_html)
            self.lbl_c.setText(self.base_content_html)
            return

        t_text = self.base_title_html
        c_text = self.base_content_html

        def apply_regex(text, pat, color, bold=False):
            if not pat: return text
            chars = [re.escape(c) for c in pat]
            pattern = r"\s*".join(chars)
            style = f'background-color: {color};'
            if bold: style += ' font-weight: bold;'
            return re.sub(f'({pattern})', lambda m: f'<span style="{style}">{m.group(0)}</span>', text)

        if query:
            t_text = apply_regex(t_text, query, "#ffd700")
            c_text = apply_regex(c_text, query, "#ffd700")
        if hover_target:
            t_text = apply_regex(t_text, hover_target, "#87CEEB", bold=True)
            c_text = apply_regex(c_text, hover_target, "#87CEEB", bold=True)

        self.lbl_t.setText(t_text)
        self.lbl_c.setText(c_text)

    def enterEvent(self, event):
        key = self.highlight_key or self.article_key
        if key: 
            self.hover_entered.emit(key)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)