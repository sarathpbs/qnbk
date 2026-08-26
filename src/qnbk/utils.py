"""Utility functions"""

import re
from pathlib import Path

import streamlit as st
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


def render_chemistry_preview(markdown_content: str, height: int = 400) -> None:
    """Render a beautiful real-time preview of the markdown content with full MathJax + mhchem support."""
    import json  # noqa: PLC0415

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
          const parts = markdownText.split(/(\\$\\$[\\s\\S]*?\\$\\$|\\$[^\\$]*?\\$|\\\\\\[[\\s\\S]*?\\\\\\]
          |\\\\\\([\\s\\S]*?\\\\\\))/g);
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
    st.iframe(html_code, height=height)


def chemistry_help_panel() -> None:
    """Render a collapsible sidebar/expander containing a chemistry syntax guide with copy-pasteable snippets."""
    with st.expander("🧪 Chemistry Writing Guide (mhchem & chemfig)"):
        st.markdown("""
        Use the following syntax in the text fields. It will render beautifully in the PDF export and in the
        **Chemistry Preview** tab.

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
          * Code: `\\ce{Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g) ^}`&rarr; $\\ce{Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g) ^}$

        ### 2. Organic Chemistry & Structures (`\\chemfig{...}`)
        *Note: structures will render perfectly in the exported PDF, but will display as raw TeX in the St preview.*

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
