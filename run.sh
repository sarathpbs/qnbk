#!/bin/bash

# Navigate to the directory where this script is located
cd "$(dirname "$0")"

# Ensure local bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run the Streamlit app using Poetry
echo "Starting Question Bank app..."
if command -v poetry >/dev/null 2>&1; then
    poetry run streamlit run src/qnbk/Welcome.py
elif [ -x "$HOME/.local/bin/poetry" ]; then
    "$HOME/.local/bin/poetry" run streamlit run src/qnbk/Welcome.py
elif [ -x "/usr/bin/poetry" ]; then
    /usr/bin/poetry run streamlit run src/qnbk/Welcome.py
else
    echo "Error: Poetry is not installed or not found in PATH or ~/.local/bin."
    exit 1
fi

# If it fails, keep the terminal open so the user can see the error
if [ $? -ne 0 ]; then
    echo "Error: Application failed to start."
    read -p "Press Enter to close..."
fi
