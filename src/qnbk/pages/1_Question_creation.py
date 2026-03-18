"""Create questions in a structured format (Markdown with YAML front matter) using a Streamlit interface."""

import json
import os
from pathlib import Path

import streamlit as st
from loguru import logger

from qnbk import DEFAULT_QUESTIONS_DIR

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
    if existing_ids:
        new_id_num = max(existing_ids) + 1
    else:
        new_id_num = 1
    return f"{new_id_num:05d}"


def build_question_dict(
    topic: str | Path,
    difficulty: str,
    prev_year: str,
    question: str,
    options: list[str] | None,
    solution_text: str,
    correct_option: str | list[str] | None,
    extra_metadata: dict | None = None,
) -> dict:
    """Build a structured dictionary for the question, separating metadata and body content."""
    metadata = {
        "topic": topic,
        "difficulty": difficulty or "",
        "answer": correct_option or "",
        "prev_year": prev_year or "",
    }
    # include any extra metadata fields
    if extra_metadata:
        metadata.update(extra_metadata)

    # Build body which contains question text, options, and the solution (moved here)
    body = {
        "question": question,
        "options": options if sum([1 if o else 0 for o in options]) == 4 else None,
        # Store the 'solution' inside body. This matches your earlier change requests.
        "solution": (solution_text if solution_text and solution_text.strip() else None),
    }

    return {"metadata": metadata, "body": body}


def write_md_file(qdict: dict, filename: str) -> None:
    """Write the question dictionary to a Markdown file with YAML front matter for metadata and body content below.

    :param qdict:
    :param filename:
    :return:
    """
    with open(filename, "w", encoding="utf-8") as f:
        # write metadata:
        f.write("---\n")
        for k, v in qdict["metadata"].items():
            f.write(f"{k}: {v}\n")
        f.write("---\n\n\n")
        # write question
        f.write(qdict["body"]["question"] + "\n\n")
        # write options if they exist
        if qdict["body"]["options"]:
            for opt_label, opt in zip(["A", "B", "C", "D"], qdict["body"]["options"], strict=False):
                f.write(f"Option{opt_label}: {opt}\n")
        # write solution
        if qdict["body"]["solution"]:
            f.write("\n\n## Solution\n\n")
            f.write(qdict["body"]["solution"] + "\n")
    logger.info(f"Written to file: {filename}")


def main() -> None:
    """Enter here

    :return:
    """
    # ---------------------------
    # Streamlit UI
    # ---------------------------
    st.set_page_config(page_title="Question Bank Creator", layout="wide")
    st.title("Question File Creator/Editor — Question Bank format")

    output_dir = st.text_input("Output directory (relative to project root)", value=QUESTIONS_DIR)

    with st.form("qform"):
        st.subheader("Question metadata")
        topic = st.text_input("Topic (e.g. algebra, geometry)", value="")
        topic = topic.strip().capitalize() if topic else ""
        output_dir = Path(output_dir.strip()) / topic

        difficulty_options = ["", "Easy", "Medium", "Hard"]
        loaded_difficulty = ""
        difficulty_index = (
            difficulty_options.index(loaded_difficulty) if loaded_difficulty in difficulty_options else 0
        )
        difficulty = st.selectbox("Difficulty", difficulty_options, index=difficulty_index)
        prev_year = st.text_input("Years in which this appeared (optional)", help="e.g. 2023", value="")
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
            options.append(opt if opt.strip() else None)
        # remove trailing None options
        options = [o for o in options if o is not None]

        correct_answers = st.text_input(
            "Correct answers (if multiple-choice)",
            help="Leave blank for non-MCQ or when you don't want the correct option set here",
        )

        solution_text = st.text_area("Solution", height=200, value="")

        generated_file_name = f"q_{generate_id(output_dir)}.md"

        st.subheader("Output options")
        filename_override = st.text_input(
            "Filename override (optional)",
            help="Generated from the id and the folder provided",
            value=generated_file_name,
        )
        logger.info(f"Filename override: {filename_override}")

        submit = st.form_submit_button("Create question file")

    if submit:
        ensure_output_dir(output_dir)
        extra_meta = {}
        if extra_meta_text.strip():
            try:
                extra_meta = json.loads(extra_meta_text)
            except Exception as e:
                st.error(f"Extra metadata JSON parse error: {e}")
                return

        qdict = build_question_dict(
            topic=topic,
            difficulty=difficulty,
            prev_year=prev_year,
            question=question_text,
            options=options,
            solution_text=solution_text,
            correct_option=correct_answers,
            extra_metadata=extra_meta if extra_meta else None,
        )

        filepath = os.path.join(output_dir, filename_override)

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
