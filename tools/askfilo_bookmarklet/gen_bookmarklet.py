#!/usr/bin/env python3
"""Generate bookmarklet.txt from bookmarklet_source.js"""
import urllib.parse, re, os

here = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(here, 'bookmarklet_source.js'), encoding='utf-8') as f:
    full = f.read()

# Strip the comment header — everything from the first (function till the last })();
m = re.search(r'(\(function\s*\(\s*\).*?\}\s*\)\s*\(\s*\)\s*;)', full, re.DOTALL)
if not m:
    raise ValueError("Could not find IIFE in source file")

js = m.group(1)

# Minify: strip line comments, collapse whitespace
js = re.sub(r'//[^\n]*', '', js)          # remove // comments
js = re.sub(r'\n\s*', ' ', js)            # collapse newlines
js = re.sub(r'\s{2,}', ' ', js)           # collapse multiple spaces
js = js.strip()

bookmarklet = 'javascript:' + urllib.parse.quote(js)

out_path = os.path.join(here, 'bookmarklet.txt')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(bookmarklet)

print(f'Written to: {out_path}')
print(f'Total length: {len(bookmarklet)} chars')
