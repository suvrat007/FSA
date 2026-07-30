from string import Template

import streamlit as st

from functions.config import APP_NAME, THEME_COLORS

_STYLESHEET = Template(
    """
<style>
  html, body, [class*="css"], .stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  .stApp {
    background-color: $bg_dark;
    color: $text_main;
  }

  section[data-testid="stSidebar"] {
    background-color: $bg_sidebar;
    border-right: 1px solid $border;
  }

  .page-title {
    font-size: 1.9rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: $text_main;
    margin-bottom: 0.15rem;
  }

  .page-subtitle {
    font-size: 0.95rem;
    color: $text_muted;
    margin-bottom: 1.5rem;
  }

  .kpi-card {
    background-color: $bg_card;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 16px 20px;
    height: 100%;
  }

  .kpi-card:hover {
    border-color: $accent_primary;
  }

  .kpi-card .label {
    font-size: 0.75rem;
    font-weight: 600;
    color: $text_muted;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .kpi-card .value {
    font-size: 1.5rem;
    font-weight: 700;
    color: $text_main;
    margin-top: 6px;
  }

  .kpi-card .delta {
    font-size: 0.82rem;
    font-weight: 600;
    margin-top: 4px;
  }

  .kpi-card .delta-positive { color: $success; }
  .kpi-card .delta-negative { color: $danger; }

  .finding {
    background-color: $bg_card;
    border: 1px solid $border;
    border-left: 4px solid $warning;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 12px;
  }

  .finding-critical { border-left-color: $danger; }

  .finding .heading {
    font-size: 1rem;
    font-weight: 600;
    color: $text_main;
  }

  .finding .body {
    font-size: 0.88rem;
    color: $text_muted;
    margin-top: 6px;
  }

  .module-card {
    background-color: $bg_card;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 16px 18px;
    height: 100%;
  }

  .module-card .name {
    font-size: 0.95rem;
    font-weight: 600;
    color: $text_main;
  }

  .module-card .detail {
    font-size: 0.82rem;
    color: $text_muted;
    margin-top: 6px;
  }

  .grade-badge {
    display: inline-flex;
    align-items: baseline;
    gap: 12px;
    padding: 14px 22px;
    border-radius: 8px;
    border: 1px solid $border;
    border-left-width: 5px;
    background-color: $bg_card;
  }

  .grade-badge .grade-name { font-size: 1.5rem; font-weight: 700; color: $text_main; }
  .grade-badge .grade-score { font-size: 0.95rem; color: $text_muted; }
  .grade-caption { font-size: 0.82rem; color: $text_muted; margin-top: 8px; }

  .grade-strong { border-left-color: $success; }
  .grade-adequate { border-left-color: $accent_secondary; }
  .grade-weak { border-left-color: $warning; }
  .grade-critical { border-left-color: $danger; }
  .grade-unknown { border-left-color: $border_strong; }

  .dimension {
    background-color: $bg_card;
    border: 1px solid $border;
    border-left-width: 4px;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
  }

  .dimension-head {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
  }

  .dimension-name { font-size: 1.05rem; font-weight: 600; color: $text_main; }
  .dimension-grade { font-size: 0.8rem; color: $text_muted; text-transform: uppercase; letter-spacing: 0.05em; }
  .dimension-question { font-size: 0.82rem; color: $text_muted; font-style: italic; margin-top: 6px; }
  .dimension-verdict { font-size: 0.9rem; color: $text_main; margin-top: 10px; line-height: 1.6; }
</style>
"""
)

_CSS = _STYLESHEET.substitute(THEME_COLORS)


def configure_page(page_title: str) -> None:
    st.set_page_config(
        page_title=f"{page_title} | {APP_NAME}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
