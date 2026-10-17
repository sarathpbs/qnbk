"""Manage questions and export to LaTeX/PDF with modern UI and preview dialogs."""

import datetime
from itertools import groupby
from pathlib import Path
import subprocess

from loguru import logger
import streamlit as st

from qnbk import DEFAULT_LATEX_EXPORT_DIR, DEFAULT_QUESTIONS_DIR, DEFAULT_TEMPLATE_DIR, DEFAULT_TEMPLATE_NAME
from qnbk.question_index import load_indexed_questions, rebuild_index, upsert_question
from qnbk.styles import (
    get_answer_badge_html,
    get_class_badge_html,
    get_difficulty_badge_html,
    get_topic_badge_html,
    inject_custom_css,
)
from qnbk.utils import (
    escape_latex,
    md_to_latex_minimal,
    question_to_latex,
    render_chemistry_toggle,
    render_question_preview,
    write_md_file,
)

# ---------------------------
# Configuration & Setup
# ---------------------------
QUESTIONS_DIR = DEFAULT_QUESTIONS_DIR
OUTPUT_DIR = DEFAULT_LATEX_EXPORT_DIR
TEMPLATE_DIR = DEFAULT_TEMPLATE_DIR
TEMPLATE_NAME = DEFAULT_TEMPLATE_NAME
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_ENGINE = "pdflatex"

st.set_page_config(
    page_title="Worksheet Compiler — Question Bank",
    page_icon="📦",
    layout="wide",
)

inject_custom_css()


# ---------------------------
# Utilities & Data Loading
# ---------------------------
@st.cache_data(ttl=120, show_spinner="Loading questions...")
def load_all_questions(qdir: str) -> list[dict]:
    """Load questions from SQLite index with automatic filesystem rebuild fallback."""
    return load_indexed_questions(qdir)


def generate_difficulty_note(questions: list[dict]) -> str:
    """Generate a LaTeX sentence describing the contiguous difficulty ranges of the questions."""
    if not questions:
        return ""

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
        diff_display = "difficult" if diff_lower == "hard" else diff_lower

        if idx_range == 0:
            if start_idx == end_idx:
                ranges.append(f"question {start_idx} is {diff_display}")
            else:
                ranges.append(f"questions {start_idx}-{end_idx} are {diff_display}")
        else:
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
    """Render content into LaTeX template."""
    tpl = template_path.read_text(encoding="utf-8")
    show_solutions_line = r"\showsolutiontrue" if show_solutions else r"\showsolutionfalse"

    out = tpl.replace("<<<SHOW_SOLUTIONS_FLAG>>>", show_solutions_line)
    out = out.replace("<<<TITLE>>>", escape_latex(title))
    out = out.replace("<<<DATE>>>", escape_latex(date_str))
    out = out.replace("<<<QUESTIONS_BLOCK>>>", questions_tex)
    out = out.replace("<<<SOLUTIONS_BLOCK>>>", solutions_tex)
    out = out.replace("<<<ANSWER_KEY_BLOCK>>>", answer_block or "")
    out = out.replace("<<<DIFFICULTY_TOP_BLOCK>>>", difficulty_top)
    return out


