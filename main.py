import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정 및 제목 구성
st.set_page_config(
    page_title="전국 출생아(0세 인구) 변화율 지도", layout="wide"
)
st.title("👶 전국 시군구별 출생아(0세 인구) 변화율 지도")
st.caption(
    "2015년 대비 가장 최신 연도의 시군구별 0세 인구(출생아 수) 변화율(%) 단계구분도"
)


# 2. 데이터 로딩 함수 (streamlit cache 적용으로 빠른 데이터 처리)
@st.cache_data
def load_population_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    # 코드는 앞 5자리 잘라내기를 위해 반드시 문자열(dtype=str)로 읽기
    df = pd.read_csv(url, compression="gzip", dtype={"코드": str})
    return df


@st.cache_data
def load_geojson_data():
    geojson_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    return response.json()


# 데이터 로딩 상태 안내
with st.spinner("인구 및 지도 경계 데이터를 불러오는 중입니다..."):
    pop_df = load_population_data()
    geojson_data = load_geojson_data()


# 3. 0세 인구 계산 및 시군구 단위 집계
# 행정동 코드(10자리)의 앞 5자리를 잘라서 시군구 코드로 사용
pop_df["sigungu_code"] = pop_df["코드"].str[:5]

# 기준 연도(2015년) 및 가장 최신 연도 자동 산출
year_min = 2015
year_max = pop_df["연도"].max()

# 2015년 시군구별 0세 인구 합산
df_2015 = (
    pop_df[pop_df["연도"] == year_min]
    .groupby("sigungu_code")["계_0세"]
    .sum()
    .reset_index()
    .rename(columns={"계_0세": "인구0세_2015"})
)

# 최신 연도 시군구별 0세 인구 합산 (시도, 시군구 명칭 보존)
df_latest = (
    pop_df[pop_df["연도"] == year_max]
    .groupby("sigungu_code")
    .agg({"시도": "first", "시군구": "first", "계_0세": "sum"})
    .reset_index()
    .rename(columns={"계_0세": f"인구0세_{year_max}"})
)

# 두 연도 데이터 병합
merged_df = pd.merge(df_latest, df_2015, on="sigungu_code", how="inner")

# 변화율(%) 계산: (최신 0세인구 - 2015년 0세인구) / 2015년 0세인구 * 100
merged_df["변화율"] = (
    (merged_df[f"인구0세_{year_max}"] - merged_df["인구0세_2015"])
    / merged_df["인구0세_2015"]
    * 100
).round(1)


# 4. 5단계 범례 구간 분할
# 구간: -50% 미만, -50%~-40%, -40%~-30%, -30%~-20%, -20% 이상
bins = [-float("inf"), -50, -40, -30, -20, float("inf")]
labels = [
    "-50% 미만(급감)",
    "-50% 이상 ~ -40% 미만",
    "-40% 이상 ~ -30% 미만",
    "-30% 이상 ~ -20% 미만",
    "-20% 이상",
]

merged_df["변화율_구간"] = pd.cut(
    merged_df["변화율"], bins=bins, labels=labels
)


# 5. Plotly 단계구분도(Choropleth Mapbox) 시각화
# 감소폭이 클수록 진한 붉은색 계열 적용
color_discrete_map = {
    "-50% 미만(급감)": "#67000d",
    "-50% 이상 ~ -40% 미만": "#a50f15",
    "-40% 이상 ~ -30% 미만": "#e31a1c",
    "-30% 이상 ~ -20% 미만": "#fc4e2a",
    "-20% 이상": "#fcbba1",
}

fig = px.choropleth_mapbox(
    merged_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",  # GeoJSON 시군구 코드 매칭
    color="변화율_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"변화율_구간": labels},  # 범례 정렬
    mapbox_style="white-bg",  # 배경 타일 없이 경계선만 표시
    center={"lat": 35.8, "lon": 127.8},  # 대한민국 중심 좌표
    zoom=6.1,
    hover_name="시군구",
    hover_data={
        "시도": True,
        "인구0세_2015": ":,명",
        f"인구0세_{year_max}": ":,명",
        "변화율": ":.1f%",
        "sigungu_code": False,
    },
    labels={
        "변화율_구간": "변화율 구간",
        "인구0세_2015": "2015년 0세 인구",
        f"인구0세_{year_max}": f"{year_max}년 0세 인구",
        "변화율": "변화율(%)",
    },
)

# 지도 스타일 및 범례 위치 지정
fig.update_layout(
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend=dict(
        title=f"<b>0세 인구 변화율 ({year_min} vs {year_max})</b>",
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


# 6. 하단 상위/하위 10개 지역 표 나란히 배치
st.subheader(
    f"📊 {year_min}년 대비 {year_max}년 출생아(0세 인구) 변화 상위/하위 10개 지역"
)

col1, col2 = st.columns(2)

# 감소율이 가장 큰 지역 TOP 10 (변화율 오름차순)
top_decrease = (
    merged_df.sort_values(by="변화율", ascending=True)
    .head(10)[["시도", "시군구", "인구0세_2015", f"인구0세_{year_max}", "변화율"]]
    .reset_index(drop=True)
)
top_decrease.index = top_decrease.index + 1

# 감소율이 적거나 증가한 지역 TOP 10 (변화율 내림차순)
top_stable = (
    merged_df.sort_values(by="변화율", ascending=False)
    .head(10)[["시도", "시군구", "인구0세_2015", f"인구0세_{year_max}", "변화율"]]
    .reset_index(drop=True)
)
top_stable.index = top_stable.index + 1

with col1:
    st.write(
        "🔴 **0세 인구 감소율이 가장 큰 지역 TOP 10** (출생아 급감 및 초저출생 위험 지역)"
    )
    st.dataframe(top_decrease, use_container_width=True)

with col2:
    st.write(
        "🟢 **0세 인구 감소율이 적거나 증가한 지역 TOP 10** (출산율 방어 및 영유아 유입 지역)"
    )
    st.dataframe(top_stable, use_container_width=True)

st.markdown("---")


# 7. 요약 안내 상자 (Info Box)
st.info(f"""
### 💡 출생아 수 급감이 가져올 사회적 영향과 정책적 대안

1. **소아의료 인프라 붕괴 및 보육시설 폐업**
   - 출생아 수의 급격한 감소는 소아청소년과 병·의원의 경영난과 소아 응급의료 체계의 붕괴를 초래합니다.
   - 전국적인 어린이집, 유치원의 연쇄 폐업으로 이어져 지역 내 필수 육아 인프라가 해체되고 있습니다.

2. **초저출생과 지역 소멸의 악순환**
   - 영유아 인구가 줄어든 지역은 젊은 부모 세대의 이탈이 심화되어 지역 인구 구조가 더욱 급격히 고령화됩니다.
   - 이는 생산연령인구 감소와 지자체 세수 감소로 이어져 지역 소멸 위기를 가속화합니다.

3. **출산 장려 및 정주 여건 개선을 위한 대안**
   - **지역 맞춤형 양육 인프라 지원:** 소아 필수 의료 인프라를 공공에서 유지하고, 출산 및 육아 수당 지원을 강화해야 합니다.
   - **일·가정 양립 및 정주 여건 개선:** 신혼부부 주거 지원 및 청년층이 정착할 수 있는 일자리·교육 여건을 조성하는 것이 핵심입니다.
""")
