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

        # 메모리 캐시
        self.parsed_cache = {} 
        self.reference_map = {} 

    def _load_config(self):
        if not os.path.exists(self.config_file):
            return {"DATA_DIR": "data", "DATABASES": {}, "IMAGE_FOLDERS": {}}
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def add_law(self, name, code, file_path=None):
        if name in self.config["DATABASES"]: return False, "이미 존재"
        self.config["DATABASES"][name] = code
        dest = os.path.join(self.data_dir, f"{code}.txt")
        if file_path: shutil.copy2(file_path, dest)
        else:
            with open(dest, 'w', encoding='utf-8') as f: f.write("내용 없음")
        self._save_config()
        return True, "완료"
    
    def delete_law(self, name):
        if name not in self.config["DATABASES"]: return
        code = self.config["DATABASES"].pop(name)
        for ext in ['.txt', '_pres.txt', '_rule.txt']:
            path = os.path.join(self.data_dir, f"{code}{ext}")
            if os.path.exists(path): os.remove(path)
        self._save_config()

    # --- [핵심 수정] 텍스트 파싱 로직 강화 ---
    def parse_text(self, text):
        lines = text.split('\n')
        parsed_dict = {} 
        
        curr_chap = ""
        curr_title = ""
        curr_lines = []
        
        re_chap = re.compile(r'^제\d+장\s')
        
        # [수정된 정규식]
        # 1. (제 \d+ 조) : "제2조" 를 먼저 찾고
        # 2. (?:\s*의\s*\d+)? : 그 뒤에 "의2" 가 붙을 수도 있고 아닐 수도 있음
        # 결과적으로 "제2조"와 "제2조의2"를 모두 정확히 잡아냅니다.
        re_art = re.compile(r'^(제\s*\d+\s*조(?:\s*의\s*\d+)?)') 

        def save_buffer(chapter, title, lines):
            if not title: return
            
            match = re_art.match(title)
            if not match: return
            
            # "제 2 조 의 2" -> "제2조의2" (공백 제거)
            raw_art_str = match.group(1)
            art_num = raw_art_str.replace(" ", "") 
            
            content = '\n'.join(lines)
            
            if art_num in parsed_dict:
                parsed_dict[art_num]['content'] += "\n\n" + content
            else:
                parsed_dict[art_num] = {
                    'chapter': chapter,
                    'article_key': art_num,
                    'title': title,
                    'content': content
                }

        for line in lines:
            line = line.strip()
            if not line: continue
            
            if re_chap.match(line):
                curr_chap = line
            elif re_art.match(line):
                save_buffer(curr_chap, curr_title, curr_lines)
                curr_title = line
                curr_lines = []
            else:
                if curr_title: curr_lines.append(line)
        
        save_buffer(curr_chap, curr_title, curr_lines)
        
        return list(parsed_dict.values())

    # --- 외부 법령 추출 헬퍼 ---
    def _extract_external_article(self, law_code, target_article):
        path = os.path.join(self.data_dir, f"{law_code}.txt")
        if not os.path.exists(path): return None
        
        with open(path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        parsed = self.parse_text(full_text)
        for p in parsed:
            # target_article(제5조)과 p['article_key'](제5조) 비교
            if p['article_key'] == target_article:
                return p
        return None

    def get_parsed_data(self, law_name):
        code = self.config["DATABASES"].get(law_name)
        if not code: return []
        
        path = os.path.join(self.data_dir, f"{code}.txt")
        if not os.path.exists(path): return []

        with open(path, 'r', encoding='utf-8') as f:
            main_text = f.read()
        
        main_data = self.parse_text(main_text)

        pres_path = os.path.join(self.data_dir, f"{code}_pres.txt")
        rule_path = os.path.join(self.data_dir, f"{code}_rule.txt")

        pres_data = []
        if os.path.exists(pres_path):
            with open(pres_path, 'r', encoding='utf-8') as f: pres_data = self.parse_text(f.read())

        rule_data = []
        if os.path.exists(rule_path):
            with open(rule_path, 'r', encoding='utf-8') as f: rule_data = self.parse_text(f.read())

        self.build_reference_map(main_data, pres_data, rule_data, law_name)
        return main_data

    def build_reference_map(self, main, pres, rule, current_law_name):
        self.reference_map = {}
        
        # 1. 역참조 키워드 정규식
        keywords = [r"에\s*따른", r"에\s*따라", r"의\s*규정에\s*의한", r"의\s*규정에\s*의하여", r"에서", r"단서에\s*따른"]
        kw_pattern = "|".join(keywords)
        prefix_pattern = fr"(?:{re.escape(current_law_name)}|이\s*법|법)"
        
        # 조항 추출 패턴 (제2조의2 등)
        article_core = r"(제\d+조(?:의\s?\d+)?)"
        
        full_regex = re.compile(fr"{prefix_pattern}\s*{article_core}(?:\s*제\d+항)?\s*(?:{kw_pattern})")

        def add_ref(source_list, ref_type):
            for item in source_list:
                text = item['title'] + " " + item['content']
                matches = full_regex.findall(text)
                for m in matches:
                    m = m.replace(" ", "")
                    if m not in self.reference_map: self.reference_map[m] = []
                    exists = any(x['data']['title'] == item['title'] for x in self.reference_map[m])
                    if not exists:
                        self.reference_map[m].append({'type': ref_type, 'data': item})

        add_ref(pres, 'I. 시행령')
        add_ref(rule, 'II. 시행규칙')

        # 2. 관련 조항 (본문 -> 타 조항)
        db_names = list(self.config['DATABASES'].keys())
        law_names_pattern = "|".join([re.escape(n) for n in db_names] + [r"이\s*법", r"법"])
        
        re_ref_generic = re.compile(fr"({law_names_pattern})?\s*(제\d+조(?:의\s?\d+)?)")
        
        main_dict = {m['article_key']: m for m in main}

        for m in main:
            target_key = m['article_key']
            matches = re_ref_generic.findall(m['content'])
            seen_refs = set()

            for law_name, art_num in matches:
                art_num_clean = art_num.replace(" ", "")
                law_name = law_name.strip().replace(" ", "")

                # 같은 법 참조
                if not law_name or law_name in ["법", "이법", current_law_name.replace(" ", "")]:
                    if art_num_clean == target_key: continue
                    full_ref_key = f"same_{art_num_clean}"
                    if full_ref_key in seen_refs: continue
                    seen_refs.add(full_ref_key)

                    if art_num_clean in main_dict:
                        if target_key not in self.reference_map: self.reference_map[target_key] = []
                        exists = any(x['data']['article_key'] == art_num_clean and x['type'] == 'III. 관련 조항' 
                                     for x in self.reference_map[target_key])
                        if not exists:
                            self.reference_map[target_key].append({'type': 'III. 관련 조항', 'data': main_dict[art_num_clean]})
                
                # 다른 법 참조
                else:
                    if law_name in self.config["DATABASES"]:
                        law_code = self.config["DATABASES"][law_name]
                        full_ref_key = f"{law_code}_{art_num_clean}"
                        if full_ref_key in seen_refs: continue
                        seen_refs.add(full_ref_key)

                        ext_data = self._extract_external_article(law_code, art_num_clean)
                        if ext_data:
                            if target_key not in self.reference_map: self.reference_map[target_key] = []
                            ext_data_copy = ext_data.copy()
                            ext_data_copy['title'] = f"[{law_name}] {ext_data['title']}"
                            self.reference_map[target_key].append({'type': 'IV. 타법 참조', 'data': ext_data_copy})

    def get_related_articles(self, article_key):
        return self.reference_map.get(article_key, [])