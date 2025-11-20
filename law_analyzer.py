# law_analyzer.py (수정 완료 버전)

import re
# import config # <--- config.py 대신 config_manager를 사용해야 함
import config_manager # config_manager를 임포트한다고 가정

class LawAnalyzer:
    """
    주어진 텍스트에서 다른 법률이나 조문을 참조하는 부분을 분석하는 클래스입니다.
    """
    # 🌟 수정: config_manager_instance 인자를 추가로 받도록 변경
    def __init__(self, parser, config_manager_instance):
        self.parser = parser
        self.config_manager = config_manager_instance # <--- 인스턴스 저장
        
        # config_manager에서 법률의 전체 이름을 가져와 참조 패턴을 생성
        # 🌟 수정: config.DATABASES 대신 self.config_manager.get_databases() 사용
        law_names = '|'.join(re.escape(name) for name in self.config_manager.get_databases().keys())

        # 정규식 패턴: (이하 동일)
        # 그룹 1: 법률명 (예: 법인세법)
        # 그룹 2: 이 법 (예: 이 법)
        # 그룹 3: 조항 전체 (예: 제2조제1항제1호)
        self.ref_pattern = re.compile(
            rf'(?:「({law_names})」\s*)?'
            rf'(이\s*법)?\s*'
            rf'(제\d+조(?:\s*의\s*\d+)?(?:제\d+항)?(?:제\d+호)?)',
            re.MULTILINE
        )
    
    # find_reference 함수는 self.config_manager를 사용하도록 이미 수정되어 있어야 합니다.
    def find_reference(self, text, current_law_full_name=None):
        """텍스트에서 첫 번째 참조 조문을 찾아 법률 약어와 조문 제목을 반환합니다."""
        match = self.ref_pattern.search(text)
        
        if match:
            law_name_ref = match.group(1)
            is_this_law = match.group(2)
            article_ref_full = match.group(3)
            
            ref_law_abbr = None
            
            # 1. 외부 법률 참조
            if law_name_ref:
                # 🌟 수정: config 대신 self.config_manager 사용
                ref_law_abbr = self.config_manager.get_databases().get(law_name_ref)
            
            # 2. '이 법' 또는 법률명 없이 조항만 참조
            elif is_this_law or (law_name_ref is None and current_law_full_name):
                # 🌟 수정: config 대신 self.config_manager 사용
                ref_law_abbr = self.config_manager.get_databases().get(current_law_full_name)
            
            # 조문 제목 추출 (이하 동일)
            article_title_match = re.search(r'(제\d+조(?:\s*의\s*\d+)?)', article_ref_full)
            article_title = article_title_match.group(1) if article_title_match else None
            
            if ref_law_abbr and article_title:
                return ref_law_abbr, article_title
        
        return None, None