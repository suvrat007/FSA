from dataclasses import dataclass, field, replace
from typing import Any, List

DEFAULT_FORECAST_YEARS = 5


@dataclass
class ForecastAssumptions:
    rev_growth_rates: List[float] = field(default_factory=lambda: [10.0, 9.0, 8.0, 8.0, 7.5])
    ebitda_margin: float = 18.0
    tax_rate: float = 25.0
    dso: float = 40.0
    dio: float = 55.0
    dpo: float = 45.0
    capex_percent_rev: float = 8.0
    depr_percent_ppe: float = 10.0
    interest_rate: float = 7.5
    dividend_payout_ratio: float = 25.0
    n_years: int = DEFAULT_FORECAST_YEARS

    def derive(self, **overrides: Any) -> "ForecastAssumptions":
        return replace(self, **overrides)

    def growth_for(self, index: int) -> float:
        if not self.rev_growth_rates:
            return 0.0

        if index < len(self.rev_growth_rates):
            return self.rev_growth_rates[index]

        return self.rev_growth_rates[-1]
