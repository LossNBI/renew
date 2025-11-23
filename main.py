import sys
from PyQt5.QtWidgets import QApplication
from ui_main import LawViewerWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LawViewerWindow()
    ex.show()
    sys.exit(app.exec_())