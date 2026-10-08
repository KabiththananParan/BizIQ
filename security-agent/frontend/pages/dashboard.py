"""Main Security Dashboard view."""

import json
from datetime import datetime
import streamlit as st

try:
    from frontend.api.client import (
        APIError,
        AuthenticationError,
        ConnectionError,
        PermissionDeniedError,
        SecurityAPIClient,
    )
    from frontend.components.charts import render_signals_chart
    from frontend.components.events_table import render_recent_events_table
    from frontend.components.metric_cards import render_metric_cards
    from frontend.components.security_signals import render_security_signals_summary
except ImportError:
    from api.client import (
        APIError,
        AuthenticationError,
        ConnectionError,
        PermissionDeniedError,
        SecurityAPIClient,
    )
    from components.charts import render_signals_chart
    from components.events_table import render_recent_events_table
    from components.metric_cards import render_metric_cards
    from components.security_signals import render_security_signals_summary



def _navigate_to_ai_analysis() -> None:
    """Select the AI analysis view before the next Streamlit render."""
    st.session_state["nav_selection"] = "AI Security Analysis"


def _validation_activity(recent_events: list[dict]) -> list[dict[str, str]]:
    """Extract only safe agent-validation fields from existing audit events."""
    activity: list[dict[str, str]] = []
    for event in recent_events:
        if event.get("event") != "SECURITY_REQUEST_VALIDATED":
            continue
        try:
            details = json.loads(event.get("details") or "{}")
        except (TypeError, json.JSONDecodeError):
            details = {}
        activity.append(
            {
                "Time": str(event.get("timestamp", ""))[11:16],
                "Source": str(details.get("source_agent", "")),
                "Target": str(details.get("target_agent", "")),
                "Operation": str(details.get("operation", "")),
                "Status": str(details.get("validation_result", event.get("status", ""))),
            }
        )
    return activity


def render_dashboard_page(
    api_client: SecurityAPIClient,
    token: str,
    current_user: dict,
    start_utc: datetime | None = None,
    end_utc: datetime | None = None,
) -> None:
    """Render the main security dashboard including overview metrics, signals, charts, and audit events.

    Parameters:
        api_client: SecurityAPIClient instance.
        token: Current active JWT token string.
        current_user: Authenticated user dictionary.
        start_utc: Optional UTC start datetime.
        end_utc: Optional UTC end datetime.
    """
    st.markdown("## 🛡️ Security & Compliance Monitoring")
    st.caption("Aggregated real-time security events, deterministic signal detection, and access telemetry.")

    # Time window badge display
    if start_utc and end_utc:
        st.info(f"🕒 **Observation Window (UTC):** `{start_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}` to `{end_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}`")

    # Fetch data from FastAPI backend
    try:
        with st.spinner("Loading security dashboard..."):
            dashboard_data = api_client.get_dashboard(token=token, start=start_utc, end=end_utc)
    except AuthenticationError as exc:
        st.error(f"🔒 **Authentication Required:** {exc.message}")
        if st.button("Log In Again"):
            st.session_state.clear()
            st.rerun()
        return
    except PermissionDeniedError as exc:
        st.error(f"⛔ **Access Denied:** {exc.message}")
        return
    except ConnectionError as exc:
        st.error(f"🔌 **Connection Failure:** {exc.message}")
        return
    except APIError as exc:
        st.error(f"⚠️ **Security Service Error:** {exc.message}")
        return
    except Exception:
        st.error("⚠️ Security service temporarily unavailable. Please try again later.")
        return

    overview = dashboard_data.get("overview", {})
    signals = dashboard_data.get("signals", {})
    recent_events = dashboard_data.get("recent_events", [])

    # 1. Overview Metric Cards
    render_metric_cards(overview)
    st.markdown("---")

    # 2. Security Signals and Chart Layout
    col_chart, col_signals = st.columns([3, 2])
    with col_chart:
        render_signals_chart(signals)
    with col_signals:
        render_security_signals_summary(signals)

    st.markdown("---")

    # 3. Recent Security Events Table
    render_recent_events_table(recent_events)

    st.markdown("---")

    # 4. Agent validation activity uses the existing audit feed; no new table is needed.
    st.markdown("### Agent Security")
    st.success("Validation endpoint: ONLINE")
    validation_activity = _validation_activity(recent_events)
    if validation_activity:
        st.dataframe(validation_activity, hide_index=True, use_container_width=True)
    else:
        st.caption("No recent agent validation activity in the selected observation window.")

    st.markdown("---")

    # 5. Shortcut Callout for AI Security Analysis
    st.markdown("### 🤖 Next Steps: Investigate Individual Users")
    st.write(
        "Run in-depth AI-assisted behavioral security analysis on individual user telemetry using server-side deterministic evidence and the Groq LLM model."
    )
    st.button(
        "🔍 Open AI Security Analysis",
        type="primary",
        on_click=_navigate_to_ai_analysis,
    )
