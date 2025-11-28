# ui_widgets.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import pyqtSignal, Qt
import re

class ArticleWidget(QWidget):
    link_clicked = pyqtSignal(str) 

    def __init__(self, chapter, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        self.chapter = chapter
        self.title_text = title
        self.plain_content = content 
        
        # 상태 저장용 변수
        self.current_search_query = "" 
        self.current_hover_target = ""
        self.font_family = font_family
        self.font_size = font_size

        self.article_key = title.split('(')[0].strip().replace(" ", "") # 공백 제거 키

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
        
        # 초기 렌더링
        self.render_content()

    def set_custom_font(self, family, size):
        self.font_family = family
        self.font_size = size
        self.lbl_t.setFont(QFont(family, size + 2, QFont.Bold))
        self.lbl_c.setFont(QFont(family, size))

    # [핵심] 텍스트 렌더링 (검색어, 호버, 링크 처리 통합)
    def render_content(self):
        text = self.plain_content
        
        # HTML 특수문자 이스케이프 (태그 오작동 방지)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 1. 검색어 하이라이트 (노란색)
        if self.current_search_query:
            # 대소문자 구분 없이 치환하려면 re.sub 사용 권장되나, 간단히 replace 사용
            # (정확한 매칭을 위해선 plain text 상태에서 해야 함)
            q = self.current_search_query
            text = text.replace(q, f'<span style="background-color: #ffd700;">{q}</span>')

        # 2. 호버 타겟 하이라이트 (하늘색) - 역참조 위치 표시
        if self.current_hover_target:
            t = self.current_hover_target
            # 이미 검색어 하이라이트가 적용된 상태일 수 있으므로 주의
            # 여기서는 단순하게 치환합니다.
            text = text.replace(t, f'<span style="background-color: #87CEEB; font-weight: bold;">{t}</span>')

        # 3. 법령 링크 처리
        def replace_link(match):
            law_name = match.group(1)
            return f'<a href="{law_name}" style="color: #0000FF; text-decoration: underline;">{law_name}</a>'
        re_law = re.compile(r'(「[^」]+」)')
        text = re_law.sub(replace_link, text)

        self.lbl_c.setText(text)

    # 외부에서 호출하는 하이라이트 설정 함수
    def set_highlight(self, search_query, hover_target=None):
        self.current_search_query = search_query
        # hover_target이 None이면 기존 유지, 빈 문자열이면 해제
        if hover_target is not None:
            self.current_hover_target = hover_target
        self.render_content()

    def on_link_click(self, url):
        self.link_clicked.emit(url)

class SectionSeparator(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 30, 0, 10) # 위쪽 여백을 줘서 구분감 형성
        
        # 굵은 바 (왼쪽 데코레이션)
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setFixedHeight(25)
        bar.setStyleSheet("background-color: #2980b9;")
        layout.addWidget(bar)
        
        # 텍스트
        label = QLabel(title)
        label.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        label.setStyleSheet("color: #2980b9;")
        layout.addWidget(label)
        
        layout.addStretch(1)
        self.setLayout(layout)
        
        # 전체 배경색 (선택사항, 구분감을 더 주기 위해)
        self.setStyleSheet("background-color: #f0f8ff;") # 아주 연한 하늘색

# [수정] 호버 이벤트를 감지하는 ReferenceWidget
class ReferenceWidget(QWidget):
    # 마우스가 들어오고 나갈 때 보낼 신호
    hover_entered = pyqtSignal(str) # "제5조"
    hover_left = pyqtSignal()

    def __init__(self, category, title, content, font_family="Malgun Gothic", font_size=10):
        super().__init__()
        
        # 제목에서 "제O조" 추출하여 호버 타겟으로 설정
        # 예: "[소득세법] 제5조" -> "제5조" 추출 필요, 혹은 전체 타이틀
        # 단순하게 타이틀의 공백 제거된 article_key를 사용하기 위해 처리
        self.target_key = ""
        # 괄호 앞부분만 추출 (예: 제5조(정의) -> 제5조)
        match = re.match(r'.*?(제\d+(?:의\s*\d+)?조)', title)
        if match:
            self.target_key = match.group(1).replace(" ", "") # 공백 제거된 키 (제5조의2)
            # 하이라이트는 공백이 있을 수도 있는 원본 텍스트 매칭이 필요할 수 있으나,
            # 여기서는 편의상 "제5조" 같은 핵심 키워드를 보냅니다.

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 20)
        
        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet("color: #d35400; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl_cat)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont(font_family, font_size + 1, QFont.Bold))
        lbl_t.setWordWrap(True)
        layout.addWidget(lbl_t)

        self.lbl_c = QLabel(content)
        self.lbl_c.setFont(QFont(font_family, font_size))
        self.lbl_c.setWordWrap(True)
        self.lbl_c.setStyleSheet("line-height: 1.5; color: #555555;")
        layout.addWidget(self.lbl_c)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(line)
        self.setLayout(layout)

    # 마우스 진입
    def enterEvent(self, event):
        if self.target_key:
            self.hover_entered.emit(self.target_key)
        super().enterEvent(event)

    # 마우스 이탈
    def leaveEvent(self, event):
        self.hover_left.emit()
        super().leaveEvent(event)