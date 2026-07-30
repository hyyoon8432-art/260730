import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. 페이지 기본 설정 및 제목 표시
st.set_page_config(page_title="전국 시군구 고령화 지도", layout="wide")
st.title("🗺️ 전국 시군구별 고령화 비율 지도")
st.caption("최신 연도 데이터 기준 65세 이상 인구 비율(%) 단계구분도")


# 2. 데이터 로딩 (캐시 적용으로 매번 다시 불러오는 부담 축소)
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    # 코드는 5자리 시군구 추출을 위해 문자열(dtype=str)로 읽기
    df = pd.read_csv(url, compression="gzip", dtype={"코드": str})
    return df


@st.cache_data
def load_geojson_data():
    geojson_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()


# 로딩 상태 안내
with st.spinner("데이터를 불러오는 중입니다..."):
    pop_df = load_population_data()
    geojson_data = load_geojson_data()


# 3. 데이터 가공 및 65세 이상 고령화율 계산
# 가장 최신 연도 자동 필터링
latest_year = pop_df["연도"].max()
df_latest = pop_df[pop_df["연도"] == latest_year].copy()

# 행정동 코드(10자리)의 앞 5자리를 잘라서 시군구 코드로 사용
df_latest["sigungu_code"] = df_latest["코드"].str[:5]

# 65세 이상 인구합 계산을 위한 열(Column) 이름 모으기 ('계_65세' ~ '계_100세 이상')
# 전체 인구 합산 열은 '계_0세'부터 시작하는 모든 '계_' 시작 열의 합
total_pop_cols = [col for col in df_latest.columns if col.startswith("계_")]

elderly_cols = []
for col in total_pop_cols:
    age_str = col.replace("계_", "").replace("세 이상", "").replace("세", "")
    if age_str.isdigit():
        if int(age_str) >= 65:
            elderly_cols.append(col)
    elif "100" in col:  # '계_100세 이상' 처리
        elderly_cols.append(col)

# 시군구 단위로 총인구와 65세 이상 인구 집계
df_latest["총인구"] = df_latest[total_pop_cols].sum(axis=1)
df_latest["고령인구"] = df_latest[elderly_cols].sum(axis=1)

# 시군구별(sigungu_code) GroupBy 합산
# 시도, 시군구 명칭은 표시에 사용하기 위해 first()로 가져옴
sigungu_df = (
    df_latest.groupby("sigungu_code")
    .agg({"시도": "first", "시군구": "first", "총인구": "sum", "고령인구": "sum"})
    .reset_index()
)

# 고령화율(%) 계산 (소수점 첫째 자리까지)
sigungu_df["고령화율"] = (
    sigungu_df["고령인구"] / sigungu_df["총인구"] * 100
).round(1)


# 4. 5단계 범례 구간 할당 (19%, 23%, 28%, 38% 경계 기준)
bins = [-1, 19, 23, 28, 38, 100]
labels = [
    "19% 미만",
    "19% 이상 ~ 23% 미만",
    "23% 이상 ~ 28% 미만",
    "28% 이상 ~ 38% 미만",
    "38% 이상",
]

sigungu_df["고령화_구간"] = pd.cut(
    sigungu_df["고령화율"], bins=bins, labels=labels
)


# 5. Plotly 단계구분도(Choropleth) 생성
# 5단계 옅은 색 ~ 진한 색상 팔레트 (Purples 기준)
color_discrete_map = {
    "19% 미만": "#f2f0f7",
    "19% 이상 ~ 23% 미만": "#cbc9e2",
    "23% 이상 ~ 28% 미만": "#9e9ac8",
    "28% 이상 ~ 38% 미만": "#756bb1",
    "38% 이상": "#542788",
}

fig = px.choropleth_mapbox(
    sigungu_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",  # GeoJSON 내 시군구 코드 속성
    color="고령화_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"고령화_구간": labels},  # 범례 순서 정렬
    mapbox_style="white-bg",  # 지도 타일 배경 없이 경계선만 표시
    center={"lat": 35.8, "lon": 127.8},  # 대한민국 중심 좌표
    zoom=6.1,
    hover_name="시군구",
    hover_data={"시도": True, "고령화율": ":.1f%", "sigungu_code": False},
    labels={"고령화_구간": "고령화율 구간", "고령화율": "고령화율(%)"},
)

# 지도 스타일 및 여백 세부 조정
fig.update_layout(
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend=dict(
        title="<b>고령화 비율 구간</b>",
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


# 6. 하단 상위/하위 10개 지역 표 나란히 표시
st.subheader(f"📊 {latest_year}년 시군구 고령화율 순위 (상위/하위 10곳)")

col1, col2 = st.columns(2)

# 상위 10개 (고령화율 높은 순)
top10 = (
    sigungu_df.sort_values(by="고령화율", ascending=False)
    .head(10)[["시도", "시군구", "고령화율"]]
    .reset_index(drop=True)
)
top10.index = top10.index + 1  # 순위 1부터 시작

# 하위 10개 (고령화율 낮은 순)
bottom10 = (
    sigungu_df.sort_values(by="고령화율", ascending=True)
    .head(10)[["시도", "시군구", "고령화율"]]
    .reset_index(drop=True)
)
bottom10.index = bottom10.index + 1

with col1:
    st.write("🔴 **고령화율 가장 높은 지역 TOP 10**")
    st.dataframe(top10, use_container_width=True)

with col2:
    st.write("🔵 **고령화율 가장 낮은 지역 TOP 10**")
    st.dataframe(bottom10, use_container_width=True)
