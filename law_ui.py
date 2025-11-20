# law_ui.py (최종 통합 버전)

import tkinter as tk
from tkinter import ttk, Toplevel, scrolledtext, messagebox
import os
import re 

class LawBrowserUI:
    def __init__(self, master, law_options, start_callback, data_manager_callback):
        self.master = master
        self.law_options = law_options
        self.start_callback = start_callback
        self.data_manager_callback = data_manager_callback
        
        self.pane1 = None
        self.pane2 = None
        self.pane3 = None
        self.law_listbox = None
        self.selection_frame = None

        self.create_selection_screen()
        
    # --- 1. 초기 선택 화면 ---
    def create_selection_screen(self):
        """법률을 선택하는 초기 화면을 생성합니다."""
        self.selection_frame = ttk.Frame(self.master, padding="10")
        self.selection_frame.pack(fill='both', expand=True)

        ttk.Label(self.selection_frame, text="탐색할 법률을 선택하세요:", font=('Helvetica', 14)).pack(pady=10)

        self.selected_law = tk.StringVar(self.master)
        if self.law_options:
            self.selected_law.set(self.law_options[0])

        law_menu = ttk.OptionMenu(self.selection_frame, self.selected_law, 
                                 self.law_options[0] if self.law_options else "선택 없음", 
                                 *self.law_options)
        law_menu.pack(pady=5)

        ttk.Button(self.selection_frame, text="탐색 시작", 
                   command=lambda: self.start_callback(self.selected_law.get())).pack(pady=5)

        ttk.Button(self.selection_frame, text="데이터 관리", 
                   command=self.data_manager_callback).pack(pady=15)

    # --- 2. 메인 레이아웃 및 텍스트 패널 생성 ---
    def create_main_layout(self, article_click_handler):
        """3분할 메인 화면 생성"""
        if self.selection_frame: self.selection_frame.destroy()
        
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill='both', expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        self.pane1 = self._create_text_pane(main_frame, "창 1: 메인 법률", 0)
        self.pane2 = self._create_text_pane(main_frame, "창 2: 1차 참조", 1)
        self.pane3 = self._create_text_pane(main_frame, "창 3: 2차 참조", 2)
        
        # 이 핸들러는 이제 직접 사용되지 않지만, 호환성을 위해 유지
        self.article_click_handler = article_click_handler

    def _create_text_pane(self, parent, title, column):
        """텍스트 창 생성 및 하이퍼링크 스타일 정의"""
        frame = ttk.Frame(parent, borderwidth=2, relief="groove")
        frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(frame, text=title, font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        vscroll = ttk.Scrollbar(frame)
        text_widget = tk.Text(frame, wrap='word', yscrollcommand=vscroll.set)
        vscroll.config(command=text_widget.yview)
        vscroll.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)
        
        # 🌟 [핵심] 하이퍼링크 스타일 정의 (파란색, 밑줄)
        text_widget.tag_config("hyperlink", foreground="blue", underline=1)
        # 마우스 커서 변경 (손가락 모양)
        text_widget.tag_bind("hyperlink", "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind("hyperlink", "<Leave>", lambda e: text_widget.config(cursor="arrow"))
        
        return text_widget

    # --- 3. 법률 내용 표시 (하이퍼링크 적용) ---
    def display_main_law(self, article_data, analyzer, current_law_full_name, link_click_callback):
        """창 1에 내용을 표시하고 텍스트 링크를 생성합니다."""
        self.pane1.config(state=tk.NORMAL)
        self.pane1.delete('1.0', tk.END)
        
        for title, content in article_data.items():
            # 1. 조문 제목
            self.pane1.insert(tk.END, f"--- {title} ---\n", 'article_title')
            self.pane1.tag_config('article_title', font=('Helvetica', 10, 'bold'), background='#E0E0E0')
            
            # 2. 내용 시작 위치
            start_mark = self.pane1.index(tk.END)
            self.pane1.insert(tk.END, content + "\n\n")
            
            # 3. Analyzer를 통해 링크 위치 찾기
            links = analyzer.extract_links(content, current_law_full_name)
            
            for link in links:
                # 텍스트 위젯 내의 절대 인덱스 계산
                s_idx = f"{start_mark} + {link['start']} chars"
                e_idx = f"{start_mark} + {link['end']} chars"
                
                # 고유 태그 이름
                tag_name = f"link_{title}_{link['start']}"
                
                # 태그 적용 (스타일 + 이벤트)
                self.pane1.tag_add("hyperlink", s_idx, e_idx)
                self.pane1.tag_add(tag_name, s_idx, e_idx)
                
                # 클릭 이벤트 바인딩
                self.pane1.tag_bind(tag_name, "<Button-1>", 
                    lambda event, la=link['law_abbr'], art=link['article']: link_click_callback(la, art))

        self.pane1.config(state=tk.DISABLED)

    def update_pane_with_link(self, pane_num, header, content, analyzer, law_full_name, link_click_callback):
        """창 2, 3 업데이트 및 링크 생성"""
        target_pane = self.pane2 if pane_num == 2 else self.pane3
        
        target_pane.config(state=tk.NORMAL)
        target_pane.delete('1.0', tk.END)
        target_pane.insert(tk.END, header + "\n\n", 'header')
        target_pane.tag_config('header', font=('Helvetica', 10, 'italic'), foreground='red')
        
        if content:
            start_mark = target_pane.index(tk.END)
            target_pane.insert(tk.END, content)
            
            links = analyzer.extract_links(content, law_full_name)
            for link in links:
                s_idx = f"{start_mark} + {link['start']} chars"
                e_idx = f"{start_mark} + {link['end']} chars"
                tag_name = f"link_{pane_num}_{link['start']}"
                
                target_pane.tag_add("hyperlink", s_idx, e_idx)
                target_pane.tag_add(tag_name, s_idx, e_idx)
                target_pane.tag_bind(tag_name, "<Button-1>", 
                    lambda event, la=link['law_abbr'], art=link['article']: link_click_callback(la, art))

        target_pane.config(state=tk.DISABLED)

    def scroll_to_article(self, pane_num, article_title):
        """특정 조문 위치로 스크롤 이동"""
        target_pane = self.pane2 if pane_num == 2 else self.pane3
        
        # 조문 제목 검색
        search_res = target_pane.search(article_title, "1.0", stopindex=tk.END)
        if search_res:
            target_pane.see(search_res) # 스크롤 이동
            # 하이라이트 (노란색 배경)
            line_end = f"{search_res} lineend"
            target_pane.tag_add("highlight", search_res, line_end)
            target_pane.tag_config("highlight", background="yellow")

    # --- 4. 이미지 관련 ---
    def display_law_images(self, law_full_name, data_dir, image_list):
        """이미지 파일 목록 표시"""
        if not image_list: return

        img_window = Toplevel(self.master)
        img_window.title(f"{law_full_name} 관련 그림 파일")
        
        text_widget = scrolledtext.ScrolledText(img_window, wrap=tk.WORD, width=50, height=10)
        text_widget.pack(padx=10, pady=10, fill='both', expand=True)
        
        text_widget.insert(tk.END, "--- 해당 법률의 그림 파일 목록 ---\n\n")
        
        for idx, img_file in enumerate(image_list, 1):
            text_widget.insert(tk.END, f"{idx}. {img_file}\n")
            text_widget.tag_add(img_file, f"{text_widget.index(tk.END)}-2c linestart", f"{text_widget.index(tk.END)}-2c lineend")
            text_widget.tag_config(img_file, foreground="purple", underline=1)
            text_widget.tag_bind(img_file, "<Button-1>", 
                                 lambda event, f=img_file, d=data_dir: self.show_image(f, d))
        text_widget.config(state=tk.DISABLED)

    def show_image(self, filename_with_subdir, data_dir):
        image_path = os.path.join(data_dir, filename_with_subdir)
        if os.path.exists(image_path):
            messagebox.showinfo("그림 파일 열기", f"파일 위치:\n{image_path}")
        else:
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다.\n{image_path}")

    # --- 5. 데이터 관리 창 ---
    def create_data_manager_window(self, current_databases, add_law_callback, delete_law_callback):
        manager_window = Toplevel(self.master)
        manager_window.title("법률 데이터 관리")
        manager_window.geometry("600x400")
        
        ttk.Label(manager_window, text="법률 목록 관리", font=('Helvetica', 14, 'bold')).pack(pady=10)
        main_frame = ttk.Frame(manager_window, padding=10)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="현재 등록된 법률:").pack(anchor='w', pady=(0, 5))
        self.law_listbox = tk.Listbox(main_frame, height=10)
        self.law_listbox.pack(fill='x', padx=5, pady=5)
        
        for full_name in current_databases.keys():
            self.law_listbox.insert(tk.END, full_name)
            
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="법률 추가", 
                   command=lambda: self._show_add_law_dialog(manager_window, add_law_callback)).pack(side='left', padx=5)

        ttk.Button(button_frame, text="선택된 법률 삭제", 
                   command=lambda: self._delete_selected_law(delete_law_callback, current_databases)).pack(side='left', padx=5)

    def _show_add_law_dialog(self, parent_window, add_law_callback):
        dialog = Toplevel(parent_window)
        dialog.title("새 법률 추가")
        dialog.geometry("300x250")
        
        fields = [("전체 이름 (예: 법인세법)", "full_name"), ("약어 (예: corp_tax)", "abbr")]
        entries = {}
        for i, (label_text, key) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(dialog)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew')
            entries[key] = entry

        has_image_var = tk.BooleanVar()
        ttk.Checkbutton(dialog, text="관련 그림 파일 존재", variable=has_image_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        def submit():
            full_name = entries['full_name'].get().strip()
            abbr = entries['abbr'].get().strip()
            has_image = has_image_var.get()
            if not full_name or not abbr:
                messagebox.showerror("오류", "입력값을 확인하세요.")
                return
            if add_law_callback(full_name, abbr, has_image):
                self.law_listbox.insert(tk.END, full_name)
                dialog.destroy()

        ttk.Button(dialog, text="추가", command=submit).grid(row=3, column=0, columnspan=2, pady=10)
        dialog.grid_columnconfigure(1, weight=1)
        
    def _delete_selected_law(self, delete_law_callback, current_databases):
        selected_indices = self.law_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("경고", "선택된 항목이 없습니다.")
            return
        full_name = self.law_listbox.get(selected_indices[0])
        if messagebox.askyesno("삭제 확인", f"'{full_name}'을 삭제하시겠습니까?"):
            if delete_law_callback(full_name):
                self.law_listbox.delete(selected_indices[0])
                messagebox.showinfo("완료", "삭제되었습니다.")