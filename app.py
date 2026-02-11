import streamlit as st
import requests
import datetime
from urllib.parse import unquote
from typing import Dict, List, Optional, Tuple
import logging

# ==================== 설정 상수 ====================
API_CONFIG = {
    'num_rows': 30,
    'page_no': 1,
    'timeout': 15,
    'inqry_div': '1'
}

# ★ 여기가 핵심 수정 부분입니다! (선생님의 특수 주소 추가)
API_ENDPOINTS = {
    '입찰공고': [
        'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch', # 표준
        'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch' # 특수(ad)
    ],
    '사전규격': [
        # 1. 선생님 스크린샷에 있던 바로 그 주소 (가장 중요!)
        'https://apis.data.go.kr/1230000/ao/HrcspsSstndrdInfoService/getBfSpecListInfoServcPPSSrch',
        # 2. 표준 주소
        'https://apis.data.go.kr/1230000/BfSpecInfoService01/getBfSpecListInfoServcPPSSrch',
        # 3. 혹시 몰라 추가한 주소
        'https://apis.data.go.kr/1230000/ad/BfSpecInfoService/getBfSpecListInfoServcPPSSrch'
    ]
}

FIELD_MAPPING = {
    '입찰공고': {
        'title': 'bidNtceNm',
        'org': 'dminsttNm',
        'date': 'bidClseDt',
        'link': 'bidNtceDtlUrl',
        'date_label': '마감일',
        'param_name': 'bidNtceNm'
    },
    '사전규격': {
        'title': 'bfSpecNm',
        'org': 'dminsttNm',
        'date': 'bfSpecRegDt',
        'link': 'bfSpecDtlUrl',
        'date_label': '등록일',
        'param_name': 'bfSpecNm'
    }
}

# ==================== 로깅 설정 ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 페이지 설정 ====================
st.set_page_config(
    page_title="나라장터 용역 알리미 Pro",
    page_icon="📢",
    layout="wide"
)

# ==================== 유틸리티 함수 ====================
def format_datetime(date_str: str) -> str:
    """날짜 문자열을 포맷팅"""
    if date_str and len(date_str) == 12:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}"
    return date_str or '-'

def get_api_key() -> Optional[str]:
    """Secrets에서 API 키 가져오기"""
    try:
        return st.secrets["public_api_key"]
    except KeyError:
        st.error("🚨 API 키가 설정되지 않았습니다. [Settings] > [Secrets]에 'public_api_key'를 추가해주세요.")
        return None
    except Exception as e:
        st.error(f"🚨 API 키 로드 중 오류: {str(e)}")
        return None

def validate_date_range(date_range: Tuple) -> Optional[Tuple[str, str]]:
    """날짜 범위 검증 및 포맷팅"""
    if len(date_range) != 2:
        st.warning("📅 시작일과 종료일을 모두 선택해주세요.")
        return None
    
    start_dt, end_dt = date_range
    inqry_bgn_dt = start_dt.strftime("%Y%m%d") + "0000"
    inqry_end_dt = end_dt.strftime("%Y%m%d") + "2359"
    
    return inqry_bgn_dt, inqry_end_dt

# ==================== API 호출 함수 ====================
@st.cache_data(ttl=600)  # 10분간 캐시
def fetch_nara_data(
    search_type: str,
    keyword: str,
    start_date: str,
    end_date: str,
    service_key: str
) -> Optional[Dict]:
    """
    나라장터 API에서 데이터 조회
    """
    urls = API_ENDPOINTS.get(search_type, [])
    param_name = FIELD_MAPPING[search_type]['param_name']
    
    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': str(API_CONFIG['num_rows']),
        'pageNo': str(API_CONFIG['page_no']),
        'inqryDiv': API_CONFIG['inqry_div'],
        'inqryBgnDt': start_date,
        'inqryEndDt': end_date,
        param_name: keyword,
        'type': 'json'
    }
    
    # 여러 엔드포인트 시도
    for idx, url in enumerate(urls, 1):
        try:
            logger.info(f"API 호출 시도 {idx}/{len(urls)}: {url}")
            response = requests.get(url, params=params, timeout=API_CONFIG['timeout'])
            
            if response.status_code == 200:
                data = response.json()
                
                # API 응답 검증
                if 'response' not in data:
                    logger.warning(f"잘못된 응답 구조: {url}")
                    continue
                
                result_code = data.get('response', {}).get('header', {}).get('resultCode')
                if result_code != '00':
                    result_msg = data.get('response', {}).get('header', {}).get('resultMsg', '알 수 없는 오류')
                    logger.warning(f"API 오류 ({result_code}): {result_msg}")
                    continue
                
                logger.info(f"✅ API 호출 성공: {url}")
                return {
                    'data': data,
                    'url': url,
                    'attempt': idx
                }
            
            else:
                logger.warning(f"HTTP {response.status_code}: {url}")
                
        except requests.Timeout:
            logger.error(f"타임아웃 ({API_CONFIG['timeout']}초 초과): {url}")
        except requests.RequestException as e:
            logger.error(f"네트워크 오류: {url} - {str(e)}")
        except ValueError as e:
            logger.error(f"JSON 파싱 오류: {url} - {str(e)}")
        except Exception as e:
            logger.error(f"예상치 못한 오류: {url} - {str(e)}")
    
    return None

