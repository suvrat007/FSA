from typing import Union

import numpy as np
import pandas as pd

from functions.config import DEFAULT_SCALE, currency_symbol, get_scale

Numeric = Union[float, int, np.number, None]


def is_missing(value: Numeric) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value)) or bool(np.isinf(value))
    except (TypeError, ValueError):
        return True


def format_currency(
    value: Numeric,
    scale_key: str = DEFAULT_SCALE,
    currency: str = "INR",
    decimals: int = 2,
) -> str:
    if is_missing(value):
        return "N/A"

    scale = get_scale(scale_key)
    symbol = currency_symbol(currency)
    prefix = f"{symbol} " if symbol else ""

    return f"{prefix}{float(value) * scale['factor']:,.{decimals}f}{scale['suffix']}"


def format_percent(
    value: Numeric,
    decimals: int = 2,
    multiply_by_100: bool = False,
    signed: bool = True,
) -> str:
    if is_missing(value):
        return "N/A"

    scaled = float(value) * 100.0 if multiply_by_100 else float(value)
    sign_flag = "+" if signed else ""

    return f"{scaled:{sign_flag}.{decimals}f}%"


def format_ratio(value: Numeric, decimals: int = 2, suffix: str = "x") -> str:
    if is_missing(value):
        return "N/A"

    return f"{float(value):.{decimals}f}{suffix}"


def scale_frame(df: pd.DataFrame, scale_key: str = DEFAULT_SCALE) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    return (df * get_scale(scale_key)["factor"]).round(2)


def safe_divide(
    numerator: Union[Numeric, pd.Series],
    denominator: Union[Numeric, pd.Series],
    default: float = np.nan,
) -> Union[float, pd.Series]:
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        result = numerator / denominator
        return result.replace([np.inf, -np.inf], default)

    if is_missing(numerator) or is_missing(denominator) or float(denominator) == 0.0:
        return default

    result = float(numerator) / float(denominator)

    return default if np.isinf(result) else result
