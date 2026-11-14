#!/bin/bash

# Navigate to the project directory
cd /home/ranga/qnbk || exit 1

echo "Starting Question Bank app..."

# Run poetry via login/interactive environment or standard path
if command -v poetry &>/dev/null; then
    poetry run streamlit run src/qnbk/Welcome.py
elif [ -f "$HOME/.local/bin/poetry" ]; then
    "$HOME/.local/bin/poetry" run streamlit run src/qnbk/Welcome.py
elif [ -f "/usr/local/bin/poetry" ]; then
    "/usr/local/bin/poetry" run streamlit run src/qnbk/Welcome.py
elif [ -f "/usr/bin/poetry" ]; then
    /usr/bin/poetry run streamlit run src/qnbk/Welcome.py
else
    echo "Error: 'poetry' command not found in PATH or standard locations."
    echo "Checking ~/.local/bin..."
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "Error: Application failed to start."
    read -p "Press Enter to close..."
fi
