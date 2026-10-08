"""Recent security events table component."""

import pandas as pd
import streamlit as st


def render_recent_events_table(events: list[dict]) -> None:
    """Render a structured dataframe/table of recent security audit events.

    Parameters:
        events: List of event dicts from backend GET /api/v1/security/dashboard.
    """
    st.markdown("### Recent Security Events")

    if not events:
        st.info("No recent security events found in the selected time window.")
        return

    table_data = []
    for ev in events:
        table_data.append(
            {
                "Event": ev.get("event") or "-",
                "User ID": ev.get("user_id") if ev.get("user_id") is not None else "Unassigned",
                "Status": ev.get("status") or "-",
                "IP Address": ev.get("ip_address") or "N/A",
                "Timestamp (UTC)": ev.get("timestamp") or "-",
                "Details": ev.get("details") or "-",
            }
        )

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )
