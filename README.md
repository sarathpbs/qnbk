# Question Bank (qnbk)

A Streamlit-based question bank management system for creating, organizing, and compiling questions into LaTeX/PDF worksheets.

## Overview

This application provides a complete workflow for managing educational questions:

- **Create Questions**: Add new questions with metadata using an intuitive web interface
- **Browse & Filter**: Search and filter questions by topic, difficulty, and other criteria
- **Export to LaTeX/PDF**: Compile selected questions into professional worksheets with optional answer keys

## Features

### 1. Question Creation (`2_Add_Questions.py`)
- Web-based form for creating new questions
- Support for multiple-choice (MCQ) and open-response questions
- Metadata fields:
  - Topic (e.g., Algebra, Calculus, Geometry)
  - Difficulty level (Easy, Medium, Hard)
  - Previous exam years
  - Custom metadata via JSON
- Auto-generated question IDs
- Automatic file organization by topic
- Real-time preview of created questions

### 2. Question Compilation (`1_Compile_Questions.py`)
- Browse all questions in the database
- Advanced filtering by topic and difficulty
- Individual question selection
- LaTeX template-based rendering
- Intelligent option layout (horizontal for short options, vertical for complex ones)
- Optional solution inclusion
- Answer key generation
- Direct PDF compilation via pdflatex
- Download buttons for both .tex and .pdf files

## Installation

### Prerequisites
- Python 3.10 - 3.14
- Poetry (for dependency management)
- pdflatex (for PDF compilation)
  - macOS: Install via Homebrew using the Brewfile
  ```bash
  brew bundle
  ```

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd qnbk
```

2. Install dependencies:
```bash
make deps
```


## Usage

### Starting the Application

Run the Streamlit app:
```bash
poetry run streamlit run src/qnbk/app.py
```

Or use the make command if available:
```bash
make run
```

The app will open in your browser at `http://localhost:8501`

### Creating Questions

1. Navigate to **"Add Questions"** page
2. Fill in the question metadata:
   - Topic (will organize questions into subdirectories)
   - Difficulty level
   - Question ID (optional - auto-generated if blank)
3. Enter the question text (supports LaTeX math notation)
4. Add up to 4 options for MCQ questions
5. Select the correct answer
6. Write the solution explanation
7. Click **"Create question file"**

### Question File Format

Questions are stored as Markdown files with YAML frontmatter:

```markdown
---
topic: Calculus
difficulty: Easy
answer: A
prev_year: 2023
---

What is the derivative of \(x^2\)?

OptionA: \(2x\)
OptionB: 2
OptionC: \(x^3\)
OptionD: \(x\)

## Solution

Differentiate: \(f'(x)=2x\). So option A is correct.
```

### Compiling Questions to PDF

1. Navigate to **"Compile Questions"** page
2. Use the sidebar to filter by:
   - Topic(s)
   - Difficulty level(s)
3. Toggle options:
   - **Include solutions**: Add solutions after each question or as an answer key
   - **Compile to PDF**: Generate PDF automatically (requires pdflatex)
4. Preview and select questions using checkboxes
5. Enter a title for the worksheet
6. Click **"Export selected questions to LaTeX and PDF"**
7. Download the generated .tex and/or .pdf files

## LaTeX Support

The application supports LaTeX mathematical notation:
- Inline math: `\( ... \)` or `$ ... $`
- Display math: `\[ ... \]` or `$$ ... $$`
- Bold: `**text**` → `\textbf{text}`
- Italic: `*text*` → `\emph{text}`
- Code: `` `text` `` → `\texttt{text}`

The system intelligently escapes LaTeX special characters while preserving math environments.

## Configuration

Key configuration variables (in `1_Compile_Questions.py`):

```python
QUESTIONS_DIR = Path("data/mathematics")   # Question storage location
OUTPUT_DIR = Path("output")                # Export destination
TEMPLATE_DIR = Path("data/latex")          # LaTeX template location
PDF_ENGINE = "pdflatex"                    # PDF compiler
```

## Development

### Dependencies

Key packages:
- `streamlit` - Web application framework
- `loguru` - Enhanced logging

Development tools:
- `mypy` - Type checking
- `black` - Code formatting
- `flake8` - Linting

## Features in Detail

### Smart Option Layout
The compiler automatically chooses the best layout for multiple-choice options:
- **Horizontal layout**: For short, simple options (≤140 chars total, no display math)
- **Vertical layout**: For longer options or those containing complex math

### Answer Key Generation
When "Include solutions" is enabled:
- Solutions appear after each question in the main document
- A separate answer key page is appended at the end
- Each answer shows the letter and the full option text

### Question ID Management
- Auto-increments based on existing questions in the topic folder
- Format: `q_00001.md`, `q_00002.md`, etc.
- Can be overridden manually during creation

## Troubleshooting

### PDF Compilation Fails
- Ensure `pdflatex` is installed: `which pdflatex`
- Check the LaTeX template exists at `data/latex/latex_template.tex`
- Review error output in the Streamlit interface

### Questions Not Appearing
- Verify question files are present.
- Check YAML frontmatter is properly formatted with `---` delimiters
- Ensure topic and difficulty are set in the frontmatter

### LaTeX Rendering Issues
- Verify math delimiters are properly closed
- Check for unescaped special characters outside math mode
- Review the generated .tex file for syntax errors

## License

Proprietary (see `pyproject.toml`)

## Authors

BalajiSeshaSarath.Pokuri

---

**Version**: 0.0.0
**Python**: 3.10 - 3.14
