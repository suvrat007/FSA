from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from functions.datamodel import FinancialDataModel
from functions.quality import SEVERITY_CRITICAL, evaluate_red_flags
from functions.ratios import (
    ASSET_TURNOVER,
    CASH_RATIO,
    CCC,
    CFO_TO_NET_INCOME,
    CURRENT_RATIO,
    DEBT_TO_ASSETS,
    DEBT_TO_EQUITY,
    DSO,
    EBITDA_MARGIN,
    FCF_TO_REVENUE,
    INTEREST_COVERAGE,
    NET_DEBT_TO_EBITDA,
    NET_MARGIN,
    QUICK_RATIO,
    ROA,
    ROCE,
    ROE,
    compute_all_ratios,
    read_ratio,
)
from functions.sectors import MODEL_FINANCIAL, classify_business_model

GRADE_STRONG = "Strong"
GRADE_ADEQUATE = "Adequate"
GRADE_WEAK = "Weak"
GRADE_CRITICAL = "Critical"
GRADE_UNAVAILABLE = "Not assessed"

GRADE_BANDS = [(75.0, GRADE_STRONG), (55.0, GRADE_ADEQUATE), (35.0, GRADE_WEAK)]

TREND_IMPROVING = "Improving"
TREND_STABLE = "Stable"
TREND_DETERIORATING = "Deteriorating"
TREND_SENSITIVITY = 5.0

LIQUIDITY = "Liquidity"
SOLVENCY = "Solvency and Leverage"
PROFITABILITY = "Profitability"
EFFICIENCY = "Operating Efficiency"
CASH_QUALITY = "Cash Flow Quality"

DIMENSION_ORDER = [LIQUIDITY, SOLVENCY, PROFITABILITY, EFFICIENCY, CASH_QUALITY]

DIMENSION_WEIGHTS: Dict[str, float] = {
    LIQUIDITY: 0.18,
    SOLVENCY: 0.24,
    PROFITABILITY: 0.26,
    EFFICIENCY: 0.12,
    CASH_QUALITY: 0.20,
}

DIMENSION_QUESTION: Dict[str, str] = {
    LIQUIDITY: "Can the company meet obligations falling due within the next twelve months?",
    SOLVENCY: "Is the capital structure sustainable and is debt comfortably serviced?",
    PROFITABILITY: "Does the business earn an adequate return on sales and on capital?",
    EFFICIENCY: "How quickly is capital cycled through operations back into cash?",
    CASH_QUALITY: "Do reported profits convert into actual cash?",
}

FINANCIAL_DIMENSIONS_NOT_APPLICABLE = [LIQUIDITY, EFFICIENCY]

CRITICAL_PENALTY = 6.0
ADVISORY_PENALTY = 2.0
MAX_PENALTY = 18.0


@dataclass(frozen=True)
class Benchmark:
    ratio: str
    label: str
    unit: str
    higher_is_better: bool
    strong: float
    adequate: float
    weak: float

    def threshold_text(self) -> str:
        direction = "at least" if self.higher_is_better else "no more than"

        return (
            f"{direction} {self.strong:g}{self.unit} is strong, "
            f"{direction} {self.adequate:g}{self.unit} is adequate"
        )


BENCHMARKS: Dict[str, List[Benchmark]] = {
    LIQUIDITY: [
        Benchmark(CURRENT_RATIO, "Current ratio", "x", True, 2.0, 1.5, 1.0),
        Benchmark(QUICK_RATIO, "Quick ratio", "x", True, 1.5, 1.0, 0.7),
        Benchmark(CASH_RATIO, "Cash ratio", "x", True, 0.5, 0.25, 0.10),
    ],
    SOLVENCY: [
        Benchmark(DEBT_TO_EQUITY, "Debt to equity", "x", False, 0.30, 1.00, 2.00),
        Benchmark(DEBT_TO_ASSETS, "Debt to assets", "x", False, 0.20, 0.35, 0.55),
        Benchmark(INTEREST_COVERAGE, "Interest coverage", "x", True, 6.0, 3.0, 1.5),
        Benchmark(NET_DEBT_TO_EBITDA, "Net debt to EBITDA", "x", False, 1.0, 2.5, 4.0),
    ],
    PROFITABILITY: [
        Benchmark(EBITDA_MARGIN, "EBITDA margin", "%", True, 20.0, 12.0, 6.0),
        Benchmark(NET_MARGIN, "Net profit margin", "%", True, 12.0, 6.0, 2.0),
        Benchmark(ROE, "Return on equity", "%", True, 18.0, 12.0, 6.0),
        Benchmark(ROCE, "Return on capital employed", "%", True, 15.0, 10.0, 5.0),
        Benchmark(ROA, "Return on assets", "%", True, 8.0, 4.0, 1.5),
    ],
    EFFICIENCY: [
        Benchmark(ASSET_TURNOVER, "Asset turnover", "x", True, 1.0, 0.6, 0.3),
        Benchmark(DSO, "Days sales outstanding", " days", False, 45.0, 75.0, 120.0),
        Benchmark(CCC, "Cash conversion cycle", " days", False, 30.0, 75.0, 120.0),
    ],
    CASH_QUALITY: [
        Benchmark(CFO_TO_NET_INCOME, "Operating cash flow to net income", "x", True, 1.1, 0.8, 0.5),
        Benchmark(FCF_TO_REVENUE, "Free cash flow to revenue", "%", True, 8.0, 3.0, 0.0),
    ],
}


