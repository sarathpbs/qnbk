# Question Bank (qnbk)

Streamlit utilities for creating, editing, organizing, and compiling question-bank files into LaTeX/PDF worksheets.

## What Is In Here?

- `src/qnbk/Welcome.py`: Streamlit app entry page
- `src/qnbk/pages/1_Question_creation.py`: create question files
- `src/qnbk/pages/2_Question_compilation.py`: filter/select questions and export `.tex`/`.pdf`
- `src/qnbk/pages/3_Question_editor.py`: edit existing question files
- `src/qnbk/utils.py`: parsing and markdown read/write helpers
- `data/latex/latex_template.tex`: LaTeX template used during export
- `questions_output/`: default question storage
- `output/`: generated LaTeX/PDF outputs

## Features

### 1) Question Creation

From `1_Question_creation.py`:

- Create question files with YAML front matter + markdown body
- Metadata capture:
  - class (VIII, IX, X, XI, XII)
  - topic
  - difficulty
  - previous year
  - answer
  - optional JSON metadata
- Auto-generate IDs like `q_00001.md`
- Organize files under class/topic folders (for example `questions_output/Class-XI/Algebra/`)
- Preview saved file contents in the UI

### 2) Question Compilation

From `2_Question_compilation.py`:

- Recursively load all `.md` files from a selected question root
- Sidebar filtering by class, topic, and difficulty
- Select individual questions for export
- Render using `data/latex/latex_template.tex`
- Optional answer key generation and optional `last_used` metadata update
- Compile `.tex` to `.pdf` via `pdflatex`
- Download generated `.tex` and `.pdf` directly from Streamlit

### 3) Question Editing

From `3_Question_editor.py`:

- Load an existing file from path
- Edit metadata, question text, options, and solution
- Save back to the same file or a new path
- Download the edited content if direct write is unavailable

## Installation

### Prerequisites

- Python `>=3.10,<3.15`
- Poetry
- `pdflatex` (for PDF build)

On macOS, dependencies can be bootstrapped with:

```bash
brew bundle
```

Then install Python dependencies:

```bash
make deps
```

## Run

Start the app:

```bash
make run
```

Equivalent direct command:

```bash
poetry run streamlit run src/qnbk/Welcome.py
```

The app will open in your browser at `http://localhost:8501`

## Default Paths Used By The App

Defined in `src/qnbk/__init__.py`:

- `DEFAULT_QUESTIONS_DIR = Path("questions_output")`
- `DEFAULT_LATEX_EXPORT_DIR = Path("output")`
- `DEFAULT_TEMPLATE_DIR = Path("data/latex")`
- `DEFAULT_TEMPLATE_NAME = "latex_template.tex"`

## Question File Format

Each question is markdown with YAML front matter.

```markdown
---
topic: Algebra
class: XI
difficulty: Easy
answer: B
prev_year: 2024
last_used:
---

What is the derivative of \(x^2\)?

OptionA: \(x\)
OptionB: \(2x\)
OptionC: \(x^3\)
OptionD: 2

## Solution

Differentiate: \(f'(x)=2x\).
```

Notes:

- `OptionA`..`OptionD` are treated as MCQ options when all are present.
- If options are blank/missing, the question behaves like open response.
- Solution is taken from the `## Solution` section in the body.

## Workflow

1. Create/update question files in `questions_output/` via the create or editor page.
2. Open the compilation page and filter/select questions.
3. Export to `.tex`, then optionally compile to `.pdf`.
4. Download artifacts from Streamlit (files also appear in `output/`).

## Development Notes

- Project metadata and dependencies: `pyproject.toml`
- Common tasks: `Makefile` (run `make help`)
- Core dependencies currently include:
  - `streamlit`
  - `loguru`
  - `PyYAML`

## Troubleshooting

- PDF compilation fails:
  - confirm `pdflatex` is installed and on `PATH`
  - verify `data/latex/latex_template.tex` exists
- Questions not loading:
  - ensure YAML front matter is wrapped with `---`
  - ensure files are under the selected root directory
- Export has unexpected formatting:
  - inspect generated `.tex` in `output/` for escaped characters/math delimiters

### ✅ Recommended Pattern for Images

Instead of using figure, use inline rendering:
```tex
\begin{center}
\includegraphics[width=0.6\textwidth]{image}
\end{center}
```
#### Optional Caption Replacement

If a caption is needed, use `\captionof` without the figure environment:
```tex
\begin{center}
\includegraphics[width=0.6\textwidth]{image}
\captionof{figure}{Your image caption.}
\end{center}
```

## Author

- BalajiSeshaSarath.Pokuri

## License

Proprietary (`LicenseRef-Proprietary` in `pyproject.toml`).
