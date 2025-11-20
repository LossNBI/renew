# law_ui.py (수정 버전)

import tkinter as tk
from tkinter import ttk, Toplevel, scrolledtext, messagebox # messagebox 추가
import os
import re # <--- 1. re 모듈 임포트 추가

class LawBrowserUI:
    # 🌟 수정: data_manager_callback 인자를 추가로 받도록 변경
    def __init__(self, master, law_options, start_callback, data_manager_callback):
        self.master = master
        self.law_options = law_options
        self.start_callback = start_callback
        self.data_manager_callback = data_manager_callback # <--- 추가된 인자 저장
        
        self.pane1 = None
        self.pane2 = None
        self.pane3 = None

        self.create_selection_screen()
        
    def create_selection_screen(self):
        """법률을 선택하는 초기 화면을 생성하고, 데이터 관리 버튼을 추가합니다."""
        
        # 1. 프레임 생성 (이 부분이 누락되면 오류 발생)
        self.selection_frame = ttk.Frame(self.master, padding="10")
        self.selection_frame.pack(fill='both', expand=True)

        # 2. UI 요소 생성
        ttk.Label(self.selection_frame, text="탐색할 법률을 선택하세요:", font=('Helvetica', 14)).pack(pady=10)

        self.selected_law = tk.StringVar(self.master)
        self.selected_law.set(self.law_options[0])

        law_menu = ttk.OptionMenu(self.selection_frame, self.selected_law, self.law_options[0], *self.law_options)
        law_menu.pack(pady=5)

        # 3. 버튼 생성 및 콜백 연결 (탐색 시작)
        ttk.Button(self.selection_frame, text="탐색 시작", 
                   command=lambda: self.start_callback(self.selected_law.get())).pack(pady=5)

        # 4. 버튼 생성 및 콜백 연결 (데이터 관리)
        # show_data_manager 대신 main.py에서 전달받은 self.data_manager_callback을 사용합니다.
        ttk.Button(self.selection_frame, text="데이터 관리", 
                   command=self.data_manager_callback).pack(pady=15)
        
    # --- create_main_layout 함수는 이전과 동일 ---
    def create_main_layout(self, article_click_handler):
        """3분할된 메인 탐색 화면을 생성합니다."""
        self.selection_frame.destroy()
        
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill='both', expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        self.pane1 = self._create_text_pane(main_frame, "창 1: 메인 법률", 0)
        self.pane2 = self._create_text_pane(main_frame, "창 2: 1차 참조", 1)
        self.pane3 = self._create_text_pane(main_frame, "창 3: 2차 참조", 2)
        
        self.article_click_handler = article_click_handler

    # --- _create_text_pane 함수 (개선) ---
    def _create_text_pane(self, parent, title, column):
        """텍스트 창과 스크롤바를 생성하고 그리드에 배치합니다."""
        frame = ttk.Frame(parent, borderwidth=2, relief="groove")
        frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(frame, text=title, font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        vscroll = ttk.Scrollbar(frame)
        text_widget = tk.Text(frame, wrap='word', yscrollcommand=vscroll.set)
        vscroll.config(command=text_widget.yview)

        vscroll.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)

        return text_widget

    # --- display_main_law 함수는 이전과 동일 ---
    def display_main_law(self, article_data):
        """창 1에 메인 법률 내용을 표시합니다."""
        self.pane1.config(state=tk.NORMAL)
        self.pane1.delete('1.0', tk.END)
        
        for title, content in article_data.items():
            start_index = self.pane1.index(tk.END)
            
            # re.match를 사용하기 위해 re 모듈이 필요했음 (해결됨)
            if re.match(r'제\d+조(?:\s*의\s*\d+)?', title):
                self.pane1.insert(tk.END, f"--- {title} ---\n", 'article_title')
                self.pane1.insert(tk.END, content + "\n\n")

                # 이벤트 바인딩: 클릭 시 main.py의 로직 함수 호출
                self.pane1.tag_add(title, start_index, f"{self.pane1.index(tk.END)}-2c")
                self.pane1.tag_config(title, foreground='blue', underline=1, font=('Helvetica', 10, 'bold'))
                self.pane1.tag_bind(title, '<Button-1>', 
                                    lambda event, t=title: self.article_click_handler(t))
            else:
                self.pane1.insert(tk.END, f"\n\n*** {title} ***\n", 'section_title')
                self.pane1.insert(tk.END, content + "\n\n")
                self.pane1.tag_config('section_title', font=('Helvetica', 12, 'italic'), background='#F0F0F0')
        
        self.pane1.config(state=tk.DISABLED) # 읽기 전용으로 설정

    # --- update_reference_panes 및 _update_pane 함수는 이전과 동일 ---
    def update_reference_panes(self, header2, content2, header3, content3):
        """창 2와 창 3의 내용을 업데이트합니다."""
        self._update_pane(self.pane2, header2, content2)
        self._update_pane(self.pane3, header3, content3)

    def _update_pane(self, pane, header, content):
        """주어진 창에 내용을 업데이트합니다."""
        pane.config(state=tk.NORMAL) 
        pane.delete('1.0', tk.END)
        pane.insert(tk.END, header + "\n\n", 'header')
        pane.insert(tk.END, content)
        pane.tag_config('header', font=('Helvetica', 10, 'italic'), foreground='red')
        pane.config(state=tk.DISABLED) 

    # --- 2. 이미지 관련 함수 추가 (main.py에서 데이터를 전달받아야 함) ---

    def display_law_images(self, law_full_name, data_dir, image_list):
        """현재 법률에 연결된 이미지 파일 목록을 별도의 창에 표시합니다."""
        
        if not image_list:
            return

        # 새 창 생성
        img_window = Toplevel(self.master)
        img_window.title(f"{law_full_name} 관련 그림 파일")
        
        text_widget = scrolledtext.ScrolledText(img_window, wrap=tk.WORD, width=50, height=10)
        text_widget.pack(padx=10, pady=10, fill='both', expand=True)
        
        text_widget.insert(tk.END, "--- 해당 법률의 그림 파일 목록 ---\n\n")
        
        for idx, img_file in enumerate(image_list, 1):
            text_widget.insert(tk.END, f"{idx}. {img_file}\n")
            
            # 하이퍼링크처럼 태그 지정. 클릭 시 show_image 호출
            text_widget.tag_add(img_file, f"{text_widget.index(tk.END)}-2c linestart", f"{text_widget.index(tk.END)}-2c lineend")
            text_widget.tag_config(img_file, foreground="purple", underline=1)
            # lambda 함수를 사용하여 이미지 파일명과 data_dir을 전달
            text_widget.tag_bind(img_file, "<Button-1>", 
                                 lambda event, f=img_file, d=data_dir: self.show_image(f, d))

        text_widget.config(state=tk.DISABLED)

    def show_image(self, filename_with_subdir, data_dir):
        """특정 그림 파일을 열기 위한 준비 (Tkinter는 이미지 로드가 복잡하여 경로만 표시)"""
        
        # data_dir과 하위 폴더/파일명 결합
        image_path = os.path.join(data_dir, filename_with_subdir)
        
        if os.path.exists(image_path):
            messagebox.showinfo("그림 파일 열기", f"'{filename_with_subdir}' 파일을 열 준비가 되었습니다.\n경로: {image_path}\n(실제 이미지를 보려면 Pillow 라이브러리가 필요합니다.)")
        else:
            messagebox.showerror("오류", f"'{filename_with_subdir}' 파일을 찾을 수 없습니다.")

    def create_data_manager_window(self, current_databases, add_law_callback, delete_law_callback):
        """
        데이터 관리용 새 창을 띄우고, 관리 함수들을 사용하여 UI를 구성합니다.
        
        Args:
            current_databases (dict): 현재 설정된 법률 목록 {전체 이름: 약어}.
            add_law_callback (function): 새 법률을 추가하는 main.py의 함수.
            delete_law_callback (function): 법률을 삭제하는 main.py의 함수.
        """
        manager_window = Toplevel(self.master)
        manager_window.title("법률 데이터 관리")
        manager_window.geometry("600x400")
        
        # 1. 상단 라벨
        ttk.Label(manager_window, text="법률 목록 관리", font=('Helvetica', 14, 'bold')).pack(pady=10)
        
        main_frame = ttk.Frame(manager_window, padding=10)
        main_frame.pack(fill='both', expand=True)

        # 2. 법률 목록 표시
        list_label = ttk.Label(main_frame, text="현재 등록된 법률:")
        list_label.pack(anchor='w', pady=(0, 5))
        
        # Listbox로 법률 목록 표시
        self.law_listbox = tk.Listbox(main_frame, height=10)
        self.law_listbox.pack(fill='x', padx=5, pady=5)
        
        for full_name in current_databases.keys():
            self.law_listbox.insert(tk.END, full_name)
            
        # 3. 버튼 프레임 (추가/삭제)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)

        # 법률 추가 버튼 (클릭 시 새 창 또는 입력 필드 표시)
        ttk.Button(button_frame, text="법률 추가", 
                   command=lambda: self._show_add_law_dialog(manager_window, add_law_callback)).pack(side='left', padx=5)

        # 법률 삭제 버튼
        ttk.Button(button_frame, text="선택된 법률 삭제", 
                   command=lambda: self._delete_selected_law(delete_law_callback, current_databases)).pack(side='left', padx=5)


    def _show_add_law_dialog(self, parent_window, add_law_callback):
        """새 법률 정보를 입력받는 작은 창을 띄웁니다."""
        
        dialog = Toplevel(parent_window)
        dialog.title("새 법률 추가")
        dialog.geometry("300x250")
        
        fields = [
            ("전체 이름 (예: 법인세법)", "full_name"),
            ("약어 (예: corp_tax)", "abbr")
        ]
        
        entries = {}
        for i, (label_text, key) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(dialog)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew')
            entries[key] = entry

        # 이미지 유무 체크박스
        has_image_var = tk.BooleanVar()
        ttk.Checkbutton(dialog, text="관련 그림 파일 존재", variable=has_image_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        def submit():
            full_name = entries['full_name'].get().strip()
            abbr = entries['abbr'].get().strip()
            has_image = has_image_var.get()

            if not full_name or not abbr:
                messagebox.showerror("오류", "전체 이름과 약어를 입력해야 합니다.")
                return

            if add_law_callback(full_name, abbr, has_image):
                # 성공 시 목록 업데이트 및 창 닫기
                self.law_listbox.insert(tk.END, full_name)
                dialog.destroy()

        ttk.Button(dialog, text="추가", command=submit).grid(row=3, column=0, columnspan=2, pady=10)
        dialog.grid_columnconfigure(1, weight=1)
        
        
    def _delete_selected_law(self, delete_law_callback, current_databases):
        """선택된 법률을 삭제하는 함수."""
        selected_indices = self.law_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("경고", "삭제할 법률을 목록에서 선택하세요.")
            return

        selected_index = selected_indices[0]
        full_name_to_delete = self.law_listbox.get(selected_index)

        if messagebox.askyesno("삭제 확인", f"'{full_name_to_delete}'를 정말 삭제하시겠습니까?"):
            if delete_law_callback(full_name_to_delete):
                # 성공 시 UI 목록 업데이트
                self.law_listbox.delete(selected_index)
                # Note: 실제 config_manager의 데이터 구조가 main.py에서 업데이트되므로, 
                # 여기서는 단순히 UI만 업데이트합니다.
                messagebox.showinfo("완료", f"'{full_name_to_delete}'가 삭제되었습니다.")
            # 실패 메시지는 delete_law_callback 내부에서 처리됩니다.
    
    # 텍스트 창 생성 시 커서 설정 추가 (선택 사항)
    def _create_text_pane(self, parent, title, column):
        frame = ttk.Frame(parent, borderwidth=2, relief="groove")
        frame.grid(row=0, column=column, sticky="nsew", padx=5, pady=5)
        ttk.Label(frame, text=title, font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        vscroll = ttk.Scrollbar(frame)
        # state는 나중에 조절하므로 초기생성시는 기본값
        text_widget = tk.Text(frame, wrap='word', yscrollcommand=vscroll.set) 
        vscroll.config(command=text_widget.yview)
        vscroll.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)
        
        # 링크 태그 스타일 미리 정의 (파란색, 밑줄, 손가락 커서)
        text_widget.tag_config("hyperlink", foreground="blue", underline=1)
        # 마우스가 올라가면 손가락 모양, 나가면 화살표 (Tkinter 기본 기능 활용)
        text_widget.tag_bind("hyperlink", "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind("hyperlink", "<Leave>", lambda e: text_widget.config(cursor="arrow"))
        
        return text_widget

    def display_main_law(self, article_data, analyzer, current_law_full_name, link_click_callback):
        """
        창 1에 법률 내용을 표시하고, 하이퍼링크를 생성합니다.
        Analyzer와 Callback을 여기서 직접 사용합니다.
        """
        self.pane1.config(state=tk.NORMAL)
        self.pane1.delete('1.0', tk.END)
        
        for title, content in article_data.items():
            # 1. 조문 제목 삽입
            self.pane1.insert(tk.END, f"--- {title} ---\n", 'article_title')
            self.pane1.tag_config('article_title', font=('Helvetica', 10, 'bold'), background='#E0E0E0')
            
            # 2. 조문 내용 시작 위치 기록
            start_mark = self.pane1.index(tk.END)
            self.pane1.insert(tk.END, content + "\n\n")
            
            # 3. 링크 분석 및 태그 적용
            links = analyzer.extract_links(content, current_law_full_name)
            
            for link in links:
                # 텍스트 위젯 내의 절대 인덱스 계산
                # start_mark(예: "3.0")에서 +N글자 이동한 위치 계산
                s_idx = f"{start_mark} + {link['start']} chars"
                e_idx = f"{start_mark} + {link['end']} chars"
                
                # 고유 태그 이름 생성 (이벤트 바인딩용)
                tag_name = f"link_{title}_{link['start']}"
                
                # 태그 추가 (시각 효과 + 이벤트용)
                self.pane1.tag_add("hyperlink", s_idx, e_idx) # 파란색 스타일
                self.pane1.tag_add(tag_name, s_idx, e_idx)    # 개별 클릭 이벤트
                
                # 클릭 이벤트 바인딩 (대상 법률과 조문을 콜백으로 전달)
                # 주의: lambda의 late binding 문제를 피하기 위해 기본값 인자 사용
                self.pane1.tag_bind(tag_name, "<Button-1>", 
                    lambda event, la=link['law_abbr'], art=link['article']: link_click_callback(la, art))

        self.pane1.config(state=tk.DISABLED)
        
    # 창 2, 3 업데이트용 함수 (링크 기능 포함)
    def update_pane_with_link(self, pane_num, header, content, analyzer, law_full_name, link_click_callback):
        target_pane = self.pane2 if pane_num == 2 else self.pane3
        
        target_pane.config(state=tk.NORMAL)
        target_pane.delete('1.0', tk.END)
        target_pane.insert(tk.END, header + "\n\n", 'header')
        target_pane.tag_config('header', font=('Helvetica', 10, 'italic'), foreground='red')
        
        # 내용이 없으면 종료
        if not content:
             target_pane.config(state=tk.DISABLED)
             return

        # 내용 삽입 위치 기록
        start_mark = target_pane.index(tk.END)
        target_pane.insert(tk.END, content)
        
        # 링크 분석 및 태그 (위와 동일한 로직)
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

    # 스크롤 이동 기능 (중요!)
    def scroll_to_article(self, pane_num, article_title):
        target_pane = self.pane2 if pane_num == 2 else self.pane3
        
        # 텍스트 위젯에서 조문 제목 검색
        search_res = target_pane.search(article_title, "1.0", stopindex=tk.END)
        if search_res:
            # 해당 위치가 보이도록 스크롤 이동
            target_pane.see(search_res)
            # 하이라이트 (선택사항)
            line_end = f"{search_res} lineend"
            target_pane.tag_add("highlight", search_res, line_end)
            target_pane.tag_config("highlight", background="yellow")