@dataclass
class MetricAssessment:
    label: str
    ratio: str
    value: float
    unit: str
    score: float
    grade: str
    benchmark_text: str
    commentary: str


@dataclass
class DimensionAssessment:
    name: str
    question: str
    score: float
    grade: str
    trend: str
    weight: float
    applicable: bool
    metrics: List[MetricAssessment] = field(default_factory=list)
    verdict: str = ""


@dataclass
class CompanyAssessment:
    company_name: str
    ticker: str
    period: str
    score: float
    grade: str
    dimensions: List[DimensionAssessment]
    verdict: str
    caveats: List[str] = field(default_factory=list)
    critical_findings: int = 0
    advisory_findings: int = 0

    def dimension(self, name: str) -> Optional[DimensionAssessment]:
        for entry in self.dimensions:
            if entry.name == name:
                return entry

        return None

    def summary_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Dimension": entry.name,
                    "Grade": entry.grade,
                    "Score": entry.score if entry.applicable else np.nan,
                    "Trend": entry.trend,
                    "Weight": f"{entry.weight:.0%}",
                }
                for entry in self.dimensions
            ]
        )


def assess_company(model: FinancialDataModel) -> CompanyAssessment:
    ratios = compute_all_ratios(model)
    is_financial = classify_business_model(model) == MODEL_FINANCIAL
    latest_year = model.years[-1] if model.years else ""

    findings = evaluate_red_flags(model)
    critical = sum(1 for item in findings if item["severity"] == SEVERITY_CRITICAL)
    advisory = len(findings) - critical

    dimensions = [
        _assess_dimension(name, ratios, model.years, is_financial) for name in DIMENSION_ORDER
    ]

    base_score = _weighted_score(dimensions)
    penalty = min(MAX_PENALTY, critical * CRITICAL_PENALTY + advisory * ADVISORY_PENALTY)
    score = round(max(0.0, base_score - penalty), 1) if not np.isnan(base_score) else np.nan
    grade = _grade_for(score)

    caveats = _build_caveats(model, ratios, is_financial, penalty)

    return CompanyAssessment(
        company_name=model.company_name,
        ticker=model.ticker,
        period=latest_year,
        score=score,
        grade=grade,
        dimensions=dimensions,
        verdict=_overall_verdict(model, dimensions, score, grade, critical, advisory, penalty),
        caveats=caveats,
        critical_findings=critical,
        advisory_findings=advisory,
    )


