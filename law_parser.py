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
        if not law_abbr: return False
        if law_abbr in self.laws: return True

        file_path = os.path.join(self.data_dir, f"{law_abbr}.txt")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return False

        # ---------------------------------------------------------
        # 🌟 핵심 수정: 정규식 패턴에 '부칙'을 추가합니다.
        # 그룹 1: 제O조(제목)
        # 그룹 2: 제O조 (제목 없는 경우)
        # 그룹 3: 부칙 <...> (부칙 헤더 감지)
        # ---------------------------------------------------------
        article_pattern = re.compile(
            r'\s*(제\d+조(?:\s*의\s*\d*)?\s*\(.*?\))|'  # 그룹 1: 제1조(목적)
            r'\s*(제\d+조\s*(?:[^\(\s]*)\s*)|'          # 그룹 2: 제1조
            r'\s*(부\s*칙\s*(?:<.*?>)?)\s*',            # 그룹 3: 부칙 <개정 2024...>
            re.MULTILINE
        )
        
        parsed_articles = {}
        parts = re.split(article_pattern, content)
        
        current_title = ""
        current_content_buffer = []
        
        for part in parts:
            if not part or part.isspace(): continue
            part = part.strip()
            
            # 1. 조문 제목 또는 부칙 헤더인 경우
            if (re.fullmatch(r'제\d+조(?:\s*의\s*\d*)?\s*\(.*?\)', part) or 
                re.fullmatch(r'제\d+조\s*(?:[^\(\s]*)\s*', part) or
                part.startswith("부칙") or part.startswith("부 칙")): # 부칙 감지
                
                # 이전 내용 저장
                if current_title and current_content_buffer:
                    parsed_articles[current_title] = "\n".join(current_content_buffer)
                
                # 새 제목 설정 (부칙의 경우 구분을 명확히 하기 위해 약간 변형 가능)
                current_title = part
                current_content_buffer = []
            
            # 2. 내용인 경우
            else:
                current_content_buffer.append(part)

        # 마지막 내용 저장
        if current_title and current_content_buffer:
            parsed_articles[current_title] = "\n".join(current_content_buffer)

        image_map = self._map_images_to_law(law_abbr)
        
        self.laws[law_abbr] = {
            '법률명': full_name,
            '조문': self._clean_articles(parsed_articles), 
            '이미지': image_map 
        }
        return True

    def _clean_articles(self, articles):
        """조문 및 부칙 내용 정리"""
        cleaned = {}
        current_header = ""
        
        for key, value in articles.items():
            value = value.strip()
            
            # 조문도 아니고 부칙도 아닌 것 (장/절 제목 등)
            # 🌟 수정: '부칙'으로 시작하는 키는 헤더로 취급하지 않고 본문으로 넘깁니다.
            is_article = re.match(r'제\d+조(?:\s*의\s*\d+)?', key)
            is_addenda = key.startswith("부칙") or key.startswith("부 칙")
            
            if not is_article and not is_addenda:
                current_header += key + "\n" + value + "\n"
                continue
            
            # 조문이나 부칙인 경우
            if current_header:
                cleaned[key] = current_header + "\n" + value
                current_header = ""
            else:
                cleaned[key] = value
        
        if current_header:
            cleaned['기타_헤더'] = current_header

        return cleaned

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

    def get_article_content(self, law_abbr, article_title):
        """특정 법률의 조문 내용을 반환합니다."""
        return self.laws.get(law_abbr, {}).get('조문', {}).get(article_title, f"Error: {law_abbr}의 {article_title}을(를) 찾을 수 없습니다.")

    def get_law_titles(self, law_abbr):
        """법률의 모든 조문 제목(키)을 순서대로 반환합니다."""
        return list(self.laws.get(law_abbr, {}).get('조문', {}).keys())
        
    def get_law_images(self, law_abbr):
        """특정 법률에 매핑된 이미지 목록 (경로 포함)을 반환합니다."""
        return self.laws.get(law_abbr, {}).get('이미지', {}).get('ALL', [])