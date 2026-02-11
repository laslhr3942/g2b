import streamlit as st
import requests
import datetime
from urllib.parse import unquote
from typing import Dict, List, Optional, Tuple
import logging

# ==================== 설정 및 주소(Endpoint) ====================
API_ENDPOINTS = {
    '입찰공고': {
        'url': 'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch',
        'param_name': 'bidNtceNm',  # 공고명
        'date_param': 'bidClseDt'   # 마감일
    },
    '사전규격': {
        # ★ 핵심 수정: 스크린샷의 정확한 주소 + 문서에서 찾은 정확한 명령어
        'url': 'https://apis.data.go.kr/1230000/ao/HrcspsSstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch',
        'param_name': 'bfSpecNm',   # 사전규격명
        'date_param': 'bfSpecRegDt' # 등록일
    }
}

API_CONFIG = {'num_rows': 30, 'page_no': 1, 'timeout': 15, 'inqryDiv': '1'}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="나라장터 용역 알리미 Pro", page_icon="📢", layout="wide")

# ==================== 유틸리티 함수 ====================
def get_api_key() -> Optional[str]:
    """Secrets에서 키 가져오기 (이름: public_api_key)"""
    try:
        return st.secrets["public_api_key"]
    except KeyError:
        st.error("🚨 Secrets 설정 오류: 'public_api_key'를 찾을 수 없습니다.")
        return None

def format_datetime(date_str: str) -> str:
    if date_str and len(date_str) == 12:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}"
    return date_str or '-'

# ==================== API 호출 및 파싱 ====================
@st.cache_data(ttl=600)
def fetch_nara_data(search_type, keyword, start_date, end_date, service_key):
    config = API_ENDPOINTS.get(search_type)
    if not config: return None

    url = config['url']
    
    # 공통 파라미터
    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': str(API_CONFIG['num_rows']), 
        'pageNo': str(API_CONFIG['page_no']),
        'inqryDiv': API_CONFIG['inqryDiv'], 
        'inqryBgnDt': start_date, 
        'inqryEndDt': end_date,
        'type': 'json'
    }
    
    # 검색어 파라미터 추가
    params[config['param_name']] = keyword
    
    try:
        response = requests.get(url, params=params, timeout=API_CONFIG['timeout'])
        
        # 디버깅용: URL과 응답 코드 출력 (성공하면 숨김)
        if response.status_code != 200:
            st.warning(f"접속 실패 ({response.status_code}): {url}")
            return None

        data = response.json()
        if 'response' in data and 'body' in data['response']:
            return {'data': data, 'url': url}
            
    except Exception as e:
        logger.error(f"오류 발생: {url} - {e}")
    
    return None

def parse_items(api_response, search_type):
    items = api_response.get('data', {}).get('response', {}).get('body', {}).get('items')
    if not items: return []
    if not isinstance(items, list): items = [items]
    
    config = API_ENDPOINTS[search_type]
    parsed_items = []
    
    # 필드명 매핑 (서비스마다 다름)
    field_map = {
        '입찰공고': {'title': 'bidNtceNm', 'org': 'dminsttNm', 'date': 'bidClseDt', 'link': 'bidNtceDtlUrl'},
        '사전규격': {'title': 'bfSpecNm', 'org': 'dminsttNm', 'date': 'bfSpecRegDt', 'link': 'bfSpecDtlUrl'}
    }
    
    mapping = field_map[search_type]
    
    for item in items:
        # 사전규격은 필드명이 다를 수 있어 예외 처리
        title = item.get(mapping['title'])
        if not title and search_type == '사전규격':
            # 혹시 bfSpecNm이 없으면 다른 이름 필드(사업명 등)를 찾아봄
            title = item.get('prdctNm') or item.get('bsnsNm') or '제목 없음'
            
        parsed_items.append({
            'title': title,
            'org': item.get(mapping['org'], '기관명 없음'),
            'date': format_datetime(item.get(mapping['date'], '')),
            'link': item.get(mapping['link'], '#'),
            'date_label': '마감일' if search_type == '입찰공고' else '등록일'
        })
    return parsed_items

# ==================== 메인 화면 ====================
def main():
    st.title("📢 나라장터 용역 정보 검색기 Pro")
    st.markdown("입찰공고와 사전규격을 구분해서 검색하고, 날짜를 달력으로 지정해보세요.")
    
    with st.sidebar:
        st.header("🔍 검색 옵션")
        search_type = st.radio("정보 유형", ("입찰공고", "사전규격"))
        st.divider()
        keyword = st.text_input("검색어", placeholder="예: 기획, 디자인")
        today = datetime.datetime.now()
        date_range = st.date_input("기간", (today - datetime.timedelta(days=7), today))
        search_btn = st.button("검색 시작 🚀", type="primary")

    if search_btn:
        if not keyword:
            st.warning("⚠️ 검색어를 입력해주세요!")
            return
            
        service_key = get_api_key()
        if not service_key: return
        
        if len(date_range) != 2:
            st.warning("📅 날짜 범위를 정확히 선택해주세요.")
            return
            
        start_dt, end_dt = date_range
        
        with st.spinner(f"📡 '{search_type}' 정보를 찾는 중입니다..."):
            api_response = fetch_nara_data(
                search_type, keyword, 
                start_dt.strftime("%Y%m%d")+"0000", end_dt.strftime("%Y%m%d")+"2359", 
                service_key
            )
            
        if api_response:
            # ★ 여기가 수정된 부분입니다! (괄호 닫음)
            items = parse_items(api_response, search_type)
            
            if items:
                st.success(f"✅ 총 {len(items)}건 발견!")
                for item in items:
                    with st.expander(f"[{item['org']}] {item['title']}"):
                        st
