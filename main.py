import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="전국 시군구별 출생 비율(0세 인구) 지도", layout="wide"
)
st.title("👶 전국 시군구별 출생 비율(0세 인구 비율) 지도")
st.caption("최신 연도 데이터 기준 전체 인구 대비 0세 인구 비율(%) 단계구분도")


# 2. 데이터 로딩 함수 (캐시 적용으로 빠르게 실행)
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    # 코드는 앞 5자리 잘라내기를 위해 반드시 문자열(dtype=str)로 읽습니다.
    df = pd.read_csv(url, compression="gzip", dtype={"코드": str})
    return df


@st.cache_data
def load_geojson_data():
    geojson_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()


# 로딩 상태 메시지 표시
with st.spinner("인구 데이터 및 지도 경계 데이터를 불러오는 중입니다..."):
    pop_df = load_population_data()
    geojson_data = load_geojson_data()


# 3. 데이터 가공 및 0세 인구 비율 계산
# 가장 최신 연도 자동 도출 및 해당 연도 데이터만 필터링
latest_year = pop_df["연도"].max()
df_latest = pop_df[pop_df["연도"] == latest_year].copy()

# 행정동 코드(10자리)의 앞 5자리를 잘라서 시군구 코드로 지정
df_latest["sigungu_code"] = df_latest["코드"].str[:5]

# 전체 인구('계_'로 시작하는 모든 열의 합) 계산
total_pop_cols = [col for col in df_latest.columns if col.startswith("계_")]
df_latest["총인구"] = df_latest[total_pop_cols].sum(axis=1)

# 시군구별(sigungu_code) GroupBy 합산
sigungu_df = (
    df_latest.groupby("sigungu_code")
    .agg({"시도": "first", "시군구": "first", "총인구": "sum", "계_0세": "sum"})
    .reset_index()
)

# 0세 인구 비율(%) 계산: (0세 인구 / 총인구) * 100
sigungu_df["0세인구비율"] = (
    sigungu_df["계_0세"] / sigungu_df["총인구"] * 100
).round(2)


# 4. 5단계 범례 구간 지정
# 구간 경계: 0.25% 미만, 0.25%~0.35%, 0.35%~0.45%, 0.45%~0.55%, 0.55% 이상
bins = [-float("inf"), 0.25, 0.35, 0.45, 0.55, float("inf")]
labels = [
    "0.25% 미만(초저출생)",
    "0.25% 이상 ~ 0.35% 미만",
    "0.35% 이상 ~ 0.45% 미만",
    "0.45% 이상 ~ 0.55% 미만",
    "0.55% 이상",
]

sigungu_df["비율_구간"] = pd.cut(
    sigungu_df["0세인구비율"], bins=bins, labels=labels
)


# 5. Plotly 단계구분도(Choropleth Mapbox) 생성
# 출생 비율이 높은 곳은 진한 색(Blues 계열 사용)
color_discrete_map = {
    "0.25% 미만(초저출생)": "#f7fbff",
    "0.25% 이상 ~ 0.35% 미만": "#c6dbef",
    "0.35% 이상 ~ 0.45% 미만": "#6baed6",
    "0.45% 이상 ~ 0.55% 미만": "#2171b5",
    "0.55% 이상": "#08306b",
}

fig = px.choropleth_mapbox(
    sigungu_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",  # GeoJSON 내 시군구 5자리 코드 매칭
    color="비율_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"비율_구간": labels},  # 범례 순서 정렬
    mapbox_style="white-bg",  # 배경 타일 없이 경계선만 표시
    center={"lat": 35.8, "lon": 127.8},  # 대한민국 중심 좌표
    zoom=6.1,
    hover_name="시군구",
    hover_data={
        "시도": True,
        "0세인구비율": ":.2f%",
        "계_0세": ":,명",
        "총인구": ":,명",
        "sigungu_code": False,
    },
    labels={
        "비율_구간": "0세 인구 비율 구간",
        "0세인구비율": "0세 인구 비율(%)",
        "계_0세": "0세 인구 수",
        "총인구": "총인구 수",
    },
)

# 지도 여백 및 범례 디자인 조정
fig.update_layout(
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend=dict(
        title=f"<b>0세 인구 비율 ({latest_year}년)</b>",
        yanchor="top",
        y=0.98,
        xanchor="left",
        x=0.02,
        bgcolor="rgba(255, 255, 255, 0.8)",
    ),
)

# 지도 화면 출력
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# 6. 하단 상위/하위 10개 지역 표 나란히 배치
st.subheader(f"📊 {latest_year}년 시군구별 0세 인구 비율 순위 (상위/하위 10곳)")

col1, col2 = st.columns(2)

# 상위 10개 (비율이 높은 순)
top10 = (
    sigungu_df.sort_values(by="0세인구비율", ascending=False)
    .head(10)[["시도", "시군구", "계_0세", "총인구", "0세인구비율"]]
    .reset_index(drop=True)
)
top10.index = top10.index + 1
top10.columns = ["시도", "시군구", "0세 인구 수", "총인구 수", "0세 인구 비율(%)"]

# 하위 10개 (비율이 낮은 순)
bottom10 = (
    sigungu_df.sort_values(by="0세인구비율", ascending=True)
    .head(10)[["시도", "시군구", "계_0세", "총인구", "0세인구비율"]]
    .reset_index(drop=True)
)
bottom10.index = bottom10.index + 1
bottom10.columns = [
    "시도",
    "시군구",
    "0세 인구 수",
    "총인구 수",
    "0세 인구 비율(%)",
]

with col1:
    st.write("🔵 **0세 인구 비율이 가장 높은 지역 TOP 10**")
    st.dataframe(top10, use_container_width=True)

with col2:
    st.write("⚪ **0세 인구 비율이 가장 낮은 지역 TOP 10**")
    st.dataframe(bottom10, use_container_width=True)
