import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="박스오피스 대시보드", layout="wide", page_icon="🎬")
st.title("🎬 일별 박스오피스 조회")

# Secrets 체크
if "KOBIS_KEY" not in st.secrets:
    st.error("Streamlit Secrets에 'KOBIS_KEY'가 설정되어 있지 않습니다.")
    st.stop()

KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 기준 날짜 계산 (한국 시간 기준)
now_korea = datetime.now(ZoneInfo("Asia/Seoul")).date()
yesterday = now_korea - timedelta(days=1)

# Sidebar 또는 메인 화면 상단에 날짜 선택 달력 추가
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요",
    value=yesterday,
    max_value=yesterday,  # 오늘 이후 날짜 선택 불가
    help="박스오피스 집계 특성상 어제 날짜까지만 조회할 수 있습니다."
)

# KOBIS API용 날짜 포맷 (YYYYMMDD)
target_dt = selected_date.strftime("%Y%m%d")
st.caption(f"조회 기준일: {selected_date.strftime('%Y년 %m월 %d일')}")

# 캐싱 적용된 데이터 요청 함수
@st.cache_data(ttl=3600)
def fetch_box_office(api_key, target_date):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    try:
        res = requests.get(url, params={"key": api_key, "targetDt": target_date}, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

data = fetch_box_office(KOBIS_KEY, target_dt)

if "error" in data:
    st.error(f"API 호출 중 오류가 발생했습니다: {data['error']}")
    st.stop()

if "faultInfo" in data:
    st.error("인증키가 올바르지 않습니다. Secrets의 KOBIS_KEY를 확인해 주세요.")
    st.stop()

box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

# 영화 목록이 비어있는 경우 안내 문구 처리
if not box_list:
    st.warning("그날은 아직 집계 전입니다.")
    st.stop()

# 데이터 전처리
df = pd.DataFrame(box_list)
for col in ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]:
    df[col] = pd.to_numeric(df[col])

# 1위 영화 지표 카드
top = df.sort_values("rank").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("해당 일자 1위", top["movieNm"])
c2.metric("당일 관객수", f"{top['audiCnt']:,}명")
c3.metric("누적 관객수", f"{top['audiAcc']:,}명")

st.divider()

# 표 구성
table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
table = table.sort_values("순위").reset_index(drop=True)

st.subheader(f"📋 {selected_date.strftime('%Y-%m-%d')} 박스오피스 TOP 10")
st.dataframe(
    table,
    hide_index=True,
    column_config={
        "관객수": st.column_config.NumberColumn(format="%d명"),
        "누적관객": st.column_config.NumberColumn(format="%d명"),
        "스크린수": st.column_config.NumberColumn(format="%d개"),
    },
    use_container_width=True
)

st.subheader("📈 관객수 상위 5편")
top5 = table.sort_values("관객수", ascending=False).head(5)
st.bar_chart(top5.set_index("영화명")["관객수"])
