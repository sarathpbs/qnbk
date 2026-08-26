"""Utility functions"""

import re
from pathlib import Path

import yaml
from loguru import logger

option_pattern_raw = r"^\s*Option([A-D])\s*[:\-]?\s*(.+)"
opt_pattern = re.compile(option_pattern_raw, re.M)
opt_pattern_bare = re.compile(r"^\s*([A-D])[\.\)]\s*(.+)", re.M)


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
        options = qdict["body"]["options"]
        if all(options.values()):
            for opt_label, opt in options.items():
                f.write(f"Option{opt_label}: {opt}\n")
        # write solution
        if qdict["body"]["solution"]:
            f.write("\n\n## Solution\n\n")
            f.write(qdict["body"]["solution"] + "\n")
    logger.info(f"Written to file: {filename}")


def split_solution_from_body(body: str) -> tuple[str, str]:
    """Separate solution section from the main body, if it exists.

    Look for a line that starts with "Solution"
    (optionally preceded by up to 3 # for headers, and followed by optional : or -), and split the body
    into question part and solution part.

    :param body:
    :return:
    """
    if not body:
        return body, ""
    lines = body.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        m = re.match(r"^\s*(#{1,3}\s*)?Solution\b\s*[:\-]?\s*(.*)$", line, re.IGNORECASE)
        if m:
            first_line_content = m.group(2) or ""
            rest = "".join(lines[idx + 1 :])
            solution = (first_line_content + ("\n" + rest if rest else "")).lstrip()
            return "".join(lines[:idx]), solution
    return body, ""


def read_question_file(path: Path, qns_dir: Path = "data") -> dict:
    """Get metadata, question, options and solution from a question file.

    Expects a Markdown file with YAML frontmatter for metadata, and the body containing the question text, options,
    and solution.
    @:param path: Path to the question Markdown file.
    """
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        msg = f"No YAML frontmatter found in {path}"
        raise ValueError(msg)
    meta_raw, body = m.group(1), m.group(2)
    meta = yaml.safe_load(meta_raw)
    if not meta:
        meta = {}
    # Have default values for all the required metadata fields.
    meta.setdefault("topic", "Uncategorized")
    meta.setdefault("difficulty", "Unknown")
    meta.setdefault("answer", None)
    meta.setdefault("class", "Unknown")
    meta.setdefault("last_used", "")
    meta.setdefault("prev_year", "")
    meta.setdefault("source", "")

    body = body.rstrip("\n")
    body_without_solution, extracted_solution = split_solution_from_body(body)
    yaml_solution = meta.pop("solution", None)
    solution_text = extracted_solution if extracted_solution and extracted_solution.strip() else (yaml_solution or "")

    options = {}
    # See if the options are named `OptionA: ...` etc. If not, try the bare format `A. ...` or `A) ...`
    for m_opt in opt_pattern.finditer(body_without_solution):
        letter = m_opt.group(1).upper()
        text_opt = m_opt.group(2).strip()
        options[letter] = text_opt
    if not options:
        for m in opt_pattern_bare.finditer(body_without_solution):
            options[m.group(1).upper()] = m.group(2).strip()
    split_opt = re.split(option_pattern_raw, body_without_solution, maxsplit=1, flags=re.M)
    question_text = split_opt[0].strip() if split_opt else body_without_solution.strip()

    return {
        "path": path,
        "meta": meta,
        "body": body_without_solution.strip(),
        "solution": solution_text.strip(),
        "question_text": question_text,
        "options": options,
        "filename": path.name,
        "relpath": str(path.relative_to(qns_dir)) if qns_dir in path.parents or path == qns_dir else str(path),
    }


