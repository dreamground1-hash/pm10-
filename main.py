import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import linregress
import statsmodels.api as sm
from io import BytesIO

st.set_page_config(
    page_title="미세먼지 농도와 기상 요인의 관계 분석",
    page_icon="🌫️",
    layout="wide"
)

st.title("🌫️ 미세먼지 농도와 기상 요인의 관계 분석")
st.caption("경상남도 대기환경측정망 자료를 활용한 PM10 회귀분석")
st.markdown(
    """
    **탐구 질문:** 미세먼지 농도는 정말 바람이 안 불고 추울수록 높아지는가?

    분석 대상은 **PM10**이며, 풍속·온도·습도를 설명변수로 사용합니다.
    """
)

# -----------------------------
# 데이터 읽기 및 열 이름 정리
# -----------------------------
RENAME_MAP = {
    "PM-10": "PM10",
    "PM10": "PM10",
    "PM-2.5": "PM2.5",
    "PM2.5": "PM2.5",
    "일자": "일자",
    "풍속": "풍속",
    "습도": "습도",
    "온도": "온도",
}

REQUIRED = ["PM10", "풍속", "온도", "습도"]
NUMERIC_CANDIDATES = ["PM10", "PM2.5", "PM-10", "PM-2.5", "O3", "CO", "SO2", "NO2", "풍속", "습도", "온도"]

def read_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    if name.endswith((".xlsx", ".xls")):
        data = pd.read_excel(BytesIO(raw))
    elif name.endswith(".csv"):
        try:
            data = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            data = pd.read_csv(BytesIO(raw), encoding="cp949")
    else:
        raise ValueError("엑셀(.xlsx, .xls) 또는 CSV 파일만 업로드할 수 있습니다.")

    data.columns = [str(c).strip() for c in data.columns]
    data = data.rename(columns=RENAME_MAP)
    return data

