"""Manage questions and export to latex/PDF."""

import datetime
import re
import subprocess
from pathlib import Path

import streamlit as st
from loguru import logger

from qnbk import DEFAULT_LATEX_EXPORT_DIR, DEFAULT_QUESTIONS_DIR, DEFAULT_TEMPLATE_DIR, DEFAULT_TEMPLATE_NAME
from qnbk.utils import read_question_file, write_md_file

# ---------------------------
# Configuration
# ---------------------------
QUESTIONS_DIR = DEFAULT_QUESTIONS_DIR
OUTPUT_DIR = DEFAULT_LATEX_EXPORT_DIR
TEMPLATE_DIR = DEFAULT_TEMPLATE_DIR
TEMPLATE_NAME = DEFAULT_TEMPLATE_NAME
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_ENGINE = "pdflatex"  # change if you prefer xelatex or lualatex

# Extract options in the form OptionA: text or OptionA - text or OptionA text


# ---------------------------
# Utilities
# ---------------------------


def load_all_questions(qdir: Path) -> list[dict]:
    """Load all question files from the given directory and subdirectories."""
    files = sorted(qdir.rglob("*.md"))
    qs = []
    for f in files:
        try:
            qs.append(read_question_file(f, qdir))
        except Exception as e:
            st.error(f"Error reading {f}: {e}")
    return qs


# Minimal LaTeX-escaping (keeps common math delimiters intact)
LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
}


def escape_latex(s: str) -> str:
    """Escapes LaTeX special characters in the input string, while preserving math delimiters and content.

    :param s:
    :return:
    """
    if not isinstance(s, str):
        return s
    math_pat = re.compile(
        r"(\\\(.+?\\\))|(\\\[.+?\\\])|(\$\$.+?\$\$)|(\$.+?\$)|(\\begin\{([^}]+)\}.*?\\end\{\6\})", re.S
    )
    replacements = {}
    token_idx = 0

    def _repl(m):  # noqa: ANN001, ANN202
        nonlocal token_idx
        token = f"@@MATH{token_idx}@@"
        replacements[token] = m.group(0)
        token_idx += 1
        return token

    protected = math_pat.sub(_repl, s)
    for k, v in LATEX_SPECIALS.items():
        protected = protected.replace(k, v)
    for token, math in replacements.items():
        protected = protected.replace(token, math)
    logger.info(f"{s=} -> {protected=}")
    return protected


def md_to_latex_minimal(md_text: str) -> str:
    """Convert a subset of Markdown syntax to LaTeX."""
    t = md_text
    t = re.sub(r"^\s*# (.+)$", r"\\section*{\1}", t, flags=re.M)
    t = re.sub(r"^\s*## (.+)$", r"\\subsection*{\1}", t, flags=re.M)
    t = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", t)
    t = re.sub(r"\*(.+?)\*", r"\\emph{\1}", t)
    t = re.sub(r"`(.+?)`", r"\\texttt{\1}", t)
    t = t.replace("  \n", "\\\\\n")
    return t  # noqa: RET504


def question_to_latex(q: dict) -> str:
    """Render one question to LaTeX.

    Chooses horizontal options layout when short and simple, else vertical enumerate.
    """
    question_text = q["question_text"]
    question_text = md_to_latex_minimal(question_text)
    question_text = escape_latex(question_text)

    # ensure options mapping exists
    options = q.get("options", {}) or {}

    opt_order = ["A", "B", "C", "D"]
    # build option latex texts
    opt_texts = {}
    for o in opt_order:
        raw = options.get(o, "")
        t_md = md_to_latex_minimal(raw)
        t_tex = escape_latex(t_md)
        t_tex = t_tex.replace("\n", "\\\\\n")
        opt_texts[o] = t_tex

    # Decide whether to render horizontally
    # HEURISTIC: total chars short and no display-math or long environments
    H_THRESH = 140
    has_display_math = any(("$$" in s or r"\[" in s or r"\begin{" in s) for s in options.values())
    total_len = sum(len(s) for s in options.values())
    use_horizontal = (not has_display_math) and (total_len <= H_THRESH) and all(s.strip() for s in options.values())

    s = []
    # question as an item in top-level enumerate (caller/template handles outer enumerate)
    s.append("\\item " + question_text + "\n")

    # correct = (meta.get("answer") or "").strip().upper()
    if all(opt_texts.values()):
        if use_horizontal:
            # use the `OptionRow` macro to render options in a single horizontal row
            opt_args = []
            for letter in opt_order:
                body = opt_texts[letter]
                # ensure each argument is TeX safe (already escaped)
                opt_args.append(body)
            # use the OptionRow macro: pass four parameters
            # join with ' & ' handled by the macro; here we build the macro call
            macro_call = "\\OptionRow{" + "}{".join(opt_args) + "}"
            s.append(macro_call + "\n")
        else:
            # fallback to vertical options using nested enumerate
            s.append("\\begin{enumerate}\n")
            for letter in opt_order:
                s.append("\\item " + opt_texts[letter] + "\n")
            s.append("\\end{enumerate}\n")

    # Solution (always included in .tex; printing controlled by template)
    sol_text = q.get("solution", "") or ""
    if sol_text:
        sol_text_md = md_to_latex_minimal(sol_text)
        sol_text_tex = escape_latex(sol_text_md)
        s.append("\\begin{solution}")
        s.append(sol_text_tex)
        s.append("\\end{solution}\n")

    return "\n".join(s)