def compile_latex(tex_path: Path, workdir: Path) -> tuple[bool, Path | Exception]:
    """Compile LaTeX file to PDF using pdflatex (two passes for references)."""
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
# Modal Dialog for Question Details
# ---------------------------
@st.dialog("Question Details & Preview", width="large")
def show_question_dialog(q: dict) -> None:
    """Displays a modal dialog with full rendered preview, math/chemistry, and metadata."""
    meta = q.get("meta", {})
    diff_badge = get_difficulty_badge_html(meta.get("difficulty"))
    class_badge = get_class_badge_html(meta.get("class"))
    topic_badge = get_topic_badge_html(meta.get("topic"))
    ans_badge = get_answer_badge_html(meta.get("answer"))

    st.markdown(
        f"""
        <div style="margin-bottom: 1.2rem; display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
            {class_badge} {topic_badge} {diff_badge} {ans_badge}
        </div>
        """,
        unsafe_allow_html=True,
    )

    t1, t2 = st.tabs(["📝 Rendered Preview", "📄 File Info & Raw"])

    with t1:
        options = q.get("options") or {}
        non_empty_opts = {k: v for k, v in options.items() if v and v.strip()}
        full_content_md = q.get("question_text", "").strip() + "\n\n"
        if non_empty_opts:
            full_content_md += "#### Options\n"
            correct_ans_raw = str(meta.get("answer") or "").upper()
            correct_letters = [x.strip() for x in correct_ans_raw.split(",") if x.strip()]
            for o in ["A", "B", "C", "D"]:
                opt_val = options.get(o, "")
                if opt_val.strip():
                    if o in correct_letters:
                        full_content_md += f"* **Option {o}**: {opt_val} *(Correct Answer)*  \n"
                    else:
                        full_content_md += f"* **Option {o}**: {opt_val}  \n"
        if q.get("solution"):
            full_content_md += f"\n\n#### Solution\n{q['solution']}"
        render_question_preview(full_content_md, height=380)

    with t2:
        st.markdown(f"**File Path:** `{q.get('relpath', '-')}`")
        if meta.get("source"):
            st.markdown(f"**Source:** {meta.get('source')}")
        if meta.get("prev_year"):
            st.markdown(f"**Previous Years:** {meta.get('prev_year')}")
        if meta.get("last_used"):
            st.markdown(f"**Last Used:** {meta.get('last_used')}")

        st.markdown("#### Raw File Content")
        st.code(q.get("body", ""), language="markdown")


# ---------------------------
# Main App Header & Directory Controls
# ---------------------------
st.title("Worksheet Compiler & PDF Generator")
st.caption("Filter questions from your indexed repository, select items, and export formatted worksheets.")

dir_col, refresh_col, rebuild_col = st.columns([7, 1.2, 1.2], vertical_alignment="bottom")
with dir_col:
    QUESTIONS_DIR = Path(
        st.text_input("Questions directory (relative to project root)", value=str(QUESTIONS_DIR))
    )
with refresh_col:
    if st.button("🔄 Refresh", help="Reload question cache", use_container_width=True):
        load_all_questions.clear()
        st.rerun()
with rebuild_col:
    if st.button("🛠️ Reindex", help="Rebuild SQLite index from disk files", use_container_width=True):
        count = rebuild_index(QUESTIONS_DIR)
        load_all_questions.clear()
        st.success(f"Indexed {count} questions!")
        st.rerun()

if not QUESTIONS_DIR.exists():
    st.error(f"Questions directory '{QUESTIONS_DIR}' not found. Please ensure it exists.")
    st.stop()

questions = load_all_questions(str(QUESTIONS_DIR))