def parse_items(api_response: Dict, search_type: str) -> List[Dict]:
    """API 응답에서 아이템 추출 및 파싱"""
    items = api_response.get('data', {}).get('response', {}).get('body', {}).get('items')
    
    if not items:
        return []
    
    # 단일 아이템을 리스트로 변환
    if not isinstance(items, list):
        items = [items]
    
    mapping = FIELD_MAPPING[search_type]
    parsed_items = []
    
    for item in items:
        parsed_items.append({
            'title': item.get(mapping['title'], '제목 없음'),
            'org': item.get(mapping['org'], '기관명 없음'),
            'date': format_datetime(item.get(mapping['date'], '')),
            'link': item.get(mapping['link'], '#'),
            'date_label': mapping['date_label'],
            'raw': item  # 원본 데이터 보관
        })
    
    return parsed_items

# ==================== UI 렌더링 함수 ====================
def render_item_card(item: Dict):
    """검색 결과 아이템을 카드 형식으로 렌더링"""
    with st.expander(f"[{item['org']}] {item['title']}"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"🏢 수요기관: {item['org']}")
            st.write(f"📅 {item['date_label']}: {item['date']}")
        with col2:
            if item['link'] != '#':
                st.link_button("상세보기 👉", item['link'])
            else:
                st.caption("링크 없음")

def display_results(items: List[Dict], api_info: Dict):
    """검색 결과 전체 출력"""
    if items:
        st.success(f"✅ 총 {len(items)}건의 정보를 찾았습니다.")
        
        # 디버그 정보 (개발자용 - 성공한 주소 확인용)
        with st.expander("🔧 연결 성공 주소 확인 (개발자용)", expanded=False):
            st.write(f"사용된 주소: `{api_info['url']}`")
        
        for item in items:
            render_item_card(item)
    else:
        st.info("📭 조건에 맞는 결과가 없습니다. 기간이나 검색어를 변경해보세요.")

# ==================== 메인 로직 ====================
def main():
    st.title("📢 나라장터 용역 정보 검색기 Pro")
    st.markdown("입찰공고와 사전규격을 구분해서 검색하고, 날짜를 달력으로 지정해보세요.")
    
    with st.sidebar:
        st.header("🔍 검색 옵션")
        
        search_type = st.radio(
            "정보 유형을 선택하세요",
            ("입찰공고", "사전규격")
        )
        
        st.divider()
        
        keyword = st.text_input("검색어 입력", placeholder="예: 기획, 디자인, 인공지능")
        
        today = datetime.datetime.now()
        seven_days_ago = today - datetime.timedelta(days=7)
        
        date_range = st.date_input(
            "검색 기간 설정 (시작일 - 종료일)",
            (seven_days_ago, today)
        )
        
        # 고급 설정
        with st.expander("⚙️ 고급 설정"):
            custom_rows = st.number_input(
                "표시할 결과 수",
                min_value=10, max_value=100,
                value=API_CONFIG['num_rows'], step=10
            )
            if custom_rows != API_CONFIG['num_rows']:
                API_CONFIG['num_rows'] = custom_rows
        
        search_btn = st.button("검색 시작 🚀", type="primary")
    
    if search_btn:
        if not keyword:
            st.warning("⚠️ 검색어를 입력해주세요!")
            return
        
        service_key = get_api_key()
        if not service_key:
            return
        
        date_result = validate_date_range(date_range)
        if not date_result:
            return
        
        start_date, end_date = date_result
        
        with st.spinner(f"📡 '{search_type}' 정보를 찾는 중입니다..."):
            if 'search_type' not in st.session_state:
                st.session_state.search_type = search_type
            
            api_response = fetch_nara_data(
                search_type=search_type,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                service_key=service_key
            )
        
        if api_response:
            items = parse_items(api_response, search_type)
            display_results(items, api_response)
        else:
            st.error("❌ 서버 연결 실패 (모든 주소 시도 실패)")
            st.write("**팁:** 잠시 후 다시 시도하거나, 공공데이터포털 활용신청 상태를 확인하세요.")

if __name__ == "__main__":
    main()
