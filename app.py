import streamlit as st
import requests
import datetime
from urllib.parse import unquote
from typing import Dict, List, Optional, Tuple
import logging

# ==================== 설정 및 주소(Endpoint) ====================
# ★ 여기가 핵심! 선생님의 특수 주소(ao)를 제일 위에 올렸습니다.
API_ENDPOINTS = {
    '입찰공고': [
        'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch', # 표준
        'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch' # 특수(ad)
    ],
    '사전규격': [
        # 1. 선생님 스크린샷에 있던 그 주소 (ao) - 가장 유력!
        'https://apis.data.go.kr/1230000/ao/HrcspsSstndrdInfoService/getBfSpecListInfoServcPPSSrch',
        # 2. 표준 주소
        'https://apis.data.go.kr/1230000/BfSpecInfoService01/getBfSpecListInfoServcPPSSrch',
        # 3. 혹시 몰라 추가한 주소 (ad)
        'https://apis.data.go.kr/1230000/ad/BfSpecInfoService/getBfSpecListInfoServcPPSSrch'
    ]
}

FIELD_MAPPING = {
    '입찰공고': {
        'title': 'bidNtceNm', 'org': 'dminsttNm', 'date': 'bidClseDt',
        'link': 'bidNtceDtlUrl', 'date_label': '마감일', 'param_name': 'bidNtceNm'
    },
    '사전규격': {
        'title': 'bfSpecNm', 'org': 'dminsttNm', 'date': 'bfSpecRegDt',
        'link': 'bfSpecDtlUrl', 'date_label': '등록일', 'param_name': 'bfSpecNm'
    }
}

API_CONFIG = {'num_rows': 30, 'page_no': 1, 'timeout': 15, 'inqry_div': '1'}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="나라장터 용역 알리미 Pro", page_icon="📢", layout="wide")

# ==================== 유틸리티 함수 ====================
def get_api_key() -> Optional[str]:
    """Secrets에서 키 가져오기"""
    try:
        # ★ 코드에서는 이 이름을 찾습니다! Secrets에도 이 이름으로 저장되어야 합니다.
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
    urls = API_ENDPOINTS.get(search_type, [])
    param_name = FIELD_MAPPING[search_type]['param_name']
    
    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': str(API_CONFIG['num_rows']), 'pageNo': str(API_CONFIG['page_no']),
        'inqryDiv': API_CONFIG['inqry_div'], 'inqryBgnDt': start_date, 'inqryEndDt': end_date,
        param_name: keyword, 'type': 'json'
    }
    
    for idx, url in enumerate(urls, 1):
        try:
            response = requests.get(url, params=params, timeout=API_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'body' in data['response']:
                    return {'data': data, 'url': url} # 성공!
            else:
                # 에러 발생 시 로그 출력 (디버깅용)
                logger.warning(f"접속 실패 ({response.status_code}): {url}")
        except Exception as e:
            logger.error(f"오류 발생: {url} - {e}")
            continue
    return None

def parse_items(api_response, search_type):
    items = api_response.get('data', {}).get('response', {}).get('body', {}).get('items')
    if not items: return []
    if not isinstance(items, list): items = [items]
    
    mapping = FIELD_MAPPING[search_type]
    parsed_items = []
    for item in items:
        parsed_items.append({
            'title': item.get(mapping['title'], '제목 없음'),
            'org': item.get(mapping['org'], '기관명 없음'),
            'date': format_datetime(item.get(mapping['date'], '')),
            'link': item.get(mapping['link'], '#'),
            'date_label': mapping['date_label']
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
        if not service_key: return # 키가 없으면 중단
        
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
            items = parse_items(api_response, search_type)
            if items:
                st.success(f"✅ 총 {len(items)}건 발견! (연결된 주소: ...{api_response['url'][-30:]})")
                for item in items:
                    with st.expander(f"[{item['org']}] {item['title']}"):
                        st.write(f"📅 {item['date_label']}: {item['date']}")
                        if item['link'] != '#': st.link_button("상세보기", item['link'])
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.error("❌ 서버 연결 실패")
            st.write("팁: 1. Secrets에 'public_api_key'가 정확한지 확인하세요.")
            st.write("2. 사전규격 승인이 아직 '대기' 상태일 수 있습니다.")

if __name__ == "__main__":
    main()
