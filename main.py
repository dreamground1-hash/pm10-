import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(
    page_title="미세먼지와 기상 요인 분석",
    page_icon="🌫️",
    layout="wide"
)

st.title("🌫️ 미세먼지 농도와 기상 요인의 관계")
st.markdown(
    """
    **탐구 질문:** 미세먼지 농도는 정말 바람이 안 불고 추울수록 높아지는가?

    경상남도 대기환경측정망 자료에서 **PM10, 풍속, 온도**를 이용해 그래프로 살펴봅니다.
    """
)

st.subheader("데이터 파일 업로드")
uploaded_files = st.file_uploader(
    "경상남도 대기환경측정망 엑셀 또는 CSV 파일을 업로드하세요. 여러 파일을 함께 선택할 수 있습니다.",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("엑셀 또는 CSV 파일을 업로드하면 데이터 개요와 그래프가 표시됩니다.")
    st.stop()


def load_file(uploaded_file):
    content = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith((".xlsx", ".xls")):
        data = pd.read_excel(BytesIO(content))
    elif filename.endswith(".csv"):
        try:
            data = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
        except UnicodeDecodeError:
            data = pd.read_csv(BytesIO(content), encoding="cp949")
    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")

    data.columns = [str(column).strip() for column in data.columns]
    return data


frames = []
for uploaded_file in uploaded_files:
    try:
        frames.append(load_file(uploaded_file))
    except Exception as error:
        st.error(f"{uploaded_file.name} 파일을 읽지 못했습니다: {error}")

if not frames:
    st.stop()

df = pd.concat(frames, ignore_index=True, sort=False)

# 실제 자료의 열 이름(PM-10, PM-2.5)을 표준 이름으로 통일
rename_columns = {}
for column in df.columns:
    normalized = str(column).strip().upper().replace(" ", "")
    if normalized in ["PM-10", "PM10"]:
        rename_columns[column] = "PM10"
    elif normalized in ["PM-2.5", "PM2.5"]:
        rename_columns[column] = "PM2.5"
    elif normalized in ["일자", "날짜", "측정일"]:
        rename_columns[column] = "일자"
    elif normalized in ["풍속"]:
        rename_columns[column] = "풍속"
    elif normalized in ["온도", "기온"]:
        rename_columns[column] = "온도"
    elif normalized in ["습도"]:
        rename_columns[column] = "습도"
df = df.rename(columns=rename_columns)

st.header("1. 데이터 개요")

row_count = len(df)
column_count = len(df.columns)
missing_total = int(df.isna().sum().sum())

metric1, metric2, metric3 = st.columns(3)
metric1.metric("전체 행 수", f"{row_count:,}행")
metric2.metric("전체 열 수", f"{column_count:,}열")
metric3.metric("전체 빈 값 수", f"{missing_total:,}개")

st.markdown("**열 이름 · 자료형 · 빈 값 개수**")
overview = pd.DataFrame({
    "열 이름": df.columns,
    "자료형": [str(df[column].dtype) for column in df.columns],
    "빈 값 개수": [int(df[column].isna().sum()) for column in df.columns]
})
st.dataframe(overview, use_container_width=True, hide_index=True)

with st.expander("업로드한 데이터 미리 보기"):
    st.dataframe(df, use_container_width=True, hide_index=True)

st.header("2. 탐구 질문과 연결된 그래프")

required_columns = ["PM10", "풍속", "온도"]
missing_columns = [column for column in required_columns if column not in df.columns]

if missing_columns:
    st.error(
        "그래프를 만들기 위한 열을 찾을 수 없습니다: "
        + ", ".join(missing_columns)
        + ". 파일의 열 이름을 확인해 주세요. PM-10(또는 PM10), 풍속, 온도가 필요합니다."
    )
    st.stop()

# 그래프에 필요한 열을 숫자형으로 변환하고, 해당 열에 결측값이 있는 행만 제외
plot_df = df[required_columns].copy()
for column in required_columns:
    plot_df[column] = pd.to_numeric(plot_df[column], errors="coerce")
plot_df = plot_df.replace([np.inf, -np.inf], np.nan).dropna()

st.caption(
    f"그래프에는 PM10, 풍속, 온도 값이 모두 있는 {len(plot_df):,}개 행을 사용합니다. "
    "데이터 전체를 임의로 생성하거나 결측값을 채우지 않았습니다."
)

if len(plot_df) < 2:
    st.warning("그래프를 그리려면 세 변수의 값이 모두 있는 데이터가 2개 이상 필요합니다.")
    st.stop()


def scatter_with_trend(data, x_column, x_title, chart_title):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x_column],
            y=data["PM10"],
            mode="markers",
            name="실제 관측값",
            marker={"size": 8, "opacity": 0.7}
        )
    )

    # x값이 모두 같으면 회귀선을 계산할 수 없으므로 산점도만 표시
    if data[x_column].nunique() >= 2:
        slope, intercept = np.polyfit(data[x_column], data["PM10"], 1)
        x_line = np.linspace(data[x_column].min(), data[x_column].max(), 100)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="선형 추세선",
                line={"width": 3}
            )
        )

    fig.update_layout(
        title=chart_title,
        xaxis_title=x_title,
        yaxis_title="PM10 농도 (㎍/㎥)",
        height=440,
        legend_title_text=""
    )
    return fig


left, right = st.columns(2)

with left:
    st.plotly_chart(
        scatter_with_trend(
            plot_df,
            "풍속",
            "풍속 (m/s)",
            "풍속과 PM10 농도의 관계"
        ),
        use_container_width=True
    )

with right:
    st.plotly_chart(
        scatter_with_trend(
            plot_df,
            "온도",
            "온도 (℃)",
            "온도와 PM10 농도의 관계"
        ),
        use_container_width=True
    )

st.caption(
    "그래프는 변수 사이의 분포와 선형 추세를 시각적으로 확인하기 위한 것입니다. "
    "그래프에 대한 결론이나 탐구 질문의 답은 앱에서 제시하지 않으며, "
    "그래프를 직접 살펴보고 구술 활동에서 설명합니다."
)
