# app.py
import datetime
import re
import subprocess
from pathlib import Path

import streamlit as st
import yaml
from loguru import logger

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
opt_pattern = re.compile(r"^\s*Option([A-D])\s*[:\-]?\s*(.+)", re.M)


# ---------------------------
# Utilities
# ---------------------------
def extract_solution_from_body(body: str):
    if not body:
        return body, ""
    lines = body.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if "<!-- solution" in line.lower():
            sol_lines = lines[idx + 1 :]
            return "".join(lines[:idx]), "".join(sol_lines).lstrip()
        m = re.match(r"^\s*(#{1,3}\s*)?Solution\b\s*[:\-]?\s*(.*)$", line, re.I)
        if m:
            first_line_content = m.group(2) or ""
            rest = "".join(lines[idx + 1 :])
            solution = (first_line_content + ("\n" + rest if rest else "")).lstrip()
            return "".join(lines[:idx]), solution
    return body, ""


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

    body = body.rstrip("\n")
    body_without_solution, extracted_solution = extract_solution_from_body(body)
    yaml_solution = meta.pop("solution", None)
    solution_text = extracted_solution if extracted_solution and extracted_solution.strip() else (yaml_solution or "")

    # opt_pattern = re.compile(r"^\s*Option([A-D])\s*[:\-]?\s*(.+)", re.M)
    options = {}
    for m_opt in opt_pattern.finditer(body_without_solution):
        letter = m_opt.group(1).upper()
        text_opt = m_opt.group(2).strip()
        options[letter] = text_opt

    return {
        "path": path,
        "meta": meta,
        "body": body_without_solution.strip(),
        "solution": solution_text.strip(),
        "options": options,
        "filename": path.name,
        "relpath": str(path.relative_to(QUESTIONS_DIR))
        if QUESTIONS_DIR in path.parents or path == QUESTIONS_DIR
        else str(path),
    }


def load_all_questions(qdir: Path):
    files = sorted(qdir.rglob("*.md"))
    qs = []
    for f in files:
        try:
            qs.append(read_question_file(f))
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


def escape_latex(s: str):
    if not isinstance(s, str):
        return s
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


def question_to_latex(q):
    """
    Render one question to LaTeX.
    - Chooses horizontal options layout when short and simple, else vertical enumerate.
    - Uses \MyCorrectMark to highlight a correct option (template defines it).
    """
    meta = q["meta"]
    body_md = q["body"]
    # extract question text (before OptionA)
    split_opt = re.split(r"^\s*Option[A-D]\s*[:\-]?\s*", body_md, maxsplit=1, flags=re.M)
    question_text = split_opt[0].strip() if split_opt else body_md.strip()
    question_text = md_to_latex_minimal(question_text)
    question_text = escape_latex(question_text)

    # ensure options mapping exists
    options = q.get("options", {}) or {}
    if not options:
        opt_pattern = re.compile(r"^\s*([A-D])[\.\)]\s*(.+)", re.M)
        for m in opt_pattern.finditer(body_md):
            options[m.group(1)] = m.group(2).strip()

    opt_order = ["A", "B", "C", "D"]
    # build option latex texts
    opt_texts = []
    for o in opt_order:
        raw = options.get(o, "")
        t_md = md_to_latex_minimal(raw)
        t_tex = escape_latex(t_md)
        t_tex = t_tex.replace("\n", "\\\\\n")
        opt_texts.append(t_tex)

    # Decide whether to render horizontally
    # Heuristic: total chars short and no display-math or long environments
    H_THRESH = 140
    has_display_math = any(("$$" in s or r"\[" in s or r"\begin{" in s) for s in options.values())
    total_len = sum(len(s) for s in options.values())
    use_horizontal = (not has_display_math) and (total_len <= H_THRESH) and all(s.strip() for s in options.values())

    s = []
    # question as an item in top-level enumerate (caller/template handles outer enumerate)
    s.append("\\item " + question_text + "\n")

    correct = (meta.get("answer") or "").strip().upper()

    if use_horizontal:
        # prepare each option, wrapping correct one with \MyCorrectMark if include_key True
        opt_args = []
        for idx, letter in enumerate(opt_order):
            body = opt_texts[idx]
            # ensure each argument is TeX safe (already escaped)
            opt_args.append(body)
        # use the OptionRow macro: pass four parameters
        # join with ' & ' handled by the macro; here we build the macro call
        macro_call = "\\OptionRow{" + "}{".join(opt_args) + "}"
        s.append(macro_call + "\n")
    else:
        # fallback to vertical options using nested enumerate
        s.append("\\begin{enumerate}\n")
        for idx, letter in enumerate(opt_order):
            body = opt_texts[idx]
            s.append("\\item " + body + "\n")
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

