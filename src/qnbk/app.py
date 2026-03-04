# app.py
import streamlit as st
from pathlib import Path
import yaml
import re
import datetime
import subprocess
import os
import random
import copy

# ---------------------------
# Configuration
# ---------------------------
QUESTIONS_DIR = Path("data/mathematics")
OUTPUT_DIR = Path("output")
TEMPLATE_DIR = Path("data/latex")
TEMPLATE_NAME = "latex_template.tex"
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_ENGINE = "pdflatex"  # change if you prefer xelatex or lualatex

# Extract options in the form OptionA: text or OptionA - text or OptionA text
opt_pattern = re.compile(r"^\s*Option([A-D])\s*(.+)", re.M)


# ---------------------------
# Utilities
# ---------------------------
def read_question_file(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        raise ValueError(f"No YAML frontmatter found in {path}")
    meta_raw, body = m.group(1), m.group(2)
    meta = yaml.safe_load(meta_raw)
    if not meta:
        meta = {}
    meta.setdefault("topic", "Uncategorized")
    meta.setdefault("difficulty", "Unknown")
    meta.setdefault("answer", None)
    meta.setdefault("solution", "")

    options = {}
    for m_opt in opt_pattern.finditer(body):
        letter = m_opt.group(1).upper()
        text_opt = m_opt.group(2).strip()
        options[letter] = text_opt

    return {
        "path": path,
        "meta": meta,
        "body": body.strip(),
        "options": options,
        "filename": path.name,
        "relpath": str(path.relative_to(QUESTIONS_DIR)) if QUESTIONS_DIR in path.parents or path == QUESTIONS_DIR else str(path),
    }

def load_all_questions(qdir: Path):
    files = sorted(qdir.rglob("*.md"))
    qs = []
    for f in files:
        try:
            qs.append(read_question_file(f))
        except Exception as e:
            # keep scanning but report
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

def escape_latex(s: str):
    if not isinstance(s, str):
        return s
    # protect math regions: \(..\), \[..\], $$..$$, $..$
    math_pat = re.compile(r"(\\\(.+?\\\))|(\\\[.+?\\\])|(\$\$.+?\$\$)|(\$.+?\$)", re.S)
    replacements = {}
    token_idx = 0
    def repl(m):
        nonlocal token_idx
        token = f"@@MATH{token_idx}@@"
        replacements[token] = m.group(0)
        token_idx += 1
        return token
    protected = math_pat.sub(repl, s)
    for k, v in LATEX_SPECIALS.items():
        protected = protected.replace(k, v)
    for token, math in replacements.items():
        protected = protected.replace(token, math)
    return protected

def md_to_latex_minimal(md_text: str):
    t = md_text
    t = re.sub(r"^\s*# (.+)$", r"\\section*{\1}", t, flags=re.M)
    t = re.sub(r"^\s*## (.+)$", r"\\subsection*{\1}", t, flags=re.M)
    t = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", t)
    t = re.sub(r"\*(.+?)\*", r"\\emph{\1}", t)
    t = re.sub(r"`(.+?)`", r"\\texttt{\1}", t)
    t = t.replace("  \n", "\\\\\n")
    return t

def question_to_latex(q, include_solution=True, include_key=True):
    meta = q["meta"]
    body_md = q["body"]
    # split question text before OptionA or before first option marker
    split_opt = re.split(r"^\s*Option[A-D]\s*[:\-]?\s*", body_md, maxsplit=1, flags=re.M)
    if len(split_opt) >= 1:
        question_text = split_opt[0].strip()
    else:
        question_text = body_md.strip()
    question_text = md_to_latex_minimal(question_text)
    question_text = escape_latex(question_text)

    # ensure options mapping exists
    options = q.get("options", {}) or {}
    if not options:
        # try fallback extraction in case file used different syntax
        opt_pattern = re.compile(r"^\s*([A-D])[\.\)]\s*(.+)", re.M)
        for m in opt_pattern.finditer(body_md):
            options[m.group(1)] = m.group(2).strip()

    opt_order = ["A", "B", "C", "D"]
    opt_latex_lines = []
    for o in opt_order:
        text = options.get(o, "")
        text = md_to_latex_minimal(text)
        text = escape_latex(text)
        text = text.replace("\n", "\\\\\n")
        opt_latex_lines.append((o, text))

    s = []
    s.append("\\question")
    # include small metadata line
    s.append(f"\\textbf{{Topic:}} {escape_latex(str(meta.get('topic','')))} \\quad \\textbf{{Difficulty:}} {escape_latex(str(meta.get('difficulty','')))}\\\\")
    s.append(question_text + "\n")
    s.append("\\begin{choices}")
    correct = (meta.get("answer") or "").strip().upper()
    for letter, text in opt_latex_lines:
        if include_key and letter.upper() == (correct or "").upper():
            # use indirection macro; template defines \MyCorrectChoice appropriately
            s.append("\\MyCorrectChoice " + text)
        else:
            s.append("\\choice " + text)
    s.append("\\end{choices}\n")
    if meta.get("solution"):
        sol_text = md_to_latex_minimal(meta.get("solution", ""))
        sol_text = escape_latex(sol_text)
        s.append("\\begin{solution}")
        s.append(sol_text)
        s.append("\\end{solution}\n")
    return "\n".join(s)

def render_latex_template_simple(template_path: Path, title: str, date_str: str, questions_tex: str,
                                 show_solutions: bool, show_correct: bool, answer_key_rows=None) -> str:
    tpl = template_path.read_text(encoding="utf-8")

    # Build flags (these are the names produced by \newif\if...)
    show_solutions_line = r"\showsolutionstrue" if show_solutions else r"\showsolutionsfalse"
    show_correct_line = r"\showcorrectstrue" if show_correct else r"\showcorrectsfalse"

    # Build answer key block if provided
    answer_block = ""
    if answer_key_rows:
        rows = ["\\newpage", "\\section*{Answer Key}", "\\begin{tabular}{ll}", "Question & Answer \\\\ \\hline"]
        for r in answer_key_rows:
            rows.append(f"{r['number']} & {r['answer']} \\\\")
        rows.append("\\end{tabular}")
        answer_block = "\n".join(rows)

    out = tpl.replace("<<<SHOW_SOLUTIONS_FLAG>>>", show_solutions_line)
    out = out.replace("<<<SHOW_CORRECT_FLAG>>>", show_correct_line)
    out = out.replace("<<<TITLE>>>", escape_latex(title))
    out = out.replace("<<<DATE>>>", escape_latex(date_str))
    out = out.replace("<<<QUESTIONS_BLOCK>>>", questions_tex)
    out = out.replace("<<<ANSWER_KEY_BLOCK>>>", answer_block)

    return out

def compile_latex(tex_path: Path, workdir: Path):
    cmd = [PDF_ENGINE, "-interaction=nonstopmode", tex_path.name]
    try:
        subprocess.run(cmd, cwd=workdir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(cmd, cwd=workdir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pdf_path = tex_path.with_suffix(".pdf")
        return True, pdf_path
    except subprocess.CalledProcessError as e:
        return False, e

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Question Bank Exporter", layout="wide")
st.title("Question Bank — Streamlit + Markdown → LaTeX/PDF")

if not QUESTIONS_DIR.exists():
    st.error(f"Questions directory {QUESTIONS_DIR} not found. Create it and add .md files.")
    st.stop()

questions = load_all_questions(QUESTIONS_DIR)

# Build filters and sidebar
with st.sidebar:
    st.header("Filters & Export options")
    all_topics = sorted({q["meta"].get("topic","Uncategorized") for q in questions})
    all_difficulties = sorted({q["meta"].get("difficulty","Unknown") for q in questions})

    selected_topics = st.multiselect("Topic(s)", all_topics, default=all_topics)
    selected_difficulties = st.multiselect("Difficulty level(s)", all_difficulties, default=all_difficulties)
    preview_mode = st.checkbox("Show preview before selecting", value=True)

    # Mode selector
    mode = st.radio("Mode", ["Student", "Instructor"], index=0, help="Instructor mode shows solutions and correct choices by default.")

    # sensible defaults based on mode (they can still be changed below)
    if mode == "Instructor":
        default_include_solutions = True
        default_include_key_inline = True
        default_answer_key_at_end = True
    else:
        default_include_solutions = False
        default_include_key_inline = False
        default_answer_key_at_end = False

    include_solutions = st.checkbox("Include solutions in compiled PDF", value=default_include_solutions)
    include_answer_key_inline = st.checkbox("Mark correct choice inline (shows correct choice)", value=default_include_key_inline)
    export_with_key_at_end = st.checkbox("Generate answer key at end of document", value=default_answer_key_at_end)

    # explicit control for showing correct choices inline (user override)
    show_correct_inline = st.checkbox("Show correct choice inline (Instructor-style)", value=(mode=="Instructor"))

    compile_pdf = st.checkbox("Compile to PDF (requires pdflatex installed)", value=True)

    st.write("---")
    st.write("Export destination:")
    st.write(str(OUTPUT_DIR.resolve()))
    st.write("---")
    st.write("Tip: put question files under `questions/` with YAML frontmatter: topic, difficulty, answer, solution.")

# Filter questions
filtered = [q for q in questions if q["meta"].get("topic") in selected_topics and q["meta"].get("difficulty") in selected_difficulties]
st.markdown(f"**Found {len(filtered)} questions** matching filters.")

# Present questions with selection checkboxes
selected_indices = []
cols = st.columns([1,8,2])
with cols[0]:
    st.write("Select")
with cols[1]:
    st.write("Question (preview)")
with cols[2]:
    st.write("Meta")

for idx, q in enumerate(filtered):
    checkbox_key = f"sel_{idx}"
    row_cols = st.columns([1,8,2])
    with row_cols[0]:
        # accessible (hidden) label
        sel = st.checkbox(f"Select {q['filename']}", key=checkbox_key, label_visibility="collapsed")
        if sel:
            selected_indices.append(idx)
    with row_cols[1]:
        # Build preview: header + options
        body_lines = [ln for ln in q["body"].splitlines() if ln.strip() != ""]
        question_header = body_lines[0] if body_lines else q["filename"]

        opts = q.get("options", {})
        opt_order = ["A", "B", "C", "D"]
        opts_md_lines = []
        for letter in opt_order:
            text = opts.get(letter, "").strip()
            if text:
                opts_md_lines.append(f"**{letter}.**  {text}")
            else:
                opts_md_lines.append(f"**{letter}.**  _(missing)_")

        preview_md = f"**{q['filename']}**  \n\n{question_header}\n\n" + "\n\n".join(opts_md_lines)
        st.markdown(preview_md, unsafe_allow_html=True)
        with st.expander("Full preview"):
            st.markdown(q["body"], unsafe_allow_html=True)
            if q["meta"].get("solution"):
                if st.checkbox(f"Show solution for {q['filename']}", key=f"sol_{idx}"):
                    st.markdown("**Solution**\n\n" + q["meta"]["solution"])

    with row_cols[2]:
        st.write(f"Topic: {q['meta'].get('topic')}  \nDiff: {q['meta'].get('difficulty')}")
        ans_letter = (q['meta'].get('answer') or "").strip().upper()
        ans_text = q.get("options", {}).get(ans_letter, "")
        if ans_text:
            st.write(f"Answer: **{ans_letter}** — {ans_text}")
        else:
            st.write(f"Answer: **{ans_letter}**")
        st.write(f"Path: {q.get('relpath','-')}")

# Build list of chosen question objects
chosen = [filtered[i] for i in selected_indices]

st.write("---")
st.markdown(f"**{len(chosen)} selected for export**")
if len(chosen) == 0:
    st.info("Select at least one question to enable export.")
else:
    if st.button("Export selected questions to LaTeX and (optionally) PDF"):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tex_name = OUTPUT_DIR / f"question_export_{timestamp}.tex"

        # Build LaTeX fragments for chosen questions (always include solution environments in .tex)
        question_fragments = []
        for q in chosen:
            # Ensure options exist (fallback extraction)
            if not q.get("options"):
                opt_pattern = re.compile(r"^\s*Option([A-D])\s*[:\-]?\s*(.+)", re.M)
                opts = {}
                for m in opt_pattern.finditer(q["body"]):
                    opts[m.group(1)] = m.group(2).strip()
                q["options"] = opts
            question_fragments.append(question_to_latex(q, include_solution=True, include_key=include_answer_key_inline))

        questions_tex = "\n\n".join(question_fragments)

        # Build optional answer key rows if requested
        answer_key_rows = []
        if (not include_answer_key_inline) and export_with_key_at_end:
            for i, q in enumerate(chosen, start=1):
                answer_letter = (q["meta"].get("answer") or "").strip().upper()
                ans_text = q.get("options", {}).get(answer_letter, "")
                display = f"{answer_letter} — {ans_text}" if ans_text else f"{answer_letter}"
                display_escaped = escape_latex(display)
                answer_key_rows.append({"number": i, "answer": display_escaped})

        # Render template (no Jinja)
        template_path = TEMPLATE_DIR / TEMPLATE_NAME
        title = "Question Bank Export"
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        tex_text = render_latex_template_simple(
            template_path,
            title=title,
            date_str=date_str,
            questions_tex=questions_tex,
            show_solutions=include_solutions,
            show_correct=show_correct_inline,
            answer_key_rows=answer_key_rows
        )

        tex_path = tex_name
        tex_path.write_text(tex_text, encoding="utf-8")
        st.success(f"Wrote LaTeX file: {tex_path}")

        # Provide download of .tex
        with open(tex_path, "rb") as f:
            st.download_button("Download .tex", data=f.read(), file_name=tex_path.name)

        # Optionally compile to PDF
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