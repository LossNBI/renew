# law_analyzer.py

import re
# import config_manager # main.py에서 주입받으므로 제거 가능하거나 유지

class LawAnalyzer:
    def __init__(self, parser, config_manager_instance):
        self.parser = parser
        self.config_manager = config_manager_instance
        
        # 법률 이름 목록 가져오기
        law_names = '|'.join(re.escape(name) for name in self.config_manager.get_databases().keys())

        # 정규식: 그룹을 나눠서 정확히 매칭
        self.ref_pattern = re.compile(
            rf'(?:「({law_names})」\s*)?'  # 그룹 1: 외부 법률명
            rf'(이\s*법)?\s*'              # 그룹 2: 이 법
            rf'(제\d+조(?:\s*의\s*\d+)?(?:제\d+항)?(?:제\d+호)?)', # 그룹 3: 조문 번호
            re.MULTILINE
        )
    
    def extract_links(self, text, current_law_full_name):
        """텍스트 내의 모든 참조 링크 정보를 리스트로 반환합니다."""
        links = []
        
        # finditer를 사용하여 모든 매칭되는 링크를 찾습니다.
        for match in self.ref_pattern.finditer(text):
            law_name_ref = match.group(1)
            is_this_law = match.group(2)
            article_ref_full = match.group(3)
            
            target_law_abbr = None
            
            # 1. 외부 법률 참조
            if law_name_ref:
                target_law_abbr = self.config_manager.get_databases().get(law_name_ref)
            # 2. 내부 참조 ('이 법' 또는 법률명 생략)
            elif is_this_law or (law_name_ref is None and current_law_full_name):
                target_law_abbr = self.config_manager.get_databases().get(current_law_full_name)

            # 조문 제목 추출 ('제O조' 형식까지만 추출)
            article_title_match = re.search(r'(제\d+조(?:\s*의\s*\d+)?)', article_ref_full)
            target_article = article_title_match.group(1) if article_title_match else None
            
            if target_law_abbr and target_article:
                # (시작인덱스, 끝인덱스, 대상법률약어, 대상조문)
                links.append({
                    "start": match.start(),
                    "end": match.end(),
                    "law_abbr": target_law_abbr,
                    "article": target_article
                })
                
        return links