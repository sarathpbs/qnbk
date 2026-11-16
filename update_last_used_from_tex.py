#!/usr/bin/env python3
"""
update_last_used_from_tex.py

Extracts question markdown paths from a compiled LaTeX (.tex) file
and updates their 'last_used' frontmatter field to a specified date.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_tex_for_sources(tex_file: Path) -> list[str]:
    """Find all '% SOURCE: ...' lines in the LaTeX file."""
    content = tex_file.read_text(encoding="utf-8")
    # Matches: '% SOURCE: path/q.md' and '% % SOURCE: path/q.md'
    pattern = re.compile(r"^\s*%(?:\s*%)?\s*SOURCE:\s*([^\r\n]+)", re.MULTILINE)
    matches = pattern.findall(content)

    # Deduplicate while preserving order
    seen = set()
    sources = []
    for m in matches:
        clean = m.strip().replace("\\", "/")
        if clean and clean not in seen:
            seen.add(clean)
            sources.append(clean)
    return sources


def resolve_question_path(rel_path_str: str, base_dirs: list[Path]) -> Path | None:
    """Find the markdown file under provided search directories."""
    p = Path(rel_path_str)
    if p.is_absolute() and p.exists():
        return p

    for base in base_dirs:
        candidate = base / p
        if candidate.exists():
            return candidate

        # Fallback: search by filename if directory moved
        matches = list(base.rglob(p.name))
        if matches:
            return matches[0]

    return None


def update_frontmatter_last_used(md_path: Path, new_date: str, dry_run: bool = False) -> tuple[bool, str]:
    """
    Updates or inserts 'last_used: <new_date>' in the YAML frontmatter.
    Returns (success, old_value).
    """
    text = md_path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"

    # Match YAML frontmatter between starting and ending '---'
    fm_match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", text, re.DOTALL)
    if not fm_match:
        return False, "No YAML frontmatter found"

    fm_text = fm_match.group(1)

    # Check if last_used already exists
    last_used_match = re.search(r"^(\s*last_used\s*:\s*)(.*)$", fm_text, re.MULTILINE)
    if last_used_match:
        old_val = last_used_match.group(2).strip() or "<empty>"
        new_fm = re.sub(
            r"^(\s*last_used\s*:\s*).*$",
            rf"\g<1>{new_date}",
            fm_text,
            flags=re.MULTILINE,
        )
    else:
        old_val = "<not set>"
        new_fm = fm_text.rstrip() + f"{newline}last_used: {new_date}{newline}"

    if not dry_run:
        new_content = text[: fm_match.start(1)] + new_fm.strip() + text[fm_match.end(1) :]
        md_path.write_text(new_content, encoding="utf-8")

    return True, old_val


def main():
    parser = argparse.ArgumentParser(
        description="Batch update question 'last_used' dates based on a compiled .tex worksheet."
    )
    parser.add_argument(
        "tex_files",
        nargs="+",
        type=Path,
        help="Path to one or more .tex files (e.g. 11_maths_level1.tex)",
    )
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Target date in YYYY-MM-DD format (default: today's date).",
    )
    parser.add_argument(
        "--questions-dir",
        "-q",
        type=Path,
        default=None,
        help="Path to questions directory (default: checks 'questions_output' or current dir).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the update without modifying files.",
    )

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.")

    # Search paths for questions
    base_dirs = []
    if args.questions_dir:
        base_dirs.append(args.questions_dir)
    # Common default locations
    base_dirs.extend([
        Path("questions_output"),
        Path("../questions_output"),
        Path.cwd(),
    ])

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Target Date: {args.date}")
    print(f"Search Dirs: {[str(d) for d in base_dirs if d.exists()]}\n")

    total_updated = 0
    total_missing = 0

    for tex_path in args.tex_files:
        if not tex_path.exists():
            print(f"File not found: {tex_path}")
            continue

        print(f"--- Processing: {tex_path.name} ---")
        sources = parse_tex_for_sources(tex_path)
        print(f"Found {len(sources)} question sources in {tex_path.name}.")

        for rel_path in sources:
            md_path = resolve_question_path(rel_path, base_dirs)
            if not md_path:
                print(f"  [MISSING] Could not find: {rel_path}")
                total_missing += 1
                continue

            success, old_val = update_frontmatter_last_used(md_path, args.date, dry_run=args.dry_run)
            if success:
                action_tag = "[WOULD UPDATE]" if args.dry_run else "[UPDATED]"
                print(f"  {action_tag} {rel_path} ({old_val} -> {args.date})")
                total_updated += 1
            else:
                print(f"  [SKIPPED] {rel_path}: {old_val}")

    print("\nSummary:")
    print(f"  Total processed/updated: {total_updated}")
    if total_missing:
        print(f"  Missing files: {total_missing}")


if __name__ == "__main__":
    main()

