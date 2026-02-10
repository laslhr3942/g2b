import streamlit as st
import requests
import datetime
from urllib.parse import unquote

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="나라장터 용역 알리미 Pro",
    page_icon="📢",
    layout="wide"
)

# 2. 제목 및 설명
st.title("📢 나라장터 용역 정보 검색기 Pro")
st.markdown("입찰공고와 사전규격을 구분해서 검색하고, 날짜를 달력으로 지정해보세요.")

# 3. 사이드바: 검색 옵션 설정
with st.sidebar:
    st.header("🔍 검색 옵션")
    
    # [기능 1] 정보 유형 선택 (라디오 버튼)
    search_type = st.radio(
        "정보 유형을 선택하세요",
        ("입찰공고", "사전규격")
    )
    
    st.divider()

    # [기능 2] 검색어 입력
    keyword = st.text_input("검색어 입력", placeholder="예: 기획, 디자인, 인공지능")
    
    # [기능 3] 날짜 선택 (달력)
    # 기본값: 오늘로부터 7일 전 ~ 오늘
    today = datetime.datetime.now()
    seven_days_ago = today - datetime.timedelta(days=7)
    
    date_range = st.date_input(
        "검색 기간 설정 (시작일 - 종료일)",
        (seven_days_ago, today) # 기본 범위
    )
    
    search_btn = st.button("검색 시작 🚀", type="primary")

# 4. API 통신 함수
def search_nara():
    # Streamlit Secrets에서 API 키 가져오기
    try:
        service_key = st.secrets["public_api_key"]
    except:
        st.error("🚨 API 키가 설정되지 않았습니다. [Settings] > [Secrets]를 확인해주세요.")
        return

    # 날짜 유효성 체크 (사용자가 날짜를 하나만 선택했을 때 대비)
    if len(date_range) != 2:
        st.warning("📅 시작일과 종료일을 모두 선택해주세요.")
        return
    
    start_dt, end_dt = date_range
    
    # API 요청용 날짜 포맷 변환 (YYYYMMDDHHMM)
    inqry_bgn_dt = start_dt.strftime("%Y%m%d") + "0000"
    inqry_end_dt = end_dt.strftime("%Y%m%d") + "2359"

    # [중요] 선택한 유형에 따라 API 주소(URL) 바꾸기
    if search_type == "입찰공고":
        # 용역 입찰 공고 조회
        url = 'https://apis.data.go.kr/1230000/BidPublicInfoService02/getBidPblancListInfoServcPPSSrch'
        nm_param = 'bidNtceNm' # 파라미터 이름: 공고명
    else:
        # 용역 사전 규격 조회 (주소가 다름!)
        url = 'https://apis.data.go.kr/1230000/BfSpecInfoService01/getBfSpecListInfoServcPPSSrch'
        nm_param = 'bfSpecNm'  # 파라미터 이름: 사전규격명

    # 요청 파라미터 설정
    params = {
        'serviceKey': unquote(service_key),
        'numOfRows': '30',
        'pageNo': '1',
        'inqryDiv': '1',
        'inqryBgnDt': inqry_bgn_dt,
        'inqryEndDt': inqry_end_dt,
        nm_param: keyword, # 위에서 정한 변수명 사용 (공고명 vs 규격명)
        'type': 'json'
    }

    # 데이터 요청 및 결과 출력
    with st.spinner(f"📡 '{search_type}'에서 '{keyword}'(으)로 검색 중..."):
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('response', {}).get('body', {}).get('items')
                
                if items:
                    if not isinstance(items, list): items = [items]
                    
                    st.success(f"총 {len(items)}건의 정보를 찾았습니다!")
                    
                    # 결과를 보기 좋게 카드 형태로 출력
                    for item in items:
                        # API마다 필드명이 조금씩 달라서 get으로 안전하게 가져오기
                        if search_type == "입찰공고":
                            title = item.get('bidNtceNm', '제목 없음')
                            org = item.get('dminsttNm', '기관명 없음')
                            date_info = item.get('bidClseDt', '-') # 입찰마감일시
                            link = item.get('bidNtceDtlUrl', '#')
                            date_label = "마감일"
                        else: # 사전규격일 때
                            title = item.get('bfSpecNm', '제목 없음')
                            org = item.get('dminsttNm', '기관명 없음') 
                            date_info = item.get('bfSpecRegDt', '-') # 등록일시
                            link = item.get('bfSpecDtlUrl', '#') # 사전규격은 링크 필드명이 다를 수 있음
                            date_label = "등록일"

                        # 날짜 포맷팅 (YYYYMMDDHHMM -> YYYY-MM-DD HH:MM)
                        if date_info and len(date_info) == 12:
                            date_info = f"{date_info[:4]}-{date_info[4:6]}-{date_info[6:8]} {date_info[8:10]}:{date_info[10:12]}"

                        # UI 카드 그리기
                        with st.expander(f"[{org}] {title}"):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"🏢 수요기관: {org}")
                                st.write(f"📅 {date_label}: {date_info}")
                            with col2:
                                if link != '#':
                                    st.link_button("상세보기 👉", link)
                                else:
                                    st.caption("링크 정보 없음")
                else:
                    st.info("조건에 맞는 결과가 없습니다. 기간이나 검색어를 변경해보세요.")
            else:
                st.error(f"서버 연결 실패 (에러 코드: {response.status_code})")
                if search_type == "사전규격":
                    st.warning("💡 팁: '사전규격' 검색이 안 된다면, 공공데이터포털에서 [조달청_나라장터_사전규격정보] API 활용신청이 되어있는지 확인해주세요!")

        except Exception as e:
            st.error(f"오류 발생: {e}")

# 5. 실행 로직
if search_btn:
    if keyword:
        search_nara()
    else:
        st.warning("⚠️ 검색어를 입력해주세요!")