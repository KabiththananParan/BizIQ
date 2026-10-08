import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import streamlit as st

# Ensure frontend root and parent directory are on sys.path
_frontend_dir = Path(__file__).resolve().parent
_parent_dir = _frontend_dir.parent
for _p in (str(_frontend_dir), str(_parent_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from frontend.api.client import (
        AuthenticationError,
        ConnectionError,
        PermissionDeniedError,
        SecurityAPIClient,
        ValidationError,
    )
    from frontend.pages.ai_analysis import render_ai_analysis_page
    from frontend.pages.agent_validation import render_agent_validation_page
    from frontend.pages.dashboard import render_dashboard_page
    from frontend.utils.config import API_BASE_URL
except ImportError:
    from api.client import (
        AuthenticationError,
        ConnectionError,
        PermissionDeniedError,
        SecurityAPIClient,
        ValidationError,
    )
    from pages.ai_analysis import render_ai_analysis_page
    from pages.agent_validation import render_agent_validation_page
    from pages.dashboard import render_dashboard_page
    from utils.config import API_BASE_URL


# Initialize client
api_client = SecurityAPIClient(base_url=API_BASE_URL)

# Configure Streamlit page settings
st.set_page_config(
    page_title="BizIQ Security & Compliance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom enterprise CSS styling
st.markdown(
    """
    <style>
    /* Hide default Streamlit multipage navigation */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-container {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #334155;
    }
    .user-badge {
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-admin { background-color: #dc2626; color: white; }
    .badge-analyst { background-color: #2563eb; color: white; }
    .badge-user { background-color: #475569; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)



def render_login_view() -> None:
    """Render the login form when unauthenticated."""
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div style='text-align: center; margin-top: 2rem;'>", unsafe_allow_html=True)
        st.markdown("<h1 style='font-size: 2.5rem; margin-bottom: 0;'>🛡️ BizIQ Security</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; margin-bottom: 2rem;'>Security monitoring and AI-assisted access analysis</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Sign In to Security Console")
            email = st.text_input("Email / Username", placeholder="e.g. analyst@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter both email/username and password.")
                    return

                try:
                    with st.spinner("Authenticating..."):
                        token_resp = api_client.login(email.strip(), password)
                        token = token_resp.get("access_token")
                        user_info = api_client.get_current_user(token)

                    # Store session state
                    st.session_state["access_token"] = token
                    st.session_state["current_user"] = user_info
                    st.session_state["nav_selection"] = "Dashboard"
                    st.success("Authenticated successfully!")
                    st.rerun()

                except AuthenticationError as exc:
                    st.error(f"🔒 {exc.message}")
                except ConnectionError as exc:
                    st.error(f"🔌 {exc.message}")
                except ValidationError as exc:
                    st.error(exc.message)
                except Exception:
                    st.error("⚠️ An unexpected authentication error occurred. Please try again.")


def render_authenticated_app() -> None:
    """Render authenticated dashboard application."""
    token = st.session_state.get("access_token")
    current_user = st.session_state.get("current_user", {})
    user_role = current_user.get("role", "USER")

    # 1. Access Control Enforcement for USER role
    if user_role == "USER":
        st.markdown("<h1 class='main-header'>BizIQ Security & Compliance</h1>", unsafe_allow_html=True)
        st.markdown("<p class='sub-header'>Security monitoring and AI-assisted access analysis</p>", unsafe_allow_html=True)

        st.error(
            "⛔ **Access Denied:** Your account has the `USER` role and does not have the required "
            "`VIEW_SECURITY_ANALYSIS` permission to access security monitoring or AI analysis features."
        )
        st.info("Please contact a system administrator if you require security analyst privileges.")

        if st.button("Sign Out", type="secondary"):
            st.session_state.clear()
            st.rerun()
        return

    # 2. Sidebar for ANALYST and ADMIN roles
    with st.sidebar:
        st.markdown("## 🛡️ BizIQ Security")
        st.markdown("---")

        # User profile summary
        full_name = current_user.get("full_name", "User")
        email = current_user.get("email", "")
        badge_class = f"badge-{user_role.lower()}"

        st.markdown(
            f"**Signed in as:**<br>"
            f"👤 **{full_name}**<br>"
            f"📧 <small>{email}</small><br>"
            f"<span class='user-badge {badge_class}'>{user_role}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Navigation
        st.session_state.setdefault("nav_selection", "Dashboard")
        nav_choice = st.radio(
            "Navigation",
            ["Dashboard", "AI Security Analysis", "Agent Validation"],
            key="nav_selection",
        )

        st.markdown("---")

        # Time Window Filter (UTC)
        st.markdown("### 🕒 Time Window Filter (UTC)")
        filter_preset = st.selectbox(
            "Filter Presets",
            ["Last 24 hours", "Last 7 days", "Last 30 days", "Custom Range"],
            index=0,
        )

        now_utc = datetime.now(timezone.utc)
        if filter_preset == "Last 24 hours":
            start_utc = now_utc - timedelta(hours=24)
            end_utc = now_utc
        elif filter_preset == "Last 7 days":
            start_utc = now_utc - timedelta(days=7)
            end_utc = now_utc
        elif filter_preset == "Last 30 days":
            start_utc = now_utc - timedelta(days=30)
            end_utc = now_utc
        else:  # Custom Range
            custom_start_date = st.date_input("Start Date (UTC)", value=(now_utc - timedelta(days=1)).date())
            custom_end_date = st.date_input("End Date (UTC)", value=now_utc.date())
            start_utc = datetime.combine(custom_start_date, time.min, tzinfo=timezone.utc)
            end_utc = datetime.combine(custom_end_date, time.max, tzinfo=timezone.utc)

        st.markdown("---")

        # Refresh button
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.session_state["last_refresh"] = datetime.now(timezone.utc).isoformat()
            st.rerun()

        # Logout button
        if st.button("🚪 Sign Out", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 3. Main Header
    st.markdown("<h1 class='main-header'>BizIQ Security & Compliance</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Security monitoring and AI-assisted access analysis</p>", unsafe_allow_html=True)

    # 4. Render selected page
    if nav_choice == "Dashboard":
        render_dashboard_page(
            api_client=api_client,
            token=token,
            current_user=current_user,
            start_utc=start_utc,
            end_utc=end_utc,
        )
    elif nav_choice == "AI Security Analysis":
        render_ai_analysis_page(
            api_client=api_client,
            token=token,
            current_user=current_user,
        )
    elif nav_choice == "Agent Validation":
        render_agent_validation_page(
            api_client=api_client,
            token=token,
            current_user=current_user,
        )


def main() -> None:
    """Application entry point."""
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        render_login_view()
    else:
        render_authenticated_app()


if __name__ == "__main__":
    main()
