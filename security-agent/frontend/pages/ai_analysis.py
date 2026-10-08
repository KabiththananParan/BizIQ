"""AI Security Analysis page for deep-dive investigations of specific users."""

from datetime import datetime, timedelta, timezone
import streamlit as st

try:
    from frontend.api.client import (
        APIError,
        AuthenticationError,
        ConnectionError,
        NotFoundError,
        PermissionDeniedError,
        SecurityAPIClient,
        ValidationError,
    )
except ImportError:
    from api.client import (
        APIError,
        AuthenticationError,
        ConnectionError,
        NotFoundError,
        PermissionDeniedError,
        SecurityAPIClient,
        ValidationError,
    )



def _navigate_to_dashboard() -> None:
    """Select the dashboard view before the next Streamlit render."""
    st.session_state["nav_selection"] = "Dashboard"


def render_ai_analysis_page(
    api_client: SecurityAPIClient,
    token: str,
    current_user: dict,
) -> None:
    """Render the AI Security Analysis investigation interface.

    Parameters:
        api_client: SecurityAPIClient instance.
        token: Current active JWT token string.
        current_user: Authenticated user dictionary.
    """
    st.markdown("## 🤖 AI-Assisted Security Analysis")
    st.caption("Perform behavioral access analysis on user telemetry using server-side deterministic signals and the Groq LLM model.")

    st.button("← Back to Dashboard", on_click=_navigate_to_dashboard)

    # Form for target user investigation
    with st.container():
        st.markdown("#### Select User & Analysis Window")
        col_user, col_hours = st.columns([1, 2])

        with col_user:
            target_user_id = st.number_input(
                "Target User ID",
                min_value=1,
                max_value=999999,
                value=1,
                step=1,
                help="Identifier of the registered user to analyze",
            )

        with col_hours:
            window_choice = st.selectbox(
                "Evidence Time Window",
                ["Last 24 hours", "Last 7 days", "Last 30 days"],
                index=0,
                help="Timeframe of login attempts and audit logs to evaluate",
            )

        now_utc = datetime.now(timezone.utc)
        if window_choice == "Last 24 hours":
            start_time = now_utc - timedelta(hours=24)
        elif window_choice == "Last 7 days":
            start_time = now_utc - timedelta(days=7)
        else:
            start_time = now_utc - timedelta(days=30)
        end_time = now_utc

        analyze_button = st.button("🚀 Analyze User Security with AI", type="primary")

    if analyze_button:
        try:
            with st.spinner("Running AI security analysis with Groq (openai/gpt-oss-20b)..."):
                result = api_client.analyze_security(
                    token=token,
                    user_id=int(target_user_id),
                    start=start_time,
                    end=end_time,
                )
            st.session_state["last_ai_result"] = result
            st.session_state["last_analyzed_user"] = target_user_id
        except AuthenticationError as exc:
            st.error(f"🔒 **Authentication Error:** {exc.message}")
            return
        except PermissionDeniedError as exc:
            st.error(f"⛔ **Permission Denied:** {exc.message}")
            return
        except NotFoundError as exc:
            st.warning(f"🔍 **User Not Found:** User ID {target_user_id} does not exist in the database.")
            return
        except ValidationError as exc:
            st.error(f"⚠️ **Validation Error:** {exc.message}")
            return
        except ConnectionError as exc:
            st.error(f"🔌 **Connection Failure:** {exc.message}")
            return
        except APIError as exc:
            st.error(f"⚠️ **AI Service Error:** {exc.message}")
            return
        except Exception:
            st.error("⚠️ AI security analysis temporarily unavailable. Please try again later.")
            return

    # Render result if available in session state
    result = st.session_state.get("last_ai_result")
    if result:
        st.markdown("---")
        st.markdown("### 📊 AI Security Assessment Report")
        st.caption(f"Target User ID: `{st.session_state.get('last_analyzed_user', target_user_id)}` | Label: **AI-assisted security analysis**")

        risk_level = result.get("risk_level", "UNKNOWN").upper()
        suspicious = result.get("suspicious", False)
        confidence = result.get("confidence", 0.0)
        findings = result.get("findings", [])
        evidence = result.get("evidence", [])
        recommendation = result.get("recommendation", "")

        # Color mapping for risk badges
        risk_colors = {
            "LOW": ("🟢 LOW", "success"),
            "MEDIUM": ("🟠 MEDIUM", "warning"),
            "HIGH": ("🔴 HIGH", "error"),
            "UNKNOWN": ("⚪ Analysis unavailable / insufficient evidence", "info"),
        }
        risk_display, _ = risk_colors.get(risk_level, ("⚪ UNKNOWN", "info"))

        # Score Summary Cards
        col_risk, col_susp, col_conf = st.columns(3)
        with col_risk:
            st.metric("RISK LEVEL", risk_display)
        with col_susp:
            susp_text = "⚠️ YES (Suspicious Activity)" if suspicious else "✅ NO (Normal Behavior)"
            st.metric("SUSPICIOUS ACTIVITY", susp_text)
        with col_conf:
            st.metric("CONFIDENCE", f"{int(confidence * 100)}%")

        # Findings and Evidence Side-by-Side
        col_find, col_evid = st.columns(2)
        with col_find:
            st.markdown("#### 🔎 Findings")
            if findings:
                for f in findings:
                    signal = f.get("signal", "Signal")
                    desc = f.get("description", "")
                    st.markdown(f"- **{signal}**: {desc}")
            else:
                st.write("No suspicious findings identified.")

        with col_evid:
            st.markdown("#### 📋 Security Evidence")
            if evidence:
                for e in evidence:
                    st.markdown(f"- {e}")
            else:
                st.write("No security evidence recorded for this user window.")

        # Recommendation Box
        st.markdown("#### 💡 Recommendation")
        if recommendation:
            st.info(recommendation)
        else:
            st.info("No specific mitigation steps required based on current evidence.")

        # Advisory Disclaimer Banner
        st.caption(
            "⚠️ **Disclaimer:** AI analysis is advisory and based on available security evidence. "
            "Authentication and authorization are enforced independently. "
            "AI assessments reflect server-side LLM synthesis and should be reviewed by a human security analyst."
        )
