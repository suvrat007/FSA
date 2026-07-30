from typing import Any, Dict, List, Optional

import numpy as np
import streamlit as st

from functions.assessment import (
    GRADE_ADEQUATE,
    GRADE_CRITICAL,
    GRADE_STRONG,
    GRADE_UNAVAILABLE,
    GRADE_WEAK,
    TREND_DETERIORATING,
    TREND_IMPROVING,
    CompanyAssessment,
    DimensionAssessment,
)
from functions.datamodel import DERIVED, MISSING, REPORTED, FinancialDataModel
from functions.methodology import METHODOLOGY_REGISTRY
from functions.quality import SEVERITY_CRITICAL

GRADE_CLASS = {
    GRADE_STRONG: "grade-strong",
    GRADE_ADEQUATE: "grade-adequate",
    GRADE_WEAK: "grade-weak",
    GRADE_CRITICAL: "grade-critical",
    GRADE_UNAVAILABLE: "grade-unknown",
}

TREND_LABEL = {
    TREND_IMPROVING: "trend improving",
    TREND_DETERIORATING: "trend deteriorating",
}

PROVENANCE_CLASS = {
    REPORTED: "origin-reported",
    DERIVED: "origin-derived",
    MISSING: "origin-missing",
}


def render_kpi_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    is_positive: bool = True,
) -> None:
    delta_class = "delta-positive" if is_positive else "delta-negative"
    delta_html = f'<div class="delta {delta_class}">{delta}</div>' if delta else ""

    st.markdown(
        f'<div class="kpi-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def render_module_card(name: str, detail: str) -> None:
    st.markdown(
        f'<div class="module-card"><div class="name">{name}</div>'
        f'<div class="detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def render_finding(finding: Dict[str, Any]) -> None:
    critical_class = " finding-critical" if finding["severity"] == SEVERITY_CRITICAL else ""

    st.markdown(
        f'<div class="finding{critical_class}">'
        f'<div class="heading">{finding["rule_id"]} &middot; {finding["rule_name"]} '
        f'({finding["severity"]})</div>'
        f'<div class="body"><strong>Observation.</strong> {finding["observation"]}<br>'
        f'<strong>Why it matters.</strong> {finding["finance_reason"]}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_grade_badge(grade: str, score: float = np.nan, caption: str = "") -> None:
    css_class = GRADE_CLASS.get(grade, "grade-unknown")
    score_html = (
        f'<span class="grade-score">{score:.0f}/100</span>'
        if score is not None and not np.isnan(score)
        else ""
    )
    caption_html = f'<div class="grade-caption">{caption}</div>' if caption else ""

    st.markdown(
        f'<div class="grade-badge {css_class}"><span class="grade-name">{grade}</span>'
        f"{score_html}</div>{caption_html}",
        unsafe_allow_html=True,
    )


def render_dimension(dimension: DimensionAssessment) -> None:
    css_class = GRADE_CLASS.get(dimension.grade, "grade-unknown")
    score_text = (
        f"{dimension.score:.0f}/100"
        if dimension.applicable and not np.isnan(dimension.score)
        else "not scored"
    )
    trend_text = TREND_LABEL.get(dimension.trend, "trend stable")

    st.markdown(
        f'<div class="dimension {css_class}">'
        f'<div class="dimension-head">'
        f'<span class="dimension-name">{dimension.name}</span>'
        f'<span class="dimension-grade">{dimension.grade} &middot; {score_text} &middot; {trend_text}</span>'
        f"</div>"
        f'<div class="dimension-question">{dimension.question}</div>'
        f'<div class="dimension-verdict">{dimension.verdict}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if not dimension.metrics:
        return

    with st.expander(f"Evidence behind the {dimension.name.lower()} rating", expanded=False):
        for metric in dimension.metrics:
            st.markdown(
                f"**{metric.label} — {metric.value:,.2f}{metric.unit}** "
                f"({metric.grade}, {metric.score:.0f}/100)"
            )
            st.caption(f"{metric.commentary} Benchmark: {metric.benchmark_text}.")


def render_assessment_caveats(assessment: CompanyAssessment) -> None:
    if not assessment.caveats:
        return

    with st.expander("How to read this assessment", expanded=False):
        for caveat in assessment.caveats:
            st.markdown(f"- {caveat}")


def render_load_result(result, context: str = "") -> None:
    prefix = f"{context}: " if context else ""

    if result.ok:
        st.success(f"{prefix}loaded {result.model.company_name} from {result.source_label}.")
    else:
        st.error(f"{prefix}{result.message}")


def render_data_quality(model: FinancialDataModel) -> None:
    reported = len(model.items_by_provenance(REPORTED))
    derived = len(model.items_by_provenance(DERIVED))
    missing = len(model.items_by_provenance(MISSING))

    with st.expander(
        f"Data quality — {model.completeness():.0f}% of standard line items populated "
        f"({reported} reported, {derived} derived, {missing} unavailable)",
        expanded=False,
    ):
        st.caption(f"Source: {model.source}")

        columns = st.columns(3)
        columns[0].metric("Reported by source", reported)
        columns[1].metric("Derived by platform", derived)
        columns[2].metric("Unavailable", missing)

        if model.caveats:
            st.markdown("**Assumptions applied to this dataset**")
            for caveat in model.caveats:
                st.markdown(f"- {caveat}")

        st.markdown("**Origin of each line item**")
        st.dataframe(model.provenance_frame(), width="stretch", hide_index=True, height=280)


def render_provenance_legend(model: FinancialDataModel) -> None:
    derived = model.items_by_provenance(DERIVED)
    missing = model.items_by_provenance(MISSING)

    if not derived and not missing:
        st.caption("Every line item shown was reported directly by the source.")
        return

    parts = []

    if derived:
        parts.append(f"**Derived by the platform:** {', '.join(derived)}")

    if missing:
        parts.append(f"**Not available from this source (held at zero):** {', '.join(missing)}")

    st.caption(" \n".join(parts))


def render_methodology(topic: str, expanded: bool = False) -> None:
    entry = METHODOLOGY_REGISTRY.get(topic)

    if not entry:
        return

    with st.expander(f"Methodology: {entry['title']}", expanded=expanded):
        st.caption(f"Category: {entry['category']}")
        st.code(entry["formula"], language="text")

        st.markdown("**Financial concept**")
        st.write(entry["finance_concept"])

        st.markdown("**Interpretation**")
        st.write(entry["interpretation"])

        st.markdown("**Implementation**")
        st.write(entry["implementation"])

        st.markdown("**Data source**")
        st.write(entry["data_source"])