# ---------------------------
# Sidebar Filters & Configuration
# ---------------------------
with st.sidebar:
    render_chemistry_toggle()
    st.write("---")
    st.header("🎯 Filter Question Bank")

    all_classes = sorted({q["meta"].get("class") or "None" for q in questions})
    # Use modern st.pills for class selection
    selected_classes = st.pills(
        "Class",
        all_classes,
        default=all_classes,
        selection_mode="multi",
        help="Select classes to filter questions",
    )
    if not selected_classes:
        selected_classes = all_classes

    class_filtered_questions = [q for q in questions if (q["meta"].get("class") or "None") in selected_classes]

    all_topics = sorted({q["meta"].get("topic") or "Uncategorized" for q in class_filtered_questions})
    all_difficulties = sorted({q["meta"].get("difficulty") or "Unknown" for q in class_filtered_questions})

    selected_topics = st.multiselect("Topic(s)", all_topics, default=all_topics)

    # Use modern st.pills for difficulty selection
    selected_difficulties = st.pills(
        "Difficulty",
        all_difficulties,
        default=all_difficulties,
        selection_mode="multi",
    )
    if not selected_difficulties:
        selected_difficulties = all_difficulties

    # Use modern st.segmented_control for Question Type
    question_type_filter = st.segmented_control(
        "Question Format",
        options=["All", "Objective", "Subjective"],
        default="All",
        help="Filter by objective (MCQ) or subjective (open-response) questions.",
    )

    # Use modern st.segmented_control for Usage Filter
    usage_filter_action = st.segmented_control(
        "Usage Filter",
        options=["All", "Hide Recent", "Only Recent"],
        default="All",
        help="Filter questions based on their 'last_used' timestamp.",
    )

    cutoff_date = None
    if usage_filter_action != "All":
        date_preset = st.selectbox(
            "Time Window",
            options=["1 Month", "3 Months", "1 Year", "Custom Date..."],
            index=0,
        )
        current_utc_date = datetime.datetime.now(datetime.timezone.utc).date()
        if date_preset == "1 Month":
            cutoff_date = current_utc_date - datetime.timedelta(days=30)
        elif date_preset == "3 Months":
            cutoff_date = current_utc_date - datetime.timedelta(days=90)
        elif date_preset == "1 Year":
            cutoff_date = current_utc_date - datetime.timedelta(days=365)
        elif date_preset == "Custom Date...":
            cutoff_date = st.date_input("Cutoff Date", value=current_utc_date)

    st.write("---")
    st.header("⚙️ Worksheet Output Settings")

    # 1. Update last used
    update_last_used = st.checkbox(
        "Update 'last_used' date in files on export",
        value=False,
        help="Marks exported questions with today's date in their YAML metadata.",
    )

    # 2. Sort questions (automatically includes difficulty note at top)
    sort_by_difficulty = st.checkbox(
        "Sort questions by difficulty (Easy → Medium → Hard)",
        value=False,
        help="Sorts questions and automatically includes difficulty range note at the top of the worksheet.",
    )
    show_difficulty_note = sort_by_difficulty

    # 3. Append answer key
    include_answer_key = st.checkbox(
        "Append answer key at the end",
        value=False,
        disabled=st.session_state.get("solutions_inline", False),
    )

    # 4. Append detailed solutions
    include_solutions = st.checkbox(
        "Append detailed solutions section at end",
        value=False,
        disabled=st.session_state.get("solutions_inline", False),
    )

    # 5. Convert MCQs to subjective
    convert_to_subjective = st.checkbox(
        "Convert MCQs to subjective (hide options)",
        value=False,
        help="Hides MCQ options so students must write out full responses.",
    )

    # 6. Show solutions immediately
    solutions_inline = st.checkbox(
        "Show solutions immediately below questions",
        value=False,
        key="solutions_inline",
        help="Options are hidden and solutions are placed immediately under each question.",
    )

    # Compile to PDF is always enabled
    compile_pdf = True

    st.write("---")
    st.caption(f"Export directory: `{OUTPUT_DIR.resolve()}`")

# ---------------------------
# Filter Question List
# ---------------------------
filtered = []
for q in class_filtered_questions:
    if q["meta"].get("topic") not in selected_topics:
        continue
    if q["meta"].get("difficulty") not in selected_difficulties:
        continue

    has_options = any(q.get("options", {}).values())
    if question_type_filter == "Objective" and not has_options:
        continue
    if question_type_filter == "Subjective" and has_options:
        continue

    if usage_filter_action != "All" and cutoff_date is not None:
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
        if usage_filter_action == "Hide Recent" and is_recent:
            continue
        elif usage_filter_action == "Only Recent" and not is_recent:
            continue

    filtered.append(q)

# ---------------------------
# Selection State & Handlers
# ---------------------------
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()


def toggle_selection(rpath: str) -> None:
    if st.session_state.get(f"cb_{rpath}", False):
        st.session_state.selected_questions.add(rpath)
    else:
        st.session_state.selected_questions.discard(rpath)


def select_all_filtered() -> None:
    for q in filtered:
        r = q["relpath"]
        st.session_state.selected_questions.add(r)
        st.session_state[f"cb_{r}"] = True


def deselect_all_filtered() -> None:
    for q in filtered:
        r = q["relpath"]
        st.session_state.selected_questions.discard(r)
        st.session_state[f"cb_{r}"] = False


def clear_all_selections() -> None:
    for r in list(st.session_state.selected_questions):
        st.session_state[f"cb_{r}"] = False
    st.session_state.selected_questions.clear()


# ---------------------------
# Top Controls & Worksheet Header
# ---------------------------
top_col1, top_col2 = st.columns([6, 4], vertical_alignment="bottom")
with top_col1:
    title = st.text_input("Worksheet Title (appears on printed PDF header)", value="Practice Worksheet")
