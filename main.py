import sys
from PyQt5.QtWidgets import QApplication
from ui_manager import LawViewerWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 폰트 이쁘게
    font = app.font()
    font.setFamily("Malgun Gothic")
    font.setPointSize(10)
    app.setFont(font)
    
    ex = LawViewerWindow()
    ex.show()
    sys.exit(app.exec_())