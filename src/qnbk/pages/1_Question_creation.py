"""Create questions in a structured format (Markdown with YAML front matter) using a Streamlit interface."""

import json
import os
from pathlib import Path

import streamlit as st
from loguru import logger

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.utils import write_md_file, render_chemistry_preview, chemistry_help_panel

QUESTIONS_DIR = DEFAULT_QUESTIONS_DIR


def ensure_output_dir(out_dir: Path) -> None:
    """Ensure the output directory exists, creating it if necessary."""
    os.makedirs(out_dir, exist_ok=True)


def generate_id(directory: Path) -> str:
    """Find the latest question number in the directory and generate a new ID by incrementing it.

    If no questions exist, start with 001.
    :param directory:
    :return:
    """
    existing_ids = []
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
    """Build a structured dictionary for the question, separating metadata and body content."""
    metadata = {
        "topic": topic,
        "class": class_num,
        "difficulty": difficulty or "",
        "answer": correct_option or "",
        "prev_year": prev_year or "",
        "source": source or "",
        "last_used": "",
    }
    # include any extra metadata fields
    if extra_metadata:
        metadata.update(extra_metadata)

    # Build body which contains question text, options, and the solution (moved here)
    body = {
        "question": question,
        "options": options,
        "solution": (solution_text if solution_text and solution_text.strip() else None),
    }
    logger.info(f"{options=}")

    return {"metadata": metadata, "body": body}


def main() -> None:
    """Enter here

    :return:
    """
    # ---------------------------
    # Streamlit UI
    # ---------------------------
    st.set_page_config(page_title="Question Bank Creator", layout="wide")
    st.title("Question File Creator/Editor — Question Bank format")

    output_dir_base = st.text_input("Output directory (relative to project root)", value=str(QUESTIONS_DIR))

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.subheader("Question metadata")
        topic = st.text_input("Topic (e.g. algebra, geometry)", value="")
        topic = topic.strip().capitalize() if topic else ""
        class_num = st.selectbox("Class", ["XII", "XI", "X", "IX", "VIII"], index=0)

        resolved_output_dir = Path(output_dir_base.strip()) / f"Class-{class_num}" / topic

        difficulty_options = ["", "Easy", "Medium", "Hard"]
        difficulty = st.selectbox("Difficulty", difficulty_options, index=0)
        prev_year = st.text_input("Years in which this appeared (optional)", help="e.g. 2023", value="")
        source = st.text_input("Source (optional)", help="e.g. NCERT, JEE 2024", value="")
        extra_meta_text = st.text_area(
            "Extra metadata (as JSON) — optional",
            placeholder='{"learning_objective":"LO1", "chapter": 3}',
            height=80,
            value="",
        )

        st.subheader("Question content")
        question_text = st.text_area("Question text", height=200, value="")
        st.markdown("**Options (leave some blank for open-response)**")
        options = []
        for i in range(4):
            opt = st.text_input(f"Option {chr(65 + i)}")
            options.append(opt)

        options = dict(zip(["A", "B", "C", "D"], options, strict=False))
        logger.info(f"{options=}")

        correct_answers = st.text_input(
            "Correct answer(s)",
            help="Enter the option letter(s) (e.g. A, B) or the text/LaTeX answer for open-response (e.g. \\ce{CaCO3}).",
        )

        solution_text = st.text_area("Solution", height=200, value="")

        generated_file_name = f"q_{generate_id(resolved_output_dir)}.md"

        st.subheader("Output options")
        filename_override = st.text_input(
            "Filename override (optional)",
            help="Generated from the id and the folder provided",
            value=generated_file_name,
        )
        logger.info(f"Filename override: {filename_override}")

        submit = st.button("Create question file")

    with right_col:
        tab_preview, tab_guide = st.tabs(["🧪 Chemistry Preview", "📖 Writing Guide"])
        
        with tab_preview:
            st.markdown("### Real-time Rendered Preview")
            # Build preview markdown
            preview_md = f"### Question\n\n{question_text}\n\n"
            
            # Check if any options are filled
            non_empty_opts = {k: v for k, v in options.items() if v.strip()}
            if non_empty_opts:
                preview_md += "#### Options\n"
                for label in ["A", "B", "C", "D"]:
                    opt_val = options.get(label, "")
                    if opt_val.strip():
                        preview_md += f"* **Option {label}**: {opt_val}\n"
            
            if solution_text.strip():
                preview_md += f"\n\n#### Solution\n{solution_text}"
                
            render_chemistry_preview(preview_md, height=600)
            
        with tab_guide:
            chemistry_help_panel()

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
            options=options,
            solution_text=solution_text,
            correct_option=correct_answers,
            extra_metadata=extra_meta if extra_meta else None,
        )

        filepath = os.path.join(resolved_output_dir, filename_override)

        # write file
        try:
            logger.info(f"Writing {qdict} to file: {filepath}")
            write_md_file(qdict, filepath)
        except Exception as e:
            st.error(f"Error writing file: {e}")
            return

        st.success(f"Saved question to: `{filepath}`")
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        st.code(content, language="md")


if __name__ == "__main__":
    main()
