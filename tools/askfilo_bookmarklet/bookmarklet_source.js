/**
 * qnbk Question Extractor Bookmarklet — Source (Readable)
 *
 * This is the human-readable source. To use it, copy the single-line
 * version from bookmarklet.txt and save it as a browser bookmark.
 *
 * HOW IT WORKS:
 *   1. Parses JSON-LD structured data already embedded in the askfilo page
 *   2. Reads the breadcrumb trail from the DOM for topic/class
 *   3. Reads difficulty and exam metadata from the DOM
 *   4. Builds a .md stub in your qnbk format
 *   5. Opens a popup window with the stub in a copyable textarea
 *
 * WHAT IT EXTRACTS (without AI):
 *   - topic      : from breadcrumb (e.g. "Permutations and Combinations")
 *   - class      : from JSON-LD educationalLevel (e.g. "XI")
 *   - difficulty : from DOM CSS class (Easy / Medium / Hard)
 *   - prev_year  : from DOM exam info element (e.g. "NEET 2020")
 *   - source     : current page URL
 *   - question   : from JSON-LD mainEntity.name
 *   - solution   : from JSON-LD mainEntity.acceptedAnswer.text
 *
 * WHAT YOU FILL IN MANUALLY:
 *   - answer     : correct option letter
 *   - last_used  : when you use the question in a test
 *   - OptionA-D  : text/LaTeX for each option (image-based options skipped)
 */

(function () {
  // ── 1. Parse all JSON-LD blocks on the page ──────────────────────────────
  var qaData = {};
  var breadcrumbData = [];

  document.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
    try {
      var d = JSON.parse(s.textContent);
      if (d["@type"] === "QAPage") {
        qaData = d;
      }
      if (d["@type"] === "BreadcrumbList") {
        breadcrumbData = d.itemListElement || [];
      }
    } catch (e) { /* skip malformed blocks */ }
  });

  // ── 2. Extract structured fields ─────────────────────────────────────────
  var entity = qaData.mainEntity || {};
  var answer = entity.acceptedAnswer || {};

  // Question text: prefer .name (usually cleaner title), fall back to .text
  var questionText = (entity.name || entity.text || "TODO: paste question here").trim();

  // Solution text
  var solutionText = (answer.text || "").trim();

  // Class: from JSON-LD educationalLevel e.g. "Class 11" -> "XI"
  var levelStr = entity.educationalLevel || "";
  var classMap = { "Class 9": "IX", "Class 10": "X", "Class 11": "XI", "Class 12": "XII" };
  var classRoman = classMap[levelStr] || levelStr.replace("Class ", "").trim();

  // Topic: second-to-last breadcrumb item (last item is the question title itself)
  var breadcrumbNames = breadcrumbData.map(function (i) { return i.name || ""; });
  var topic = breadcrumbNames.length >= 2
    ? breadcrumbNames[breadcrumbNames.length - 2]
    : (breadcrumbNames[0] || "TODO");

  // ── 3. Extract from DOM ──────────────────────────────────────────────────

  // Difficulty: element whose class contains "difficulty"
  var difficulty = "Unknown";
  var diffEl = document.querySelector('[class*="question-difficulty"]');
  if (diffEl) {
    difficulty = diffEl.textContent.trim();
  }

  // Exam / prev_year: element whose class contains "question-info-text"
  var prevYear = "None";
  var examEl = document.querySelector('[class*="question-info-text"]');
  if (examEl) {
    prevYear = examEl.textContent.trim();
  }

  // Source URL
  var sourceUrl = window.location.href;

  // ── 4. Build the markdown stub ───────────────────────────────────────────
  var md = [
    "---",
    "topic: " + topic,
    "class: " + classRoman,
    "difficulty: " + difficulty,
    "answer:",
    "prev_year: " + prevYear,
    "source: " + sourceUrl,
    "last_used:",
    "---",
    "",
    questionText,
    "",
    "OptionA: # TODO",
    "OptionB: # TODO",
    "OptionC: # TODO",
    "OptionD: # TODO",
    "",
    "",
    "## Solution",
    "",
    solutionText || "# TODO",
  ].join("\n");

  // ── 5. Open popup window ─────────────────────────────────────────────────
  var popup = window.open("", "_blank", "width=720,height=560,menubar=no,toolbar=no,location=no,status=no");
  if (!popup) {
    alert("Popup blocked! Please allow popups for this site and try again.");
    return;
  }

  var css = [
    "body{margin:0;padding:16px;background:#1e1e2e;color:#cdd6f4;font-family:sans-serif;box-sizing:border-box}",
    "h3{margin:0 0 4px;color:#89b4fa;font-size:15px}",
    "p.sub{margin:0 0 10px;color:#6c7086;font-size:12px}",
    "textarea{display:block;width:100%;height:410px;background:#11111b;color:#cdd6f4;",
    "border:1px solid #45475a;border-radius:6px;padding:12px;font-family:monospace;",
    "font-size:12.5px;line-height:1.5;resize:none;box-sizing:border-box;outline:none}",
    "textarea:focus{border-color:#89b4fa}",
    ".row{display:flex;gap:10px;margin-top:10px;align-items:center}",
    "button{padding:7px 18px;background:#89b4fa;color:#1e1e2e;border:none;border-radius:6px;cursor:pointer;font-weight:700;font-size:13px}",
    "button:hover{background:#b4befe}",
    "#st{font-size:12px;color:#a6e3a1}",
  ].join("");

  var html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    + '<title>qnbk Stub</title><style>' + css + '</style></head><body>'
    + '<h3>&#128203; qnbk Question Stub</h3>'
    + '<p class="sub">Edit below, then copy to clipboard. Paste into your questions_output file.</p>'
    + '<textarea id="md" spellcheck="false"></textarea>'
    + '<div class="row">'
    + '<button onclick="'
    +   "navigator.clipboard.writeText(document.getElementById('md').value)"
    +   ".then(function(){var s=document.getElementById('st');"
    +   "s.textContent='\\u2713 Copied!';"
    +   "setTimeout(function(){s.textContent=''},2500)})"
    + '">Copy to Clipboard</button>'
    + '<span id="st"></span>'
    + '</div>'
    + '</body></html>';

  popup.document.write(html);
  popup.document.close();

  // Set value via JS so that LaTeX characters like \ $ { } are not HTML-escaped
  popup.document.getElementById("md").value = md;

})();