def render_latex_template_simple(template_path: Path, title: str, date_str: str,
                                 questions_tex: str, show_solutions: bool, answer_block=None) -> str:
    tpl = template_path.read_text(encoding="utf-8")

    show_solutions_line = r"\showsolutiontrue" if show_solutions else r"\showsolutionfalse"

    # TODO: Solutions_flag does not work!
    #  TODO: fix the template to conditionally show/hide solutions based on this flag. For now, it always includes solutions in the .tex and relies on the template to hide them if show_solutions is False.
    out = tpl.replace("<<<SHOW_SOLUTIONS_FLAG>>>", show_solutions_line)
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
    all_topics = sorted({q["meta"].get("topic", "Uncategorized") for q in questions})
    all_difficulties = sorted({q["meta"].get("difficulty", "Unknown") for q in questions})

    selected_topics = st.multiselect("Topic(s)", all_topics, default=all_topics)
    selected_difficulties = st.multiselect("Difficulty level(s)", all_difficulties, default=all_difficulties)

    include_solutions = st.checkbox("Include solutions in compiled PDF (Answer key at end)",
                                    value=False)

    compile_pdf = st.checkbox("Compile to PDF (requires pdflatex installed)", value=True)

    st.write("---")
    st.write("Export destination:")
    st.write(str(OUTPUT_DIR.resolve()))
    st.write("---")
    st.write(
        f"Tip: put question files under `{QUESTIONS_DIR}` with YAML frontmatter: topic, difficulty, answer (solution goes "
        f"in the body)."
    )

# Filter questions
filtered = [
    q
    for q in questions
    if q["meta"].get("topic") in selected_topics and q["meta"].get("difficulty") in selected_difficulties
]
st.markdown(f"**Found {len(filtered)} questions** matching filters.")

# Present questions with selection checkboxes (show only question text in list)
selected_indices = []
cols = st.columns([1, 8, 2])
with cols[0]:
    st.write("Select")
with cols[1]:
    st.write("Question (preview)")
with cols[2]:
    st.write("Meta")

for idx, q in enumerate(filtered):
    checkbox_key = f"sel_{idx}"
    row_cols = st.columns([1, 8, 2])
    with row_cols[0]:
        sel = st.checkbox(f"Select {q['filename']}", key=checkbox_key, label_visibility="collapsed")
        if sel:
            selected_indices.append(idx)
    with row_cols[1]:
        split_opt = re.split(r"^\s*Option[A-D]\s*[:\-]?\s*", q["body"], maxsplit=1, flags=re.M)
        question_text = split_opt[0].strip() if split_opt else q["body"].strip()
        preview_md = f"**{q['filename']}**  \n\n{question_text}"
        st.markdown(preview_md, unsafe_allow_html=True)
        with st.expander("Full preview"):
            st.markdown(q["body"], unsafe_allow_html=True)
            soltext = q.get("solution", "")
            if soltext:
                if st.checkbox(f"Show solution for {q['filename']}", key=f"sol_{idx}"):
                    st.markdown("**Solution**\n\n" + soltext)

    with row_cols[2]:
        st.write(f"Topic: {q['meta'].get('topic')}  \nDiff: {q['meta'].get('difficulty')}")
        ans_letter = (q["meta"].get("answer") or "").strip().upper()
        ans_text = q.get("options", {}).get(ans_letter, "")
        if ans_text:
            st.write(f"Answer: **{ans_letter}** — {ans_text}")
        else:
            st.write(f"Answer: **{ans_letter}**")
        st.write(f"Path: {q.get('relpath', '-')}")

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

        question_fragments = []
        for q in chosen:
            if not q.get("options"):
                # opt_pattern = re.compile(r"^\s*Option([A-D])\s*[:\-]?\s*(.+)", re.M)
                opts = {}
                for m in opt_pattern.finditer(q["body"]):
                    opts[m.group(1)] = m.group(2).strip()
                q["options"] = opts
            question_fragments.append(
                question_to_latex(q)
            )

        # questions_tex now should be a sequence of \item ... entries
        questions_tex = "\n\n".join(question_fragments)
        # wrap in top-level enumerate in the template; template expects items inside an enumerate

        answer_block = ''
        if include_solutions:
            answer_key_rows = []
            for i, q in enumerate(chosen, start=1):
                answer_letter = (q["meta"].get("answer") or "").strip().upper()
                ans_text = q.get("options", {}).get(answer_letter, "")
                display = f"{answer_letter} — {ans_text}" if ans_text else f"{answer_letter}"
                display_escaped = escape_latex(display)
                answer_key_rows.append({"number": i, "answer": display_escaped})
            answer_block = "\pagebreak" + "\n".join([f"{row['number']}:{row['answer']}\n" for row in answer_key_rows])

        template_path = TEMPLATE_DIR / TEMPLATE_NAME
        title = "Question Bank Export"
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
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
