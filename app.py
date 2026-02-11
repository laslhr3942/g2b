import streamlit as st
import requests
import datetime
from urllib.parse import unquote
import logging
import sys

# 1. 가장 먼저 페이지 설정 (이게 없으면 에러 날 수 있음)
st.set_page_config(page_title="나라장터 검색기 Pro", page_icon="📢", layout="wide")

# 2. 앱이 살아있는지 확인하는 디버깅 메시지 (성공하면 나중에 지워도 됨)
st.toast("앱이 실행되었습니다! 🚀") 

# ==================== 설정 및 주소 ====================
API_ENDPOINTS = {
    '입찰공고': {
        'url': 'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch',
        'param_name': 'bidNtceNm',
        'date_param': 'bidClseDt'
    },
    '사전규격': {
        # 선생님 스크린샷 기반 정확한 주소 + 명령어
        'url': 'https://apis.data.go.kr/1230000/ao/HrcspsSstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch',
        'param_name': 'bfSpecNm',
        'date_param': 'bfSpecRegDt'
    }
}

API_CONFIG = {'num_rows': 30, 'page_no': 1, 'timeout': 15, 'inqryDiv': '1'}

# ==================== 함수 정의 ====================
def get_api_key():
    try:
        # Secrets에서 키를 가져옴. 없으면 에러 메시지 출력
        key = st.secrets.get("public_api_key")
        if not key:
            st.error("🚨 Secrets에 'public_api_key'가 없습니다!")
            return None
        return key
    except Exception as e:
        st.error(f"🚨 키 확인 중 에러 발생: {e}")
        return None

def fetch_nara_data(search_type, keyword, start_date, end_date, service_key):
    config = API_ENDPOINTS.get(search_type)
    url = config['url']
    
    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': str(API_CONFIG['num_rows']), 
        'pageNo': str(API_CONFIG['page_no']),
        'inqryDiv': API_CONFIG['inqryDiv'], 
        'inqryBgnDt': start_date, 
        'inqryEndDt': end_date,
        'type': 'json',
        config['param_name']: keyword
    }
    
    try:
        response = requests.get(url, params=params, timeout=API_CONFIG['timeout'])
        if response.status_code != 200:
            st.warning(f"접속 실패 (코드 {response.status_code}): {url}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"통신 에러: {e}")
        return None

def format_date(date_str):
    if date_str and len(date_str) == 12:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str

# ==================== 메인 화면 (UI) ====================
def main():
    st.title("📢 나라장터 용역 정보 검색기 Pro")
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("🔍 검색 설정")
        search_type = st.radio("유형", ["입찰공고", "사전규격"])
        keyword = st.text_input("검색어", "여행")
        
        today = datetime.datetime.now()
        date_range = st.date_input("기간", (today - datetime.timedelta(days=7), today))
        
        btn = st.button("검색 시작 🚀", type="primary")

    # 검색 버튼 클릭 시 실행
    if btn:
        service_key = get_api_key()
        if not service_key:
            return

        if len(date_range) != 2:
            st.warning("날짜 범위를 정확히 선택해주세요.")
            return

        start_dt = date_range[0].strftime("%Y%m%d") + "0000"
        end_dt = date_range[1].strftime("%Y%m%d") + "2359"

        with st.spinner(f"데이터를 불러오는 중... ({search_type})"):
            data = fetch_nara_data(search_type, keyword, start_dt, end_dt, service_key)

        if data:
            try:
                items = data['response']['body']['items']
                if not items:
                    st.info("검색 결과가 없습니다.")
                else:
                    if not isinstance(items, list): items = [items]
                    st.success(f"✅ 총 {len(items)}건을 찾았습니다!")
                    
                    for item in items:
                        # 필드명 찾기 (사전규격/입찰공고 자동 대응)
                        title = item.get('bidNtceNm') or item.get('bfSpecNm') or item.get('prdctNm') or "제목 없음"
                        org = item.get('dminsttNm', '기관명 없음')
                        date_val = item.get('bidClseDt') or item.get('bfSpecRegDt') or ""
                        link = item.get('bidNtceDtlUrl') or item.get('bfSpecDtlUrl')
                        
                        with st.expander(f"[{org}] {title}"):
                            st.write(f"📅 날짜: {format_date(date_val)}")
                            if link:
                                st.link_button("상세보기", link)
            except Exception as e:
                st.error(f"데이터 처리 중 오류: {e}")
                st.write(data) # 디버깅용 데이터 출력
        else:
            st.error("서버에서 응답을 받지 못했습니다.")

# ==================== 실행 진입점 (중요!) ====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("프로그램 실행 중 치명적인 오류가 발생했습니다.")
        st.exception(e)
