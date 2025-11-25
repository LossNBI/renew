# data_manager.py

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

        # 메모리 캐시 (파싱된 데이터 저장)
        self.parsed_cache = {} 
        self.reference_map = {} # { "법제5조": [ {type:'pres', content:...}, ... ] }

    def _load_config(self):
        if not os.path.exists(self.config_file):
            return {"DATA_DIR": "data", "DATABASES": {}, "IMAGE_FOLDERS": {}}
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def add_law(self, name, code, file_path=None):
        # (이전과 동일)
        if name in self.config["DATABASES"]: return False, "이미 존재"
        self.config["DATABASES"][name] = code
        dest = os.path.join(self.data_dir, f"{code}.txt")
        if file_path: shutil.copy2(file_path, dest)
        else:
            with open(dest, 'w', encoding='utf-8') as f: f.write("내용 없음")
        self._save_config()
        return True, "완료"

    # --- [핵심] 텍스트 파싱 및 구조화 ---
    def parse_text(self, text):
        lines = text.split('\n')
        parsed = []
        curr_chap = ""
        curr_title = ""
        curr_lines = []
        
        re_chap = re.compile(r'^제\d+장\s')
        re_art = re.compile(r'^(제\d+(?:의\d+)?조)') # 제5조, 제5조의2 추출

        for line in lines:
            line = line.strip()
            if not line: continue
            
            if re_chap.match(line):
                curr_chap = line
            elif re_art.match(line):
                # 저장
                if curr_title:
                    content = '\n'.join(curr_lines)
                    art_num = re_art.match(curr_title).group(1) # "제5조" 추출
                    parsed.append({'chapter': curr_chap, 'article_key': art_num, 'title': curr_title, 'content': content})
                
                curr_title = line
                curr_lines = []
            else:
                if curr_title: curr_lines.append(line)
        
        if curr_title:
            content = '\n'.join(curr_lines)
            art_num = re_art.match(curr_title).group(1)
            parsed.append({'chapter': curr_chap, 'article_key': art_num, 'title': curr_title, 'content': content})
            
        return parsed

    def get_parsed_data(self, law_name):
        # 1. 메인 법 로드
        code = self.config["DATABASES"].get(law_name)
        if not code: return []
        
        path = os.path.join(self.data_dir, f"{code}.txt")
        if not os.path.exists(path): return []

        with open(path, 'r', encoding='utf-8') as f:
            main_text = f.read()
        
        main_data = self.parse_text(main_text)

        # 2. 관련 법령 로드 (시행령, 시행규칙)
        # 파일명이 고정되어 있다고 가정하거나 설정에서 가져옴 (여기선 예시로 고정)
        pres_path = os.path.join(self.data_dir, f"{code}_pres.txt")
        rule_path = os.path.join(self.data_dir, f"{code}_rule.txt")

        pres_data = []
        if os.path.exists(pres_path):
            with open(pres_path, 'r', encoding='utf-8') as f:
                pres_data = self.parse_text(f.read())

        rule_data = []
        if os.path.exists(rule_path):
            with open(rule_path, 'r', encoding='utf-8') as f:
                rule_data = self.parse_text(f.read())

        # 3. 참조 맵핑 (Cross-Reference Indexing)
        self.build_reference_map(main_data, pres_data, rule_data)
        
        return main_data

    def build_reference_map(self, main, pres, rule):
        self.reference_map = {}
        
        # 정규식: "법 제OO조" 찾기
        re_ref_law = re.compile(r'법\s?(제\d+(?:의\d+)?조)') 

        # (1) 시행령(Pres) -> 법
        for p in pres:
            # 본문이나 제목에서 "법 제X조" 가 나오는지 확인
            matches = re_ref_law.findall(p['content']) + re_ref_law.findall(p['title'])
            for m in matches: # m = "제5조"
                if m not in self.reference_map: self.reference_map[m] = []
                self.reference_map[m].append({'type': 'I. 시행령', 'data': p})

        # (2) 시행규칙(Rule) -> 법
        for r in rule:
            matches = re_ref_law.findall(r['content']) + re_ref_law.findall(r['title'])
            for m in matches:
                if m not in self.reference_map: self.reference_map[m] = []
                self.reference_map[m].append({'type': 'II. 시행규칙', 'data': r})

        # (3) 법 -> 법 (동일 법 내 참조)
        # 예: "제4조제2호" -> "제4조"를 찾아야 함
        re_self_ref = re.compile(r'(제\d+(?:의\d+)?조)') # "제4조"
        
        # 메인 법 데이터를 딕셔너리로 변환 (빠른 검색용)
        main_dict = {m['article_key']: m for m in main}

        for m in main:
            target_key = m['article_key'] # 현재 보고 있는 조 (예: 제5조)
            
            # 본문에서 다른 조항 언급 찾기
            refs = re_self_ref.findall(m['content'])
            unique_refs = sorted(list(set(refs)))
            
            for ref in unique_refs:
                if ref == target_key: continue # 자기 자신 제외
                if ref in main_dict:
                    if target_key not in self.reference_map: self.reference_map[target_key] = []
                    # 중복 방지 체크 후 추가
                    exists = any(x['data']['article_key'] == ref for x in self.reference_map[target_key])
                    if not exists:
                        self.reference_map[target_key].append({'type': 'III. 관련 조항', 'data': main_dict[ref]})

    def get_related_articles(self, article_key):
        """ 제5조를 주면 -> 시행령, 시행규칙, 참조조항 리스트 반환 """
        return self.reference_map.get(article_key, [])