def normalize_date(series):
    # 숫자형 YYYYMMDD와 문자열 날짜를 모두 처리
    text = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    parsed = pd.to_datetime(text, format="%Y%m%d", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(text.loc[missing], errors="coerce")
    return parsed

def make_download_csv(data):
    return data.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

uploaded_files = st.file_uploader(
    "경상남도 대기환경측정망 엑셀 또는 CSV 파일을 업로드하세요. 여러 파일을 한 번에 선택할 수 있습니다.",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("분석을 시작하려면 보유한 원본 파일을 업로드하세요. 예: 1~2월 농도.xlsx, 8~9월 농도.xlsx")
    st.stop()

frames = []
file_errors = []
for file in uploaded_files:
    try:
        frames.append(read_uploaded_file(file))
    except Exception as e:
        file_errors.append(f"{file.name}: {e}")

if file_errors:
    for message in file_errors:
        st.error(message)

if not frames:
    st.error("읽을 수 있는 데이터 파일이 없습니다.")
    st.stop()

df_original = pd.concat(frames, ignore_index=True, sort=False)
original_rows = len(df_original)
original_cols = len(df_original.columns)

# 날짜 및 숫자형 변환
if "일자" in df_original.columns:
    df_original["일자"] = normalize_date(df_original["일자"])

for col in NUMERIC_CANDIDATES:
    actual_col = RENAME_MAP.get(col, col)
    if actual_col in df_original.columns:
        df_original[actual_col] = pd.to_numeric(df_original[actual_col], errors="coerce")

# 중복 날짜는 자동 삭제하지 않고 사용자에게 알림
duplicate_dates = 0
if "일자" in df_original.columns:
    duplicate_dates = int(df_original["일자"].duplicated(keep=False).sum())

# -----------------------------
# 데이터 개요
# -----------------------------
st.header("1. 데이터 개요")

date_valid = df_original["일자"].dropna() if "일자" in df_original.columns else pd.Series(dtype="datetime64[ns]")
date_start = date_valid.min().strftime("%Y-%m-%d") if len(date_valid) else "확인 불가"
date_end = date_valid.max().strftime("%Y-%m-%d") if len(date_valid) else "확인 불가"
month_count = int(date_valid.dt.to_period("M").nunique()) if len(date_valid) else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 행 수", f"{original_rows:,}행")
c2.metric("전체 열 수", f"{original_cols:,}열")
c3.metric("자료 시작일", date_start)
c4.metric("자료 마지막 날짜", date_end)

c5, c6 = st.columns(2)
c5.metric("자료가 포함된 월", f"{month_count}개월")
c6.metric("중복 날짜가 포함된 행", f"{duplicate_dates:,}행")

st.subheader("열 이름과 자료형")
dtype_table = pd.DataFrame({
    "열 이름": df_original.columns,
    "자료형": [str(dtype) for dtype in df_original.dtypes],
    "결측치 수": [int(df_original[col].isna().sum()) for col in df_original.columns]
})
st.dataframe(dtype_table, use_container_width=True, hide_index=True)

st.subheader("원본 데이터 미리보기")
st.dataframe(df_original, use_container_width=True, hide_index=True)

missing_required_cols = [col for col in REQUIRED if col not in df_original.columns]
if missing_required_cols:
    st.error(f"필수 분석 열이 없습니다: {', '.join(missing_required_cols)}")
    st.write("파일의 열 이름을 확인해 주세요. 필요한 열은 PM-10(또는 PM10), 풍속, 습도, 온도입니다.")
    st.stop()

# -----------------------------
# 전처리
# -----------------------------
st.header("2. 데이터 전처리")

analysis_df = df_original.copy()
for col in REQUIRED:
    analysis_df[col] = pd.to_numeric(analysis_df[col], errors="coerce")

before_rows = len(analysis_df)
missing_by_row = analysis_df[REQUIRED].isna().any(axis=1)
missing_rows = int(missing_by_row.sum())
clean_df = analysis_df.loc[~missing_by_row].copy()
after_missing_rows = len(clean_df)

# IQR 이상치 탐지: 제거하지 않고 표시
outlier_flags = pd.DataFrame(index=clean_df.index)
iqr_summary = []
for col in REQUIRED:
    q1 = clean_df[col].quantile(0.25)
    q3 = clean_df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    flag = (clean_df[col] < lower) | (clean_df[col] > upper)
    outlier_flags[col] = flag
    iqr_summary.append({
        "변수": col,
        "Q1": q1,
        "Q3": q3,
        "IQR": iqr,
        "하한": lower,
        "상한": upper,
        "이상치 개수": int(flag.sum())
    })

clean_df["이상치 포함"] = outlier_flags.any(axis=1)
outlier_rows = int(clean_df["이상치 포함"].sum())

p1, p2, p3 = st.columns(3)
p1.metric("전처리 전 행 수", f"{before_rows:,}행")
p2.metric("결측치로 제외한 행", f"{missing_rows:,}행")
p3.metric("회귀분석에 사용할 행 수", f"{after_missing_rows:,}행")

st.markdown(
    """
    - **결측치 처리:** PM10, 풍속, 온도, 습도 중 하나라도 값이 없는 행은 회귀분석에서 제외했습니다.
    - **이상치 처리:** 각 변수에 IQR 기준(1.5×IQR)을 적용해 이상치를 표시했지만, 실제 관측값일 수 있으므로 임의로 삭제하지 않았습니다.
    - **중복 날짜:** 중복 날짜가 있더라도 자동 삭제하지 않았습니다. 같은 날짜의 측정소별 관측값일 가능성이 있으므로 원자료의 구조를 확인해야 합니다.
    """
)
st.write(f"결측치 처리 후 행 수: **{after_missing_rows:,}행**")
st.write(f"IQR 기준 이상치가 하나 이상 포함된 행: **{outlier_rows:,}행** (삭제하지 않음)")
st.subheader("변수별 IQR 이상치 확인")
st.dataframe(pd.DataFrame(iqr_summary).round(3), use_container_width=True, hide_index=True)

if len(clean_df) < 3:
    st.error("회귀분석을 수행하기에 유효한 데이터가 부족합니다. 최소 3개 이상의 유효한 행이 필요합니다.")
    st.stop()

# -----------------------------
# 회귀분석
# -----------------------------
st.header("3. 회귀분석")

st.caption("PM10을 종속변수로 설정했습니다. 단순회귀분석은 변수별 관계를, 다중회귀분석은 풍속·온도·습도를 함께 고려한 관계를 살펴봅니다.")

def simple_regression(data, x_col, y_col="PM10"):
    result = linregress(data[x_col], data[y_col])
    return result

def plot_simple_regression(data, x_col, x_label, title):
    result = simple_regression(data, x_col)
    fig = px.scatter(
        data,
        x=x_col,
        y="PM10",
        trendline="ols",
        title=title,
        labels={x_col: x_label, "PM10": "PM10 농도 (㎍/㎥)"},
        hover_data=["일자"] if "일자" in data.columns else None
    )
    fig.update_layout(height=440)
    return fig, result

# ① 풍속
st.subheader("① 풍속과 PM10의 관계")
if clean_df["풍속"].nunique() < 2:
    st.warning("풍속 값이 모두 같아 단순회귀분석을 수행할 수 없습니다.")
else:
    wind_fig, wind_res = plot_simple_regression(
        clean_df, "풍속", "풍속 (m/s)", "풍속과 PM10 농도의 관계"
    )
    st.plotly_chart(wind_fig, use_container_width=True)
    a, b, c, d = st.columns(4)
    a.metric("회귀계수", f"{wind_res.slope:.4f}")
    b.metric("상관계수", f"{wind_res.rvalue:.4f}")
    c.metric("결정계수 R²", f"{wind_res.rvalue**2:.4f}")
    d.metric("p값", f"{wind_res.pvalue:.4g}")
    if wind_res.slope < 0:
        wind_direction = "풍속이 증가할수록 PM10이 감소하는 방향"
    elif wind_res.slope > 0:
        wind_direction = "풍속이 증가할수록 PM10이 증가하는 방향"
    else:
        wind_direction = "풍속과 PM10 사이에 선형적인 증가·감소 방향이 거의 없는 상태"
    st.write(f"**해석:** 회귀계수는 {wind_res.slope:.4f}이며, {wind_direction}의 관계가 관찰됩니다.")
    st.write("p값은 통계적 유의성을 살펴보는 참고값입니다. 일반적으로 p<0.05일 때 통계적으로 유의한 선형 관계의 근거가 있다고 해석하지만, 인과관계를 증명하지는 않습니다.")

# ② 온도
st.subheader("② 온도와 PM10의 관계")
if clean_df["온도"].nunique() < 2:
    st.warning("온도 값이 모두 같아 단순회귀분석을 수행할 수 없습니다.")
else:
    temp_fig, temp_res = plot_simple_regression(
        clean_df, "온도", "온도 (℃)", "온도와 PM10 농도의 관계"
    )
    st.plotly_chart(temp_fig, use_container_width=True)
    a, b, c, d = st.columns(4)
    a.metric("회귀계수", f"{temp_res.slope:.4f}")
    b.metric("상관계수", f"{temp_res.rvalue:.4f}")
    c.metric("결정계수 R²", f"{temp_res.rvalue**2:.4f}")
    d.metric("p값", f"{temp_res.pvalue:.4g}")
    if temp_res.slope < 0:
        temp_direction = "온도가 높아질수록 PM10이 감소하는 방향"
    elif temp_res.slope > 0:
        temp_direction = "온도가 높아질수록 PM10이 증가하는 방향"
    else:
        temp_direction = "온도와 PM10 사이에 선형적인 증가·감소 방향이 거의 없는 상태"
    st.write(f"**해석:** 회귀계수는 {temp_res.slope:.4f}이며, {temp_direction}의 관계가 관찰됩니다.")
    st.write("따라서 추울수록 PM10이 높아진다는 예상과 일치하는지 회귀계수의 부호를 확인할 수 있습니다.")

# ③ 다중회귀
st.subheader("③ 풍속·온도·습도를 함께 고려한 다중회귀분석")
X = clean_df[["풍속", "온도", "습도"]].astype(float)
y = clean_df["PM10"].astype(float)

if X.nunique().min() < 2:
    st.warning("독립변수 중 값이 모두 같은 변수가 있어 다중회귀분석 결과가 불안정할 수 있습니다.")
else:
    X_const = sm.add_constant(X)
    try:
        model = sm.OLS(y, X_const).fit()
        model_table = pd.DataFrame({
            "변수": model.params.index,
            "회귀계수": model.params.values,
            "p값": model.pvalues.values
        })
        st.dataframe(model_table.round(5), use_container_width=True, hide_index=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("다중회귀 결정계수 R²", f"{model.rsquared:.4f}")
        m2.metric("수정 결정계수", f"{model.rsquared_adj:.4f}")
        m3.metric("분석 데이터 수", f"{int(model.nobs):,}개")

        # 표준화 회귀계수
        std_X = (X - X.mean()) / X.std(ddof=0)
        std_y = (y - y.mean()) / y.std(ddof=0)
        std_model = sm.OLS(std_y, sm.add_constant(std_X)).fit()
        std_coefs = std_model.params.drop("const", errors="ignore").sort_values(key=lambda s: s.abs(), ascending=False)

        coef_df = std_coefs.rename("표준화 회귀계수").reset_index()
        coef_df.columns = ["변수", "표준화 회귀계수"]
        coef_fig = px.bar(
            coef_df,
            x="변수",
            y="표준화 회귀계수",
            title="기상 요인별 표준화 회귀계수 비교",
            labels={"변수": "독립변수", "표준화 회귀계수": "표준화 회귀계수"}
        )
        coef_fig.update_layout(height=380)
        st.plotly_chart(coef_fig, use_container_width=True)

        st.markdown("**다중회귀분석 해석 시 주의할 점**")
        st.write("표준화 회귀계수의 절댓값이 클수록 다른 변수를 함께 고려했을 때 상대적인 관계의 크기가 큰 것으로 볼 수 있습니다. 다만 변수 사이의 상관관계가 높으면 계수 해석이 불안정해질 수 있습니다.")
        with st.expander("회귀분석 상세 결과 보기"):
            st.text(model.summary().as_text())
    except Exception as e:
        st.error(f"다중회귀분석 중 문제가 발생했습니다: {e}")
        model = None

# -----------------------------
# 결과 해석
# -----------------------------
st.header("4. 결과 해석 및 탐구 질문에 대한 답변")

if clean_df["풍속"].nunique() >= 2 and clean_df["온도"].nunique() >= 2:
    wind_text = "음의 관계" if wind_res.slope < 0 else ("양의 관계" if wind_res.slope > 0 else "뚜렷한 선형 방향이 없는 관계")
    temp_text = "음의 관계" if temp_res.slope < 0 else ("양의 관계" if temp_res.slope > 0 else "뚜렷한 선형 방향이 없는 관계")

    st.markdown("**① 풍속에 대한 결과**")
    st.write(
        f"풍속과 PM10의 상관계수는 **{wind_res.rvalue:.3f}**, 결정계수는 **{wind_res.rvalue**2:.3f}**입니다. "
        f"두 변수는 {wind_text}를 보이며, 회귀계수는 **{wind_res.slope:.3f}**입니다."
    )
    st.markdown("**② 온도에 대한 결과**")
    st.write(
        f"온도와 PM10의 상관계수는 **{temp_res.rvalue:.3f}**, 결정계수는 **{temp_res.rvalue**2:.3f}**입니다. "
        f"두 변수는 {temp_text}를 보이며, 회귀계수는 **{temp_res.slope:.3f}**입니다."
    )
    stronger = "풍속" if abs(wind_res.rvalue) > abs(temp_res.rvalue) else "온도"
    st.markdown("**③ 두 변수 비교**")
    st.write(
        f"단순 상관계수의 절댓값을 비교하면 **{stronger}**가 PM10과 더 강한 선형 관계를 보였습니다. "
        "이는 이번 자료에서 관찰된 관계의 크기 비교이며, 원인이나 영향력을 확정하는 것은 아닙니다."
    )

    st.markdown("**④ 탐구 질문에 대한 잠정적인 답변**")
    if wind_res.slope < 0 and temp_res.slope > 0:
        answer = "이번 자료에서는 풍속이 낮을수록, 온도가 낮을수록 PM10이 높아지는 경향과 대체로 일치하는 결과가 나타났습니다."
    elif wind_res.slope < 0 and temp_res.slope <= 0:
        answer = "이번 자료에서는 풍속에 대해서는 예상과 일치하는 방향이 나타났지만, 온도에 대해서는 '추울수록 높다'는 예상과 일치하지 않는 방향이 나타났습니다."
    elif wind_res.slope >= 0 and temp_res.slope > 0:
        answer = "이번 자료에서는 온도에 대해서는 예상과 일치하는 방향이 나타났지만, 풍속에 대해서는 '바람이 약할수록 높다'는 예상과 일치하지 않는 방향이 나타났습니다."
    else:
        answer = "이번 자료에서는 풍속과 온도 모두 처음 예상과 일치하지 않거나 뚜렷한 선형 관계가 나타나지 않았습니다."
    st.write(answer)
    st.caption("이 답변은 회귀계수의 방향을 바탕으로 한 자동 요약입니다. p값, 표본 수, 결정계수와 자료의 한계도 함께 확인해 최종 결론을 작성하세요.")
else:
    st.info("풍속과 온도의 단순회귀 결과가 모두 계산된 경우 결과 해석이 표시됩니다.")

st.subheader("탐구의 한계 및 추가로 확인할 점")
st.markdown(
    """
    - 미세먼지 농도는 풍속과 온도 외에도 습도, 강수, 계절, 배출원, 국외 유입 등 여러 요인의 영향을 받을 수 있습니다.
    - 이번 자료는 경상남도 관측 자료이므로 평택시를 비롯한 다른 지역에 결과를 그대로 적용할 수 없습니다.
    - 업로드한 파일의 관측 기간과 측정 지점 범위가 제한적일 수 있습니다.
    - 회귀분석은 변수 사이의 통계적 관계를 보여 주며, 그 자체로 원인과 결과를 증명하지는 않습니다.
    - 월별·계절별 차이가 결과에 영향을 주었는지 추가로 분석할 수 있습니다.
    """
)

st.header("5. 분석에 사용한 데이터 내려받기")
st.download_button(
    "전처리된 분석 데이터 CSV 다운로드",
    data=make_download_csv(clean_df),
    file_name="PM10_회귀분석_전처리데이터.csv",
    mime="text/csv"
)

st.caption("자료 출처: 경상남도 보건환경연구원, 경상남도 대기환경측정망 자료. 원본 파일의 출처와 이용 조건은 별도로 확인해 주세요.")
