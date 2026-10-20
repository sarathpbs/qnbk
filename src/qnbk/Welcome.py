"""Operational Dashboard and Introduction to Question Bank (qnbk)."""


from pathlib import Path
import streamlit as st
import pandas as pd

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.question_index import load_indexed_questions, rebuild_index
from qnbk.styles import inject_custom_css

st.set_page_config(
    page_title="Question Bank — Dashboard",
    page_icon="📚",
    layout="wide",
)

inject_custom_css()


def main() -> None:
    """Render the modernized dashboard."""
    # Hero Section
    st.markdown(
        """
        <div class="hero-container">
          <div class="hero-title">Question Bank Studio 📚</div>
          <p class="hero-subtitle">
            A unified workspace for authoring, organizing, and compiling exam-ready LaTeX & PDF worksheets.
            Manage your question repository with instant preview and SQLite-backed fast filtering.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load questions to compute live metrics
    q_dir = DEFAULT_QUESTIONS_DIR
    questions = []
    if q_dir.exists():
        questions = load_indexed_questions(str(q_dir))

    total_q = len(questions)
    mcq_q = sum(1 for q in questions if any((q.get("options") or {}).values()))
    subj_q = total_q - mcq_q
    solved_q = sum(1 for q in questions if q.get("solution") and q["solution"].strip())
    topics_set = {q["meta"].get("topic") for q in questions if q["meta"].get("topic")}
    classes_set = {q["meta"].get("class") for q in questions if q["meta"].get("class")}

    # Top KPI Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-card-label">Total Questions</div>
              <div class="metric-card-value">{total_q}</div>
              <div class="metric-card-desc">Across {len(topics_set)} topics & {len(classes_set)} grades</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        pct_mcq = int(mcq_q / total_q * 100) if total_q > 0 else 0
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-card-label">MCQs (Objective)</div>
              <div class="metric-card-value">{mcq_q}</div>
              <div class="metric-card-desc">{pct_mcq}% of total bank</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        pct_subj = int(subj_q / total_q * 100) if total_q > 0 else 0
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-card-label">Subjective (Open)</div>
              <div class="metric-card-value">{subj_q}</div>
              <div class="metric-card-desc">{pct_subj}% open-response</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        pct_solved = int(solved_q / total_q * 100) if total_q > 0 else 0
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-card-label">With Solutions</div>
              <div class="metric-card-value">{solved_q}</div>
              <div class="metric-card-desc">{pct_solved}% solution coverage</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.write("")

    # Visual Analytics & Distribution
    if questions:
        st.subheader("📊 Question Bank Distribution")
        chart_col1, chart_col2 = st.columns(2)

        chart_data = []
        for q in questions:
            chart_data.append(
                {
                    "Class": f"Class {q['meta'].get('class') or 'Unassigned'}",
                    "Topic": q["meta"].get("topic") or "Uncategorized",
                    "Difficulty": q["meta"].get("difficulty") or "Unknown",
                }
            )
        df = pd.DataFrame(chart_data)

        with chart_col1:
            st.caption("**Questions by Topic & Class**")
            topic_class_counts = df.groupby(["Topic", "Class"]).size().unstack(fill_value=0)
            st.bar_chart(topic_class_counts)

        with chart_col2:
            st.caption("**Questions by Difficulty**")
            diff_counts = df["Difficulty"].value_counts()
            st.bar_chart(diff_counts, color="#3B82F6")

    st.write("")
    st.write("")

    # Quick Launch Action Cards
    st.subheader("🚀 Quick Actions")
    a1, a2, a3 = st.columns(3)

    with a1:
        st.markdown(
            """
            <div class="action-card">
              <div>
                <div class="action-card-icon">📝</div>
                <div class="action-card-title">Question Creation</div>
                <div class="action-card-text">
                  Author new questions with structured YAML metadata, structured LaTeX and auto-numbered IDs.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Creator →", key="nav_create", use_container_width=True):
            st.switch_page("pages/1_Question_creation.py")

    with a2:
        st.markdown(
            """
            <div class="action-card">
              <div>
                <div class="action-card-icon">📦</div>
                <div class="action-card-title">Worksheet Compilation</div>
                <div class="action-card-text">
                  Filter questions by class, topic, or difficulty. Select items, generate LaTeX worksheets, and compile to PDF.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Compiler →", key="nav_compile", use_container_width=True):
            st.switch_page("pages/2_Question_compilation.py")

    with a3:
        st.markdown(
            """
            <div class="action-card">
              <div>
                <div class="action-card-icon">✏️</div>
                <div class="action-card-title">Question Editor</div>
                <div class="action-card-text">
                  Load existing markdown question files, tweak wording or metadata, and update the index with real-time preview.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Editor →", key="nav_edit", use_container_width=True):
            st.switch_page("pages/3_Question_editor.py")

    st.write("")
    st.write("---")

    # Collapsible File Format & LaTeX Quick Guide
    with st.expander("📖 Question Bank File Specifications & LaTeX Formatting Guide"):
        st.markdown(
            """
            ### Markdown + YAML Front-Matter Standard
            Each question is stored as an independent Markdown file with YAML front matter:

            ```markdown
            ---
            topic: Algebra
            class: XI
            difficulty: Easy
            answer: B
            prev_year: 2024
            source: NCERT
            last_used: 2026-09-16
            ---

            What is the derivative of \\(x^2\\)?

            OptionA: \\(x\\)
            OptionB: \\(2x\\)
            OptionC: \\(x^3\\)
            OptionD: 2

            ## Solution

            Differentiate using power rule: \\(f'(x) = 2x\\).
            ```

            ### Math Notation
            * **Inline Math**: `\\( ... \\)` or `$ ... $`
            * **Display Math**: `\\[ ... \\]` or `$$ ... $$`
            """
        )


if __name__ == "__main__":
    main()
