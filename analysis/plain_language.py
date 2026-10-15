"""Plain-language checks that a script can do, for every text a reader sees.

Used by check_writing.py, and as a CLI on rendered text:
    python3 -I analysis/plain_language.py <file.txt|file.md> [...]
Checks, per sentence: length (25 words for descriptive text, 20 for instructions),
no contractions, no progressive or perfect tenses, no -ing verb forms outside
technical names. Per paragraph: at most 6 sentences. Vocabulary is not checked.
"""

import re
import sys

# -ing words that are technical names here, or are not verb forms
ING_OK = {
    "during", "thing", "something", "nothing", "anything", "everything", "string", "ring", "king", "spring",
    "screening", "onboarding", "tracking", "pricing", "ceiling", "morning", "evening",
    # technical names: department names, the vendor's WARNING outcome, document types, cited source titles
    "engineering", "marketing", "warning", "warnings", "driving", "meeting", "meetings", "banking", "hiring",
    "finding", "findings", "operating",  # audit "control finding"; "operating model"
}
DESCRIPTIVE_MAX, INSTRUCTION_MAX, PARA_MAX = 25, 20, 6
IMPERATIVE = re.compile(r"^(CAUTION: |WARNING: )?(Do|Record|Hold|Set|Ask|Examine|Compare|Correct|Test|Show|Add|Use|Make|Find|Send|Keep|Replace|Run|Start|Stop|Check|Measure|Read|Open|Talk|Report|Write|Get|Put|Choose|Remove|Move|Enter|Type|Decide)\b")


def sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"“(])", text) if s]


def words(s):
    return [w for w in s.split(" ") if re.search(r"[A-Za-z0-9]", w)]


def check_sentence(s, instruction=None):
    """Return a list of problems for one sentence."""
    out = []
    n = len(words(s))
    is_instr = bool(IMPERATIVE.match(s)) if instruction is None else instruction
    limit = INSTRUCTION_MAX if is_instr else DESCRIPTIVE_MAX
    if n > limit:
        out.append(f"{n} words (max {limit})")
    if re.search(r"\b\w+'(t|re|ve|ll|d)\b|n['’]t\b|\b(it|that|there|what|here)['’]s\b", s, re.I):
        out.append("contraction")
    if re.search(r"\b(is|are|was|were|be|been|am)\s+(not\s+)?\w+ing\b", s, re.I):
        bad = [m.group(0) for m in re.finditer(r"\b(is|are|was|were|be|been|am)\s+(not\s+)?(\w+ing)\b", s, re.I) if m.group(3).lower() not in ING_OK]
        if bad:
            out.append("progressive: " + bad[0])
    if re.search(r"\b(has|have|had)\s+(not\s+)?(been|\w+ed|done|made|found|shown|seen|given|taken|known)\b", s, re.I):
        out.append("perfect tense")
    ing = [w for w in re.findall(r"\b[A-Za-z]+ing\b", s) if w.lower() not in ING_OK and not w.isupper()]
    if ing:
        out.append("-ing: " + ", ".join(sorted(set(ing))))
    return out


def check_text(text, instruction=None):
    """Check a block of text; return (sentence, problems) pairs and paragraph problems."""
    found = []
    for para in re.split(r"\n\s*\n", text):
        sents = sentences(para)
        if len(sents) > PARA_MAX:
            found.append((para[:80] + "…", [f"{len(sents)} sentences in one paragraph (max {PARA_MAX})"]))
        for s in sents:
            p = check_sentence(s, instruction)
            if p:
                found.append((s, p))
    return found


# ---------- extract reader-facing text blocks ----------
from html.parser import HTMLParser

BLOCK_TAGS = {"p", "li", "td", "th", "dd", "dt", "h1", "h2", "h3", "h4", "h5", "summary", "label", "caption",
              "figcaption", "button", "title", "div", "section", "article", "header", "footer", "main", "tr", "ul", "ol", "table", "dl", "nav", "details"}
SKIP_TAGS = {"script", "style", "svg", "noscript", "code", "pre", "template"}


class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.skip = [], [], 0

    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.out.append(t)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        elif tag in BLOCK_TAGS or tag == "br":
            self.flush()
        elif tag == "span":
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS:
            self.flush()
        elif tag == "span":
            self.buf.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def blocks_from_html(html):
    b = _Blocks()
    b.feed(html)
    b.flush()
    return b.out


def blocks_from_md(md):
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip() or line.strip().startswith("<!--") or re.match(r"^\|?\s*-{3,}", line.strip()):
            continue
        line = re.sub(r"^#+\s*|^\s*[-*]\s+|^###\s*Notes:\s*", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line).replace("**", "").replace("`", "")
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else [line.strip()]
        out += [c for c in cells if c]
    return out


def check_blocks(blocks):
    found = []
    for b in blocks:
        found += check_text(b)
    return found


def assert_plain(text, where="", instruction=None):
    bad = check_text(text, instruction)
    assert not bad, f"plain language: {where}: " + " | ".join(f"{p}: {s}" for s, p in bad[:5])


if __name__ == "__main__":
    total = 0
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if path.endswith((".html", ".htm")):
            bad = check_blocks(blocks_from_html(text))
        elif path.endswith(".md"):
            bad = check_blocks(blocks_from_md(text))
        elif path.endswith(".json"):
            import json
            bad = check_blocks(json.loads(text))
        else:
            bad = check_text(text)
        seen = set()
        bad = [x for x in bad if not (x[0] in seen or seen.add(x[0]))]
        total += len(bad)
        for s, p in bad:
            print(f"{path}: {'; '.join(p)} :: {s[:160]}")
    print(f"plain-language problems: {total}")
    sys.exit(1 if total else 0)
