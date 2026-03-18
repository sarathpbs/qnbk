from pathlib import Path

# Shared defaults used by Streamlit pages so create/compile/edit all point to the same bank.
DEFAULT_QUESTIONS_DIR = Path("questions_output")
DEFAULT_LATEX_EXPORT_DIR = Path("output")
DEFAULT_TEMPLATE_DIR = Path("data/latex")
DEFAULT_TEMPLATE_NAME = "latex_template.tex"

__all__ = [
    "DEFAULT_LATEX_EXPORT_DIR",
    "DEFAULT_QUESTIONS_DIR",
    "DEFAULT_TEMPLATE_DIR",
    "DEFAULT_TEMPLATE_NAME",
]
