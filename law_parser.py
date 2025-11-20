# law_parser.py (수정 버전)

import re
import os
from collections import defaultdict
import config_manager

class LawParser:
    # 수정: 'parser' 인자를 제거하고 'config_manager_instance'만 받습니다.
    def __init__(self, config_manager_instance): 
        # self.parser = parser # <--- 이 라인도 삭제해야 합니다.
        self.config_manager = config_manager_instance 
        
        # 이제 config_manager를 사용하여 DATABASES에 접근합니다.
        # 이 law_names 변수는 LawParser에서는 사용되지 않지만, LawAnalyzer와 코드를 혼동하여 남긴 것으로 보입니다.
        # LawParser에서 사용되지 않으므로 제거하거나 그대로 두셔도 됩니다.
        law_names = '|'.join(re.escape(name) for name in self.config_manager.get_databases().keys()) 
        
        self.data_dir = self.config_manager.get_data_dir()
        self.law_abbr_map = self.config_manager.get_databases()
        self.image_folder_map = self.config_manager.get_image_folders()
        
        self.laws = defaultdict(dict) 
        self.check_data_directory()
    
    # --- 1. 누락된 메서드 추가 ---
    def check_data_directory(self):
        """'data' 디렉터리 존재 여부를 확인하고 없으면 생성합니다."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"'{self.data_dir}' 폴더가 생성되었습니다. 법률 파일을 넣어주세요.")

    def get_available_laws(self):
        """config에 정의된 법률 목록 (전체 이름)을 반환합니다."""
        return list(self.law_abbr_map.keys())

    def get_law_abbr(self, full_name):
        """법률 전체 이름으로 약어를 찾습니다."""
        return self.law_abbr_map.get(full_name)

    def load_law(self, full_name):
        """법률 전체 이름으로 파일을 로드하고 파싱합니다."""
        law_abbr = self.get_law_abbr(full_name)
        if not law_abbr:
             return False
             
        if law_abbr in self.laws:
            return True

        file_path = os.path.join(self.data_dir, f"{law_abbr}.txt")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return False

        # 조문 제목 및 내용 분리 정규식: 제1조(목적), 제1조의2(정의) 등을 분리
        # 그룹 1: 제O조(제목) 형식, 그룹 2: 제O조 형식 (장/절 제목 분리를 위해 사용)
        article_pattern = re.compile(
            r'\s*(제\d+조(?:\s*의\s*\d*)?\s*\(.*?\))|\s*(제\d+조\s*(?:[^\(\s]*)\s*)', 
            re.MULTILINE
        )
        
        parsed_articles = {}
        parts = re.split(article_pattern, content)
        
        current_article_title = ""
        current_content_buffer = []
        
        for part in parts:
            if not part or part.isspace():
                continue
            
            part = part.strip()
            
            # 조문 제목인 경우
            if re.fullmatch(r'제\d+조(?:\s*의\s*\d*)?\s*\(.*?\)', part) or re.fullmatch(r'제\d+조\s*(?:[^\(\s]*)\s*', part):
                # 이전 조문 내용 저장
                if current_article_title and current_content_buffer:
                    parsed_articles[current_article_title] = "\n".join(current_content_buffer)
                
                # 새 조문 제목 설정 및 버퍼 초기화
                current_article_title = part
                current_content_buffer = []
            
            # 내용인 경우 (제목으로 분류되지 않은 모든 텍스트)
            else:
                current_content_buffer.append(part)

        # 마지막 조문 내용 저장
        if current_article_title and current_content_buffer:
            parsed_articles[current_article_title] = "\n".join(current_content_buffer)

        # 3. 불필요한 임시 파싱 라인 제거
        
        # 이미지 매핑
        image_map = self._map_images_to_law(law_abbr)
        
        self.laws[law_abbr] = {
            '법률명': full_name,
            '조문': self._clean_articles(parsed_articles), 
            '이미지': image_map 
        }
        return True

    # --- 2. 중복된 함수 중 하나를 제거하고 남은 함수에 주석 추가 ---
    def _map_images_to_law(self, law_abbr):
        """법률 약어를 기준으로 관련 이미지 파일을 별도 폴더에서 찾습니다."""
        image_map = {}
        # config_manager에서 폴더 이름을 가져오거나, 기본 패턴을 사용
        image_subdir_name = self.image_folder_map.get(law_abbr, f"{law_abbr}_png")
        image_dir_path = os.path.join(self.data_dir, image_subdir_name)
        
        related_images = []

        if not os.path.exists(image_dir_path):
            return image_map

        for filename in os.listdir(image_dir_path):
            # 해당 법률 약어로 시작하는 모든 .png 파일을 찾습니다.
            if filename.startswith(f"{law_abbr}_") and filename.endswith(".png"):
                # 저장 시 하위 폴더 이름을 포함한 상대 경로로 저장
                related_images.append(os.path.join(image_subdir_name, filename))
        
        if related_images:
             image_map['ALL'] = related_images

        return image_map

    def _clean_articles(self, articles):
        """조문 내용에서 불필요한 공백을 정리하고 장/절을 조문에 포함시킵니다."""
        cleaned = {}
        current_header = ""
        
        for key, value in articles.items():
            value = value.strip()
            # 조문 제목이 아닌 경우 (장/절 제목 또는 기타 텍스트)
            if not re.match(r'제\d+조(?:\s*의\s*\d+)?', key):
                current_header += key + "\n" + value + "\n"
                continue
            
            # 조문 제목인 경우
            if current_header:
                cleaned[key] = current_header + "\n" + value
                current_header = ""
            else:
                cleaned[key] = value
        
        # 제목이 없는 장/절 처리 (파일 시작이나 끝에 있을 경우)
        if current_header:
            cleaned['기타_헤더'] = current_header

        return cleaned

    def get_article_content(self, law_abbr, article_title):
        """특정 법률의 조문 내용을 반환합니다."""
        return self.laws.get(law_abbr, {}).get('조문', {}).get(article_title, f"Error: {law_abbr}의 {article_title}을(를) 찾을 수 없습니다.")

    def get_law_titles(self, law_abbr):
        """법률의 모든 조문 제목(키)을 순서대로 반환합니다."""
        return list(self.laws.get(law_abbr, {}).get('조문', {}).keys())
        
    def get_law_images(self, law_abbr):
        """특정 법률에 매핑된 이미지 목록 (경로 포함)을 반환합니다."""
        return self.laws.get(law_abbr, {}).get('이미지', {}).get('ALL', [])