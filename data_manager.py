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

    # --- [수정 1] 중복 방지 및 내용 통합 파싱 ---
    def parse_text(self, text):
        lines = text.split('\n')
        
        # 리스트 대신 딕셔너리로 관리 (키: '제1조' -> 값: 데이터)
        parsed_dict = {} 
        
        curr_chap = ""
        curr_title = ""
        curr_lines = []
        
        re_chap = re.compile(r'^제\d+장\s')
        re_art = re.compile(r'^(제\d+(?:의\s*\d+)?조)')

        def save_buffer(chapter, title, lines):
            if not title: return
            raw_art_str = re_art.match(title).group(1)
            art_num = raw_art_str.replace(" ", "")
            content = '\n'.join(lines)
            
            # [핵심] 이미 존재하는 조항이면 내용 이어붙이기 (중복 제거)
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
                # 새로운 조 시작 전, 이전 내용 저장
                save_buffer(curr_chap, curr_title, curr_lines)
                
                curr_title = line
                curr_lines = []
            else:
                if curr_title: curr_lines.append(line)
        
        # 마지막 항목 저장
        save_buffer(curr_chap, curr_title, curr_lines)
        
        # 딕셔너리를 리스트로 변환 (순서 유지를 위해 article_key 숫자 기준 정렬 추천하지만, 파일 순서대로)
        # 파이썬 3.7+ 에서는 딕셔너리 입력 순서가 유지되므로 그대로 변환
        return list(parsed_dict.values())

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

    # --- [수정 2] 다른 법령 추출 헬퍼 함수 ---
    def _extract_external_article(self, law_code, target_article):
        """ 다른 법 파일(code)을 열어서 target_article(제5조) 내용을 가져옴 """
        path = os.path.join(self.data_dir, f"{law_code}.txt")
        if not os.path.exists(path): return None
        
        # 파일 전체를 다 파싱하면 느리므로, 간단하게 찾기
        # 하지만 정확성을 위해 parse_text 로직을 재사용하는 것이 안전함
        with open(path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        # 파싱 (메모리 낭비가 걱정되면 캐싱 기능 추가 가능)
        parsed = self.parse_text(full_text)
        for p in parsed:
            if p['article_key'] == target_article:
                return p
        return None

    def build_reference_map(self, main, pres, rule, current_law_name):
        self.reference_map = {}
        
        # 1. 역참조 (시행령/규칙 -> 법) : 기존 로직 강화
        # "법 제O조... 에 따른"
        
        keywords = [r"에\s*따른", r"에\s*따라", r"의\s*규정에\s*의한", r"의\s*규정에\s*의하여", r"에서", r"단서에\s*따른"]
        kw_pattern = "|".join(keywords)
        prefix_pattern = fr"(?:{re.escape(current_law_name)}|이\s*법|법)"
        article_core = r"(제\d+조(?:의\s?\d+)?)"
        
        # 정규식: (법) (제5조) ... (에 따른)
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

        # 2. 관련 조항 (법 본문 -> 같은 법 OR 다른 법)
        # 정규식: (소득세법)? (제5조)
        # 그룹1: 법 이름 (없으면 같은 법)
        # 그룹2: 조항 번호
        
        # 사용 가능한 법 DB 이름들을 정규식으로 만듦 (정확한 매칭 위해)
        db_names = list(self.config['DATABASES'].keys())
        # "이 법", "법" 도 포함
        law_names_pattern = "|".join([re.escape(n) for n in db_names] + [r"이\s*법", r"법"])
        
        # 패턴: (법이름 혹은 공백) + (제N조)
        re_ref_generic = re.compile(fr"({law_names_pattern})?\s*(제\d+조(?:의\s?\d+)?)")
        
        # 빠른 검색을 위한 메인 데이터 맵
        main_dict = {m['article_key']: m for m in main}

        for m in main:
            target_key = m['article_key'] # 현재 보고 있는 조항 (제1조)
            
            # 본문에서 모든 "제~조" 찾기
            matches = re_ref_generic.findall(m['content'])
            # matches 예: [('소득세법', '제5조'), ('', '제3조'), ('이 법', '제2조')]
            
            seen_refs = set() # 한 조항 내에서 중복 방지

            for law_name, art_num in matches:
                art_num_clean = art_num.replace(" ", "")
                law_name = law_name.strip().replace(" ", "") # 공백제거 ("이 법" -> "이법")

                # (1) 같은 법 참조
                if not law_name or law_name in ["법", "이법", current_law_name.replace(" ", "")]:
                    if art_num_clean == target_key: continue # 자기 자신 제외
                    
                    full_ref_key = f"same_{art_num_clean}" # 중복 체크용 키
                    if full_ref_key in seen_refs: continue
                    seen_refs.add(full_ref_key)

                    if art_num_clean in main_dict:
                        if target_key not in self.reference_map: self.reference_map[target_key] = []
                        
                        # 이미 리스트에 있는지 확인
                        exists = any(x['data']['article_key'] == art_num_clean and x['type'] == 'III. 관련 조항' 
                                     for x in self.reference_map[target_key])
                        if not exists:
                            self.reference_map[target_key].append({
                                'type': 'III. 관련 조항', 
                                'data': main_dict[art_num_clean]
                            })
                
                # (2) 다른 법 참조 (config에 등록된 법인 경우)
                else:
                    # config의 DATABASES 키 중 law_name과 일치하는게 있는지 확인
                    # law_name이 "소득세법" 이면 DB 키 "소득세법"을 찾음
                    if law_name in self.config["DATABASES"]:
                        law_code = self.config["DATABASES"][law_name]
                        
                        full_ref_key = f"{law_code}_{art_num_clean}"
                        if full_ref_key in seen_refs: continue
                        seen_refs.add(full_ref_key)

                        # 외부 파일에서 해당 조항 추출
                        ext_data = self._extract_external_article(law_code, art_num_clean)
                        if ext_data:
                            if target_key not in self.reference_map: self.reference_map[target_key] = []
                            
                            # 제목을 "소득세법 제5조" 처럼 변경해서 표시
                            ext_data_copy = ext_data.copy()
                            ext_data_copy['title'] = f"[{law_name}] {ext_data['title']}"
                            
                            self.reference_map[target_key].append({
                                'type': 'IV. 타법 참조', 
                                'data': ext_data_copy
                            })

    def get_related_articles(self, article_key):
        return self.reference_map.get(article_key, [])