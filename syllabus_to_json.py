"""
syllabus_to_json.py
Usage:
    python syllabus_to_json.py /path/to/2.1.2_2019_Syllabus_CurriculumWise.docx.pdf output.json
Produces structured JSON with keys:
  - year
  - semester
  - subjects: [ { subject, subject_code, category(optional), credit(optional),
                  topics: [...], course_outcomes: [...] , raw_text: "..." }, ... ]
"""

import sys
import pdfplumber
import re
import json

# --- Helper regexes (tuned for the uploaded syllabus style) ---
# Subject heading example: (IT/PC/B/T/211) Data Structures and Algorithms
SUBJECT_HEADING_RE = re.compile(
    r"^\s*\((?P<code>[A-Z0-9/]+)\)\s*(?P<title>[^(\n\r]+)",
    flags=re.IGNORECASE
)

# Year / Semester heading examples: "2nd Year 1st Semester" or "4th Year 2nd Semester"
YEAR_SEM_RE = re.compile(r"(?P<year>\d+(?:st|nd|rd|th)\s+Year)\s+(?P<semester>\d+(?:st|nd|rd|th)\s+Semester)", re.IGNORECASE)

# Course outcomes block heading (if worded explicitly)
CO_OUTCOME_HEADERS = [
    r"course outcomes",
    r"course outcome",
    r"course objectives",
    r"outcomes",
    r"learning outcomes",
    r"objectives"
]
CO_OUTCOME_RE = re.compile(r"(?:" + r"|".join(CO_OUTCOME_HEADERS) + r")[:\s-]*", re.IGNORECASE)

# Topic / Section heuristics: lines that are bullets or look like "Introduction:", "Module-1", or "Topics:"
TOPIC_LEADERS = (r"introduction", r"module", r"topics?", r"chapter", r"contents?", r"syllabus", r"unit")

# -----------------------------------------------------------------------------
def extract_text_from_pdf(path):
    pages = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            txt = p.extract_text() or ""
            pages.append(txt)
    full = "\n".join(pages)
    # normalize whitespace
    return re.sub(r"\r", "\n", full)

def split_into_subject_blocks(text):
    """
    Find all subject headings and split the document into blocks per subject.
    Returns list of tuples: (heading_match, block_text)
    """
    lines = text.splitlines()
    headings = []
    for i, line in enumerate(lines):
        m = SUBJECT_HEADING_RE.match(line)
        if m:
            headings.append((i, m))
    blocks = []
    for idx, (i, m) in enumerate(headings):
        start = i
        end = headings[idx+1][0] if idx+1 < len(headings) else len(lines)
        block_text = "\n".join(lines[start:end]).strip()
        blocks.append((m, block_text))
    return blocks

def extract_topics_and_outcomes(block_text):
    """
    Heuristics:
      - Topics: gather lines with colon (e.g., "Introduction: ...") or lines starting with bullets/dashes
      - Modules: detect "Module-1", "Module 1", "Unit 1" and collect following paragraphs until next module or blank line
      - Course outcomes: try to find an explicit heading; otherwise leave empty list
    """
    topics = []
    outcomes = []
    # Try to find an explicit Course Outcomes section
    co_match = CO_OUTCOME_RE.search(block_text)
    if co_match:
        # take substring from that match to next double newline or next subject-like heading
        start = co_match.start()
        tail = block_text[start:]
        # split at two newlines or next capitalized heading line
        parts = re.split(r"\n\s*\n", tail, maxsplit=1)
        co_text = parts[0]
        # clean heading
        co_text = CO_OUTCOME_RE.sub("", co_text).strip()
        # split on semicolons or sentences
        outcomes = [s.strip() for s in re.split(r"[;\n•\-–•]+", co_text) if s.strip()]
    # Extract modules/topics
    # Find lines with Module- or Unit- or lines that look like "Introduction: ..."
    for line in block_text.splitlines():
        line_strip = line.strip()
        if not line_strip:
            continue
        # module/unit
        if re.match(r"^(Module|MODULE|Unit|UNIT|Chapter|CHAPTER)\b", line_strip):
            topics.append(line_strip)
            continue
        # colon-based topic headings
        if ":" in line_strip:
            # often "Introduction: ...", "Topics:" etc.
            left = line_strip.split(":", 1)[0]
            if any(left.lower().startswith(tl) for tl in TOPIC_LEADERS):
                # keep whole line for context
                topics.append(line_strip)
                continue
        # bullets / short lines (<100 chars) with capitalized start could be topics
        if re.match(r"^[\u2022\-\*\•\–\—]\s*(.+)", line_strip):
            cleaned = re.sub(r"^[\u2022\-\*\•\–\—]\s*", "", line_strip)
            topics.append(cleaned)
            continue
        # sometimes topics are lines with many commas and lower length
        if len(line_strip) < 200 and ("," in line_strip or len(line_strip.split())<=12) and line_strip[0].isalpha():
            # naive check for topic-like line (skip long paragraphs)
            # exclude the initial heading line (which often contains code/title)
            topics.append(line_strip)
    # dedupe and clean
    topics = [t.strip() for t in dict.fromkeys(topics) if len(t.strip())>1]
    outcomes = [o.strip() for o in dict.fromkeys(outcomes) if len(o.strip())>1]
    return topics, outcomes

