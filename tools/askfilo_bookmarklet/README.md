# AskFilo Question Extractor Bookmarklet

A browser bookmarklet to extract question metadata, problem statement, and solution from [askfilo.com](https://askfilo.com) directly into the `qnbk` markdown format.

No external servers, extensions, or AI APIs are needed—it runs client-side in the browser using the page's structured data (JSON-LD) and DOM elements.

---

## 🚀 Quick Setup & Installation

### Option 1: Drag and Drop (Recommended)
1. Open [`install.html`](./install.html) in your browser (Chrome, Edge, Firefox, Brave, Safari, etc.).
2. Ensure your bookmarks bar is visible:
   - **Chrome / Edge / Brave**: `Ctrl + Shift + B` (Windows/Linux) or `Cmd + Shift + B` (macOS)
   - **Firefox**: `Ctrl + B`
3. Drag the purple **📋 qnbk Extract** button up to your bookmarks bar.

### Option 2: Manual Bookmark Creation
1. Open your browser's Bookmark Manager (`Ctrl + Shift + O` or via settings).
2. Create a new bookmark:
   - **Name**: `📋 qnbk Extract`
   - **URL / Location**: Copy and paste the entire contents of [`bookmarklet.txt`](./bookmarklet.txt) (starts with `javascript:...`).
3. Save the bookmark.

---

## 📖 How to Use

1. Navigate to any question page on **askfilo.com** in your browser.
2. Click the **📋 qnbk Extract** bookmark in your bookmarks bar.
3. A popup window will open displaying the pre-filled Markdown stub.
4. Proofread and complete the remaining fields:
   - Add/verify `answer:` (e.g. `A`, `B`, `C`, or `D`)
   - Fill in option details (`OptionA` - `OptionD`), converting any chemical structures to LaTeX/`\chemfig` or text if needed.
5. Click **Copy to Clipboard**.
6. Paste the markdown into your question bank under `questions_output/Class-<Level>/<Topic>/q_XXXXX.md`.

---

## 🔍 What Gets Extracted Automatically

| Field | Source | Example Output |
| :--- | :--- | :--- |
| **`topic`** | Page breadcrumbs trail | `Permutations and Combinations` |
| **`class`** | JSON-LD `educationalLevel` | `XI` |
| **`difficulty`** | DOM difficulty badge | `Easy` |
| **`prev_year`** | DOM exam metadata | `NEET 2020` |
| **`source`** | Page URL (`window.location.href`) | `https://askfilo.com/...` |
| **`question text`**| JSON-LD `mainEntity.name` / `.text` | LaTeX / text formatted equation |
| **`solution`** | JSON-LD `acceptedAnswer.text` | Step-by-step solution text |
| **`OptionA` - `OptionD`** | Stubs (`# TODO`) | Left for manual entry |

---

## 🛠️ Maintenance & Development

All source files are located in `tools/askfilo_bookmarklet/`:

* [`bookmarklet_source.js`](./bookmarklet_source.js): Human-readable JavaScript source code.
* [`gen_bookmarklet.py`](./gen_bookmarklet.py): Python utility that minifies and URL-encodes `bookmarklet_source.js` into `bookmarklet.txt`.
* [`gen_installer.py`](./gen_installer.py): Generates [`install.html`](./install.html) embedding the minified bookmarklet for easy drag-and-drop.

### Updating the Extractor Logic

If you want to modify the extraction rules or markdown template:

1. Edit [`bookmarklet_source.js`](./bookmarklet_source.js).
2. Re-generate the bookmarklet and installer:
   ```bash
   cd tools/askfilo_bookmarklet
   python3 gen_bookmarklet.py
   python3 gen_installer.py
   ```
3. Re-drag the updated bookmark button from `install.html` to your browser.
