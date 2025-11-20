# law_analyzer.py

import re
import config_manager

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
            
            # 매칭은 되었으나 내용이 비어있는 경우 건너뜀 (안전장치)
            if not article_ref_full and not law_name_ref:
                continue

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
    
    # (기존 find_reference는 사용하지 않게 되지만 호환성을 위해 남겨둘 수 있음)
    def find_reference(self, text, current_law_full_name=None):
        links = self.extract_links(text, current_law_full_name)
        if links:
            return links[0]['law_abbr'], links[0]['article']
        return None, None