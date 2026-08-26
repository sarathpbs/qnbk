#!/bin/bash

# Navigate to the directory where this script is located
cd "$(dirname "$0")"

# Run the Streamlit app using Poetry
echo "Starting Question Bank app..."
/usr/bin/poetry run streamlit run src/qnbk/Welcome.py

# If it fails, keep the terminal open so the user can see the error
if [ $? -ne 0 ]; then
    echo "Error: Application failed to start."
    read -p "Press Enter to close..."
fi
