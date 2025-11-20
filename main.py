# main.py

import tkinter as tk
from tkinter import ttk, messagebox
import os
from law_parser import LawParser
from law_analyzer import LawAnalyzer
from law_ui import LawBrowserUI 
from config_manager import ConfigManager

class LawBrowserApp:
    def __init__(self, master):
        self.master = master
        self.config_manager = ConfigManager()
        self.parser = LawParser(self.config_manager)
        self.analyzer = LawAnalyzer(self.parser, self.config_manager)
        
        self.current_law_full_name = None 
        law_options = list(self.config_manager.get_databases().keys()) 

        if not law_options:
            ttk.Label(self.master, text="데이터 폴더에 법률 파일이 없습니다.", font=('Helvetica', 14)).pack(pady=50)
            return

        self.ui = LawBrowserUI(master, law_options, self.start_browser, self.open_data_manager_ui)

    def start_browser(self, law_full_name):
        self.current_law_full_name = law_full_name
        current_law_abbr = self.parser.get_law_abbr(law_full_name)
        
        if not self.parser.load_law(self.current_law_full_name):
             messagebox.showerror("오류", f"파일 로드 실패: {current_law_abbr}.txt")
             return 

        # 1. 메인 레이아웃 생성 (기존 핸들러는 이제 안쓰지만 호환성 위해 남겨둠)
        self.ui.create_main_layout(lambda x: None) 
        
        # 2. 창 1 데이터 표시 (🌟 수정: Analyzer와 콜백 전달)
        law_data = self.parser.laws.get(current_law_abbr, {}) 
        self.ui.display_main_law(
            law_data.get('조문', {}), 
            self.analyzer, 
            self.current_law_full_name, 
            self.on_link_click_pane1 # 🌟 1번 창 링크 클릭 시 실행될 함수
        )
        
        # 3. 이미지 목록
        image_list = self.parser.get_law_images(current_law_abbr)
        self.ui.display_law_images(law_full_name, self.config_manager.get_data_dir(), image_list)

    # 🌟 1번 창 링크 클릭 핸들러
    def on_link_click_pane1(self, target_law_abbr, target_article):
        # 약어로 전체 이름 찾기
        all_dbs = self.config_manager.get_databases()
        try:
            target_law_full_name = [k for k, v in all_dbs.items() if v == target_law_abbr][0]
        except IndexError:
            return # 약어를 못 찾으면 무시

        if not self.parser.load_law(target_law_full_name): return

        # 전체 내용을 가져옴 (법제처 스타일)
        full_content = self._get_full_text(target_law_abbr)
        header = f"참조: {target_law_full_name} > {target_article}"
        
        # 2번 창 업데이트 (Analyzer와 2번 창용 콜백 전달)
        self.ui.update_pane_with_link(
            2, header, full_content, self.analyzer, target_law_full_name, self.on_link_click_pane2
        )
        
        # 스크롤 이동
        self.ui.scroll_to_article(2, f"--- {target_article} ---")

    # 🌟 2번 창 링크 클릭 핸들러
    def on_link_click_pane2(self, target_law_abbr, target_article):
        all_dbs = self.config_manager.get_databases()
        try:
            target_law_full_name = [k for k, v in all_dbs.items() if v == target_law_abbr][0]
        except IndexError:
            return

        if not self.parser.load_law(target_law_full_name): return

        full_content = self._get_full_text(target_law_abbr)
        header = f"2차 참조: {target_law_full_name} > {target_article}"
        
        # 3번 창 업데이트 (더 이상 클릭 안되게 빈 lambda 전달)
        self.ui.update_pane_with_link(
            3, header, full_content, self.analyzer, target_law_full_name, lambda a,b: None
        )
        self.ui.scroll_to_article(3, f"--- {target_article} ---")

    def _get_full_text(self, law_abbr):
        """법률의 전체 텍스트를 합쳐서 반환하는 도우미 함수"""
        data = self.parser.laws.get(law_abbr, {}).get('조문', {})
        text = ""
        for t, c in data.items():
            text += f"--- {t} ---\n{c}\n\n"
        return text

    # --- 데이터 관리 (기존 유지) ---
    def open_data_manager_ui(self):
        self.ui.create_data_manager_window(
            self.config_manager.get_databases(), self.handle_add_law, self.handle_delete_law
        )
    def handle_add_law(self, f, a, h):
        return self.config_manager.add_law(f, a, h) # (단순화)
    def handle_delete_law(self, f):
        return self.config_manager.delete_law(f) # (단순화)

if __name__ == '__main__':
    root = tk.Tk()
    app = LawBrowserApp(root)
    root.mainloop()