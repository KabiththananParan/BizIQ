"""Streamlit console for the Security Agent's REST validation contract."""

from uuid import uuid4

import streamlit as st

try:
    from frontend.api.client import (
        APIError,
        AgentValidationError,
        ConnectionError,
        SecurityAPIClient,
    )
except ImportError:
    from api.client import APIError, AgentValidationError, ConnectionError, SecurityAPIClient


AGENTS = ["nlp-agent", "ir-agent", "insight-agent", "security-agent"]
OPERATIONS = ["QUERY_DATA", "RETRIEVE_DATA", "GENERATE_INSIGHT", "SECURITY_ANALYSIS"]


def _new_request_id() -> None:
    st.session_state["agent_validation_request_id"] = f"agent-test-{uuid4()}"


def _result_message(status: str, allowed: bool) -> tuple[str, str]:
    """Return a visual label and Streamlit notification type for an API decision."""
    messages = {
        "VALID": ("✅ Request Allowed", "success"),
        "DENIED": ("❌ Request Denied", "error"),
        "INVALID_TOKEN": ("🔐 Invalid Authentication", "error"),
        "INSUFFICIENT_PERMISSION": ("🚫 Insufficient Permission", "warning"),
        "INVALID_REQUEST": ("⚠️ Invalid Request", "warning"),
    }
    return messages.get(status, ("✅ Request Allowed" if allowed else "❌ Request Denied", "info"))


def render_agent_validation_page(api_client: SecurityAPIClient, token: str, current_user: dict) -> None:
    """Render the authenticated client for the deterministic validation endpoint."""
    st.markdown("## BizIQ Agent Security Validation")
    st.caption("Test the REST security contract used for future multi-agent communication.")
    st.info(
        "This console simulates requests that other BizIQ agents can send to the Security Agent. "
        "The NLP, IR, and Insight agents are not modified or automatically connected in this phase."
    )

    st.session_state.setdefault("agent_validation_request_id", f"agent-test-{uuid4()}")
    with st.form("agent_validation_form"):
        source_agent = st.selectbox("Source Agent", AGENTS)
        target_agent = st.selectbox("Target Agent", AGENTS, index=1)
        operation = st.selectbox("Operation", OPERATIONS)
        request_id = st.text_input("Request ID", value=st.session_state["agent_validation_request_id"], disabled=True)
        request_type = st.text_input("Request Type", value="business_query")
        submitted = st.form_submit_button("Validate Request", type="primary")

    st.button("Generate New Request ID", on_click=_new_request_id)

    if submitted:
        try:
            result = api_client.validate_agent_request(
                token=token,
                user_id=int(current_user["id"]),
                request_id=request_id,
                source_agent=source_agent,
                target_agent=target_agent,
                operation=operation,
                metadata={"request_type": request_type} if request_type else {},
            )
        except AgentValidationError as exc:
            result = exc.response
        except ConnectionError as exc:
            st.error(exc.message)
            return
        except APIError as exc:
            st.error(exc.message)
            return

        st.session_state["agent_validation_result"] = result
        st.session_state["agent_validation_context"] = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "operation": operation,
        }

    result = st.session_state.get("agent_validation_result")
    if result:
        context = st.session_state.get("agent_validation_context", {})
        status = result.get("security_status", "DENIED")
        allowed = bool(result.get("allowed", False))
        message, notification = _result_message(status, allowed)
        getattr(st, notification)(message)

        st.markdown("### Validation Result")
        left, right = st.columns(2)
        with left:
            st.write(f"**Request ID:** `{result.get('request_id', '')}`")
            st.write(f"**Source Agent:** {context.get('source_agent', '')}")
            st.write(f"**Target Agent:** {context.get('target_agent', '')}")
            st.write(f"**Operation:** {context.get('operation', '')}")
        with right:
            st.write(f"**Allowed:** {'Yes' if allowed else 'No'}")
            st.write(f"**Security Status:** `{status}`")
            st.write(f"**Requires AI Analysis:** {'Yes' if result.get('requires_ai_analysis') else 'No'}")
        st.write(f"**Reason:** {result.get('reason', 'No reason was returned.')}")
