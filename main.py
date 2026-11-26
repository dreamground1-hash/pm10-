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
