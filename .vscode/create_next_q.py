import os
import sys
import glob
import re
import subprocess
from pathlib import Path


def resolve_active_path(active_file, workspace_root=None):
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


def resolve_target_directory(target, workspace_root=None):
    if not target:
        return Path(workspace_root or Path.cwd())

    resolved = resolve_active_path(target, workspace_root)
    if resolved.exists() and resolved.is_dir():
        return resolved

    if resolved.exists() and resolved.is_file():
        return resolved.parent

    candidate = resolved
    if not str(candidate).startswith('/'):
        candidate = Path(workspace_root or Path.cwd()) / candidate
    if candidate.exists() and candidate.is_dir():
        return candidate
    if candidate.parent.exists():
        return candidate.parent
    return Path(workspace_root or Path.cwd())


def get_active_directory(active_file, workspace_root=None):
    return resolve_target_directory(active_file, workspace_root)


def extract_frontmatter_fields(filepath):
    fields = {
        "topic": "Uncategorized",
        "class": "Unknown",
        "difficulty": "Unknown",
        "source": ""
    }
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_frontmatter = False
        for line in lines:
            line = line.strip()
            if line == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break # end of frontmatter
            if in_frontmatter:
                for key in fields.keys():
                    if line.startswith(f"{key}:"):
                        # Extract everything after the colon and strip whitespace
                        fields[key] = line[len(key)+1:].strip()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return fields

def get_next_filename(directory):
    files = glob.glob(os.path.join(directory, "q_*.md"))
    max_num = 0
    pattern = re.compile(r"q_(\d+)\.md$")
    for f in files:
        basename = os.path.basename(f)
        match = pattern.match(basename)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    next_num = max_num + 1
    return os.path.join(directory, f"q_{next_num:05d}.md")

def create_template(fields):
    return f"""---
topic: {fields['topic']}
class: {fields['class']}
difficulty: {fields['difficulty']}
answer: 
prev_year: 
source: {fields['source']}
last_used: 
---

Write your question here...

OptionA: 
OptionB: 
OptionC: 
OptionD: 

## Solution

Write your solution here...
"""

def main():
    if len(sys.argv) < 2:
        print("Error: No active file provided.")
        sys.exit(1)

    active_file = sys.argv[1].strip("'\"").replace('\\', '/')

    repo_root = Path(__file__).resolve().parents[1]
    if active_file.endswith('.md'):
        active_path = resolve_active_path(active_file, repo_root)
        if str(active_path).startswith('/wsl.localhost') or 'wsl.localhost' in str(active_path):
            directory = repo_root / 'questions_output' / 'Class-XII' / 'Haloalkanes'
            active_path = directory / 'q_00001.md'
        else:
            directory = get_active_directory(active_file, repo_root)
            if not active_path.exists():
                if not str(active_path).startswith('/'):
                    active_path = repo_root / active_path
                active_path.parent.mkdir(parents=True, exist_ok=True)
                active_path.touch(exist_ok=True)
    else:
        directory = resolve_target_directory(active_file, repo_root)
        active_path = directory / "q_00001.md"

    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)

    if active_file.endswith('.md'):
        fields = extract_frontmatter_fields(str(active_path))
    else:
        fields = {
            "topic": "Uncategorized",
            "class": "Unknown",
            "difficulty": "Unknown",
            "source": "",
        }
    new_filepath = get_next_filename(str(directory))

    new_path = Path(new_filepath)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(create_template(fields))

    print(f"Created {new_path}")

    # Open the newly created file in the Windows VSCode instance
    try:
        # Convert the Linux filepath to Windows format
        res = subprocess.run(["wslpath", "-w", str(new_path)], capture_output=True, text=True, check=True)
        windows_path = res.stdout.strip()

        # Run the Windows code.exe CLI via cmd.exe, setting the CWD to C:\ to prevent UNC warnings
        subprocess.run(["cmd.exe", "/c", "code", "-r", windows_path], cwd="/mnt/c", check=True)
    except Exception as e:
        print(f"Error opening file in VSCode: {e}")

if __name__ == "__main__":
    main()
