import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정 및 제목 구성
st.set_page_config(
    page_title="전국 초·중·고 학령인구 변화율 지도", layout="wide"
)
st.title("🏫 전국 시군구별 초·중·고 학령인구(7~18세) 변화율 지도")
st.caption(
    "2015년 대비 가장 최신 연도의 시군구별 초·중·고 학령인구 변화율(%) 단계구분도"
)


# 2. 데이터 로딩 함수 (캐시를 적용하여 새로고침 시 속도 최적화)
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    # 코드는 앞 5자리 잘라내기를 위해 문자열(dtype=str)로 읽기
    df = pd.read_csv(url, compression="gzip", dtype={"코드": str})
    return df


@st.cache_data
def load_geojson_data():
    geojson_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()


# 로딩 안내 메시지
with st.spinner("데이터를 로딩 중입니다..."):
    pop_df = load_population_data()
    geojson_data = load_geojson_data()


# 3. 학령인구(7세 ~ 18세) 계산 및 시군구 단위 집계
# 행정동 코드(10자리)의 앞 5자리를 잘라서 시군구 코드로 지정
pop_df["sigungu_code"] = pop_df["코드"].str[:5]

# 초1~고3 학령인구 열 모으기 ('계_7세'부터 '계_18세'까지)
school_age_cols = [f"계_{age}세" for age in range(7, 19)]

# 행 단위 학령인구 합산
pop_df["학령인구"] = pop_df[school_age_cols].sum(axis=1)

# 기준 연도(2015년) 및 가장 최신 연도 자동 산출
year_min = 2015
year_max = pop_df["연도"].max()

# 2015년 시군구별 학령인구 합산
df_2015 = (
    pop_df[pop_df["연도"] == year_min]
    .groupby("sigungu_code")["학령인구"]
    .sum()
    .reset_index()
    .rename(columns={"학령인구": "학령인구_2015"})
)

# 최신 연도 시군구별 학령인구 합산 (시도, 시군구 명칭 유지)
df_latest = (
    pop_df[pop_df["연도"] == year_max]
    .groupby("sigungu_code")
    .agg({"시도": "first", "시군구": "first", "학령인구": "sum"})
    .reset_index()
    .rename(columns={"학령인구": f"학령인구_{year_max}"})
)

# 시군구 코드로 2015년과 최신 연도 데이터 병합
merged_df = pd.merge(df_latest, df_2015, on="sigungu_code", how="inner")

# 변화율(%) 계산: (최신 학령인구 - 2015년 학령인구) / 2015년 학령인구 * 100
merged_df["변화율"] = (
    (merged_df[f"학령인구_{year_max}"] - merged_df["학령인구_2015"])
    / merged_df["학령인구_2015"]
    * 100
).round(1)


# 4. 5단계 범례 구간 분할
# 구간값: -40% 미만, -40%~-30%, -30%~-20%, -20%~-10%, -10% 이상
bins = [-float("inf"), -40, -30, -20, -10, float("inf")]
labels = [
    "-40% 미만(급감)",
    "-40% 이상 ~ -30% 미만",
    "-30% 이상 ~ -20% 미만",
    "-20% 이상 ~ -10% 미만",
    "-10% 이상",
]

merged_df["변화율_구간"] = pd.cut(
    merged_df["변화율"], bins=bins, labels=labels
)


# 5. Plotly 단계구분도(Choropleth Mapbox) 시각화
# 감소 폭이 클수록 진한 붉은색 계열 적용
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
    featureidkey="properties.코드",  # GeoJSON 내 5자리 코드와 연결
    color="변화율_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"변화율_구간": labels},  # 범례 순서 보정
    mapbox_style="white-bg",  # 지도 타일 배경 없이 경계선만 표시
    center={"lat": 35.8, "lon": 127.8},  # 대한민국 중심 위치
    zoom=6.1,
    hover_name="시군구",
    hover_data={
        "시도": True,
        "학령인구_2015": ":,명",
        f"학령인구_{year_max}": ":,명",
        "변화율": ":.1f%",
        "sigungu_code": False,
    },
    labels={
        "변화율_구간": "변화율 구간",
        "학령인구_2015": "2015년 학령인구",
        f"학령인구_{year_max}": f"{year_max}년 학령인구",
        "변화율": "변화율(%)",
    },
)

# 지도 여백 및 범례 레이아웃 세부 조정
fig.update_layout(
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend=dict(
        title=f"<b>학령인구 변화율 ({year_min} vs {year_max})</b>",
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
st.subheader(
    f"📊 {year_min}년 대비 {year_max}년 초·중·고 학령인구 변화 상위/하위 10개 지역"
)

col1, col2 = st.columns(2)

# 감소율이 가장 큰 지역 TOP 10 (변화율 오름차순)
top_decrease = (
    merged_df.sort_values(by="변화율", ascending=True)
    .head(10)[["시도", "시군구", "학령인구_2015", f"학령인구_{year_max}", "변화율"]]
    .reset_index(drop=True)
)
top_decrease.index = top_decrease.index + 1

# 감소율이 적거나 증가한 지역 TOP 10 (변화율 내림차순)
top_stable = (
    merged_df.sort_values(by="변화율", ascending=False)
    .head(10)[["시도", "시군구", "학령인구_2015", f"학령인구_{year_max}", "변화율"]]
    .reset_index(drop=True)
)
top_stable.index = top_stable.index + 1

with col1:
    st.write(
        "🔴 **학령인구 감소율이 가장 큰 지역 TOP 10** (학교 통폐합 및 지역 소멸 위기)"
    )
    st.dataframe(top_decrease, use_container_width=True)

with col2:
    st.write(
        "🟢 **학령인구 감소율이 적거나 증가한 지역 TOP 10** (신도시 유입 등)"
    )
    st.dataframe(top_stable, use_container_width=True)

st.markdown("---")


# 7. 요약 안내 상자 (Info Box)
st.info(f"""
### 💡 초·중·고 학령인구 감소가 가져올 사회적 영향과 대안

1. **지방 소규모 학교 통폐합 및 교원 수 감축**
   - 학령인구 급감은 학급 수 축소와 소규모 초·중·고등학교의 통폐합을 가속화합니다.
   - 이는 신규 교원 임용 규모 감소 및 교육 현장의 구조적 변화로 이어집니다.

2. **지역 교육 인프라 해체와 지방 소멸 위험**
   - 학교가 사라진 지역은 자녀 교육 문제로 인해 젊은 인구의 이탈이 더욱 가속화되는 악순환을 겪습니다.
   - 이는 거주 여건 악화와 더불어 지방 소멸을 촉진하는 주요 원인이 됩니다.

3. **대응 과제 및 정책적 대안**
   - **거점학교 육성 및 방과후 다목적 센터화:** 학교를 지역 커뮤니티 및 복지 거점으로 재탄생시킵니다.
   - **정주 여건 개선:** 신도시처럼 청년·신혼부부 정주 여건이 좋아 인구가 유입되는 성공 사례를 모델링하여 지방 도시 정주 환경을 개편해야 합니다.
""")
