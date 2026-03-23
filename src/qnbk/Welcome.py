import streamlit as st


def main() -> None:
    """Introduction to the app."""
    st.write("# Question Bank Utilities 📚")

    st.markdown(
        """
        A Streamlit-based question bank management system for **creating**, **editing**, **organizing**,
        and **compiling** questions into LaTeX/PDF worksheets.

        Use the sidebar to navigate between pages.

        ---

        ## Pages

        ### 1. 📝 Question Creation
        Create new question files with YAML front matter and a markdown body.

        - Supports **MCQ** (OptionA-D) and **open-response** questions
        - Metadata fields: class (VIII-XII), topic, difficulty, previous year, answer, and optional JSON extras
        - Organizes files under `questions_output/Class-<X>/<Topic>/`
        - Shows saved file contents on success

        ### 2. 📦 Question Compilation
        Select and export questions to a LaTeX/PDF worksheet.

        - Recursively loads all `.md` files from a chosen root folder
        - Sidebar filtering by **class**, **topic**, and **difficulty**
        - Select individual questions for export
        - Rendered using `data/latex/latex_template.tex`
        - Optional **answer key** generation
        - Optional `last_used` metadata update on export
        - Compile `.tex` → `.pdf` via `pdflatex`
        - Download `.tex` and `.pdf` directly from the browser

        ### 3. ✏️ Question Editor
        Edit an existing question file in place.

        - Load any `.md` question file by path
        - Edit metadata, question text, options, and solution
        - Save back to the same file or a new path
        - Download edited content if direct write is unavailable

        ---

        ## Question File Format

        Questions are plain markdown files with a YAML front-matter header:

        ```markdown
        ---
        topic: Algebra
        class: XI
        difficulty: Easy
        answer: B
        prev_year: 2024
        last_used:
        ---

        What is the derivative of \\(x^2\\)?

        OptionA: \\(x\\)
        OptionB: \\(2x\\)
        OptionC: \\(x^3\\)
        OptionD: 2

        ## Solution

        Differentiate: \\(f'(x)=2x\\).
        ```

        - `OptionA`-`OptionD` present → treated as MCQ; otherwise open-response.
        - LaTeX math uses `\\(...\\)` (inline) and `\\[...\\]` (block).

        ---

        ## Default Paths

        | Path | Purpose |
        |---|---|
        | `questions_output/` | Question file storage |
        | `output/` | Generated `.tex` / `.pdf` files |
        | `data/latex/latex_template.tex` | LaTeX export template |

        ---

        ## Workflow

        1. **Create** or **edit** question files via the creation/editor pages.
        2. Open the **Compilation** page, filter, and select questions.
        3. Export to `.tex`, optionally compile to `.pdf`.
        4. Download artifacts directly from the browser.
        """
    )


if __name__ == "__main__":
    main()
