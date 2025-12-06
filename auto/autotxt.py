import os
import shutil
import win32com.client as win32
from bs4 import BeautifulSoup
from urllib.parse import unquote
import tkinter as tk
from tkinter import filedialog, messagebox
import threading


def hwp_to_text_with_images(hwp_path, output_folder, image_prefix, log_callback=None):

    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    # 1. 경로 확인
    hwp_path = os.path.abspath(hwp_path)
    output_folder = os.path.abspath(output_folder)

    if not os.path.isfile(hwp_path):
        log(f"❌ 파일을 찾을 수 없습니다: {hwp_path}")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    temp_html_path = os.path.join(output_folder, "temp_export.html")

    # 2. 한글 실행 → HTML 변환
    log(f"🚀 변환 시작: {os.path.basename(hwp_path)}")
    try:
        hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        hwp.Open(hwp_path)
        hwp.SaveAs(temp_html_path, "HTML")
        hwp.Quit()
    except Exception as e:
        log(f"❌ 한글 오류: {e}")
        return

    # 3. HTML 파싱
    soup = None
    for enc in ["cp949", "utf-8"]:
        try:
            with open(temp_html_path, "r", encoding=enc) as f:
                try:
                    soup = BeautifulSoup(f, "lxml")
                except:
                    soup = BeautifulSoup(f, "html.parser")
            log(f"✔ HTML 파싱 성공 (인코딩 {enc})")
            break
        except:
            continue

    if soup is None:
        log("❌ HTML 파일 파싱 실패")
        return

    # 4. 이미지 폴더 찾기
    files_dir_1 = os.path.join(output_folder, "temp_export.files")
    files_dir_2 = os.path.join(output_folder, "temp_export_files")

    if os.path.exists(files_dir_1):
        files_dir = files_dir_1
    elif os.path.exists(files_dir_2):
        files_dir = files_dir_2
    else:
        files_dir = output_folder
        log("ℹ️ 이미지 별도 폴더 없음 → 현재 폴더 사용")

    log(f"📂 이미지 폴더: {files_dir}")

    # 5. 본문 + 이미지 추출
    final_lines = []
    img_counter = 1
    
    # [수정 1] 삭제할 원본 파일 목록을 담을 리스트 생성
    processed_original_files = [] 

    log("📸 이미지 추출 중...")

    if soup.body:
        for node in soup.body.descendants:

            # 이미지 태그
            if node.name:
                tag = node.name.lower()
                src = None

                if tag == "img":
                    src = node.get("src")
                elif tag == "v:imagedata":
                    src = node.get("src")

                if src:
                    src = unquote(src)
                    original_name = os.path.basename(src)
                    original_path = os.path.join(files_dir, original_name)

                    if os.path.exists(original_path):
                        ext = os.path.splitext(original_name)[1]
                        if not ext:
                            ext = ".png"

                        new_name = f"{image_prefix}_{img_counter:02d}{ext}"
                        new_path = os.path.join(output_folder, new_name)

                        # 복사 수행
                        shutil.copy2(original_path, new_path)
                        
                        # [수정 2] 원본 경로를 삭제 목록에 추가
                        processed_original_files.append(original_path)

                        log(f"  → 이미지 변환: {original_name} → {new_name}")
                        final_lines.append(f"[IMAGE: {new_name}]")

                        img_counter += 1

                    continue

            # 일반 텍스트
            if node.name is None and str(node).strip():
                text = str(node).strip()
                final_lines.append(text)

    # 6. txt 저장
    txt_path = os.path.join(output_folder, f"{image_prefix}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_lines))

    # 7. 임시 파일 및 원본 이미지 삭제 (정리 단계)
    try:
        # 임시 HTML 파일 삭제
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

        # [수정 3] 이미지 원본 삭제 로직 강화
        if files_dir != output_folder and os.path.exists(files_dir):
            # 이미지가 별도 하위 폴더(temp_export.files)에 있는 경우 폴더 통째로 삭제
            shutil.rmtree(files_dir)
        elif files_dir == output_folder:
            # 이미지가 저장 폴더와 같은 곳에 풀린 경우 -> 기록해둔 원본 파일만 골라서 삭제
            # set()을 사용하여 중복된 파일 경로(동일 이미지가 여러 번 쓰인 경우) 제거
            for old_path in set(processed_original_files):
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as del_err:
                        log(f"⚠️ 삭제 실패: {old_path} ({del_err})")
                        
    except Exception as e:
        log(f"⚠️ 정리 중 오류 발생: {e}")

    log("✔ 변환 완료!")
    log(f"📝 텍스트 파일: {txt_path}")
    log(f"🖼 추출된 이미지 개수: {img_counter - 1}")


###########################################
#             GUI 시작
###########################################

class App:
    def __init__(self, root):
        self.root = root
        root.title("HWP → 텍스트 + 이미지 추출기")

        self.root.geometry("500x450")

        # 파일 선택
        tk.Label(root, text="한글 파일 선택 (.hwp)").pack()
        self.hwp_entry = tk.Entry(root, width=50)
        self.hwp_entry.pack()
        tk.Button(root, text="찾기", command=self.select_hwp).pack()

        # 저장 폴더
        tk.Label(root, text="저장 폴더 선택").pack()
        self.dir_entry = tk.Entry(root, width=50)
        self.dir_entry.pack()
        tk.Button(root, text="찾기", command=self.select_folder).pack()

        # 이미지 접두사
        tk.Label(root, text="이미지 파일명 접두사").pack()
        self.prefix_entry = tk.Entry(root, width=30)
        self.prefix_entry.insert(0, "output")
        self.prefix_entry.pack()

        # 실행 버튼
        tk.Button(root, text="변환 실행", command=self.run_convert).pack(pady=10)

        # 로그창
        self.log_box = tk.Text(root, height=12, width=60)
        self.log_box.pack()

    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)

    def select_hwp(self):
        file_path = filedialog.askopenfilename(filetypes=[("HWP files", "*.hwp")])
        if file_path:
            self.hwp_entry.delete(0, tk.END)
            self.hwp_entry.insert(0, file_path)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, folder)

    def run_convert(self):
        hwp_path = self.hwp_entry.get()
        output_folder = self.dir_entry.get()
        prefix = self.prefix_entry.get()

        if not hwp_path or not output_folder:
            messagebox.showerror("오류", "파일과 저장 폴더를 선택하세요.")
            return

        # 스레드로 실행 → GUI 프리징 방지
        threading.Thread(
            target=hwp_to_text_with_images,
            args=(hwp_path, output_folder, prefix, self.log),
            daemon=True
        ).start()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()