def _assess_dimension(
    name: str,
    ratios: pd.DataFrame,
    years: List[str],
    is_financial: bool,
) -> DimensionAssessment:
    weight = DIMENSION_WEIGHTS[name]
    question = DIMENSION_QUESTION[name]

    if is_financial and name in FINANCIAL_DIMENSIONS_NOT_APPLICABLE:
        return DimensionAssessment(
            name=name,
            question=question,
            score=np.nan,
            grade=GRADE_UNAVAILABLE,
            trend=TREND_STABLE,
            weight=weight,
            applicable=False,
            verdict=(
                f"{name} is not assessed for banks and financial institutions. Deposits, loans, "
                f"and regulatory capital do not map onto the current asset and current liability "
                f"framework used here, so a general corporate reading would be misleading."
            ),
        )

    if ratios.empty or not years:
        return DimensionAssessment(
            name=name,
            question=question,
            score=np.nan,
            grade=GRADE_UNAVAILABLE,
            trend=TREND_STABLE,
            weight=weight,
            applicable=False,
            verdict=f"{name} could not be assessed because no ratio data is available.",
        )

    latest_year = years[-1]
    metrics = []

    for benchmark in BENCHMARKS[name]:
        value = read_ratio(ratios, benchmark.ratio, latest_year)

        if np.isnan(value):
            continue

        score = _score_metric(value, benchmark)
        metrics.append(
            MetricAssessment(
                label=benchmark.label,
                ratio=benchmark.ratio,
                value=value,
                unit=benchmark.unit,
                score=score,
                grade=_grade_for(score),
                benchmark_text=benchmark.threshold_text(),
                commentary=_metric_commentary(value, benchmark, score),
            )
        )

    if not metrics:
        return DimensionAssessment(
            name=name,
            question=question,
            score=np.nan,
            grade=GRADE_UNAVAILABLE,
            trend=TREND_STABLE,
            weight=weight,
            applicable=False,
            verdict=(
                f"{name} could not be assessed because the source data does not carry the "
                f"required line items."
            ),
        )

    score = round(float(np.mean([metric.score for metric in metrics])), 1)
    grade = _grade_for(score)
    trend = _dimension_trend(name, ratios, years)

    assessment = DimensionAssessment(
        name=name,
        question=question,
        score=score,
        grade=grade,
        trend=trend,
        weight=weight,
        applicable=True,
        metrics=metrics,
    )
    assessment.verdict = _dimension_verdict(assessment)

    return assessment


def _score_metric(value: float, benchmark: Benchmark) -> float:
    strong, adequate, weak = benchmark.strong, benchmark.adequate, benchmark.weak

    if not benchmark.higher_is_better:
        value, strong, adequate, weak = -value, -strong, -adequate, -weak

    floor = weak - max(abs(adequate - weak), 1e-6)
    ceiling = strong + max(abs(strong - adequate), 1e-6)

    return round(
        float(
            np.interp(
                value,
                [floor, weak, adequate, strong, ceiling],
                [0.0, 35.0, 55.0, 80.0, 100.0],
            )
        ),
        1,
    )


def _grade_for(score: float) -> str:
    if score is None or (isinstance(score, float) and np.isnan(score)):
        return GRADE_UNAVAILABLE

    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade

    return GRADE_CRITICAL


def _weighted_score(dimensions: List[DimensionAssessment]) -> float:
    usable = [entry for entry in dimensions if entry.applicable and not np.isnan(entry.score)]

    if not usable:
        return np.nan

    total_weight = sum(entry.weight for entry in usable)

    return sum(entry.score * entry.weight for entry in usable) / total_weight


def _dimension_trend(name: str, ratios: pd.DataFrame, years: List[str]) -> str:
    window = years[-3:]

    if len(window) < 2:
        return TREND_STABLE

    scores = []

    for year in (window[0], window[-1]):
        values = [
            _score_metric(read_ratio(ratios, benchmark.ratio, year), benchmark)
            for benchmark in BENCHMARKS[name]
            if not np.isnan(read_ratio(ratios, benchmark.ratio, year))
        ]

        if not values:
            return TREND_STABLE

        scores.append(float(np.mean(values)))

    delta = scores[-1] - scores[0]

    if delta > TREND_SENSITIVITY:
        return TREND_IMPROVING

    if delta < -TREND_SENSITIVITY:
        return TREND_DETERIORATING

    return TREND_STABLE


def _metric_commentary(value: float, benchmark: Benchmark, score: float) -> str:
    grade = _grade_for(score)
    comparison = "above" if benchmark.higher_is_better else "below"
    opposite = "below" if benchmark.higher_is_better else "above"

    if grade == GRADE_STRONG:
        return (
            f"{value:,.2f}{benchmark.unit} is {comparison} the {benchmark.strong:g}"
            f"{benchmark.unit} level associated with a strong position."
        )

    if grade == GRADE_ADEQUATE:
        return (
            f"{value:,.2f}{benchmark.unit} clears the {benchmark.adequate:g}{benchmark.unit} "
            f"adequacy threshold but sits {opposite} the {benchmark.strong:g}{benchmark.unit} "
            f"comfort level."
        )

    if grade == GRADE_WEAK:
        return (
            f"{value:,.2f}{benchmark.unit} falls {opposite} the {benchmark.adequate:g}"
            f"{benchmark.unit} adequacy threshold."
        )

    return (
        f"{value:,.2f}{benchmark.unit} breaches the {benchmark.weak:g}{benchmark.unit} "
        f"tolerance level and is a material concern."
    )


