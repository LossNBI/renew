# config_manager.py
import json
import os

CONFIG_FILE = "config.json"

class ConfigManager:
    """
    config.json 파일을 읽고 쓰는 역할을 담당하는 클래스입니다.
    """
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        """JSON 파일에서 설정을 읽어옵니다."""
        if not os.path.exists(CONFIG_FILE):
            # 파일이 없으면 기본 구조 반환 또는 오류 처리
            return {
                "DATA_DIR": "data",
                "DATABASES": {},
                "IMAGE_FOLDERS": {}
            }
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_config(self):
        """수정된 설정을 JSON 파일에 저장합니다."""
        # indent=4를 사용하여 사람이 읽기 쉬운 형태로 저장
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    # --- 데이터 접근 메서드 ---
    def get_data_dir(self):
        return self.config['DATA_DIR']

    def get_databases(self):
        return self.config['DATABASES']

    def get_image_folders(self):
        return self.config['IMAGE_FOLDERS']

    # --- 데이터 수정 메서드 (핵심 기능) ---
    def add_law(self, full_name, abbr, has_image=False):
        """새로운 법률 정보를 추가하고 저장합니다."""
        if full_name in self.config['DATABASES']:
            return False, "이미 존재하는 법률 이름입니다."
            
        self.config['DATABASES'][full_name] = abbr
        
        if has_image:
            self.config['IMAGE_FOLDERS'][abbr] = f"{abbr}_png"
            
        self._save_config()
        return True, "법률 정보가 추가되었습니다."

    def delete_law(self, full_name):
        """법률 정보를 삭제하고 저장합니다."""
        abbr = self.config['DATABASES'].pop(full_name, None)
        if abbr:
            self.config['IMAGE_FOLDERS'].pop(abbr, None)
            self._save_config()
            return True, "법률 정보가 삭제되었습니다."
        return False, "해당 법률을 찾을 수 없습니다."