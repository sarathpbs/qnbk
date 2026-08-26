import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path

# Add src folder to import qnbk utilities
repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root / "src"))

from qnbk.utils import read_question_file, question_to_latex


def resolve_active_path(active_file, workspace_root=None):
    """Resolves active file path into a local WSL path, handling UNC and Windows paths."""
    if not active_file:
        raise ValueError("Active file path is empty")

    normalized = active_file.replace('\\', '/')
    candidate = Path(active_file)

    if normalized.startswith('/wsl.localhost/Ubuntu/') or normalized.startswith('//wsl.localhost/Ubuntu/'):
        normalized = normalized.replace('/wsl.localhost/Ubuntu/', '', 1)
        normalized = normalized.replace('//wsl.localhost/Ubuntu/', '', 1)
        if normalized.startswith('home/ranga/qnbk/'):
            normalized = normalized[len('home/ranga/qnbk/'):]
        if workspace_root is None:
            return Path('/home/ranga/qnbk') / normalized
        return Path(workspace_root) / normalized

    if normalized.startswith('\\\\') or re.match(r"^[A-Za-z]:[/\\]", active_file):
        try:
            res = subprocess.run(["wslpath", "-u", active_file], capture_output=True, text=True, check=True)
            return Path(res.stdout.strip())
        except Exception:
            return Path(normalized)

    if candidate.is_absolute():
        if candidate.parts and candidate.parts[0] in {'/', '\\'}:
            return candidate
        return Path(workspace_root) / candidate

    if workspace_root is None:
        workspace_root = Path.cwd()
    else:
        workspace_root = Path(workspace_root)

    return (workspace_root / candidate).resolve()


def make_error_svg(error_text: str) -> str:
    """Generates an SVG image displaying the LaTeX compilation errors."""
    lines = error_text.splitlines()[:22]
    tspans = ""
    y = 65
    for line in lines:
        escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        tspans += f'<tspan x="20" y="{y}">{escaped_line}</tspan>\n'
        y += 18
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{y + 20}">
  <rect width="100%" height="100%" fill="#ffeeee" stroke="#ffcccc" stroke-width="2" rx="5"/>
  <text x="20" y="35" font-family="sans-serif" font-size="16" fill="#cc0000" font-weight="bold">LaTeX Compilation Error</text>
  <text font-family="monospace" font-size="12" fill="#333333">
    {tspans}
  </text>
</svg>"""


def compile_latex_to_svg(q_latex: str, sol_latex: str, output_svg_path: Path) -> tuple[bool, str]:
    """Compiles LaTeX to DVI using latex and converts to SVG using dvisvgm in a temp folder."""
    latex_template = r"""\documentclass[varwidth=17cm,margin=10pt]{standalone}
\usepackage{amsmath,amssymb}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{tabularx}
\usepackage{array}
\usepackage{graphicx}
\usepackage[version=4]{mhchem}
\usepackage{chemfig}
\usepackage[output=exam,randomizequestions=false,randomizeanswers=false]{mcexam}
\usepackage{enumitem}

\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\renewcommand{\labelenumi}{\arabic{enumi}.}
\renewcommand{\labelenumii}{\Alph{enumii}.}
\setlist*[setmcquestions]{itemsep=1ex, parsep=0.5ex, topsep=0.5ex}
\setlist*[setmcanswerslist]{itemsep=0.2ex, parsep=0.2ex, topsep=0.2ex}

\begin{document}
\begin{mcquestions}
<<<QUESTION_LATEX>>>
\end{mcquestions}

