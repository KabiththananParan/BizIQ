"""Plotly chart components for security signal distribution and risk overview."""

import plotly.graph_objects as go
import streamlit as st


def render_signals_chart(signals: dict) -> None:
    """Render a clean Plotly bar chart representing deterministic security signal counts.

    Parameters:
        signals: Dict of signal keys and their affected user/event counts.
    """
    labels = [
        "Repeated Failed Logins",
        "Multiple IP Addresses",
        "Repeated Access Denied",
        "Invalid Token Activity",
        "Expired Token Activity",
        "Unusual Login Frequency",
    ]

    keys = [
        "repeated_failed_logins",
        "multiple_ip_addresses",
        "repeated_access_denied",
        "invalid_token_activity",
        "expired_token_activity",
        "unusual_login_frequency",
    ]

    values = [signals.get(k, 0) for k in keys]

    # Color mapping: highlight active signals with security amber/crimson
    colors = ["#ef4444" if v > 0 else "#3b82f6" for v in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                text=values,
                textposition="auto",
                marker=dict(
                    color=colors,
                    line=dict(color="#1e293b", width=1),
                ),
                hovertemplate="<b>%{x}</b><br>Affected Users/Events: %{y}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(text="Security Signals Distribution", font=dict(size=16, color="#f8fafc")),
        xaxis=dict(
            title=dict(text="Security Signal", font=dict(size=13, color="#94a3b8")),
            tickangle=-20,
            tickfont=dict(size=11, color="#cbd5e1"),
            gridcolor="#334155",
        ),
        yaxis=dict(
            title=dict(text="Affected Users / Incidents", font=dict(size=13, color="#94a3b8")),
            dtick=1 if max(values or [1]) < 10 else None,
            gridcolor="#334155",
            tickfont=dict(size=11, color="#cbd5e1"),
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0)",
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        margin=dict(l=40, r=20, t=50, b=80),
        height=380,
    )

    st.plotly_chart(fig, use_container_width=True)
