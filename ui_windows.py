from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtCore import pyqtSignal

class DetachedWindow(QMainWindow):
    # 닫힐 때 시그널 (제목, 위젯 반환)
    closed_signal = pyqtSignal(str, QWidget) 

    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 800)
        self.content_widget = content_widget
        self.setCentralWidget(self.content_widget)

    def closeEvent(self, event):
        # 창이 닫힐 때 메인 윈도우에게 알림
        self.closed_signal.emit(self.windowTitle(), self.content_widget)
        event.accept()