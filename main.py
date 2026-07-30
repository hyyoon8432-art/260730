import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="전국 고교 학령인구 감소율 지도", layout="wide"
)
st.title("🎓 전국 시군구별 고교 학령인구(16~18세) 감소율 지도")
st.caption(
    "2015년 대비 최신 연도의 시군구별 고교 학령인구 변화율(%) 단계구분도"
)


# 2. 데이터 로딩 함수 (streamlit cache 적용으로 빠른 로딩)
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    # 코드는 앞 5자리 추출을 위해 반드시 문자열(dtype=str)로 지정해서 불러옵니다.
    df = pd.read_csv(url, compression="gzip", dtype={"코드": str})
    return df


@st.cache_data
def load_geojson_data():
    geojson_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()


# 데이터 로딩 상태 표시
with st.spinner("인구 및 지도 경계 데이터를 불러오는 중입니다..."):
    pop_df = load_population_data()
    geojson_data = load_geojson_data()


# 3. 데이터 가공 및 고교 학령인구(16~18세) 계산
# 행정동 코드(10자리)의 앞 5자리를 잘라서 시군구 코드로 사용
pop_df["sigungu_code"] = pop_df["코드"].str[:5]

# 고교 학령인구 열(계_16세, 계_17세, 계_18세)의 합계 계산
hs_cols = ["계_16세", "계_17세", "계_18세"]
pop_df["고교생인구"] = pop_df[hs_cols].sum(axis=1)

# 기준 연도(2015년) 및 최신 연도 자동 도출
year_min = 2015
year_max = pop_df["연도"].max()

# 2015년 시군구별 고교생 인구 집계
df_2015 = (
    pop_df[pop_df["연도"] == year_min]
    .groupby("sigungu_code")["고교생인구"]
    .sum()
    .reset_index()
    .rename(columns={"고교생인구": "고교생_2015"})
)

# 최신 연도 시군구별 고교생 인구 집계 (시도, 시군구 이름 포함)
df_latest = (
    pop_df[pop_df["연도"] == year_max]
    .groupby("sigungu_code")
    .agg({"시도": "first", "시군구": "first", "고교생인구": "sum"})
    .reset_index()
    .rename(columns={"고교생인구": f"고교생_{year_max}"})
)

# 두 연도 데이터 병합
merged_df = pd.merge(df_latest, df_2015, on="sigungu_code", how="inner")

# 감소율(%) 계산: (최신인구 - 2015년인구) / 2015년인구 * 100
merged_df["감소율"] = (
    (merged_df[f"고교생_{year_max}"] - merged_df["고교생_2015"])
    / merged_df["고교생_2015"]
    * 100
).round(1)


# 4. 5단계 범례 구간 지정
# 구간: -40% 미만, -40%~-30%, -30%~-20%, -20%~-10%, -10% 이상
bins = [-float("inf"), -40, -30, -20, -10, float("inf")]
labels = [
    "-40% 미만(급감)",
    "-40% 이상 ~ -30% 미만",
    "-30% 이상 ~ -20% 미만",
    "-20% 이상 ~ -10% 미만",
    "-10% 이상",
]

merged_df["감소율_구간"] = pd.cut(
    merged_df["감소율"], bins=bins, labels=labels
)


# 5. Plotly 단계구분도(Choropleth) 시각화
# 감소폭이 클수록 진한 색(Reds 계열)
color_discrete_map = {
    "-40% 미만(급감)": "#67000d",
    "-40% 이상 ~ -30% 미만": "#a50f15",
    "-30% 이상 ~ -20% 미만": "#e31a1c",
    "-20% 이상 ~ -10% 미만": "#fc4e2a",
    "-10% 이상": "#fcbba1",
}

fig = px.choropleth_mapbox(
    merged_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",  # GeoJSON 내 시군구 코드 속성 매칭
    color="감소율_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"감소율_구간": labels},  # 범례 순서 정렬
    mapbox_style="white-bg",  # 배경지도 타일 없이 경계선만 표시
    center={"lat": 35.8, "lon": 127.8},  # 대한민국 중심 좌표
    zoom=6.1,
    hover_name="시군구",
    hover_data={
        "시도": True,
        "고교생_2015": ":,명",
        f"고교생_{year_max}": ":,명",
        "감소율": ":.1f%",
        "sigungu_code": False,
    },
    labels={
        "감소율_구간": "감소율 구간",
        "고교생_2015": "2015년 고교생 수",
        f"고교생_{year_max}": f"{year_max}년 고교생 수",
        "감소율": "감소율(%)",
    },
)

# 지도 레이아웃 세부 조절
fig.update_layout(
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend=dict(
        title=f"<b>고교생 감소율 ({year_min} vs {year_max})</b>",
        yanchor="top",
        y=0.98,
        xanchor="left",
        x=0.02,
        bgcolor="rgba(255, 255, 255, 0.8)",
    ),
)

# 지도 출력
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# 6. 하단 상위/하위 10개 지역 표 나란히 표시
st.subheader(
    f"📊 {year_min}년 대비 {year_max}년 고교 학령인구 변화 상위/하위 10개 지역"
)

col1, col2 = st.columns(2)

# 감소율이 가장 큰 지역 TOP 10 (감소율 오름차순)
top_decrease = (
    merged_df.sort_values(by="감소율", ascending=True)
    .head(10)[["시도", "시군구", "고교생_2015", f"고교생_{year_max}", "감소율"]]
    .reset_index(drop=True)
)
top_decrease.index = top_decrease.index + 1

# 감소율이 적거나 증가한 지역 TOP 10 (감소율 내림차순)
top_stable = (
    merged_df.sort_values(by="감소율", ascending=False)
    .head(10)[["시도", "시군구", "고교생_2015", f"고교생_{year_max}", "감소율"]]
    .reset_index(drop=True)
)
top_stable.index = top_stable.index + 1

with col1:
    st.write(
        "🔴 **고교생 인구 감소율이 가장 큰 지역 TOP 10** (대학 미달 및 상권 위축 위험)"
    )
    st.dataframe(top_decrease, use_container_width=True)

with col2:
    st.write("🟢 **고교생 인구 감소율이 적거나 증가한 지역 TOP 10**")
    st.dataframe(top_stable, use_container_width=True)

st.markdown("---")


# 7. 요약 안내 상자 (Info Box)
st.info(f"""
### 💡 고교 학령인구 감소가 가져올 미래 변화와 대안

1. **지방 대학 입시 자원 부족 및 미달 사태**
   - 고교 학령인구의 급감은 지방 소재 대학의 신입생 충원율에 직접적인 타격을 줍니다.
   - 입학 정원 미달 현상이 심화되면서 일부 지방 대학의 폐교 및 학과 구조조정이 가속화되고 있습니다.

2. **대학가 상권 침체 및 지역 경제 위축**
   - 대학생 유동인구에 의존하던 원룸촌, 식당가, 유흥가 등 대학가 상권의 매출이 급감합니다.
   - 이는 청년층 인구의 이탈을 촉진하며, 지역 상권 쇠퇴와 지방 소멸 위험으로 직결됩니다.

3. **대응 과제 및 해결 방안**
   - **지자체-대학 협력(RIS 사업):** 지역 산업과 연계한 특성화 교육을 강화하여 지역 정주 인구를 늘려야 합니다.
   - **외국인 유학생 유치 및 평생교육 전환:** 학령인구 이외의 유학생 및 성인 학습자를 대상으로 한 교육 모델 전환이 필요합니다.
""")
