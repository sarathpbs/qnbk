/**
 * qnbk Question Extractor Bookmarklet — Source (Readable)
 *
 * HOW IT WORKS:
 *   1. Extracts data primarily from AskFilo's Next.js data (__NEXT_DATA__)
 *      for high-fidelity question text, options (OptionA-D), answer key,
 *      difficulty, class, topic, exam/prev_year, and solutions.
 *   2. Converts KaTeX rendered HTML spans and HTML math into clean regular
 *      characters (e.g. XeF2, H3O+, XeF4, XeF6).
 *   3. Falls back gracefully to JSON-LD (QAPage, Breadcrumbs) and DOM scraping
 *      if __NEXT_DATA__ is unavailable.
 *   4. Populates text & KaTeX options directly, or marks image options as # TODO (Image option).
 *   5. Builds a .md stub in qnbk format and opens a popup window.
 */

(function () {
  var classMap = {
    "Class 9": "IX", "class-9": "IX", "9": "IX",
    "Class 10": "X", "class-10": "X", "10": "X",
    "Class 11": "XI", "class-11": "XI", "11": "XI",
    "Class 12": "XII", "class-12": "XII", "12": "XII"
  };

  var optionLetters = ["A", "B", "C", "D"];

  // ── Helper: Convert KaTeX / HTML nodes to plain characters ──────────────
  function convertKatexNode(node) {
    if (node.nodeType === 3) {
      return node.nodeValue.replace(/[\u200B-\u200D\uFEFF]/g, "");
    }
    if (node.nodeType !== 1) return "";

    var cls = node.className || "";
    if (typeof cls !== "string") cls = "";

    // Ignore spacing struts and zero-width spacers
    if (cls.includes("strut") || cls.includes("pstrut") || cls.includes("vlist-s")) {
      return "";
    }

    // Handle msupsub (subscripts and superscripts -> plain characters)
    if (cls.includes("msupsub")) {
      var vlistSpans = node.querySelectorAll(".vlist-r > .vlist > span");
      if (vlistSpans.length === 2) {
        var supText = convertChildren(vlistSpans[0]);
        var subText = convertChildren(vlistSpans[1]);
        return subText + supText;
      } else if (vlistSpans.length === 1) {
        return convertChildren(vlistSpans[0]);
      }
    }

    // Handle mfrac (fractions)
    if (cls.includes("mfrac")) {
      var fracSpans = node.querySelectorAll(".vlist-r > .vlist > span");
      if (fracSpans.length >= 2) {
        var num = convertChildren(fracSpans[0]);
        var den = convertChildren(fracSpans[fracSpans.length - 1]);
        return num + "/" + den;
      }
    }

    // Handle msqrt (roots)
    if (cls.includes("msqrt")) {
      var rootBody = node.querySelector(".mord, .base, .vlist") || node;
      var rootText = convertChildren(rootBody);
      return "√(" + rootText + ")";
    }

    // Handle generic children
    var out = "";
    for (var i = 0; i < node.childNodes.length; i++) {
      out += convertKatexNode(node.childNodes[i]);
    }

    if (cls.includes("mbin") || cls.includes("mord") || cls.includes("mrel")) {
      out = out.replace(/\u2212/g, "-");
    }

    return out;
  }

  function convertChildren(node) {
    var out = "";
    for (var i = 0; i < node.childNodes.length; i++) {
      out += convertKatexNode(node.childNodes[i]);
    }
    return out.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
  }

  function cleanHtmlLatex(htmlStr) {
    if (!htmlStr || typeof htmlStr !== "string") return "";
    if (!htmlStr.includes("<") && !htmlStr.includes(">")) {
      return htmlStr.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    }

    var div = document.createElement("div");
    div.innerHTML = htmlStr;

    // Check for images without text
    var imgs = div.querySelectorAll("img");
    if (imgs.length > 0 && div.textContent.trim().length === 0) {
      return "# TODO (Image option)";
    }

    // Process KaTeX containers
    var katexEls = div.querySelectorAll(".katex");
    katexEls.forEach(function (kEl) {
      var plain = convertChildren(kEl);
      var textNode = document.createTextNode(plain);
      if (kEl.parentNode) {
        kEl.parentNode.replaceChild(textNode, kEl);
      }
    });

    // Process HTML sub / sup -> plain characters
    div.querySelectorAll("sub, sup").forEach(function (el) {
      var tn = document.createTextNode(el.textContent.trim());
      if (el.parentNode) el.parentNode.replaceChild(tn, el);
    });

    // Replace line breaks
    div.querySelectorAll("br").forEach(function (br) {
      if (br.parentNode) br.parentNode.replaceChild(document.createTextNode("\n"), br);
    });

    var result = div.textContent || "";
    result = result.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    return result;
  }

  // ── 1. Try extracting from __NEXT_DATA__ ──────────────────────────────────
  var qdd = null;
  try {
    var nextEl = document.getElementById("__NEXT_DATA__");
    if (nextEl && nextEl.textContent) {
      var nextObj = JSON.parse(nextEl.textContent);
      var pp = (nextObj && nextObj.props && nextObj.props.pageProps) ? nextObj.props.pageProps : {};
      qdd = pp.questionDetailData || pp.data || null;
    }
  } catch (e) { /* ignore JSON parse error */ }

  // ── 2. Parse JSON-LD structured data (fallback) ──────────────────────────
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
  var entity = qaData.mainEntity || {};
  var acceptedAnswer = entity.acceptedAnswer || {};

  // ── 3. Extract Fields ────────────────────────────────────────────────────

  // --- Topic ---
  var topic = "";
  if (qdd && qdd.topic) {
    topic = typeof qdd.topic === "object" ? (qdd.topic.name || "") : String(qdd.topic);
  }
  if (!topic && breadcrumbData.length > 0) {
    var bNames = breadcrumbData.map(function (i) { return i.name || ""; });
    topic = bNames.length >= 2 ? bNames[bNames.length - 2] : (bNames[0] || "");
  }
  if (!topic || topic === "TODO") topic = "TODO";

  // --- Class ---
  var classRoman = "";
  if (qdd && qdd.class) {
    var cName = typeof qdd.class === "object" ? (qdd.class.name || qdd.class.slug || "") : String(qdd.class);
    classRoman = classMap[cName] || cName.replace(/Class\s*/i, "").trim();
  }
  if (!classRoman) {
    var levelStr = entity.educationalLevel || "";
    classRoman = classMap[levelStr] || levelStr.replace(/Class\s*/i, "").trim();
  }
  if (!classRoman) classRoman = "XI";

  // --- Difficulty ---
  var difficulty = "";
  if (qdd && qdd.difficulty) {
    var diffRaw = String(qdd.difficulty).trim();
    difficulty = diffRaw.charAt(0).toUpperCase() + diffRaw.slice(1).toLowerCase();
  }
  if (!difficulty) {
    var diffEl = document.querySelector('[class*="question-difficulty"]');
    if (diffEl) {
      difficulty = diffEl.textContent.trim();
    }
  }
  if (!difficulty) difficulty = "Unknown";

  // --- Previous Year / Exam ---
  var prevYear = "";
  if (qdd && Array.isArray(qdd.exams) && qdd.exams.length > 0) {
    var ex = qdd.exams[0];
    prevYear = ex.examPaperName || ((ex.name ? ex.name + " " : "") + (ex.year || "")).trim() || ex.slug || "";
  }
  if (!prevYear) {
    var examEl = document.querySelector('[class*="question-info-text"]');
    if (examEl) {
      prevYear = examEl.textContent.trim();
    }
  }
  if (!prevYear) prevYear = "";

  // --- Source URL ---
  var sourceUrl = window.location.href;

  // --- Question Text ---
  var questionText = "";
  if (qdd) {
    questionText = (qdd.questionLatexOriginal || qdd.questionLatex || qdd.question || "").trim();
  }
  if (!questionText) {
    questionText = (entity.name || entity.text || "").trim();
  }
  if (!questionText) {
    var qEl = document.querySelector('[class*="question-title"], [class*="Question_question"]');
    if (qEl) questionText = qEl.innerHTML || qEl.textContent.trim();
  }
  questionText = cleanHtmlLatex(questionText) || "TODO: paste question here";

  // --- Options ---
  var extractedOptions = ["", "", "", ""];
  if (qdd && Array.isArray(qdd.optionsLatex) && qdd.optionsLatex.length > 0) {
    for (var i = 0; i < 4; i++) {
      if (i < qdd.optionsLatex.length && qdd.optionsLatex[i]) {
        extractedOptions[i] = cleanHtmlLatex(qdd.optionsLatex[i]);
      }
    }
  } else if (qdd && Array.isArray(qdd.options) && qdd.options.length > 0) {
    for (var i = 0; i < 4; i++) {
      if (i < qdd.options.length && qdd.options[i]) {
        var optVal = qdd.options[i];
        extractedOptions[i] = cleanHtmlLatex(typeof optVal === "string" ? optVal : (optVal.text || ""));
      }
    }
  } else {
    // DOM extraction fallback
    var optEls = document.querySelectorAll('[class*="option-item__"], [class*="option-item"]');
    var filtered = [];
    optEls.forEach(function (el) {
      if (!el.className.includes("holder") && !el.className.includes("badge")) {
        filtered.push(el);
      }
    });
    if (filtered.length >= 4) {
      for (var i = 0; i < 4; i++) {
        extractedOptions[i] = cleanHtmlLatex(filtered[i].innerHTML || filtered[i].textContent);
      }
    }
  }

  // --- Answer Key ---
  var answerKey = "";
  var rawAns = qdd ? qdd.answer : null;
  if (Array.isArray(rawAns) && rawAns.length > 0) {
    rawAns = rawAns[0];
  }
  if (rawAns !== null && rawAns !== undefined) {
    var rawStr = String(rawAns).trim();
    if (/^[0-3]$/.test(rawStr)) {
      answerKey = optionLetters[parseInt(rawStr, 10)];
    } else if (/^[A-Da-d]$/.test(rawStr)) {
      answerKey = rawStr.toUpperCase();
    } else {
      answerKey = rawStr;
    }
  }

  // --- Solution Text ---
  var solutionText = "";
  if (qdd && Array.isArray(qdd.solutions)) {
    for (var s = 0; s < qdd.solutions.length; s++) {
      var sol = qdd.solutions[s];
      var candidate = (sol.solutionLatex || sol.solutionText || sol.text || "").trim();
      if (candidate && !candidate.toLowerCase().includes("video solutions available")) {
        solutionText = candidate;
        break;
      }
    }
  }
  if (!solutionText) {
    var ansText = (acceptedAnswer.text || "").trim();
    if (ansText && !ansText.toLowerCase().includes("video solutions available")) {
      solutionText = ansText;
    }
  }
  if (!solutionText) {
    solutionText = "# TODO";
  } else {
    solutionText = cleanHtmlLatex(solutionText);
  }

  // ── 4. Build Markdown Stub ───────────────────────────────────────────────
  var mdLines = [
    "---",
    "topic: " + topic,
    "class: " + classRoman,
    "difficulty: " + difficulty,
    "answer: " + answerKey,
    "prev_year: " + prevYear,
    "source: " + sourceUrl,
    "last_used:",
    "---",
    "",
    questionText,
    "",
    "OptionA: " + (extractedOptions[0] || "# TODO"),
    "OptionB: " + (extractedOptions[1] || "# TODO"),
    "OptionC: " + (extractedOptions[2] || "# TODO"),
    "OptionD: " + (extractedOptions[3] || "# TODO"),
    "",
    "",
    "## Solution",
    "",
    solutionText
  ];

  var md = mdLines.join("\n");

  // ── 5. Open popup window ─────────────────────────────────────────────────
  var popup = window.open("", "_blank", "width=720,height=580,menubar=no,toolbar=no,location=no,status=no");
  if (!popup) {
    alert("Popup blocked! Please allow popups for this site and try again.");
    return;
  }

  var css = [
    "body{margin:0;padding:16px;background:#1e1e2e;color:#cdd6f4;font-family:sans-serif;box-sizing:border-box}",
    "h3{margin:0 0 4px;color:#89b4fa;font-size:15px}",
    "p.sub{margin:0 0 10px;color:#6c7086;font-size:12px}",
    "textarea{display:block;width:100%;height:430px;background:#11111b;color:#cdd6f4;",
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
