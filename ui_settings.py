from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QLabel, 
                             QPushButton, QGroupBox, QFormLayout, QLineEdit, 
                             QMessageBox, QFileDialog, QFontComboBox, QSpinBox)
from PyQt5.QtGui import QFont

# 1. 데이터 관리 팝업
class DataSettingsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("데이터 관리")
        self.resize(400, 350)
        
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("등록된 법률:"))
        layout.addWidget(self.list_widget)

        btn_del = QPushButton("선택 삭제")
        btn_del.setStyleSheet("background-color: #ffcccc; color: red;")
        btn_del.clicked.connect(self.del_law)
        layout.addWidget(btn_del)

        group = QGroupBox("추가하기")
        form = QFormLayout()
        self.inp_name = QLineEdit()
        self.inp_code = QLineEdit()
        self.btn_file = QPushButton("파일 찾기...")
        self.btn_file.clicked.connect(self.find_file)
        self.lbl_file = QLabel("선택 안함")
        self.f_path = None
        
        form.addRow("이름:", self.inp_name)
        form.addRow("코드:", self.inp_code)
        form.addRow("파일:", self.btn_file)
        form.addRow("", self.lbl_file)
        group.setLayout(form)
        layout.addWidget(group)

        btn_add = QPushButton("추가")
        btn_add.clicked.connect(self.add_law)
        layout.addWidget(btn_add)
        
        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for k in self.manager.config["DATABASES"]:
            self.list_widget.addItem(k)

    def find_file(self):
        f, _ = QFileDialog.getOpenFileName(self, '선택', '', '*.txt')
        if f: 
            self.f_path = f
            self.lbl_file.setText(f.split('/')[-1])

    def add_law(self):
        if not self.inp_name.text() or not self.inp_code.text(): return
        self.manager.add_law(self.inp_name.text(), self.inp_code.text(), self.f_path)
        self.refresh()
        self.inp_name.clear(); self.inp_code.clear(); self.f_path = None; self.lbl_file.setText("")

    def del_law(self):
        curr = self.list_widget.currentItem()
        if curr:
            self.manager.delete_law(curr.text())
            self.refresh()

# 2. 폰트 설정 팝업
class FontSettingsDialog(QDialog):
    def __init__(self, curr_font, curr_size, parent=None):
        super().__init__(parent)
        self.setWindowTitle("글씨 설정")
        self.resize(300, 150)
        self.sel_font = curr_font
        self.sel_size = curr_size
        
        layout = QFormLayout()
        self.fc = QFontComboBox(); self.fc.setCurrentFont(QFont(curr_font))
        self.sb = QSpinBox(); self.sb.setRange(8, 40); self.sb.setValue(curr_size)
        
        layout.addRow("글꼴:", self.fc)
        layout.addRow("크기:", self.sb)
        
        btn = QPushButton("적용")
        btn.clicked.connect(self.apply)
        layout.addRow("", btn)
        self.setLayout(layout)

    def apply(self):
        self.sel_font = self.fc.currentFont().family()
        self.sel_size = self.sb.value()
        self.accept()

# 3. 메인 메뉴 팝업 (버튼 2개)
class MainSettingsDialog(QDialog):
    def __init__(self, manager, parent_window):
        super().__init__(parent_window)
        self.manager = manager
        self.p_win = parent_window
        self.setWindowTitle("설정")
        self.resize(250, 120)
        
        layout = QVBoxLayout()
        b1 = QPushButton(" 📁 데이터 추가/삭제")
        b1.setFixedHeight(40)
        b1.clicked.connect(self.go_data)
        
        b2 = QPushButton(" 🔤 글씨 변경")
        b2.setFixedHeight(40)
        b2.clicked.connect(self.go_font)
        
        layout.addWidget(b1)
        layout.addWidget(b2)
        self.setLayout(layout)

    def go_data(self):
        DataSettingsDialog(self.manager, self).exec_()
        self.p_win.refresh_combo() # 메인창 갱신

    def go_font(self):
        dlg = FontSettingsDialog(self.p_win.curr_font, self.p_win.curr_size, self)
        if dlg.exec_() == QDialog.Accepted:
            self.p_win.update_font(dlg.sel_font, dlg.sel_size)