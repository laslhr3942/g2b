import streamlit as st
import requests
import datetime
from urllib.parse import unquote

st.set_page_config(page_title="나라장터 진단 키트", page_icon="🩺")

st.title("🩺 나라장터 연결 진단 모드")
st.write("서버가 보내는 **진짜 에러 메시지**를 확인합니다.")

# 1. API 키 가져오기 (이름이 public_api_key인지 확인)
try:
    service_key = st.secrets["public_api_key"]
    st.success(f"🔑 API 키 확인 완료: {service_key[:5]}..." + service_key[-5:])
except Exception as e:
    st.error("🚨 Secrets 설정 오류! 'public_api_key'라는 이름으로 저장되었는지 확인하세요.")
    st.stop()

# 2. 테스트할 주소 목록 (가능성 있는 모든 곳을 다 찔러봅니다)
urls_to_test = [
    # (1) 선생님 스크린샷에 있던 주소 (가장 유력한 용의자)
    "https://apis.data.go.kr/1230000/ao/HrcspsSstndrdInfoService/getBfSpecListInfoServcPPSSrch",
    # (2) 표준 주소 (보통 이걸 씀)
    "https://apis.data.go.kr/1230000/BfSpecInfoService01/getBfSpecListInfoServcPPSSrch",
    # (3) 특수 주소 (ad)
    "https://apis.data.go.kr/1230000/ad/BfSpecInfoService/getBfSpecListInfoServcPPSSrch"
]

# 3. 검색 버튼
if st.button("사전규격 접속 테스트 시작 🚀"):
    
    today = datetime.datetime.now()
    start_dt = (today - datetime.timedelta(days=5)).strftime("%Y%m%d") + "0000"
    end_dt = today.strftime("%Y%m%d") + "2359"
    
    params = {
        "serviceKey": unquote(service_key),
        "numOfRows": "1",
        "pageNo": "1",
        "inqryDiv": "1",
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "bfSpecNm": "용역", # 테스트용 검색어
        "type": "json"
    }

    st.divider()
    
    for i, url in enumerate(urls_to_test, 1):
        st.markdown(f"### 📡 시도 {i}: 주소 확인 중...")
        st.code(url)
        
        try:
            response = requests.get(url, params=params, timeout=10)
            st.write(f"상태 코드: **{response.status_code}**")
            
            # 서버가 보낸 실제 응답 내용 출력
            if response.status_code == 200:
                try:
                    data = response.json()
                    st.json(data) # 성공하면 데이터 보여줌
                    st.success("✅ 이 주소가 정답입니다!")
                except:
                    st.warning("⚠️ 접속은 됐는데 JSON이 아닙니다.")
                    st.text(response.text)
            else:
                st.error("❌ 접속 실패")
                st.text_area("서버 에러 메시지 (이걸 알려주세요!)", response.text, height=100)
                
        except Exception as e:
            st.error(f"프로그램 에러: {e}")
            
        st.divider()
