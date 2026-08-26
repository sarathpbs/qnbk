#!/usr/bin/env python3
"""Generate install.html for the qnbk bookmarklet."""
import os

here = os.path.dirname(os.path.abspath(__file__))
bm_path = os.path.join(here, 'bookmarklet.txt')

with open(bm_path, encoding='utf-8') as f:
    bm = f.read().strip()

html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>qnbk Bookmarklet Installer</title>
<style>
  :root {
    --bg: #1e1e2e; --surface: #181825; --overlay: #313244;
    --text: #cdd6f4; --sub: #6c7086; --blue: #89b4fa;
    --green: #a6e3a1; --mauve: #cba6f7;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    min-height: 100vh; display: flex; align-items: center;
    justify-content: center; padding: 24px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--overlay);
    border-radius: 12px; max-width: 620px; width: 100%; padding: 32px;
  }
  h1 { font-size: 20px; color: var(--blue); margin-bottom: 6px; }
  .sub { font-size: 13px; color: var(--sub); margin-bottom: 28px; }
  .step { display: flex; gap: 14px; margin-bottom: 22px; align-items: flex-start; }
  .num {
    background: var(--overlay); color: var(--blue); font-weight: 700;
    font-size: 13px; border-radius: 50%; width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 2px;
  }
  .step-body { flex: 1; }
  .step-body h3 { font-size: 14px; margin-bottom: 4px; }
  .step-body p { font-size: 13px; color: var(--sub); line-height: 1.6; }
  .drag-area { display: flex; align-items: center; justify-content: center; margin: 10px 0 0; }
  a.bookmark {
    display: inline-block; padding: 10px 22px; background: var(--mauve);
    color: #1e1e2e; border-radius: 8px; font-weight: 700; font-size: 14px;
    text-decoration: none; cursor: grab;
    box-shadow: 0 2px 12px rgba(203,166,247,0.3);
    transition: box-shadow 0.2s, transform 0.2s; user-select: none;
  }
  a.bookmark:hover { box-shadow: 0 4px 20px rgba(203,166,247,0.5); transform: translateY(-1px); }
  .hint { font-size: 11px; color: var(--sub); margin-top: 6px; text-align: center; }
  .divider { border: none; border-top: 1px solid var(--overlay); margin: 20px 0; }
  .what { background: var(--overlay); border-radius: 8px; padding: 14px 16px; }
  .what h3 { font-size: 13px; color: var(--blue); margin-bottom: 8px; }
  .what ul { padding-left: 18px; font-size: 12.5px; color: var(--sub); line-height: 2; }
  .what li span { color: var(--text); }
  .tag {
    display: inline-block; background: #2a2a3d; color: var(--green);
    font-family: monospace; font-size: 11px; padding: 1px 6px; border-radius: 4px;
  }
  .note { margin-top: 10px; font-size: 12px; color: var(--sub); }
  code { color: var(--green); font-family: monospace; }
</style>
</head>
<body>
<div class="card">
  <h1>&#128203; qnbk Bookmarklet</h1>
  <p class="sub">Extract question stubs from askfilo.com into your markdown question bank format &mdash; no AI, no server</p>

  <div class="step">
    <div class="num">1</div>
    <div class="step-body">
      <h3>Show your browser bookmarks bar</h3>
      <p>Press <strong>Ctrl+Shift+B</strong> (Chrome/Edge) or <strong>Ctrl+B</strong> (Firefox) to show the bookmarks bar if it is hidden.</p>
    </div>
  </div>

  <div class="step">
    <div class="num">2</div>
    <div class="step-body">
      <h3>Drag the button below to your bookmarks bar</h3>
      <div class="drag-area">
        <a class="bookmark" href="BOOKMARKLET_HREF">&#128203; qnbk Extract</a>
      </div>
      <p class="hint">Drag the purple button to your browser bookmarks bar, then release.</p>
    </div>
  </div>

  <div class="step">
    <div class="num">3</div>
    <div class="step-body">
      <h3>Use it on any askfilo question page</h3>
      <p>Navigate to an askfilo question, click the bookmark. A popup appears with the markdown stub &mdash; edit it, then copy and paste into your <code>questions_output/</code> file.</p>
    </div>
  </div>

  <hr class="divider">

  <div class="what">
    <h3>What gets extracted automatically (no AI)</h3>
    <ul>
      <li><span class="tag">topic</span> &nbsp;<span>from breadcrumb trail (e.g. "Combinations")</span></li>
      <li><span class="tag">class</span> &nbsp;<span>from JSON-LD structured data (e.g. "XI")</span></li>
      <li><span class="tag">difficulty</span> &nbsp;<span>from page DOM (Easy / Medium / Hard)</span></li>
      <li><span class="tag">prev_year</span> &nbsp;<span>from page DOM (e.g. "NEET 2020")</span></li>
      <li><span class="tag">source</span> &nbsp;<span>current page URL</span></li>
      <li><span class="tag">question text</span> &nbsp;<span>from JSON-LD (text-based questions)</span></li>
      <li><span class="tag">solution</span> &nbsp;<span>from JSON-LD acceptedAnswer.text</span></li>
    </ul>
    <p class="note">&#9888; Options are left as <code># TODO</code> stubs &mdash; fill them in manually from the source page.</p>
  </div>
</div>
</body>
</html>
"""

html = html.replace('BOOKMARKLET_HREF', bm)

out_path = os.path.join(here, 'install.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Written: {out_path}')
