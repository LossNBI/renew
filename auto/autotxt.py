import os
import shutil
import win32com.client as win32
from bs4 import BeautifulSoup

def hwp_to_text_with_images(hwp_path, output_folder, image_prefix="cor_law_pres"):
    """
    hwp_path: 원본 한글 파일 경로 (반드시 .hwp 파일이어야 함)
    output_folder: 결과물이 저장될 폴더
    image_prefix: 저장될 이미지 파일의 접두사
    """
    
    # 1. 경로 설정 및 폴더 생성
    hwp_path = os.path.abspath(hwp_path)
    output_folder = os.path.abspath(output_folder)
    
    # 파일이 실제로 존재하는지 체크
    if not os.path.isfile(hwp_path):
        print(f"오류: 입력 경로가 파일이 아닙니다. 경로를 확인해주세요: {hwp_path}")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    # 임시 HTML 파일 경로
    temp_html_path = os.path.join(output_folder, "temp_export.html")

    # 2. 한글 프로그램 실행 및 파일 열기
    print("한글 프로그램을 실행 중입니다...")
    try:
        hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule") # 보안 팝업 승인
    except Exception as e:
        print(f"오류: 한글 프로그램을 실행할 수 없습니다. {e}")
        return

    try:
        hwp.Open(hwp_path)
        # 3. HTML로 저장
        hwp.SaveAs(temp_html_path, "HTML") 
        hwp.Quit()
        print("HTML 변환 완료. 데이터 추출을 시작합니다...")
    except Exception as e:
        print(f"파일 변환 중 오류 발생: {e}")
        hwp.Quit()
        return

    # 4. HTML 파싱하여 텍스트 및 이미지 처리
    files_dir_name = "temp_export.files" 
    files_dir_path = os.path.join(output_folder, files_dir_name)
    
    if not os.path.exists(files_dir_path):
        files_dir_name = "temp_export_files"
        files_dir_path = os.path.join(output_folder, files_dir_name)

    # === [수정 포인트 1] 인코딩을 cp949로 변경 (안전하게 try-except 사용) ===
    soup = None
    try:
        with open(temp_html_path, "r", encoding="cp949") as f:
            soup = BeautifulSoup(f, "html.parser")
    except UnicodeDecodeError:
        # 혹시 utf-8로 저장된 경우를 대비한 예외 처리
        with open(temp_html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    # ===================================================================

    final_text_lines = []
    img_counter = 1

    # 본문 내용을 순서대로 탐색
    if soup and soup.body:
        for element in soup.body.descendants:
            if element.name == 'img':
                # 이미지 태그 발견 시
                original_img_name = element.get('src')
                # src가 없는 경우 패스
                if not original_img_name:
                    continue
                    
                ext = os.path.splitext(original_img_name)[1]
                
                # 새 이미지 이름 생성
                new_img_name = f"{image_prefix}_{img_counter:02d}{ext}"
                new_img_path = os.path.join(output_folder, new_img_name)
                
                # HTML 내 src는 보통 상대경로이므로 파일명만 추출해서 결합
                original_img_filename = os.path.basename(original_img_name)
                original_img_full_path = os.path.join(files_dir_path, original_img_filename)
                
                if os.path.exists(original_img_full_path):
                    # 파일 이동 (덮어쓰기 허용을 위해 move 대신 copy 후 remove 추천하거나 shutil.move 사용)
                    # 여기서는 안전하게 복사 후 삭제 방식 사용 (shutil.move는 타겟 존재시 에러날 수 있음)
                    shutil.move(original_img_full_path, new_img_path)
                    
                    # 텍스트 리스트에 태그 추가
                    tag_string = f"[IMAGE: {new_img_name}]"
                    final_text_lines.append(tag_string)
                    img_counter += 1
                else:
                    # 가끔 경로는 있는데 파일이 없는 경우가 있어 경고만 출력
                    pass

            elif element.name is None and element.strip():
                # 텍스트 노드인 경우
                text_content = element.strip()
                if not final_text_lines or text_content != final_text_lines[-1]: 
                    final_text_lines.append(text_content)

    # 5. 결과 텍스트 파일 저장
    txt_output_path = os.path.join(output_folder, "cor_law_pres.txt")
    
    # 결과물은 범용성을 위해 utf-8로 저장하는 것을 추천하지만, 
    # 기존 코드대로 cp949를 원하시면 encoding="cp949"로 유지하세요.
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(final_text_lines))

    # 6. 임시 파일 삭제
    try:
        os.remove(temp_html_path)
        if os.path.exists(files_dir_path):
            shutil.rmtree(files_dir_path)
    except:
        pass

    print(f"\n작업 완료!")
    print(f"텍스트 파일: {txt_output_path}")
    print(f"이미지 저장 폴더: {output_folder}")

# --- 실행 설정 ---
if __name__ == "__main__":
    # === [수정 포인트 2] 파일 경로를 구체적인 파일명까지 적어주세요 ===
    # 예: r"D:\code\renew\auto\test.hwp"
    input_hwp = r"D:\code\renew\auto\cor_law_pres.hwp"  
    
    output_dir = r"D:\code\renew\auto\output" 
    user_prefix = "cor_law_pres"
    
    hwp_to_text_with_images(input_hwp, output_dir, user_prefix)