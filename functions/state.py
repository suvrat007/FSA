from typing import Dict, List

import streamlit as st

from functions.assumptions import ForecastAssumptions
from functions.config import DEFAULT_SCALE
from functions.datamodel import FinancialDataModel
from functions.mock_data import get_mock_company_model

MODEL_KEY = "data_model"
SCALE_KEY = "currency_scale"
ASSUMPTIONS_KEY = "forecast_assumptions"
FORECAST_KEY = "forecast_model"
LIBRARY_KEY = "company_library"
COHORT_KEY = "industry_cohort"

NO_MODEL_MESSAGE = "No company model is loaded. Open the home page and load a dataset first."


def initialize_state() -> None:
    st.session_state.setdefault(MODEL_KEY, get_mock_company_model("RELIANCE.NS"))
    st.session_state.setdefault(SCALE_KEY, DEFAULT_SCALE)
    st.session_state.setdefault(ASSUMPTIONS_KEY, ForecastAssumptions())
    st.session_state.setdefault(LIBRARY_KEY, {})
    st.session_state.setdefault(COHORT_KEY, {})


def set_active_model(model: FinancialDataModel) -> None:
    st.session_state[MODEL_KEY] = model
    st.session_state.pop(FORECAST_KEY, None)


def require_model() -> FinancialDataModel:
    model = st.session_state.get(MODEL_KEY)

    if model is None or not model.years:
        st.warning(NO_MODEL_MESSAGE)
        st.stop()

    return model


def active_scale() -> str:
    return st.session_state.get(SCALE_KEY, DEFAULT_SCALE)


def active_assumptions() -> ForecastAssumptions:
    return st.session_state.get(ASSUMPTIONS_KEY, ForecastAssumptions())


def model_label(model: FinancialDataModel) -> str:
    return f"{model.company_name} ({model.ticker})"


def library() -> Dict[str, FinancialDataModel]:
    return st.session_state.setdefault(LIBRARY_KEY, {})


def library_models() -> List[FinancialDataModel]:
    return list(library().values())


def add_to_library(model: FinancialDataModel) -> str:
    label = model_label(model)
    library()[label] = model

    return label


def remove_from_library(label: str) -> None:
    library().pop(label, None)


def clear_library() -> None:
    st.session_state[LIBRARY_KEY] = {}


def cohort() -> Dict[str, FinancialDataModel]:
    return st.session_state.setdefault(COHORT_KEY, {})


def set_cohort(models: Dict[str, FinancialDataModel]) -> None:
    st.session_state[COHORT_KEY] = models
