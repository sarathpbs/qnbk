"""Manage questions and export to latex/PDF."""

import datetime
import re
import subprocess
from pathlib import Path

import streamlit as st
from loguru import logger

from qnbk import DEFAULT_LATEX_EXPORT_DIR, DEFAULT_QUESTIONS_DIR, DEFAULT_TEMPLATE_DIR, DEFAULT_TEMPLATE_NAME
from qnbk.utils import read_question_file, write_md_file, render_chemistry_preview

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


def find_matching_bracket(s: str, start_idx: int, open_char: str, close_char: str) -> int:
    """Finds the index of the matching closing bracket/brace, handling nesting."""
    depth = 0
    for idx in range(start_idx, len(s)):
        char = s[idx]
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return idx
    return -1


def escape_latex(s: str) -> str:
    """Escapes LaTeX special characters in the input string, while preserving math delimiters and content.

    :param s:
    :return:
    """
    if not isinstance(s, str):
        return s

    replacements = {}
    token_idx = 0
    i = 0
    n = len(s)
    result = []

    while i < n:
        # Check for delimiters
        if s.startswith(r"\(", i):
            j = s.find(r"\)", i + 2)
            if j != -1:
                token = f"@@MATH{token_idx}@@"
                replacements[token] = s[i : j + 2]
                token_idx += 1
                result.append(token)
                i = j + 2
                continue
        elif s.startswith(r"\[", i):
            j = s.find(r"\]", i + 2)
            if j != -1:
                token = f"@@MATH{token_idx}@@"
                replacements[token] = s[i : j + 2]
                token_idx += 1
                result.append(token)
                i = j + 2
                continue
        elif s.startswith("$$", i):
            j = s.find("$$", i + 2)
            if j != -1:
                token = f"@@MATH{token_idx}@@"
                replacements[token] = s[i : j + 2]
                token_idx += 1
                result.append(token)
                i = j + 2
                continue
        elif s.startswith("$", i):
            j = s.find("$", i + 1)
            if j != -1:
                token = f"@@MATH{token_idx}@@"
                replacements[token] = s[i : j + 1]
                token_idx += 1
                result.append(token)
                i = j + 1
                continue
        elif s.startswith(r"\begin{", i):
            env_match = re.match(r"^\\begin\{([^}]+)\}", s[i:])
            if env_match:
                env_name = env_match.group(1)
                end_str = f"\\end{{{env_name}}}"
                j = s.find(end_str, i)
                if j != -1:
                    end_idx = j + len(end_str)
                    token = f"@@MATH{token_idx}@@"
                    replacements[token] = s[i : end_idx]
                    token_idx += 1
                    result.append(token)
                    i = end_idx
                    continue
        elif s[i] == "\\" and i + 1 < n and s[i + 1].isalpha():
            cmd_match = re.match(r"^\\[a-zA-Z]+", s[i:])
            if cmd_match:
                cmd_len = len(cmd_match.group(0))
                cmd_end = i + cmd_len
                curr = cmd_end
                while curr < n:
                    if s[curr] == "[":
                        close_idx = find_matching_bracket(s, curr, "[", "]")
                        if close_idx != -1:
                            curr = close_idx + 1
                        else:
                            break
                    elif s[curr] == "{":
                        close_idx = find_matching_bracket(s, curr, "{", "}")
                        if close_idx != -1:
                            curr = close_idx + 1
                        else:
                            break
                    else:
                        break
                token = f"@@MATH{token_idx}@@"
                replacements[token] = s[i:curr]
                token_idx += 1
                result.append(token)
                i = curr
                continue

        result.append(s[i])
        i += 1

    protected = "".join(result)
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


