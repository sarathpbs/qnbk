"""Create questions in a structured format (Markdown with YAML front matter) using a modern Streamlit interface."""

import json
import os
from pathlib import Path

from loguru import logger
import streamlit as st

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.question_index import upsert_question
from qnbk.styles import inject_custom_css
from qnbk.utils import render_question_preview, syntax_help_panel, write_md_file

QUESTIONS_DIR = DEFAULT_QUESTIONS_DIR

st.set_page_config(
    page_title="Question Authoring Studio",
    page_icon="📝",
    layout="wide",
)

inject_custom_css()


def ensure_output_dir(out_dir: Path) -> None:
    """Ensure output directory exists."""
    os.makedirs(out_dir, exist_ok=True)


def generate_id(directory: Path) -> str:
    """Find the latest question number in directory and generate an incremented ID."""
    existing_ids = []
    if directory.exists():
        for file in directory.glob("q_*.md"):
            try:
                num_part = file.stem.split("_")[1]
                existing_ids.append(int(num_part))
            except (IndexError, ValueError):
                continue
    new_id_num = max(existing_ids) + 1 if existing_ids else 1
    return f"{new_id_num:05d}"


def build_question_dict(
    topic: str | Path,
    class_num: str,
    difficulty: str,
    prev_year: str,
    source: str,
    question: str,
    options: dict | None,
    solution_text: str,
    correct_option: str | list[str] | None,
    extra_metadata: dict | None = None,
) -> dict:
    """Build structured question dictionary."""
    metadata = {
        "topic": topic,
        "class": class_num,
        "difficulty": difficulty or "",
        "answer": correct_option or "",
        "prev_year": prev_year or "",
        "source": source or "",
        "last_used": "",
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    body = {
        "question": question,
        "options": options,
        "solution": (solution_text if solution_text and solution_text.strip() else None),
    }
    logger.info(f"{options=}")
    return {"metadata": metadata, "body": body}


def main() -> None:
    """Render question authoring page."""
    st.title("Question Authoring Studio 📝")
    st.caption("Compose new questions with metadata, LaTeX, and instant live preview.")

    output_dir_base = st.text_input("Questions Base Directory", value=str(QUESTIONS_DIR))

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.subheader("1. Question Metadata")

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            class_num = st.segmented_control(
                "Class / Grade",
                ["XI", "XII"],
                default="XI",
            )
            if not class_num:
                class_num = "XI"
        with m_col2:
            difficulty = st.pills(
                "Difficulty",
                ["Easy", "Medium", "Hard"],
                default="Medium",
            )
            if not difficulty:
                difficulty = "Medium"

        topic = st.text_input("Topic / Subject Unit (e.g. Differentiation, Thermodynamics)", value="")
        topic = topic.strip().capitalize() if topic else ""

        resolved_output_dir = Path(output_dir_base.strip()) / f"Class-{class_num}" / (topic or "General")

        col_src1, col_src2 = st.columns(2)
        with col_src1:
            source = st.text_input("Source Attribution", placeholder="e.g. NCERT, JEE Advanced 2024", value="")
        with col_src2:
            prev_year = st.text_input("Exam Years Appeared", placeholder="e.g. 2023, 2024", value="")

        with st.expander("Additional Metadata (JSON)"):
            extra_meta_text = st.text_area(
                "Extra JSON attributes",
                placeholder='{"learning_objective": "LO1", "chapter": 3}',
                height=70,
                value="",
            )

        st.write("---")
        st.subheader("2. Question Content")
        question_text = st.text_area(
            "Question Statement (Markdown & LaTeX)",
            placeholder="State the problem here. Use \\(...\\) for inline math and \\[...\\] for block equations.",
            height=180,
            value="",
        )

        st.markdown("**Options (Leave blank for subjective / open-response):**")
        opt_cols = st.columns(2)
        options = []
        for i in range(4):
            letter = chr(65 + i)
            with opt_cols[i % 2]:
                opt = st.text_input(f"Option {letter}", placeholder=f"Choice {letter}")
                options.append(opt)

        options_dict = dict(zip(["A", "B", "C", "D"], options, strict=False))

        c_col1, c_col2 = st.columns([1, 1])
        with c_col1:
            correct_answers = st.text_input(
                "Correct Answer Key",
                placeholder="e.g. B or A, C or formula",
                help="Option letter(s) (A, B, C, D) or formula text for open response",
            )
        with c_col2:
            generated_file_name = f"q_{generate_id(resolved_output_dir)}.md"
            filename_override = st.text_input(
                "Filename",
                value=generated_file_name,
                help="Target filename in the designated folder",
            )

        solution_text = st.text_area(
            "Detailed Solution / Explanation",
            placeholder="Write out steps, derivation, or explanation here...",
            height=140,
            value="",
        )

        st.write("")
        submit = st.button("💾 Save Question File", type="primary", use_container_width=True)

    with right_col:
        st.subheader("Live Preview & Syntax Helper")
        tab_preview, tab_guide = st.tabs(["🧪 Rendered Preview", "📖 Syntax Guide"])

        with tab_preview:
            preview_md = f"### Question\n\n{question_text or '*(Question statement will appear here)*'}\n\n"

            non_empty_opts = {k: v for k, v in options_dict.items() if v and v.strip()}
            if non_empty_opts:
                preview_md += "#### Options\n"
                for label in ["A", "B", "C", "D"]:
                    opt_val = options_dict.get(label, "")
                    if opt_val.strip():
                        is_ans = correct_answers and label in [x.strip().upper() for x in correct_answers.split(",")]
                        marker = "✓ " if is_ans else "• "
                        preview_md += f"{marker}**Option {label}**: {opt_val}\n"

            if solution_text.strip():
                preview_md += f"\n\n#### Solution\n{solution_text}"

            render_question_preview(preview_md, height=580)

        with tab_guide:
            syntax_help_panel()

    if submit:
        ensure_output_dir(resolved_output_dir)
        extra_meta = {}
        if extra_meta_text.strip():
            try:
                extra_meta = json.loads(extra_meta_text)
            except Exception as e:
                st.error(f"Extra metadata JSON parse error: {e}")
                return

        qdict = build_question_dict(
            topic=topic,
            class_num=class_num,
            difficulty=difficulty,
            prev_year=prev_year,
            source=source,
            question=question_text,
            options=options_dict,
            solution_text=solution_text,
            correct_option=correct_answers,
            extra_metadata=extra_meta if extra_meta else None,
        )

        filepath = os.path.join(resolved_output_dir, filename_override)

        try:
            write_md_file(qdict, filepath)
            try:
                upsert_question(qdict, filepath, Path(output_dir_base.strip()))
            except Exception as e_idx:
                logger.warning(f"Could not update index: {e_idx}")
        except Exception as e:
            st.error(f"Error writing file: {e}")
            return

        st.success(f"✅ Successfully saved question: `{filepath}`")
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        with st.expander("View Raw Saved File"):
            st.code(content, language="markdown")


if __name__ == "__main__":
    main()