def parse_subject_block(match, block_text):
    code = match.group("code").strip()
    title = match.group("title").strip()
    # attempt to pull category / credits if present in same line
    extra = ""
    # topics / outcomes
    topics, outcomes = extract_topics_and_outcomes(block_text)
    return {
        "subject": title,
        "subject_code": code,
        "raw_text": block_text,
        "topics": topics,
        "course_outcomes": outcomes
    }

def extract_year_semester(text):
    m = YEAR_SEM_RE.search(text)
    if m:
        return m.group("year").strip(), m.group("semester").strip()
    # fallback: search for "1st Semester", "2nd Semester" etc anywhere
    sem_m = re.search(r"(\d+(?:st|nd|rd|th)\s+Semester)", text, re.IGNORECASE)
    yr_m = re.search(r"(\d+(?:st|nd|rd|th)\s+Year)", text, re.IGNORECASE)
    yr = yr_m.group(1).strip() if yr_m else ""
    sem = sem_m.group(1).strip() if sem_m else ""
    return yr, sem

def main(pdf_path, out_json_path):
    print("Reading PDF...")
    text = extract_text_from_pdf(pdf_path)
    year, semester = extract_year_semester(text)
    blocks = split_into_subject_blocks(text)
    subjects = []
    for match, block_text in blocks:
        subj = parse_subject_block(match, block_text)
        subjects.append(subj)
    result = {
        "filename": pdf_path,
        "year": year,
        "semester": semester,
        "subjects": subjects
    }
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Done. Wrote {len(subjects)} subject blocks to {out_json_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python syllabus_to_json.py input.pdf output.json")
        sys.exit(1)
    pdf_path = sys.argv[1]
    out_path = sys.argv[2]
    main(pdf_path, out_path)



# """
# syllabus_to_json.py
# Usage:
#     python syllabus_to_json.py /path/to/2.1.2_2019_Syllabus_CurriculumWise.docx.pdf output.json
# Produces structured JSON with keys:
#   - year
#   - semester
#   - subjects: [ { subject, subject_code, category(optional), credit(optional),
#                   topics: [...], course_outcomes: [...] , raw_text: "..." }, ... ]
# """

# import sys
# import pdfplumber
# import re
# import json

# # --- Helper regexes (tuned for the uploaded syllabus style) ---
# # Subject heading example: (IT/PC/B/T/211) Data Structures and Algorithms
# SUBJECT_HEADING_RE = re.compile(
#     r"^\s*\((?P<code>[A-Z0-9/]+)\)\s*(?P<title>[^(\n\r]+)",
#     flags=re.IGNORECASE
# )

# # Year / Semester heading examples: "2nd Year 1st Semester" or "4th Year 2nd Semester"
# YEAR_SEM_RE = re.compile(r"(?P<year>\d+(?:st|nd|rd|th)\s+Year)\s+(?P<semester>\d+(?:st|nd|rd|th)\s+Semester)", re.IGNORECASE)

# # Course outcomes block heading (if worded explicitly)
# CO_OUTCOME_HEADERS = [
#     r"course outcomes",
#     r"course outcome",
#     r"course objectives",
#     r"outcomes",
#     r"learning outcomes",
#     r"objectives"
# ]
# CO_OUTCOME_RE = re.compile(r"(?:" + r"|".join(CO_OUTCOME_HEADERS) + r")[:\s-]*", re.IGNORECASE)

# # Topic / Section heuristics: lines that are bullets or look like "Introduction:", "Module-1", or "Topics:"
# TOPIC_LEADERS = (r"introduction", r"module", r"topics?", r"chapter", r"contents?", r"syllabus", r"unit")

# # -----------------------------------------------------------------------------
# def extract_text_from_pdf(path):
#     pages = []
#     with pdfplumber.open(path) as pdf:
#         for p in pdf.pages:
#             txt = p.extract_text() or ""
#             pages.append(txt)
#     full = "\n".join(pages)
#     # normalize whitespace
#     return re.sub(r"\r", "\n", full)

# def split_into_subject_blocks(text):
#     """
#     Find all subject headings and split the document into blocks per subject.
#     Returns list of tuples: (heading_match, block_text)
#     """
#     lines = text.splitlines()
#     headings = []
#     for i, line in enumerate(lines):
#         m = SUBJECT_HEADING_RE.match(line)
#         if m:
#             headings.append((i, m))
#     blocks = []
#     for idx, (i, m) in enumerate(headings):
#         start = i
#         end = headings[idx+1][0] if idx+1 < len(headings) else len(lines)
#         block_text = "\n".join(lines[start:end]).strip()
#         blocks.append((m, block_text))
#     return blocks

# def extract_topics_and_outcomes(block_text):
#     """
#     Heuristics:
#       - Topics: gather lines with colon (e.g., "Introduction: ...") or lines starting with bullets/dashes
#       - Modules: detect "Module-1", "Module 1", "Unit 1" and collect following paragraphs until next module or blank line
#       - Course outcomes: try to find an explicit heading; otherwise leave empty list
#     """
#     topics = []
#     outcomes = []
#     # Try to find an explicit Course Outcomes section
#     co_match = CO_OUTCOME_RE.search(block_text)
#     if co_match:
#         # take substring from that match to next double newline or next subject-like heading
#         start = co_match.start()
#         tail = block_text[start:]
#         # split at two newlines or next capitalized heading line
#         parts = re.split(r"\n\s*\n", tail, maxsplit=1)
#         co_text = parts[0]
#         # clean heading
#         co_text = CO_OUTCOME_RE.sub("", co_text).strip()
#         # split on semicolons or sentences
#         outcomes = [s.strip() for s in re.split(r"[;\n•\-–•]+", co_text) if s.strip()]
#     # Extract modules/topics
#     # Find lines with Module- or Unit- or lines that look like "Introduction: ..."
#     for line in block_text.splitlines():
#         line_strip = line.strip()
#         if not line_strip:
#             continue
#         # module/unit
#         if re.match(r"^(Module|MODULE|Unit|UNIT|Chapter|CHAPTER)\b", line_strip):
#             topics.append(line_strip)
#             continue
#         # colon-based topic headings
#         if ":" in line_strip:
#             # often "Introduction: ...", "Topics:" etc.
#             left = line_strip.split(":", 1)[0]
#             if any(left.lower().startswith(tl) for tl in TOPIC_LEADERS):
#                 # keep whole line for context
#                 topics.append(line_strip)
#                 continue
#         # bullets / short lines (<100 chars) with capitalized start could be topics
#         if re.match(r"^[\u2022\-\*\•\–\—]\s*(.+)", line_strip):
#             cleaned = re.sub(r"^[\u2022\-\*\•\–\—]\s*", "", line_strip)
#             topics.append(cleaned)
#             continue
#         # sometimes topics are lines with many commas and lower length
#         if len(line_strip) < 200 and ("," in line_strip or len(line_strip.split())<=12) and line_strip[0].isalpha():
#             # naive check for topic-like line (skip long paragraphs)
#             # exclude the initial heading line (which often contains code/title)
#             topics.append(line_strip)
#     # dedupe and clean
#     topics = [t.strip() for t in dict.fromkeys(topics) if len(t.strip())>1]
#     outcomes = [o.strip() for o in dict.fromkeys(outcomes) if len(o.strip())>1]
#     return topics, outcomes

# def parse_subject_block(match, block_text):
#     code = match.group("code").strip()
#     title = match.group("title").strip()
#     # attempt to pull category / credits if present in same line
#     extra = ""
#     # topics / outcomes
#     topics, outcomes = extract_topics_and_outcomes(block_text)
#     return {
#         "subject": title,
#         "subject_code": code,
#         "raw_text": block_text,
#         "topics": topics,
#         "course_outcomes": outcomes
#     }

# def extract_year_semester(text):
#     m = YEAR_SEM_RE.search(text)
#     if m:
#         return m.group("year").strip(), m.group("semester").strip()
#     # fallback: search for "1st Semester", "2nd Semester" etc anywhere
#     sem_m = re.search(r"(\d+(?:st|nd|rd|th)\s+Semester)", text, re.IGNORECASE)
#     yr_m = re.search(r"(\d+(?:st|nd|rd|th)\s+Year)", text, re.IGNORECASE)
#     yr = yr_m.group(1).strip() if yr_m else ""
#     sem = sem_m.group(1).strip() if sem_m else ""
#     return yr, sem

# def main(pdf_path, out_json_path):
#     print("Reading PDF...")
#     text = extract_text_from_pdf(pdf_path)
#     year, semester = extract_year_semester(text)
#     blocks = split_into_subject_blocks(text)
#     subjects = []
#     for match, block_text in blocks:
#         subj = parse_subject_block(match, block_text)
#         subjects.append(subj)
#     result = {
#         "filename": pdf_path,
#         "year": year,
#         "semester": semester,
#         "subjects": subjects
#     }
#     with open(out_json_path, "w", encoding="utf-8") as f:
#         json.dump(result, f, ensure_ascii=False, indent=2)
#     print(f"Done. Wrote {len(subjects)} subject blocks to {out_json_path}")

# if __name__ == "__main__":
#     if len(sys.argv) < 3:
#         print("Usage: python syllabus_to_json.py input.pdf output.json")
#         sys.exit(1)
#     pdf_path = sys.argv[1]
#     out_path = sys.argv[2]
#     main(pdf_path, out_path)