def question_to_latex(q: dict) -> tuple[str, str]:
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
    s.append("\\question " + question_text + "\n")

    answer_val = q["meta"].get("answer")
    answer_str = str(answer_val).strip() if answer_val is not None else ""
    correct_letters = answer_str.upper().split(",")
    flags = [
        "1" if "A" in correct_letters else "0",
        "1" if "B" in correct_letters else "0",
        "1" if "C" in correct_letters else "0",
        "1" if "D" in correct_letters else "0",
    ]
    if not all(opt_texts.values()):
        mc_text = "\\begin{mcanswers}[permutenone]\n \\answer[correct]{1}{} \n\\end{mcanswers}"
    else:
        opt_args = []
        mc_text = "\\vspace{-1em}\n\\begin{mcanswers}\n"
        if use_horizontal:
            mc_text += "\\begin{tabular}{p{0.48\\textwidth} p{0.48\\textwidth}}\n"
        for opt_num, (flag, letter) in enumerate(zip(flags, opt_order, strict=False)):
            body = opt_texts[letter]
            # ensure each argument is TeX safe (already escaped)
            opt_args.append(body)
            if flag == "1":
                mc_text += f"\\answernum{{{opt_num + 1}}}~ \\answer[correct]{{{opt_num + 1}}}{{{body}}}"
            else:
                mc_text += f"\\answernum{{{opt_num + 1}}}~ \\answer{{{opt_num + 1}}}{{{body}}}"
            if use_horizontal and opt_num % 2 == 0:
                mc_text += " & "
            else:
                mc_text += " \\\\\n"
        if use_horizontal:
            mc_text += "\\end{tabular}\n"
        mc_text += "\\end{mcanswers}\n\\vspace{-1em}"
    s.append(mc_text)

    # macro_call = "\\OptionGrid" if use_horizontal else "\\OptionList"
    # for flag in flags:
    #     macro_call = macro_call + f"{{{flag}}}"
    # for opt in opt_args:
    #     macro_call = macro_call + f"{{{opt}}}"
    # s.append(macro_call + "\n")

    # Solution (always included in .tex; printing controlled by template)
    sol_text = q.get("solution", "") or ""
    solution = []
    if sol_text:
        sol_text_md = md_to_latex_minimal(sol_text)
        sol_text_tex = escape_latex(sol_text_md)
        solution.append(sol_text_tex)

    return "\n".join(s), "\n".join(solution)


def generate_difficulty_note(questions: list[dict]) -> str:
    """Generate a LaTeX sentence describing the contiguous difficulty ranges of the questions."""
    if not questions:
        return ""

    from itertools import groupby

    items = []
    for idx, q in enumerate(questions, 1):
        diff = q["meta"].get("difficulty") or "Unknown"
        items.append((idx, diff))

    ranges = []
    for idx_range, (diff, grp) in enumerate(groupby(items, key=lambda x: x[1])):
        grp_list = list(grp)
        start_idx = grp_list[0][0]
        end_idx = grp_list[-1][0]
        
        diff_lower = diff.lower()
        if diff_lower == "hard":
            diff_display = "difficult"
        else:
            diff_display = diff_lower

        if idx_range == 0:
            # First range has the prefix "question" or "questions"
            if start_idx == end_idx:
                ranges.append(f"question {start_idx} is {diff_display}")
            else:
                ranges.append(f"questions {start_idx}-{end_idx} are {diff_display}")
        else:
            # Subsequent ranges do not repeat "questions" prefix
            if start_idx == end_idx:
                ranges.append(f"{start_idx} is {diff_display}")
            else:
                ranges.append(f"{start_idx}-{end_idx} are {diff_display}")

    if not ranges:
        return ""

    sentence = ", ".join(ranges) + "."
    sentence = sentence[0].upper() + sentence[1:]

    return f"\\noindent \\textit{{Note: {sentence}}}\\par\\medskip\n"


