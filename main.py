# main.py (수정 완료 버전)

import tkinter as tk
from tkinter import ttk, messagebox
# import config # <--- 1. 미사용 임포트 삭제
import os
from law_parser import LawParser
from law_analyzer import LawAnalyzer
from law_ui import LawBrowserUI 
from config_manager import ConfigManager

class LawBrowserApp:
    def __init__(self, master):
        self.master = master
        
        # 0. ConfigManager 인스턴스 생성
        self.config_manager = ConfigManager()

        # 1. 모델 인스턴스 생성 (config_manager 인스턴스 전달)
        self.parser = LawParser(self.config_manager)
        self.analyzer = LawAnalyzer(self.parser, self.config_manager)
        
        self.current_law_full_name = None 
        law_options = list(self.config_manager.get_databases().keys()) 

        if not law_options:
            ttk.Label(self.master, text="데이터 폴더에 법률 파일이 없습니다.", font=('Helvetica', 14)).pack(pady=50)
            return

        # 2. 뷰(UI) 인스턴스 생성 및 연결 (데이터 관리 함수도 UI에 전달)
        # 참고: law_ui.py에 create_data_manager_window가 정의되어 있어야 합니다.
        self.ui = LawBrowserUI(master, law_options, self.start_browser, self.open_data_manager_ui)

    def start_browser(self, law_full_name):
        """UI의 선택에 따라 법률을 로드하고 메인 화면을 표시합니다."""
        self.current_law_full_name = law_full_name
        current_law_abbr = self.parser.get_law_abbr(law_full_name)
        
        if not self.parser.load_law(self.current_law_full_name):
             messagebox.showerror("오류", f"법률 파일 ({current_law_abbr}.txt)을 로드할 수 없습니다.")
             return 

        # 1. 메인 레이아웃 생성
        self.ui.create_main_layout(self.on_article_click)
        
        # 2. 창 1에 데이터 표시
        law_data = self.parser.laws.get(current_law_abbr, {}) 
        self.ui.display_main_law(law_data.get('조문', {}))
        
        # 3. 이미지 목록 표시
        # 2. 중복 호출 수정: 한 번만 호출하고 필요한 모든 인자를 전달합니다.
        image_list = self.parser.get_law_images(current_law_abbr)
        self.ui.display_law_images(law_full_name, self.config_manager.get_data_dir(), image_list)

    def on_article_click(self, article_title):
        """핵심 로직: 창 1의 조문 클릭 시 호출."""
        
        current_law_abbr = self.parser.get_law_abbr(self.current_law_full_name) 

        # 1. 1차 조문 내용 가져오기
        content1 = self.parser.get_article_content(current_law_abbr, article_title)
        
        # 2. 1차 참조 분석
        ref_abbr1, ref_title1 = self.analyzer.find_reference(content1, self.current_law_full_name)
        
        content2, header2 = "", "1차 참조 조문 없음"
        ref_abbr2, ref_title2 = None, None

        all_dbs = self.config_manager.get_databases()

        if ref_title1:
            content2 = self.parser.get_article_content(ref_abbr1, ref_title1)
            
            # 약어로 전체 법률 이름 찾기
            ref_law_full_name1 = [k for k, v in all_dbs.items() if v == ref_abbr1][0]

            # 3. 2차 참조 분석
            ref_abbr2, ref_title2 = self.analyzer.find_reference(content2, ref_law_full_name1)
            
            header2 = f"1차 참조 ({ref_law_full_name1}): {ref_title1}"

        content3, header3 = "", "2차 참조 조문 없음"
        if ref_title2:
            # 2차 참조된 법률의 전체 이름을 찾습니다.
            ref_law_full_name2 = [k for k, v in all_dbs.items() if v == ref_abbr2][0]
            
            content3 = self.parser.get_article_content(ref_abbr2, ref_title2)
            # 3. header3 중복 정의 수정: content3 계산 후 한 번만 할당
            header3 = f"2차 참조 ({ref_law_full_name2}): {ref_title2}"

        # 4. 계산된 결과를 UI 모듈에 전달하여 업데이트 요청
        self.ui.update_reference_panes(header2, content2, header3, content3)

    # --- 🌟 데이터 관리 기능 구현 (이 부분은 수정할 필요 없음) ---
    def open_data_manager_ui(self):
        """데이터 관리 창을 띄우고, 관리 함수들을 전달합니다."""
        
        self.ui.create_data_manager_window(
            current_databases=self.config_manager.get_databases(),
            add_law_callback=self.handle_add_law,
            delete_law_callback=self.handle_delete_law
        )
        
    def handle_add_law(self, full_name, abbr, has_image):
        """새 법률을 추가하고, 파일 시스템을 정리하는 로직."""
        success, message = self.config_manager.add_law(full_name, abbr, has_image)
        
        if success:
            law_file_path = os.path.join(self.config_manager.get_data_dir(), f"{abbr}.txt")
            if not os.path.exists(law_file_path):
                with open(law_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"--- {full_name} ---\n\n제1조(목적)\n 이 법은 ...")
            
            if has_image:
                image_folder_path = os.path.join(self.config_manager.get_data_dir(), f"{abbr}_png")
                os.makedirs(image_folder_path, exist_ok=True)
                
        messagebox.showinfo("데이터 관리", message)
        return success

    def handle_delete_law(self, full_name):
        """법률을 삭제하고, 관련 파일을 제거하는 로직."""
        success, message = self.config_manager.delete_law(full_name)
        
        if success:
            # 데이터 파일 삭제 로직은 생략
            pass
            
        messagebox.showinfo("데이터 관리", message)
        return success


if __name__ == '__main__':
    root = tk.Tk()
    app = LawBrowserApp(root)
    root.mainloop()