def render_chemistry_preview(markdown_content: str, height: int = 400):
    """Renders a beautiful real-time preview of the markdown content with full MathJax + mhchem support."""
    import json
    import streamlit.components.v1 as components

    # JSON-serialize the markdown string to safely insert it into JS
    js_content = json.dumps(markdown_content)

    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script>
      window.MathJax = {
        tex: {
          inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
          displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
          processEscapes: true,
          packages: {'[+]': ['mhchem']}
        },
        loader: {load: ['[tex]/mhchem']}
      };
      </script>
      <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" id="MathJax-script" async></script>
      <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          font-size: 15px;
          line-height: 1.6;
          color: #31333F; /* Streamlit default text color */
          background-color: transparent;
          margin: 0;
          padding: 10px;
        }
        pre {
          background-color: #f0f2f6;
          padding: 10px;
          border-radius: 4px;
          overflow-x: auto;
        }
        code {
          font-family: monospace;
          background-color: #f0f2f6;
          padding: 2px 4px;
          border-radius: 3px;
        }
        table {
          border-collapse: collapse;
          width: 100%;
          margin-bottom: 1rem;
        }
        th, td {
          border: 1px solid #e6e9ef;
          padding: 8px;
          text-align: left;
        }
        th {
          background-color: #f8f9fa;
        }
      </style>
    </head>
    <body>
      <div id="content"></div>
      <script>
        try {
          let markdownText = <<<JS_CONTENT>>>;
          
          // Preprocess to wrap \\ce{...} outside math mode in \\( \\ce{...} \\)
          const parts = markdownText.split(/(\\$\\$[\\s\\S]*?\\$\\$|\\$[^\\$]*?\\$|\\\\\\[[\\s\\S]*?\\\\\\]|\\\\\\([\\s\\S]*?\\\\\\))/g);
          for (let i = 0; i < parts.length; i++) {
            if (i % 2 === 0) {
              parts[i] = parts[i].replace(/\\\\ce\\{([^{}]*(?:\\{[^{}]*\\}[^{}]*)*)\\}/g, '$$\\\\ce{$1}$$');
            }
          }
          markdownText = parts.join('');
          
          document.getElementById('content').innerHTML = marked.parse(markdownText);
          
          if (window.MathJax && window.MathJax.typeset) {
            window.MathJax.typeset();
          } else {
            document.getElementById('MathJax-script').addEventListener('load', () => {
              window.MathJax.typeset();
            });
          }
        } catch (e) {
          document.getElementById('content').innerHTML = "<p style='color:red;'>Preview Error: " + e.message + "</p>";
        }
      </script>
    </body>
    </html>
    """.replace("<<<JS_CONTENT>>>", js_content)
    components.html(html_code, height=height, scrolling=True)


def chemistry_help_panel():
    """Renders a collapsible sidebar/expander containing a chemistry syntax guide with copy-pasteable snippets."""
    import streamlit as st

    with st.expander("🧪 Chemistry Writing Guide (mhchem & chemfig)"):
        st.markdown("""
        Use the following syntax in the text fields. It will render beautifully in the PDF export and in the **Chemistry Preview** tab.

        ### 1. Inorganic Formulas & Reactions (`\\ce{...}`)
        Wrap formulas and chemical reactions in `\\ce{...}`. You don't need to put it inside math mode.

        * **Simple Formulas**:
          * Code: `\\ce{H2O}` &rarr; $H_2O$
          * Code: `\\ce{H2SO4}` &rarr; $H_2SO_4$
          * Code: `\\ce{NO3-}` &rarr; $NO_3^-$
        * **Reactions & Arrows**:
          * Code: `\\ce{2H2 + O2 -> 2H2O}` &rarr; $2H_2 + O_2 \\rightarrow 2H_2O$
          * Code: `\\ce{N2 + 3H2 <=> 2NH3}` &rarr; $N_2 + 3H_2 \\rightleftharpoons 2NH_3$
          * Code: `\\ce{A ->[catalyst][heat] B}` &rarr; arrow with text above/below
        * **Ions & Charges**:
          * Code: `\\ce{Na+ + Cl- -> NaCl}` &rarr; $Na^+ + Cl^- \\rightarrow NaCl$
          * Code: `\\ce{Fe^2+ + Ce^4+ -> Fe^3+ + Ce^3+}` &rarr; $Fe^{2+} + Ce^{4+} \\rightarrow Fe^{3+} + Ce^{3+}$
        * **Matter States & Gas/Precipitate**:
          * Code: `\\ce{Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g) ^}` &rarr; $\\ce{Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g) ^}$

        ### 2. Organic Chemistry & Structures (`\\chemfig{...}`)
        *Note: structures will render perfectly in the exported PDF, but will display as raw TeX in the Streamlit preview.*

        * **Bonds**:
          * Code: `\\chemfig{A-B}` (Single)
          * Code: `\\chemfig{A=B}` (Double)
          * Code: `\\chemfig{A~B}` (Triple)
        * **Branches**:
          * Code: `\\chemfig{C(-[2]H)(-[4]H)(-[6]H)-H}` (Methane)
        * **Rings & Cyclic Compounds**:
          * Code: `\\chemfig{*6(-=-=-=)}` (Benzene)
          * Code: `\\chemfig{*6(------)}` (Cyclohexane)
          * Code: `\\chemfig{*6(-=-=N-=)}` (Pyridine)
        """)

        st.markdown("### Quick Snippets (Click the copy button on the right)")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Common Inorganic Formulas")
            st.code("\\ce{H2O}", language="latex")
            st.code("\\ce{H2SO4}", language="latex")
            st.code("\\ce{CO2 + H2O <=> H2CO3}", language="latex")
            st.code("\\ce{->[heat][catalyst]}", language="latex")
        with col2:
            st.caption("Common Organic Structures")
            st.code("\\chemfig{*6(-=-=-=)}", language="latex")
            st.code("\\chemfig{*6(------)}", language="latex")
            st.code("\\chemfig{R-C(=O)-OH}", language="latex")
            st.code("\\chemfig{C(-[2])(-[4])(-[6])-}", language="latex")


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
    """Escapes LaTeX special characters in the input string, while preserving math delimiters and content."""
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
    return t


def question_to_latex(q: dict, include_options: bool = True) -> tuple[str, str]:
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

    # Decide whether to render horizontally or in a single line
    H_THRESH = 140
    SINGLE_LINE_THRESH = 65
    has_display_math = any(("$$" in s or r"\[" in s or r"\begin{" in s) for s in options.values())
    total_len = sum(len(s) for s in options.values())
    
    can_horizontal = (not has_display_math) and all(s.strip() for s in options.values())
    use_single_line = can_horizontal and (total_len <= SINGLE_LINE_THRESH)
    use_horizontal = can_horizontal and (SINGLE_LINE_THRESH < total_len <= H_THRESH)

    s = []
    # question as an item in top-level enumerate
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
    if not include_options or not all(opt_texts.values()):
        mc_text = "\\setbox0=\\vbox{\n\\begin{mcanswers}[permutenone]\n \\answernum{1}~ \\answer[correct]{1}{} \n\\end{mcanswers}\n}"
    else:
        opt_args = []
        mc_text = "\\vspace{-1em}\n\\begin{mcanswers}\n"
        if use_single_line:
            mc_text += "\\begin{tabular}{p{0.24\\textwidth} p{0.24\\textwidth} p{0.24\\textwidth} p{0.24\\textwidth}}\n"
        elif use_horizontal:
            mc_text += "\\begin{tabular}{p{0.48\\textwidth} p{0.48\\textwidth}}\n"
            
        for opt_num, (flag, letter) in enumerate(zip(flags, opt_order, strict=False)):
            body = opt_texts[letter]
            opt_args.append(body)
            if flag == "1":
                mc_text += f"\\answernum{{{opt_num + 1}}}~ \\answer[correct]{{{opt_num + 1}}}{{{body}}}"
            else:
                mc_text += f"\\answernum{{{opt_num + 1}}}~ \\answer{{{opt_num + 1}}}{{{body}}}"
            
            if use_single_line:
                if opt_num < 3:
                    mc_text += " & "
                else:
                    mc_text += " \\\\\n"
            elif use_horizontal:
                if opt_num % 2 == 0:
                    mc_text += " & "
                else:
                    mc_text += " \\\\\n"
            else:
                mc_text += " \\\\\n"
                
        if use_single_line or use_horizontal:
            mc_text += "\\end{tabular}\n"
        mc_text += "\\end{mcanswers}\n\\vspace{-1em}"
    if mc_text:
        s.append(mc_text)

    # Solution
    sol_text = q.get("solution", "") or ""
    solution = []
    if sol_text:
        sol_text_md = md_to_latex_minimal(sol_text)
        sol_text_tex = escape_latex(sol_text_md)
        solution.append(sol_text_tex)

    return "\n".join(s), "\n".join(solution)


