"""Overview metric cards component for the security dashboard."""

import streamlit as st


def render_metric_cards(overview: dict) -> None:
    """Render structured overview metric cards in responsive multi-column layout.

    Parameters:
        overview: Dict containing overview metric counts from backend GET /api/v1/security/dashboard.
    """
    st.markdown("### System Security Overview")

    # Row 1: User and Login Core Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="TOTAL USERS",
            value=overview.get("total_users", 0),
            help="Total registered user accounts across the system",
        )
    with col2:
        st.metric(
            label="ACTIVE USERS",
            value=overview.get("active_users", 0),
            help="Active user accounts permitted to authenticate",
        )
    with col3:
        st.metric(
            label="LOGIN ATTEMPTS",
            value=overview.get("total_login_attempts", 0),
            help="Total authentication attempts in the selected time window",
        )
    with col4:
        st.metric(
            label="SUCCESSFUL LOGINS",
            value=overview.get("successful_logins", 0),
            help="Successfully authenticated login sessions",
        )

    # Row 2: Security and Access Denial Metrics
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        failed = overview.get("failed_logins", 0)
        st.metric(
            label="FAILED LOGINS",
            value=failed,
            delta=f"{failed} failed" if failed > 0 else None,
            delta_color="inverse",
            help="Failed authentication attempts in window",
        )
    with col6:
        denied = overview.get("access_denied_events", 0)
        st.metric(
            label="ACCESS DENIED",
            value=denied,
            delta=f"{denied} denied" if denied > 0 else None,
            delta_color="inverse",
            help="RBAC authorization rejections in window",
        )
    with col7:
        invalid_tokens = overview.get("invalid_token_events", 0)
        st.metric(
            label="INVALID TOKENS",
            value=invalid_tokens,
            delta=f"{invalid_tokens} events" if invalid_tokens > 0 else None,
            delta_color="inverse",
            help="Invalid or malformed JWT token events",
        )
    with col8:
        expired_tokens = overview.get("expired_token_events", 0)
        st.metric(
            label="EXPIRED TOKENS",
            value=expired_tokens,
            delta=f"{expired_tokens} events" if expired_tokens > 0 else None,
            delta_color="inverse",
            help="Expired JWT token rejection events",
        )
