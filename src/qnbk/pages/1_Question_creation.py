# question_creator_app.py
import json
import os
from pathlib import Path

import streamlit as st
from loguru import logger

from qnbk.utils import read_question_file

QUESTIONS_DIR = Path("questions_output")


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
):
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
        "options": options if options else None,
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


def main():
    """The main routine
    :return:
    """
    # ---------------------------
    # Streamlit UI
    # ---------------------------
    st.set_page_config(page_title="Question Bank Creator", layout="wide")
    st.title("Question File Creator/Editor — Question Bank format")

    # Initialize session state for loaded data
    if "loaded_data" not in st.session_state:
        st.session_state.loaded_data = {}

    st.header("Load and Edit")
    file_path = st.text_input(
        "Enter a file path on server (to overwrite)",
        value=QUESTIONS_DIR / "q_00001.md",
        placeholder="/path/to/question.md",
    )
    cols = st.columns(2)
    with cols[0]:
        if_load_and_edit = st.button("Load and upload to edit")
    with cols[1]:
        if_clear_load = st.button("Clear loaded content")

    # Handle load button click
    if if_load_and_edit:
        try:
            raw = read_question_file(Path(file_path), QUESTIONS_DIR)
            st.session_state.loaded_data["output_dir"] = str(raw.get("path", "").parent).replace(
                raw.get("meta", {}).get("topic", ""), ""
            )
            st.session_state.loaded_data["topic"] = raw.get("meta", {}).get("topic", "")
            st.session_state.loaded_data["difficulty"] = raw.get("meta", {}).get("difficulty", "")
            st.session_state.loaded_data["qid"] = raw.get("filename", "").split(".")[0].split("_")[1]
            st.session_state.loaded_data["prev_year"] = raw.get("meta", {}).get("prev_year", "")
            extra_meta = {
                k: v for k, v in raw.get("meta", {}).items() if k not in ["topic", "difficulty", "prev_year", "answer"]
            }
            st.session_state.loaded_data["extra_meta_text"] = json.dumps(extra_meta, indent=2) if extra_meta else ""
            st.session_state.loaded_data["question_text"] = raw.get("question_text", "")
            st.session_state.loaded_data["options"] = (
                list(raw.get("options", {}).values()) if raw.get("options") else [""] * 4
            )
            st.session_state.loaded_data["solution_text"] = raw.get("solution", "")
            st.session_state.loaded_data["correct_answer"] = raw.get("meta", {}).get("answer", "")
            st.success(f"Loaded file: {file_path}")
        except Exception as e:
            st.error(f"Could not read {file_path}: {e}")

    # Handle clear button click
    if if_clear_load:
        st.session_state.loaded_data = {}
        st.success("Cleared loaded content")

    # Use session state data as defaults
    default_dict = st.session_state.loaded_data

    output_dir = st.text_input(
        "Output directory (relative to project root)", value=default_dict.get("output_dir", QUESTIONS_DIR)
    )

    with st.form("qform"):
        st.subheader("Question metadata")
        topic = st.text_input("Topic (e.g. algebra, geometry)", value=default_dict.get("topic", ""))
        topic = topic.strip().capitalize() if topic else ""
        output_dir = Path(output_dir.strip()) / topic

        difficulty_options = ["", "Easy", "Medium", "Hard"]
        loaded_difficulty = default_dict.get("difficulty", "")
        difficulty_index = (
            difficulty_options.index(loaded_difficulty) if loaded_difficulty in difficulty_options else 0
        )
        difficulty = st.selectbox("Difficulty", difficulty_options, index=difficulty_index)
        qid = st.text_input("Question ID (leave blank to auto-generate)", value=default_dict.get("qid"))
        prev_year = st.text_input(
            "Years in which this appeared (optional)", help="e.g. 2023", value=default_dict.get("prev_year")
        )
        extra_meta_text = st.text_area(
            "Extra metadata (as JSON) — optional",
            placeholder='{"learning_objective":"LO1", "chapter": 3}',
            height=80,
            value=default_dict.get("extra_meta_text", ""),
        )

        st.subheader("Question content")
        question_text = st.text_area("Question text", height=200, value=default_dict.get("question_text", ""))
        st.markdown("**Options (leave some blank for open-response)**")
        options = []
        for i in range(4):
            opt = st.text_input(f"Option {chr(65 + i)}", value=default_dict.get("options", [""] * 4)[i])
            options.append(opt if opt.strip() else None)
        # remove trailing None options
        options = [o for o in options if o is not None]

        correct_answers = st.text_input(
            "Correct answers (if multiple-choice)",
            value=default_dict.get("correct_answer", ""),
            help="Leave blank for non-MCQ or when you don't want the correct option set here",
        )

        solution_text = st.text_area("Solution", height=200, value=default_dict.get("solution_text", ""))

        generated_file_name = f"q_{qid.strip() if qid else generate_id(output_dir)}.md"

        st.subheader("Output options")
        filename_override = st.text_input(
            "Filename override (optional)",
            help="Generated from the id and the folder provided",
            value=generated_file_name,
        )
        logger.info(f"Filename override: {filename_override}")

        submit = st.form_submit_button("Create/Update question file")

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
