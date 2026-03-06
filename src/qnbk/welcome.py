import streamlit as st


def main():
    """Introduction to the app."""
    st.write("# Welcome to Streamlit! 👋")

    st.markdown(
        """
        A Streamlit-based question bank management system for creating, organizing, and compiling questions
        into LaTeX/PDF worksheets.
        This application provides a complete workflow for managing educational questions:
        - **Create Questions**: Add new questions with metadata using an intuitive web interface
        - **Browse & Filter**: Search and filter questions by topic, difficulty, and other criteria
        - **Export to LaTeX/PDF**: Compile selected questions into professional worksheets with optional answer keys

        ## Features

        ### 1. Question Creation/Update
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

        ### 2. Question Compilation
        - Browse all questions in the database
        - Advanced filtering by topic and difficulty
        - Individual question selection
        - LaTeX template-based rendering
        - Intelligent option layout (horizontal for short options, vertical for complex ones)
        - Optional solution inclusion
        - Answer key generation
        - Direct PDF compilation via pdflatex
        - Download buttons for both .tex and .pdf files
        """
    )


if __name__ == "__main__":
    main()