def _dimension_verdict(assessment: DimensionAssessment) -> str:
    ordered = sorted(assessment.metrics, key=lambda metric: metric.score)
    weakest = ordered[0]
    strongest = ordered[-1]

    opening = (
        f"{assessment.name} is {assessment.grade.lower()}, scoring {assessment.score:.0f} out "
        f"of 100."
    )

    if len(ordered) == 1:
        detail = f"{weakest.label} {weakest.commentary[0].lower()}{weakest.commentary[1:]}"
    elif strongest.score - weakest.score < 10:
        detail = (
            f"The measures are consistent with one another: {strongest.label.lower()} "
            f"{strongest.commentary[0].lower()}{strongest.commentary[1:]}"
        )
    else:
        detail = (
            f"{strongest.label} is the strongest measure, where "
            f"{strongest.commentary[0].lower()}{strongest.commentary[1:]} "
            f"{weakest.label} is the binding constraint, where "
            f"{weakest.commentary[0].lower()}{weakest.commentary[1:]}"
        )

    trend_text = {
        TREND_IMPROVING: "The position has improved over the last three reported periods.",
        TREND_DETERIORATING: "The position has deteriorated over the last three reported periods.",
        TREND_STABLE: "The position has held broadly steady over the last three reported periods.",
    }[assessment.trend]

    return f"{opening} {detail} {trend_text}"


def _overall_verdict(
    model: FinancialDataModel,
    dimensions: List[DimensionAssessment],
    score: float,
    grade: str,
    critical: int,
    advisory: int,
    penalty: float,
) -> str:
    usable = [entry for entry in dimensions if entry.applicable and not np.isnan(entry.score)]

    if not usable:
        return (
            f"{model.company_name} could not be assessed. The available data does not carry "
            f"enough line items to score any dimension."
        )

    ranked = sorted(usable, key=lambda entry: entry.score, reverse=True)
    strongest = ranked[0]
    weakest = ranked[-1]

    opening = (
        f"{model.company_name} scores {score:.0f} out of 100 and is rated {grade.lower()} "
        f"on the evidence in {model.years[-1] if model.years else 'the latest period'}."
    )

    if strongest.name == weakest.name:
        balance = f"The assessment rests on {strongest.name.lower()} alone."
    else:
        balance = (
            f"{strongest.name} is the strongest dimension at {strongest.score:.0f}, while "
            f"{weakest.name.lower()} is the weakest at {weakest.score:.0f} and is where "
            f"attention is best directed."
        )

    deteriorating = [entry.name.lower() for entry in usable if entry.trend == TREND_DETERIORATING]
    improving = [entry.name.lower() for entry in usable if entry.trend == TREND_IMPROVING]

    if deteriorating:
        direction = f"Deterioration is visible in {_join(deteriorating)}."
    elif improving:
        direction = f"The trend is favourable in {_join(improving)}."
    else:
        direction = "No dimension shows a material trend in either direction."

    if critical or advisory:
        findings = (
            f"The forensic rule set raised {critical} critical and {advisory} advisory finding(s), "
            f"reducing the score by {penalty:.0f} points."
        )
    else:
        findings = "The forensic rule set raised no findings, so no penalty was applied."

    return f"{opening} {balance} {direction} {findings}"


def _build_caveats(
    model: FinancialDataModel,
    ratios: pd.DataFrame,
    is_financial: bool,
    penalty: float,
) -> List[str]:
    caveats = list(model.caveats)

    if is_financial:
        caveats.append(
            "This company was identified as a bank or financial institution. Liquidity and "
            "efficiency were not scored, and the leverage thresholds used here are calibrated "
            "for non-financial corporates, so solvency should be read with caution."
        )

    caveats.append(
        "Benchmark thresholds are general corporate norms and are not adjusted by sector. A "
        "capital-intensive business will read weaker on leverage than an asset-light one for "
        "structural reasons rather than performance reasons."
    )

    if len(model.years) < 3:
        caveats.append(
            f"Only {len(model.years)} reporting period(s) are available, so trend direction is "
            f"weakly supported."
        )

    return caveats


def _join(values: List[str]) -> str:
    if len(values) == 1:
        return values[0]

    return f"{', '.join(values[:-1])} and {values[-1]}"
