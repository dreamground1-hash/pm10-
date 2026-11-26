import base64
import json
import zlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="미세먼지 농도와 기상 요인의 관계",
    page_icon="🌫️",
    layout="wide",
)

# 사용자가 제공한 2026년 1~2월 및 8~9월 경남 원본 엑셀 자료를 이 파일 안에 포함했습니다.
# 따라서 GitHub에는 main.py와 requirements.txt만 올리면 됩니다.
EMBEDDED_DATA = "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"

@st.cache_data
def load_embedded_data():
    raw = zlib.decompress(base64.b64decode(EMBEDDED_DATA))
    rows = json.loads(raw.decode("utf-8"))
    frame = pd.DataFrame(rows)
    frame["일자"] = pd.to_datetime(frame["일자"], errors="coerce")
    return frame

df = load_embedded_data()
df = df.rename(columns={"PM-10": "PM10", "PM-2.5": "PM2.5"})

st.title("🌫️ 미세먼지 농도와 기상 요인의 관계")
st.markdown(
    "**탐구 질문:** 미세먼지 농도는 정말 바람이 안 불고 추울수록 높아지는가?\n\n"
    "경상남도 대기환경측정망 원본 자료를 이용해 PM10과 풍속·온도의 관계를 그래프로 확인합니다."
)

st.header("1. 데이터 개요")
st.caption("데이터 출처: 경상남도 보건환경연구원, 경상남도 대기환경측정망 자료")
st.caption("포함 자료: 제공된 2026년 1~2월 및 8~9월 엑셀 파일")

c1, c2, c3 = st.columns(3)
c1.metric("전체 행 수", f"{len(df):,}행")
c2.metric("전체 열 수", f"{len(df.columns):,}열")
c3.metric("전체 결측치", f"{int(df.isna().sum().sum()):,}개")

overview = pd.DataFrame({
    "열 이름": df.columns,
    "자료형": [str(df[col].dtype) for col in df.columns],
    "빈 값 개수": [int(df[col].isna().sum()) for col in df.columns],
})
st.dataframe(overview, use_container_width=True, hide_index=True)

valid_dates = df["일자"].dropna()
if not valid_dates.empty:
    st.caption(
        f"실제 자료 기간: {valid_dates.min():%Y-%m-%d} ~ {valid_dates.max():%Y-%m-%d}"
        f" · 자료가 포함된 월: {valid_dates.dt.to_period('M').nunique()}개월"
    )

with st.expander("원본 데이터 전체 보기"):
    display_df = df.copy()
    display_df["일자"] = display_df["일자"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.header("2. 탐구 질문과 연결된 그래프")
st.markdown(
    "아래 그래프는 **PM10**을 대표 미세먼지 지표로 사용합니다. "
    "점 하나는 원본 자료의 하루 관측값이며, 선은 단순 선형회귀 추세선입니다."
)

analysis_columns = ["PM10", "풍속", "온도"]
plot_df = df[analysis_columns].copy()
for col in analysis_columns:
    plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
plot_df = plot_df.replace([np.inf, -np.inf], np.nan).dropna()

st.caption(
    f"회귀 그래프에 사용된 관측 행: {len(plot_df):,} / {len(df):,}행 "
    "(PM10·풍속·온도 중 하나라도 값이 없는 행은 그래프에서 제외)"
)

def make_regression_chart(frame, x_col, x_label, title):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame[x_col],
            y=frame["PM10"],
            mode="markers",
            name="실제 관측값",
            marker={"size": 9, "opacity": 0.75},
            hovertemplate=f"{x_label}: %{{x}}<br>PM10: %{{y}} ㎍/㎥<extra></extra>",
        )
    )
    if frame[x_col].nunique() >= 2:
        slope, intercept = np.polyfit(frame[x_col].to_numpy(), frame["PM10"].to_numpy(), 1)
        x_line = np.linspace(frame[x_col].min(), frame[x_col].max(), 100)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="선형회귀 추세선",
                line={"width": 3},
                hovertemplate=f"{x_label}: %{{x:.2f}}<br>추세선 PM10: %{{y:.2f}} ㎍/㎥<extra></extra>",
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="PM10 농도 (㎍/㎥)",
        height=440,
        legend_title_text="",
        margin={"l": 15, "r": 15, "t": 60, "b": 15},
    )
    return fig

if len(plot_df) < 2:
    st.warning("그래프를 만들 수 있는 유효한 관측값이 2개 미만입니다.")
else:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            make_regression_chart(plot_df, "풍속", "풍속 (m/s)", "풍속과 PM10 농도의 관계"),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            make_regression_chart(plot_df, "온도", "온도 (℃)", "온도와 PM10 농도의 관계"),
            use_container_width=True,
        )

st.info(
    "이 앱은 데이터 개요와 그래프만 제공합니다. 자동 결론이나 탐구 질문의 정답은 표시하지 않습니다. "
    "그래프에서 확인한 특징을 바탕으로 구술 활동에서 직접 설명하세요."
)