def render_latex_template_simple(
    template_path: Path,
    title: str,
    date_str: str,
    questions_tex: str,
    solutions_tex: str,
    show_solutions: bool,
    answer_block: str | None = None,
    difficulty_top: str = "",
) -> str:
    """Render into the latex template

    :param template_path:
    :param title:
    :param date_str:
    :param questions_tex:
    :param show_solutions:
    :param answer_block:
    :param difficulty_top:
    :return:
    """
    tpl = template_path.read_text(encoding="utf-8")

    show_solutions_line = r"\showsolutiontrue" if show_solutions else r"\showsolutionfalse"

    out = tpl.replace("<<<SHOW_SOLUTIONS_FLAG>>>", show_solutions_line)
    out = out.replace("<<<TITLE>>>", escape_latex(title))
    out = out.replace("<<<DATE>>>", escape_latex(date_str))
    out = out.replace("<<<QUESTIONS_BLOCK>>>", questions_tex)
    out = out.replace("<<<SOLUTIONS_BLOCK>>>", solutions_tex)
    out = out.replace("<<<ANSWER_KEY_BLOCK>>>", answer_block)
    out = out.replace("<<<DIFFICULTY_TOP_BLOCK>>>", difficulty_top)

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

    question_type_filter = st.radio(
        "Question Type:",
        options=["All", "Objective (with options)", "Subjective (no options)"],
        index=0,
        help="Filter by objective (has options) or subjective (no options) questions."
    )

    usage_filter_action = st.radio(
        "Usage Date Filter:",
        options=["All questions", "Hide recently used", "Show only recently used"],
        index=0,
        help="Filter questions based on their 'last_used' date."
    )

    cutoff_date = None
    if usage_filter_action != "All questions":
        date_preset = st.selectbox(
            "Select Time Window:",
            options=["1 Month", "3 Months", "1 Year", "Custom Date..."],
            index=0
        )
        current_utc_date = datetime.datetime.now(datetime.timezone.utc).date()
        if date_preset == "1 Month":
            cutoff_date = current_utc_date - datetime.timedelta(days=30)
        elif date_preset == "3 Months":
            cutoff_date = current_utc_date - datetime.timedelta(days=90)
        elif date_preset == "1 Year":
            cutoff_date = current_utc_date - datetime.timedelta(days=365)
        elif date_preset == "Custom Date...":
            cutoff_date = st.date_input("Select Cutoff Date:", value=current_utc_date)

    include_solutions = st.checkbox("Include detailed solutions in compiled PDF", value=False)
    include_answer_key = st.checkbox("Include answer key at the end", value=False)

    compile_pdf = st.checkbox("Compile to PDF", value=True)

    update_last_used = st.checkbox(
        "Update last used",
        value=False,
        help="If checked, updates the 'last_used' field in each of the question metadata to current date (YYYY-MM-DD)",
    )

    sort_by_difficulty = st.checkbox(
        "Sort questions by difficulty (Easy -> Medium -> Hard)",
        value=False,
        help="If checked, sorts the chosen questions so Easy ones appear first, then Medium, and Hard last.",
    )

    show_difficulty_note = st.checkbox(
        "Show difficulty range note (at top)",
        value=False,
        help="If checked, adds a note at the top of the worksheet showing the difficulty ranges of the questions.",
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
filtered = []

for q in class_filtered_questions:
    if q["meta"].get("topic") not in selected_topics:
        continue
    if q["meta"].get("difficulty") not in selected_difficulties:
        continue

    # Filter by question type (objective vs subjective)
    has_options = any(q.get("options", {}).values())
    if question_type_filter == "Objective (with options)" and not has_options:
        continue
    if question_type_filter == "Subjective (no options)" and has_options:
        continue
    if usage_filter_action != "All questions" and cutoff_date is not None:
        last_used_val = q["meta"].get("last_used")
        last_used_date = None
        if last_used_val:
            if isinstance(last_used_val, datetime.date):
                last_used_date = last_used_val
            elif isinstance(last_used_val, datetime.datetime):
                last_used_date = last_used_val.date()
            elif isinstance(last_used_val, str):
                try:
                    last_used_date = datetime.datetime.strptime(last_used_val.strip(), "%Y-%m-%d").date()
                except ValueError:
                    pass
        is_recent = last_used_date is not None and last_used_date >= cutoff_date
        if usage_filter_action == "Hide recently used" and is_recent:
            continue
        elif usage_filter_action == "Show only recently used" and not is_recent:
            continue
    filtered.append(q)
st.markdown(f"**Found {len(filtered)} questions** matching filters.")
title = st.text_input("Title for the worksheet (appears in PDF header)", value="Questions")

# Bulk selection controls
if len(filtered) > 0:
    col_sel1, col_sel2, _ = st.columns([2.5, 2.5, 7], gap="small")
    with col_sel1:
        if st.button("Select all filtered", use_container_width=True):
            for q in filtered:
                st.session_state[f"sel_{q['relpath']}"] = True
            st.rerun()
    with col_sel2:
        if st.button("Deselect all filtered", use_container_width=True):
            for q in filtered:
                st.session_state[f"sel_{q['relpath']}"] = False
            st.rerun()

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
    checkbox_key = f"sel_{q['relpath']}"
    row_cols = st.columns([1, 8, 3], gap="small", vertical_alignment="center")
    with row_cols[0]:
        sel = st.checkbox(f"Select {q['filename']}", key=checkbox_key, label_visibility="collapsed")
        if sel:
            selected_indices.append(idx)
    with row_cols[1]:
        preview_md = q["question_text"].strip()
        st.markdown(preview_md, unsafe_allow_html=True)
        with st.expander("Question details & preview"):
            tab1, tab2 = st.tabs(["📝 Standard Preview", "🧪 Chemistry Preview"])
            with tab1:
                st.markdown(q["body"], unsafe_allow_html=True)
                if q.get("solution"):
                    st.markdown("**Solution:**")
                    st.markdown(q["solution"])
            with tab2:
                full_content_md = q["question_text"] + "\n\n"
                options = q.get("options", {}) or {}
                non_empty_opts = {k: v for k, v in options.items() if v.strip()}
                if non_empty_opts:
                    full_content_md += "#### Options\n"
                    for o in ["A", "B", "C", "D"]:
                        opt_val = options.get(o, "")
                        if opt_val.strip():
                            full_content_md += f"* **Option {o}**: {opt_val}  \n"
                if q.get("solution"):
                    full_content_md += f"\n\n#### Solution\n{q['solution']}"
                render_chemistry_preview(full_content_md, height=300)

    with row_cols[2]:
        st.write(f"Diff: {q['meta'].get('difficulty')}")
        if q["meta"].get("source"):
            st.write(f"Source: {q['meta'].get('source')}")
        answer_val = q["meta"].get("answer")
        answer_raw = str(answer_val).strip() if answer_val is not None else ""
        possible_letters = [x.strip().upper() for x in answer_raw.split(",") if x.strip()]
        is_mcq_option = len(possible_letters) > 0 and all(x in ["A", "B", "C", "D"] for x in possible_letters)
        
        if is_mcq_option:
            ans_display = ",".join(possible_letters)
            st.write(f"Answer: **{ans_display}**")
        else:
            st.write(f"Answer: {answer_raw}")
        st.write(f"Path: {q.get('relpath', '-')}")

# Build list of chosen question objects
chosen = [filtered[i] for i in selected_indices]

if sort_by_difficulty:
    difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    chosen.sort(key=lambda q: difficulty_order.get(q["meta"].get("difficulty"), 3))

st.write("---")
st.markdown(f"**{len(chosen)} selected for export**")
if len(chosen) == 0:
    st.info("Select at least one question to enable export.")
else:
    if st.button("Export selected questions to LaTeX and PDF"):
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        tex_name = OUTPUT_DIR / f"Q_{timestamp}.tex"

        question_fragments = []
        solution_fragments = []
        for q_id, q in enumerate(chosen):
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
            question, solution = question_to_latex(q)
            question_fragments.append(question)
            if solution:
                solution_fragments.append(f"\\noindent \\textbf{{{q_id + 1})}} \\quad {solution}\\par\\bigskip\n")

        # wrap in top-level enumerate in the template; template expects items inside an enumerate
        answer_block = ""
        if include_answer_key:
            answer_key_rows = []
            for i, q in enumerate(chosen, start=1):
                answer_val = q["meta"].get("answer")
                answer_raw = str(answer_val).strip() if answer_val is not None else ""
                possible_letters = [x.strip().upper() for x in answer_raw.split(",") if x.strip()]
                is_mcq_option = len(possible_letters) > 0 and all(x in ["A", "B", "C", "D"] for x in possible_letters)
                
                if is_mcq_option:
                    display = ",".join(possible_letters)
                    display_escaped = escape_latex(display)
                else:
                    ans_tex = md_to_latex_minimal(answer_raw)
                    display_escaped = escape_latex(ans_tex)
                
                answer_key_rows.append(f"\\textbf{{{i})}} {display_escaped}")
            
            answers_inline = " \\quad ".join(answer_key_rows)
            answer_block = r"\bigskip" + "\n" + r"\noindent \textbf{Answer Key:}\par\medskip" + "\n" + r"\noindent " + answers_inline + "\n"

        template_path = TEMPLATE_DIR / TEMPLATE_NAME
        date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")
        difficulty_top = generate_difficulty_note(chosen) if show_difficulty_note else ""
        tex_text = render_latex_template_simple(
            template_path,
            title=title,
            date_str=date_str,
            questions_tex="\n\n".join(question_fragments),
            solutions_tex="\n\n".join(solution_fragments),
            show_solutions=include_solutions,
            answer_block=answer_block,
            difficulty_top=difficulty_top,
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