<<<SOLUTION_BLOCK>>>
\end{document}
"""
    # Build solution block if present
    sol_block = ""
    if sol_latex.strip():
        sol_block = f"\\bigskip\\noindent\\textbf{{Solution:}}\\\\\n{sol_latex.strip()}\n"

    document_tex = latex_template.replace("<<<QUESTION_LATEX>>>", q_latex).replace("<<<SOLUTION_BLOCK>>>", sol_block)

    # Ensure output base directory exists
    output_svg_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=str(repo_root / "output")) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        tex_file = tmpdir / "preview.tex"
        tex_file.write_text(document_tex, encoding="utf-8")

        # Compile tex -> dvi
        cmd_latex = ["latex", "-interaction=nonstopmode", "-halt-on-error", "preview.tex"]
        res_latex = subprocess.run(
            cmd_latex,
            cwd=str(tmpdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if res_latex.returncode != 0:
            # LaTeX compile failed, extract log errors
            log_file = tmpdir / "preview.log"
            error_details = ""
            if log_file.exists():
                log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                errors = []
                log_lines = log_content.splitlines()
                for idx, line in enumerate(log_lines):
                    if line.startswith("!"):
                        errors.append("\n".join(log_lines[idx : idx + 6]))
                error_details = "\n\n".join(errors) if errors else "\n".join(log_lines[-25:])
            else:
                error_details = res_latex.stdout or "Unknown latex compiler error."

            return False, error_details

        # Convert dvi -> svg
        dvi_file = tmpdir / "preview.dvi"
        cmd_dvisvgm = ["dvisvgm", "--no-fonts", "--exact-bbox", "preview.dvi", "-o", "preview.svg"]
        res_dvisvgm = subprocess.run(
            cmd_dvisvgm,
            cwd=str(tmpdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        svg_file = tmpdir / "preview.svg"
        if not svg_file.exists():
            error_msg = res_dvisvgm.stderr or res_dvisvgm.stdout or "dvisvgm failed to generate SVG."
            return False, error_msg

        # Copy SVG to destination and add white background
        svg_content = svg_file.read_text(encoding="utf-8")
        svg_content = re.sub(r'<svg([^>]*)>', r'<svg\1 style="background-color: white;">', svg_content, count=1)
        output_svg_path.write_text(svg_content, encoding="utf-8")
        return True, ""


def main():
    if len(sys.argv) < 2:
        print("Error: No active markdown file provided.")
        sys.exit(1)

    active_file = sys.argv[1].strip("'\"")
    if not active_file.endswith('.md'):
        print("Error: Active file is not a markdown (.md) file.")
        sys.exit(1)

    # 1. Resolve path to WSL format
    try:
        active_path = resolve_active_path(active_file, repo_root)
    except Exception as e:
        print(f"Error resolving path: {e}")
        sys.exit(1)

    if not active_path.exists():
        print(f"Error: File does not exist at path: {active_path}")
        sys.exit(1)

    # 2. Read and parse markdown question
    try:
        q = read_question_file(active_path, repo_root / "questions_output")
    except Exception as e:
        print(f"Error parsing question markdown: {e}")
        sys.exit(1)

    base_name = active_path.stem
    output_svg_path = repo_root / "output" / "previews" / f"{base_name}.svg"

    answer_val = q.get("meta", {}).get("answer")
    if answer_val is None or not str(answer_val).strip():
        print("Error: Answer not added for this question.")
        error_msg = "Validation Error: Answer is missing from metadata.\nPlease add 'answer: <option>' to the YAML frontmatter."
        output_svg_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            error_svg_content = make_error_svg(error_msg)
            output_svg_path.write_text(error_svg_content, encoding="utf-8")
            res = subprocess.run(["wslpath", "-w", str(output_svg_path)], capture_output=True, text=True, check=True)
            windows_path = res.stdout.strip()
            subprocess.run(["cmd.exe", "/c", "code", "-r", windows_path], cwd="/mnt/c", check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Failed to show error SVG: {e}")
        sys.exit(1)

    # 3. Format to LaTeX
    try:
        q_latex, sol_latex = question_to_latex(q, include_options=True)
    except Exception as e:
        print(f"Error converting markdown to LaTeX: {e}")
        sys.exit(1)

    # 4. Compile to SVG
    base_name = active_path.stem
    output_svg_path = repo_root / "output" / "previews" / f"{base_name}.svg"

    success, error_msg = compile_latex_to_svg(q_latex, sol_latex, output_svg_path)

    if not success:
        print("--- LaTeX Compilation Failed ---")
        print(error_msg)
        # Write compilation error to preview SVG so the open editor tab updates to show the error
        try:
            error_svg_content = make_error_svg(error_msg)
            output_svg_path.write_text(error_svg_content, encoding="utf-8")
        except Exception as e:
            print(f"Failed to write error SVG: {e}")
        sys.exit(1)

    print(f"Successfully compiled LaTeX preview to: {output_svg_path}")

    # 5. Open SVG in VS Code (triggers on first compile or focuses the file tab in the Windows workspace)
    try:
        # Convert the Linux path to Windows format (UNC path)
        res = subprocess.run(["wslpath", "-w", str(output_svg_path)], capture_output=True, text=True, check=True)
        windows_path = res.stdout.strip()
        # Open in Windows editor using 'code -r' (focus/re-use active window)
        # Running cmd.exe with /mnt/c as CWD ensures it operates under Windows environment context
        subprocess.run(["cmd.exe", "/c", "code", "-r", windows_path], cwd="/mnt/c", check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Note: Could not open preview tab in VSCode automatically: {e}")


if __name__ == "__main__":
    main()
