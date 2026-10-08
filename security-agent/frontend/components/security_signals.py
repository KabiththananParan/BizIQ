"""Security signals summary cards component."""

import streamlit as st


SIGNAL_DEFINITIONS = [
    (
        "repeated_failed_logins",
        "Repeated Failed Logins",
        "Users observing repeated failed authentication attempts exceeding the failure threshold.",
    ),
    (
        "multiple_ip_addresses",
        "Multiple IP Addresses",
        "Users logging in from multiple distinct client IP addresses.",
    ),
    (
        "repeated_access_denied",
        "Repeated Access Denied",
        "Users repeatedly attempting actions unauthorized for their role.",
    ),
    (
        "invalid_token_activity",
        "Invalid Token Activity",
        "Users/incidents associated with invalid or forged JWT authentication tokens.",
    ),
    (
        "expired_token_activity",
        "Expired Token Activity",
        "Users/incidents presenting expired JWT tokens during request authorization.",
    ),
    (
        "unusual_login_frequency",
        "Unusual Login Frequency",
        "Users exhibiting high-frequency authentication attempts exceeding the frequency threshold.",
    ),
]


def render_security_signals_summary(signals: dict) -> None:
    """Render deterministic security signal cards with counts and descriptions.

    Parameters:
        signals: Dict containing signal counts from backend GET /api/v1/security/dashboard.
    """
    st.markdown("### Deterministic Security Signals")
    st.caption("Summarizes deterministic rule-based security signals triggered across users in the selected time window.")

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for idx, (key, label, desc) in enumerate(SIGNAL_DEFINITIONS):
        col = cols[idx % 3]
        count = signals.get(key, 0)
        with col:
            status_indicator = "🔴 Active" if count > 0 else "🟢 Clear"
            st.metric(
                label=f"{label} ({status_indicator})",
                value=f"{count} users affected",
                help=desc,
            )
