import numpy as np
import pandas as pd

from functions.config import BS_TOTAL_ASSETS, IS_REVENUE
from functions.datamodel import FinancialDataModel
from functions.formatting import safe_divide


def compute_common_size_income_statement(model: FinancialDataModel) -> pd.DataFrame:
    return _common_size(model.income_statement, IS_REVENUE)


def compute_common_size_balance_sheet(model: FinancialDataModel) -> pd.DataFrame:
    return _common_size(model.balance_sheet, BS_TOTAL_ASSETS)


def compute_yoy_growth(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df.columns) < 2:
        return pd.DataFrame()

    return (df.pct_change(axis=1) * 100.0).round(2)


def compute_cagr(series: pd.Series) -> float:
    values = series.dropna()

    if len(values) < 2:
        return np.nan

    start_value = values.iloc[0]
    end_value = values.iloc[-1]
    periods = len(values) - 1

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return round((((end_value / start_value) ** (1.0 / periods)) - 1.0) * 100.0, 2)


def _common_size(df: pd.DataFrame, base_item: str) -> pd.DataFrame:
    if df.empty or base_item not in df.index:
        return pd.DataFrame()

    base_series = df.loc[base_item]

    return df.apply(lambda row: safe_divide(row, base_series) * 100.0, axis=1).round(2)
