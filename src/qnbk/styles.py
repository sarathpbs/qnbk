"""Scoped modern design system and CSS styling for qnbk Streamlit application."""

import streamlit as st


def inject_custom_css() -> None:
    """Inject modern styling into the current Streamlit page."""
    custom_css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      /* Base typography polish */
      html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }

      /* Hero section styling */
      .hero-container {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F8FAFC;
        padding: 2rem 2.2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15), 0 8px 10px -6px rgba(15, 23, 42, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .hero-title {
        font-size: 2.1rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
        margin-bottom: 0.5rem;
        color: #FFFFFF !important;
      }
      .hero-subtitle {
        font-size: 1.02rem;
        color: #94A3B8;
        line-height: 1.6;
        max-width: 800px;
        margin-bottom: 0;
      }

      /* Metric KPI cards */
      .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.3rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }
      .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px -2px rgba(0, 0, 0, 0.08);
      }
      .metric-card-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .metric-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.35rem;
        line-height: 1.1;
      }
      .metric-card-desc {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 0.35rem;
      }

      /* Action launcher cards */
      .action-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.4rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
      }
      .action-card:hover {
        transform: translateY(-3px);
        border-color: #CBD5E1;
        box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.08);
      }
      .action-card-icon {
        font-size: 2rem;
        margin-bottom: 0.65rem;
      }
      .action-card-title {
        font-size: 1.12rem;
        font-weight: 600;
        color: #1E293B;
        margin-bottom: 0.35rem;
      }
      .action-card-text {
        font-size: 0.88rem;
        color: #64748B;
        line-height: 1.5;
        margin-bottom: 1rem;
      }

      /* Question compilation card */
      .q-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
      }
      .q-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.06);
      }
      .q-card-selected {
        border-color: #3B82F6 !important;
        background: #F8FAFC !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
      }

      /* Badges & Chips */
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        line-height: 1.2;
        letter-spacing: 0.01em;
      }
      .badge-easy {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
      }
      .badge-medium {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
      }
      .badge-hard {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
      }
      .badge-neutral {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #E2E8F0;
      }
      .badge-class {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
      }
      .badge-topic {
        background-color: #F8FAFC;
        color: #334155;
        border: 1px solid #E2E8F0;
      }
      .badge-answer {
        background-color: #F3E8FF;
        color: #7E22CE;
        border: 1px solid #E9D5FF;
      }

      /* Modal styling */
      div[data-testid="stDialog"] div[role="dialog"] {
        border-radius: 16px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      }

      .meta-label {
        color: #94A3B8;
        font-size: 0.8rem;
        font-family: monospace;
      }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def get_difficulty_badge_html(difficulty: str) -> str:
    """Return an HTML badge for difficulty."""
    diff_lower = (difficulty or "").strip().lower()
    if diff_lower == "easy":
        cls = "badge-easy"
        icon = "🟢"
    elif diff_lower in ["medium", "med"]:
        cls = "badge-medium"
        icon = "🟡"
    elif diff_lower in ["hard", "difficult"]:
        cls = "badge-hard"
        icon = "🔴"
    else:
        cls = "badge-neutral"
        icon = "⚪"
    val = difficulty or "Unknown"
    return f'<span class="badge {cls}">{icon} {val}</span>'


def get_class_badge_html(class_name: str) -> str:
    """Return an HTML badge for class/grade."""
    cls_val = class_name or "Unknown"
    return f'<span class="badge badge-class">🎓 Class {cls_val}</span>'


def get_topic_badge_html(topic: str) -> str:
    """Return an HTML badge for topic."""
    topic_val = topic or "General"
    return f'<span class="badge badge-topic">📂 {topic_val}</span>'


def get_answer_badge_html(answer: str | None) -> str:
    """Return an HTML badge for answer."""
    if not answer:
        return ""
    return f'<span class="badge badge-answer">✓ Ans: {answer}</span>'