def render_latex_template_simple(
    template_path: Path,
    title: str,
    date_str: str,
    questions_tex: str,
    show_solutions: bool,
    answer_block: str | None = None,
) -> str:
    """Render into the latex template

    :param template_path:
    :param title:
    :param date_str:
    :param questions_tex:
    :param show_solutions:
    :param answer_block:
    :return:
    """
    tpl = template_path.read_text(encoding="utf-8")

    show_solutions_line = r"\showsolutiontrue" if show_solutions else r"\showsolutionfalse"

    out = tpl.replace("<<<SHOW_SOLUTIONS_FLAG>>>", show_solutions_line)
    out = out.replace("<<<TITLE>>>", escape_latex(title))
    out = out.replace("<<<DATE>>>", escape_latex(date_str))
    out = out.replace("<<<QUESTIONS_BLOCK>>>", questions_tex)
    out = out.replace("<<<ANSWER_KEY_BLOCK>>>", answer_block)

    return out  # noqa: RET504


def compile_latex(tex_path: Path, workdir: Path) -> tuple[bool, Path | Exception]:
    """Compile the given .tex file to PDF using pdflatex."""
    cmd = [PDF_ENGINE, "-interaction=nonstopmode", tex_path.name]
    try:
        subprocess.run(cmd, cwd=workdir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(cmd, cwd=workdir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pdf_path = tex_path.with_suffix(".pdf")
    except subprocess.CalledProcessError as e:
        return False, e
    else:
        return True, pdf_path


# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Question Bank", layout="wide")
st.title("Question Extractor")

QUESTIONS_DIR = st.text_input("Questions directory (relative to project root)", value=str(QUESTIONS_DIR))
QUESTIONS_DIR = Path(QUESTIONS_DIR)

if not QUESTIONS_DIR.exists():
    st.error(f"Questions directory {QUESTIONS_DIR} not found. Create it and add .md files.")
    st.stop()

questions = load_all_questions(QUESTIONS_DIR)

# Build filters and sidebar
with st.sidebar:
    st.header("Filters & Export options")
    all_classes = sorted({q["meta"].get("class") or "None" for q in questions})
    selected_classes = st.multiselect("Class(es)", all_classes, default=all_classes)

    # Filter questions to only those whose class is in the selected classes
    class_filtered_questions = [q for q in questions if (q["meta"].get("class") or "None") in selected_classes]

    all_topics = sorted({q["meta"].get("topic") or "Uncategorized" for q in class_filtered_questions})
    all_difficulties = sorted({q["meta"].get("difficulty") or "Unknown" for q in class_filtered_questions})

    selected_topics = st.multiselect("Topic(s)", all_topics, default=all_topics)
    selected_difficulties = st.multiselect("Difficulty level(s)", all_difficulties, default=all_difficulties)

    include_solutions = st.checkbox("Include solutions in compiled PDF (Answer key at the end)", value=False)

    compile_pdf = st.checkbox("Compile to PDF", value=True)

    update_last_used = st.checkbox(
        "Update last used",
        value=False,
        help="If checked, updates the 'last_used' field in each of the question metadata to current date (YYYY-MM-DD)",
    )

    st.write("---")
    st.write("Export destination:")
    st.write(str(OUTPUT_DIR.resolve()))
    st.write("---")
    st.write(
        f"Tip: put question files under `{QUESTIONS_DIR}` with YAML frontmatter: "
        f"class, topic, difficulty, answer (solution goes in the body)."
    )

# Filter questions
filtered = [
    q
    for q in class_filtered_questions
    if q["meta"].get("topic") in selected_topics and q["meta"].get("difficulty") in selected_difficulties
]
st.markdown(f"**Found {len(filtered)} questions** matching filters.")
title = st.text_input("Title for the worksheet (appears in PDF header)", value="Questions")

# Present questions with selection checkboxes (show only question text in list)
selected_indices = []
cols = st.columns([1, 8, 3], gap="small", vertical_alignment="center")
with cols[0]:
    st.write("Select")
with cols[1]:
    st.write("Question (preview)")
with cols[2]:
    st.write("Meta")

for idx, q in enumerate(filtered):
    checkbox_key = f"sel_{idx}"
    row_cols = st.columns([1, 8, 3], gap="small", vertical_alignment="center")
    with row_cols[0]:
        sel = st.checkbox(f"Select {q['filename']}", key=checkbox_key, label_visibility="collapsed")
        if sel:
            selected_indices.append(idx)
    with row_cols[1]:
        preview_md = q["question_text"].strip()
        st.markdown(preview_md, unsafe_allow_html=True)
        with st.expander("Question file"):
            st.markdown(q["body"], unsafe_allow_html=True)
            with st.expander("**Solution**\n"):
                st.markdown(q.get("solution", ""))

    with row_cols[2]:
        st.write(f"Diff: {q['meta'].get('difficulty')}")
        ans_letters = (q["meta"].get("answer") or "").strip().upper().split(",")
        ans_text = [q.get("options", {}).get(ans_letter, "").strip() for ans_letter in ans_letters]
        ans_text = ",".join(ans_text)
        if len(ans_text) < 12:
            st.write(f"Answer: **{ans_letters}** — {ans_text}")
        else:
            st.write(f"Answer: **{ans_letters}**")
        st.write(f"Path: {q.get('relpath', '-')}")

# Build list of chosen question objects
chosen = [filtered[i] for i in selected_indices]

st.write("---")
st.markdown(f"**{len(chosen)} selected for export**")
if len(chosen) == 0:
    st.info("Select at least one question to enable export.")
else:
    if st.button("Export selected questions to LaTeX and PDF"):
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        tex_name = OUTPUT_DIR / f"Q_{timestamp}.tex"

        question_fragments = []
        for q in chosen:
            # update the file of `q` if the checkbox is checked
            if update_last_used:
                q["meta"]["last_used"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                solution_text = q.get("solution", "")
                # write back to file
                qdict = {
                    "metadata": q.get("meta"),
                    "body": {
                        "question": q.get("question_text") or "",
                        "options": q.get("options") or {},
                        "solution": (solution_text if solution_text and solution_text.strip() else None),
                    },
                }
                logger.info(
                    f"Updating last_used for {q['filename']} to {q['meta']['last_used']}; {qdict['body']['options']}"
                )
                write_md_file(qdict, q["path"])
            q["options"] = q.get("options", {})
            question_fragments.append(question_to_latex(q))

        # questions_tex now should be a sequence of \item ... entries
        questions_tex = "\n\n".join(question_fragments)
        # wrap in top-level enumerate in the template; template expects items inside an enumerate

        answer_block = ""
        if include_solutions:
            answer_key_rows = []
            for i, q in enumerate(chosen, start=1):
                answer_letters = (q["meta"].get("answer") or "").strip().upper().split(",")
                ans_text = [q.get("options", {}).get(ans_letter, "").strip() for ans_letter in answer_letters]
                ans_text = ",".join(ans_text)
                display = f"{answer_letters} — {ans_text}" if ans_text else f"{answer_letters}"
                display_escaped = escape_latex(display)
                answer_key_rows.append({"number": i, "answer": display_escaped})
            answer_block = r"\pagebreak" + "\n".join([f"{row['number']}:{row['answer']}\n" for row in answer_key_rows])

        template_path = TEMPLATE_DIR / TEMPLATE_NAME
        date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")
        tex_text = render_latex_template_simple(
            template_path,
            title=title,
            date_str=date_str,
            questions_tex=questions_tex,
            show_solutions=include_solutions,
            answer_block=answer_block,
        )

        tex_path = tex_name
        tex_path.write_text(tex_text, encoding="utf-8")
        st.success(f"Wrote LaTeX file: {tex_path}")

        with open(tex_path, "rb") as f:
            st.download_button("Download .tex", data=f.read(), file_name=tex_path.name)

        if compile_pdf:
            st.info("Compiling to PDF (this runs pdflatex — must be installed on the server).")
            with st.spinner("Running pdflatex..."):
                ok, result = compile_latex(tex_path, tex_path.parent)
                if ok:
                    pdf_path = result
                    st.success(f"Compiled PDF: {pdf_path}")
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download PDF", data=f.read(), file_name=pdf_path.name)
                else:
                    st.error(f"Compilation failed: {result}")
