import json
import os
import shutil
import re
import sys

class LawDataManager:
    def __init__(self, config_file='config.json'):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.config_file = os.path.join(base_path, config_file)
        self.data_dir = os.path.join(base_path, "data")
        self.config = self._load_config()
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _load_config(self):
        if not os.path.exists(self.config_file):
            return {"DATA_DIR": "data", "DATABASES": {}, "IMAGE_FOLDERS": {}}
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def add_law(self, name, code, file_path=None):
        if name in self.config["DATABASES"]: return False, "이미 있는 이름입니다."
        self.config["DATABASES"][name] = code
        dest = os.path.join(self.data_dir, f"{code}.txt")
        
        if file_path:
            shutil.copy2(file_path, dest)
        else:
            if not os.path.exists(dest):
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write("제1장 총칙\n\n제1조(목적) 내용 없음")
        
        self._save_config()
        return True, "저장 완료"

    def delete_law(self, name):
        if name not in self.config["DATABASES"]: return
        code = self.config["DATABASES"].pop(name)
        path = os.path.join(self.data_dir, f"{code}.txt")
        if os.path.exists(path): os.remove(path)
        self._save_config()

    def get_parsed_data(self, law_name):
        code = self.config["DATABASES"].get(law_name)
        if not code: return []
        path = os.path.join(self.data_dir, f"{code}.txt")
        if not os.path.exists(path): return []
        
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        parsed_data = []
        curr_chapter = "제1장 총칙"
        curr_title = ""
        curr_content = []
        re_chap = re.compile(r'^제\d+장\s')
        re_art = re.compile(r'^제\d+조')

        for line in lines:
            line = line.strip()
            if not line: continue
            if re_chap.match(line):
                curr_chapter = line
            elif re_art.match(line):
                if curr_title:
                    parsed_data.append({'chapter': curr_chapter,'title': curr_title,'content': '\n'.join(curr_content)})
                curr_title = line
                curr_content = []
            else:
                if curr_title: curr_content.append(line)
        
        if curr_title:
            parsed_data.append({'chapter': curr_chapter,'title': curr_title,'content': '\n'.join(curr_content)})
            
        return parsed_data