with top_col2:
    st.markdown(
        f"""
        <div style="text-align: right; padding-bottom: 0.5rem;">
            <span class="badge badge-neutral" style="font-size: 0.85rem; padding: 0.4rem 0.8rem;">
                <b>{len(st.session_state.selected_questions)}</b> selected &nbsp;|&nbsp; <b>{len(filtered)}</b> matching
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Bulk Action Buttons
col_sel1, col_sel2, col_sel3, _ = st.columns([2, 2, 2, 4], gap="small")
with col_sel1:
    st.button("✓ Select All Filtered", on_click=select_all_filtered, use_container_width=True)
with col_sel2:
    st.button("✕ Deselect Filtered", on_click=deselect_all_filtered, use_container_width=True)
with col_sel3:
    if len(st.session_state.selected_questions) > 0:
        st.button("🗑️ Clear All", on_click=clear_all_selections, use_container_width=True)

# ---------------------------
# Pagination
# ---------------------------
PAGE_SIZE = 50
total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

pag_col1, pag_col2, pag_col3 = st.columns([2, 6, 2], gap="small", vertical_alignment="center")
with pag_col1:
    current_page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        label_visibility="collapsed",
    )
with pag_col2:
    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(filtered))
    st.caption(f"Showing **{start_idx + 1}–{end_idx}** of **{len(filtered)}** questions • Page {current_page} of {total_pages}")

page_slice = filtered[start_idx:end_idx]

st.write("")

# ---------------------------
# Question Cards Grid
# ---------------------------
for q in page_slice:
    relpath = q["relpath"]
    is_selected = relpath in st.session_state.selected_questions
    if f"cb_{relpath}" not in st.session_state:
        st.session_state[f"cb_{relpath}"] = is_selected

    meta = q.get("meta", {})
    diff_badge = get_difficulty_badge_html(meta.get("difficulty"))
    class_badge = get_class_badge_html(meta.get("class"))
    topic_badge = get_topic_badge_html(meta.get("topic"))
    ans_badge = get_answer_badge_html(meta.get("answer"))

    card_class = "q-card q-card-selected" if is_selected else "q-card"

    with st.container():
        # Render clean question row
        row_c1, row_c2, row_c3 = st.columns([0.6, 7.8, 1.6], gap="small", vertical_alignment="center")

        with row_c1:
            st.checkbox(
                f"Select {q['filename']}",
                key=f"cb_{relpath}",
                on_change=toggle_selection,
                args=(relpath,),
                label_visibility="collapsed",
            )

        with row_c2:
            st.markdown(
                f"""
                <div style="display: flex; gap: 0.4rem; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap;">
                    {class_badge} {topic_badge} {diff_badge} {ans_badge}
                    <span class="meta-label">· {q.get('relpath', '')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Question preview
            preview_snippet = q["question_text"].strip()
            if len(preview_snippet) > 280:
                preview_snippet = preview_snippet[:280] + "..."
            st.markdown(preview_snippet, unsafe_allow_html=True)

        with row_c3:
            if st.button("🔍 Inspect", key=f"btn_inspect_{relpath}", use_container_width=True):
                show_question_dialog(q)

        st.markdown("<hr style='margin: 0.4rem 0 0.85rem 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)


# ---------------------------
# Export & Compilation Section
# ---------------------------
chosen = [q for q in filtered if q["relpath"] in st.session_state.selected_questions]

if sort_by_difficulty:
    difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}
    chosen.sort(key=lambda q: difficulty_order.get(q["meta"].get("difficulty"), 3))

if solutions_inline:
    chosen = [q for q in chosen if q.get("solution") and q["solution"].strip()]

st.write("")
st.write("---")

exp_col1, exp_col2 = st.columns([7, 3], vertical_alignment="center")
with exp_col1:
    st.markdown(f"### 📦 Export Ready: **{len(chosen)} questions selected**")
    if len(chosen) == 0:
        st.info("Select one or more questions from the list above to compile into a LaTeX/PDF worksheet.")

with exp_col2:
    export_clicked = st.button(
        "🚀 Compile LaTeX & PDF Worksheet",
        type="primary",
        disabled=len(chosen) == 0,
        use_container_width=True,
    )

if export_clicked and len(chosen) > 0:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    tex_name = OUTPUT_DIR / f"Q_{timestamp}.tex"

    with st.status("Compiling LaTeX & PDF Worksheet...", expanded=True) as status_box:
        st.write("📝 Formatting questions and solutions for LaTeX...")

        question_fragments = []
        solution_fragments = []
        for q_id, q in enumerate(chosen):
            if update_last_used:
                q["meta"]["last_used"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
                solution_text = q.get("solution", "")
                qdict = {
                    "metadata": q.get("meta"),
                    "body": {
                        "question": q.get("question_text") or "",
                        "options": q.get("options") or {},
                        "solution": (solution_text if solution_text and solution_text.strip() else None),
                    },
                }
                write_md_file(qdict, q["path"])
                try:
                    upsert_question(qdict, q["path"], QUESTIONS_DIR)
                except Exception as e_idx:
                    logger.warning(f"Could not update index for {q['path']}: {e_idx}")

            q["options"] = q.get("options", {})
            include_opts = (not solutions_inline) and (not convert_to_subjective)
            question, solution = question_to_latex(q, include_options=include_opts)
            source_comment = f"% SOURCE: {q.get('relpath', 'Unknown')}\n"
            if solutions_inline:
                sol_formatted = f"\n\n\\par\\medskip\\noindent\\textbf{{Solution:}} {solution}\n"
                question_fragments.append(source_comment + question + sol_formatted)
            else:
                question_fragments.append(source_comment + question)
                if solution:
                    solution_fragments.append(f"\\noindent \\textbf{{{q_id + 1})}} \\quad {solution}\\par\\bigskip\n")

        # Answer key generation
        answer_block = ""
        if include_answer_key:
            st.write("🔑 Generating answer key block...")
            answer_key_rows = []
            for i, q in enumerate(chosen, start=1):
                answer_val = q["meta"].get("answer")
                answer_raw = str(answer_val).strip() if answer_val is not None else ""
                possible_letters = [x.strip().upper() for x in answer_raw.split(",") if x.strip()]
                is_mcq_option = len(possible_letters) > 0 and all(x in ["A", "B", "C", "D"] for x in possible_letters)

                if is_mcq_option:
                    if convert_to_subjective:
                        values = []
                        for letter in possible_letters:
                            val_raw = q.get("options", {}).get(letter, "")
                            val_md = md_to_latex_minimal(val_raw)
                            val_tex = escape_latex(val_md)
                            values.append(val_tex)
                        display_escaped = ", ".join(values)
                    else:
                        display = ",".join(possible_letters)
                        display_escaped = escape_latex(display)
                else:
                    ans_tex = md_to_latex_minimal(answer_raw)
                    display_escaped = escape_latex(ans_tex)

                answer_key_rows.append(f"\\textbf{{{i})}} {display_escaped}")

            answers_inline = " \\quad ".join(answer_key_rows)
            answer_block = (
                r"\bigskip"
                + "\n"
                + r"\noindent \textbf{Answer Key:}\par\medskip"
                + "\n"
                + r"\noindent "
                + answers_inline
                + "\n"
            )

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
        st.write(f"📄 LaTeX source written to `{tex_path.name}`")

        if compile_pdf:
            st.write(f"⚙️ Running `{PDF_ENGINE}` compiler...")
            ok, result = compile_latex(tex_path, tex_path.parent)
            if ok:
                pdf_path = result
                status_box.update(label="✅ Compilation Complete!", state="complete", expanded=False)
                st.success(f"Worksheet successfully generated: **{pdf_path.name}**")

                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📥 Download PDF Worksheet",
                            data=f.read(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                with d_col2:
                    with open(tex_path, "rb") as f:
                        st.download_button(
                            "📄 Download LaTeX (.tex)",
                            data=f.read(),
                            file_name=tex_path.name,
                            mime="text/plain",
                            use_container_width=True,
                        )
            else:
                status_box.update(label="❌ PDF Compilation Failed", state="error", expanded=True)
                st.error(f"LaTeX engine failed with error: {result}")
                with open(tex_path, "rb") as f:
                    st.download_button(
                        "📄 Download LaTeX (.tex) for debugging",
                        data=f.read(),
                        file_name=tex_path.name,
                        mime="text/plain",
                    )
        else:
            status_box.update(label="✅ LaTeX Generated!", state="complete", expanded=False)
            st.success(f"LaTeX source ready: **{tex_path.name}**")
            with open(tex_path, "rb") as f:
                st.download_button(
                    "📄 Download LaTeX (.tex)",
                    data=f.read(),
                    file_name=tex_path.name,
                    mime="text/plain",
                    use_container_width=True,
                )
