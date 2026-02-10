import streamlit as st
import requests
import datetime
from urllib.parse import unquote

# 1. 페이지 설정
st.set_page_config(
    page_title="나라장터 용역 알리미 Pro",
    page_icon="📢",
    layout="wide"
)

# 2. 제목 및 설명
st.title("📢 나라장터 용역 정보 검색기 Pro")
st.markdown("입찰공고와 사전규격을 구분해서 검색하고, 날짜를 달력으로 지정해보세요.")

# 3. 사이드바: 검색 옵션
with st.sidebar:
    st.header("🔍 검색 옵션")
    
    # 정보 유형 선택
    search_type = st.radio(
        "정보 유형을 선택하세요",
        ("입찰공고", "사전규격")
    )
    
    st.divider()

    # 검색어 입력
    keyword = st.text_input("검색어 입력", placeholder="예: 기획, 디자인, 인공지능")
    
    # 날짜 선택
    today = datetime.datetime.now()
    seven_days_ago = today - datetime.timedelta(days=7)
    
    date_range = st.date_input(
        "검색 기간 설정 (시작일 - 종료일)",
        (seven_days_ago, today)
    )
    
    search_btn = st.button("검색 시작 🚀", type="primary")

# 4. API 통신 함수
def search_nara():
    # Secrets에서 키 가져오기
    try:
        service_key = st.secrets["public_api_key"]
    except:
        st.error("🚨 API 키가 설정되지 않았습니다. [Settings] > [Secrets]에 키를 넣어주세요.")
        return

    # 날짜 체크
    if len(date_range) != 2:
        st.warning("📅 시작일과 종료일을 모두 선택해주세요.")
        return
    
    start_dt, end_dt = date_range
    inqry_bgn_dt = start_dt.strftime("%Y%m%d") + "0000"
    inqry_end_dt = end_dt.strftime("%Y%m%d") + "2359"

    # ★ 핵심 수정: 시도해볼 주소 목록 (표준 주소 + ad 주소)
    if search_type == "입찰공고":
        urls_to_try = [
            'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch', # 표준
            'https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch' # 특수
        ]
        nm_param = 'bidNtceNm' 
    else: # 사전규격
        urls_to_try = [
            'https://apis.data.go.kr/1230000/BfSpecInfoService01/getBfSpecListInfoServcPPSSrch', # 표준
            'https://apis.data.go.kr/1230000/ad/BfSpecInfoService/getBfSpecListInfoServcPPSSrch' # 특수 (여기가 문제였을 가능성 큼)
        ]
        nm_param = 'bfSpecNm'

    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': '30',
        'pageNo': '1',
        'inqryDiv': '1',
        'inqryBgnDt': inqry_bgn_dt,
        'inqryEndDt': inqry_end_dt,
        nm_param: keyword,
        'type': 'json'
    }

    # 여러 주소 시도 로직
    success = False
    with st.spinner(f"📡 '{search_type}' 정보를 찾는 중입니다..."):
        for url in urls_to_try:
            try:
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('response', {}).get('body', {}).get('items')
                    
                    if items:
                        if not isinstance(items, list): items = [items]
                        
                        st.success(f"✅ 성공! 총 {len(items)}건의 정보를 찾았습니다.")
                        
                        for item in items:
                            # 필드명 매핑
                            if search_type == "입찰공고":
                                title = item.get('bidNtceNm', '제목 없음')
                                org = item.get('dminsttNm', '기관명 없음')
                                date_val = item.get('bidClseDt', '-')
                                link = item.get('bidNtceDtlUrl', '#')
                                date_label = "마감일"
                            else:
                                title = item.get('bfSpecNm', '제목 없음')
                                org = item.get('dminsttNm', '기관명 없음')
                                date_val = item.get('bfSpecRegDt', '-')
                                link = item.get('bfSpecDtlUrl', '#')
                                date_label = "등록일"

                            # 날짜 포맷
                            if date_val and len(date_val) == 12:
                                date_val = f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:8]} {date_val[8:10]}:{date_val[10:12]}"

                            # 카드 출력
                            with st.expander(f"[{org}] {title}"):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"🏢 수요기관: {org}")
                                    st.write(f"📅 {date_label}: {date_val}")
                                with col2:
                                    if link != '#':
                                        st.link_button("상세보기 👉", link)
                                    else:
                                        st.caption("링크 없음")
                        success = True
                        break # 성공했으므로 반복 종료
                    else:
                        st.info("조건에 맞는 결과가 없습니다. (기간이나 검색어를 변경해보세요)")
                        success = True
                        break
            except Exception:
                continue # 실패하면 조용히 다음 주소 시도
        
        if not success:
            st.error("❌ 서버 연결 실패 (모든 주소 시도 실패)")
            st.write("팁: 잠시 후 다시 시도해보거나, 공공데이터포털 활용신청 상태를 확인해주세요.")

# 5. 실행
if search_btn:
    if keyword:
        search_nara()
    else:
        st.warning("⚠️ 검색어를 입력해주세요!")
