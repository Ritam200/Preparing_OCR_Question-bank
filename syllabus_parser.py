# syllabus_parser.py
import re
import json

# Basic heuristics parser for common syllabus layouts. Good if syllabus is semi-structured.
SUBJECT_HEADING_RE = re.compile(r"^\s*\(?([A-Z0-9/]+)\)?\s*[\-\:\)]?\s*(.+)$", re.IGNORECASE)
YEAR_SEM_RE = re.compile(r"(\d+(?:st|nd|rd|th)\s+Year).{0,40}?(\d+(?:st|nd|rd|th)\s+Semester)?", re.IGNORECASE)

def validate_syllabus_json(obj):
    """
    If user uploaded structured JSON syllabus, ensure it's in usable form.
    Expect a list of subject dicts. Normalize keys.
    """
    if not isinstance(obj, list):
        raise ValueError("Syllabus JSON should be a list of subjects.")
    cleaned = []
    for item in obj:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject") or item.get("subject_name") or item.get("title") or ""
        code = item.get("subject_code") or item.get("code") or ""
        topics = item.get("topics") or item.get("syllabus") or []
        cos = item.get("course_outcomes") or item.get("course_outcome") or []
        cleaned.append({
            "subject": subject.strip(),
            "subject_code": code.strip(),
            "year": item.get("year", ""),
            "semester": item.get("semester", ""),
            "topics": topics if isinstance(topics, list) else [t.strip() for t in split_topics(str(topics))],
            "course_outcomes": cos if isinstance(cos, list) else [c.strip() for c in split_topics(str(cos))],
            "raw_text": item.get("raw_text", "")
        })
    return cleaned

def split_topics(text):
    # split via bullets, semicolons, newlines
    parts = re.split(r'[\n•\u2022;•\-–]+', text)
    return [p.strip() for p in parts if p.strip()]

def parse_syllabus_text(raw_text):
    """
    Heuristic: split by subject headings (lines with code/title) or by double newlines.
    Returns list of subject dicts: subject, subject_code, year, semester, topics, course_outcomes, raw_text
    """
    lines = raw_text.splitlines()
    headings_idx = []
    for i, line in enumerate(lines):
        if SUBJECT_HEADING_RE.match(line):
            headings_idx.append(i)
    blocks = []
    if not headings_idx:
        # fallback: split paragraphs
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        for p in paragraphs:
            title_line = p.splitlines()[0]
            m = SUBJECT_HEADING_RE.match(title_line)
            if m:
                code, title = m.group(1), m.group(2)
            else:
                code, title = "", title_line
            topics, cos = extract_topics_and_cos(p)
            blocks.append({
                "subject": title.strip(),
                "subject_code": code.strip(),
                "year": "",
                "semester": "",
                "topics": topics,
                "course_outcomes": cos,
                "raw_text": p
            })
        return blocks

    for idx, start in enumerate(headings_idx):
        end = headings_idx[idx+1] if idx+1 < len(headings_idx) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        first_line = lines[start]
        m = SUBJECT_HEADING_RE.match(first_line)
        if m:
            code, title = m.group(1), m.group(2)
        else:
            code, title = "", first_line
        topics, cos = extract_topics_and_cos(block)
        blocks.append({
            "subject": title.strip(),
            "subject_code": code.strip(),
            "year": "",
            "semester": "",
            "topics": topics,
            "course_outcomes": cos,
            "raw_text": block
        })
    # try to get year/semester from whole document
    ym = YEAR_SEM_RE.search(raw_text)
    if ym:
        year = ym.group(1).strip()
        sem = (ym.group(2) or "").strip()
        for b in blocks:
            if not b["year"]:
                b["year"] = year
            if not b["semester"]:
                b["semester"] = sem
    return blocks

def extract_topics_and_cos(block_text):
    """
    Simple: find lines after keywords 'Topics','Syllabus','Course Outcomes' etc.
    """
    lines = [l.strip() for l in block_text.splitlines() if l.strip()]
    topics = []
    cos = []
    co_mode = False
    for i, line in enumerate(lines[1:], start=1):
        low = line.lower()
        if any(k in low for k in ["course outcome", "course outcomes", "learning outcomes", "outcomes", "course objective"]):
            co_mode = True
            remainder = re.sub(r'^(course outcomes?|learning outcomes?|course objectives?)[:\-\s]*', '', line, flags=re.I)
            if remainder.strip():
                cos.append(remainder.strip())
            continue
        if co_mode:
            # collect as CO until likely next heading (short upper case line)
            cos.append(line)
        else:
            # if bullet-like or comma separated or "Module" or "Unit"
            if line.startswith(("•","-","*")) or "," in line or ":" in line or re.match(r'^(Module|Unit|Chapter)\b', line, re.I):
                topics.append(line)
            else:
                # small lines likely topics
                if len(line.split()) <= 12:
                    topics.append(line)
    # cleanup
    topics = [t.strip() for t in dict.fromkeys(topics) if t.strip()]
    cos = [c.strip() for c in dict.fromkeys(cos) if c.strip()]
    return topics, cos







# # syllabus_parser.py
# import re
# import json

# # Basic heuristics parser for common syllabus layouts. Good if syllabus is semi-structured.
# SUBJECT_HEADING_RE = re.compile(r"^\s*\(?([A-Z0-9/]+)\)?\s*[\-\:\)]?\s*(.+)$", re.IGNORECASE)
# YEAR_SEM_RE = re.compile(r"(\d+(?:st|nd|rd|th)\s+Year).{0,40}?(\d+(?:st|nd|rd|th)\s+Semester)?", re.IGNORECASE)

# def validate_syllabus_json(obj):
#     """
#     If user uploaded structured JSON syllabus, ensure it's in usable form.
#     Expect a list of subject dicts. Normalize keys.
#     """
#     if not isinstance(obj, list):
#         raise ValueError("Syllabus JSON should be a list of subjects.")
#     cleaned = []
#     for item in obj:
#         if not isinstance(item, dict):
#             continue
#         subject = item.get("subject") or item.get("subject_name") or item.get("title") or ""
#         code = item.get("subject_code") or item.get("code") or ""
#         topics = item.get("topics") or item.get("syllabus") or []
#         cos = item.get("course_outcomes") or item.get("course_outcome") or []
#         cleaned.append({
#             "subject": subject.strip(),
#             "subject_code": code.strip(),
#             "year": item.get("year", ""),
#             "semester": item.get("semester", ""),
#             "topics": topics if isinstance(topics, list) else [t.strip() for t in split_topics(str(topics))],
#             "course_outcomes": cos if isinstance(cos, list) else [c.strip() for c in split_topics(str(cos))],
#             "raw_text": item.get("raw_text", "")
#         })
#     return cleaned

# def split_topics(text):
#     # split via bullets, semicolons, newlines
#     parts = re.split(r'[\n•\u2022;•\-–]+', text)
#     return [p.strip() for p in parts if p.strip()]

# def parse_syllabus_text(raw_text):
#     """
#     Heuristic: split by subject headings (lines with code/title) or by double newlines.
#     Returns list of subject dicts: subject, subject_code, year, semester, topics, course_outcomes, raw_text
#     """
#     lines = raw_text.splitlines()
#     headings_idx = []
#     for i, line in enumerate(lines):
#         if SUBJECT_HEADING_RE.match(line):
#             headings_idx.append(i)
#     blocks = []
#     if not headings_idx:
#         # fallback: split paragraphs
#         paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
#         for p in paragraphs:
#             title_line = p.splitlines()[0]
#             m = SUBJECT_HEADING_RE.match(title_line)
#             if m:
#                 code, title = m.group(1), m.group(2)
#             else:
#                 code, title = "", title_line
#             topics, cos = extract_topics_and_cos(p)
#             blocks.append({
#                 "subject": title.strip(),
#                 "subject_code": code.strip(),
#                 "year": "",
#                 "semester": "",
#                 "topics": topics,
#                 "course_outcomes": cos,
#                 "raw_text": p
#             })
#         return blocks

#     for idx, start in enumerate(headings_idx):
#         end = headings_idx[idx+1] if idx+1 < len(headings_idx) else len(lines)
#         block = "\n".join(lines[start:end]).strip()
#         first_line = lines[start]
#         m = SUBJECT_HEADING_RE.match(first_line)
#         if m:
#             code, title = m.group(1), m.group(2)
#         else:
#             code, title = "", first_line
#         topics, cos = extract_topics_and_cos(block)
#         blocks.append({
#             "subject": title.strip(),
#             "subject_code": code.strip(),
#             "year": "",
#             "semester": "",
#             "topics": topics,
#             "course_outcomes": cos,
#             "raw_text": block
#         })
#     # try to get year/semester from whole document
#     ym = YEAR_SEM_RE.search(raw_text)
#     if ym:
#         year = ym.group(1).strip()
#         sem = (ym.group(2) or "").strip()
#         for b in blocks:
#             if not b["year"]:
#                 b["year"] = year
#             if not b["semester"]:
#                 b["semester"] = sem
#     return blocks

# def extract_topics_and_cos(block_text):
#     """
#     Simple: find lines after keywords 'Topics','Syllabus','Course Outcomes' etc.
#     """
#     lines = [l.strip() for l in block_text.splitlines() if l.strip()]
#     topics = []
#     cos = []
#     co_mode = False
#     for i, line in enumerate(lines[1:], start=1):
#         low = line.lower()
#         if any(k in low for k in ["course outcome", "course outcomes", "learning outcomes", "outcomes", "course objective"]):
#             co_mode = True
#             remainder = re.sub(r'^(course outcomes?|learning outcomes?|course objectives?)[:\-\s]*', '', line, flags=re.I)
#             if remainder.strip():
#                 cos.append(remainder.strip())
#             continue
#         if co_mode:
#             # collect as CO until likely next heading (short upper case line)
#             cos.append(line)
#         else:
#             # if bullet-like or comma separated or "Module" or "Unit"
#             if line.startswith(("•","-","*")) or "," in line or ":" in line or re.match(r'^(Module|Unit|Chapter)\b', line, re.I):
#                 topics.append(line)
#             else:
#                 # small lines likely topics
#                 if len(line.split()) <= 12:
#                     topics.append(line)
#     # cleanup
#     topics = [t.strip() for t in dict.fromkeys(topics) if t.strip()]
#     cos = [c.strip() for c in dict.fromkeys(cos) if c.strip()]
#     return topics, cos




# import re
# import json

# def parse_syllabus_text(syllabus_text: str) -> list:
#     """
#     Parses raw syllabus text to extract structured information about subjects,
#     their topics, and potentially year/semester.

#     Args:
#         syllabus_text (str): The full text content of the syllabus.

#     Returns:
#         list: A list of dictionaries, where each dictionary represents a subject
#               and contains its details (subject_code, subject_name, year, semester, topics).
#     """
#     subjects_data = []
#     current_subject = None
#     current_year = "Unknown Year"
#     current_semester = "Unknown Semester"

#     # Regex to find Year and Semester headers (e.g., "2nd Year 1st Semester")
#     year_semester_pattern = re.compile(
#         r'(\d+)(?:st|nd|rd|th)?\s+Year\s+(\d+)(?:st|nd|rd|th)?\s+Semester',
#         re.IGNORECASE
#     )

#     # Regex to find Subject Code and Name (e.g., "IT/PC/B/T/211 Data Structures and Algorithms")
#     # This pattern is based on the provided syllabus structure.
#     subject_header_pattern = re.compile(
#         r'^\s*\(?(IT\/[A-Z]{2}\/[A-Z]\/[T|S]\/\d{3}[A-Z]?)\)?\s+(.+?)\s+(PC|BS|PE|HS|OE)\s+(Basic|Honours|Elective-I|Elective-II|Elective-III|Elective-IV)\s+\d+\s+\d+\s+\d+\s+(\d+\.?\d*)\s+\d+',
#         re.IGNORECASE
#     )
#     # A simpler pattern for subject headers if the above is too strict
#     simple_subject_pattern = re.compile(
#         r'^\s*\(?(IT\/[A-Z]{2}\/[A-Z]\/[T|S]\/\d{3}[A-Z]?)\)?\s*(.+)',
#         re.IGNORECASE
#     )

#     # Regex to find topic headers (e.g., "Introduction:", "Vector Algebra:", "Graph Theory:")
#     # This is a heuristic and might need fine-tuning based on actual syllabus variations.
#     topic_heading_pattern = re.compile(r'^\s*([A-Z][a-zA-Z\s&-]+?):\s*(.*)$')
#     # Pattern for bullet points or numbered lists that might indicate sub-topics
#     list_item_pattern = re.compile(r'^\s*[\-•*o]\s*(.*)$|^\s*\d+\.\s*(.*)$')


#     lines = syllabus_text.splitlines()
#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue

#         # Check for Year and Semester
#         year_sem_match = year_semester_pattern.search(line)
#         if year_sem_match:
#             current_year = int(year_sem_match.group(1))
#             current_semester = int(year_sem_match.group(2))
#             continue

#         # Check for Subject Header
#         subject_match = subject_header_pattern.match(line)
#         if not subject_match:
#             subject_match = simple_subject_pattern.match(line) # Try simpler pattern

#         if subject_match:
#             if current_subject: # Save previous subject if exists
#                 subjects_data.append(current_subject)

#             subject_code = subject_match.group(1).strip()
#             subject_name = subject_match.group(2).strip()

#             current_subject = {
#                 "subject_code": subject_code,
#                 "subject_name": subject_name,
#                 "year": current_year,
#                 "semester": current_semester,
#                 "topics": [],
#                 "course_outcomes": [] # Placeholder for COs, might need manual extraction or more complex AI
#             }
#             continue

#         # If we are inside a subject, try to extract topics
#         if current_subject:
#             topic_heading_match = topic_heading_pattern.match(line)
#             if topic_heading_match:
#                 heading = topic_heading_match.group(1).strip()
#                 content = topic_heading_match.group(2).strip()
#                 current_subject["topics"].append(f"{heading}: {content}")
#             else:
#                 # Append to the last topic or as a general topic if no specific heading
#                 if current_subject["topics"]:
#                     current_subject["topics"][-1] += " " + line
#                 else:
#                     # If no topic heading found yet, treat as general content for the subject
#                     current_subject["topics"].append(line)

#     if current_subject: # Add the last subject
#         subjects_data.append(current_subject)

#     # Post-processing: Clean up topics and add dummy COs if not found
#     for subject in subjects_data:
#         # Simple heuristic for COs: if "Course Outcome" or "CO" is mentioned, add a dummy
#         # For a real project, you'd need a more sophisticated CO extraction.
#         if not subject["course_outcomes"]:
#             subject["course_outcomes"].append("CO1: Understand basic concepts.")
#             subject["course_outcomes"].append("CO2: Apply learned principles to solve problems.")

#         # Further clean up topics by splitting long strings into more manageable chunks
#         # This is crucial for the AI to find specific matches.
#         processed_topics = []
#         for topic_str in subject["topics"]:
#             # Split by common sentence endings or list markers
#             sub_topics = re.split(r'\.\s*|\;\s*|(?<=\))\s*', topic_str)
#             sub_topics = [s.strip() for s in sub_topics if s.strip()]
#             processed_topics.extend(sub_topics)
#         subject["topics"] = processed_topics

#     return subjects_data

# # Example usage (for testing syllabus_parser.py directly)
# if __name__ == "__main__":
#     # This part is for local testing of the parser
#     # You would typically load your syllabus text from a file here
#     sample_syllabus_text = """
#     DEPARTMENT OF INFORMATION TECHNOLOGY
#     SYLLABUS OF 2ND TO 4TH YEAR OF THE
#     UNDERGRADUATE ENGINEERING DEGREE PROGRAMME

#     2nd Year 1st Semester
#     Subject Code   Subject Name   Category   Type   Contact   Credit   Marks
#     L   T   P
#     IT/PC/B/T/211   Data Structures and Algorithms   PC   Basic   3   0   0   3   100
#     IT/BS/B/T/212   Mathematics for IT-I   BS   Basic   3   0   0   3   100
#     (IT/PC/B/T/213) Database Management Systems PC Basic 3 0 0 3 100
#     Introduction: History of Evolution of DBMS and advantages over traditional file system.
#     Data Model: Introduction to Relational data model and object oriented data model; Keys, Entity-Relationship Model.
#     SQL: Introduction to SQL, Stored Procedures and Triggers.

#     2nd Year 2nd Semester
#     IT/PC/B/T/225   Computer Networks   PC   Basic   3   0   0   3   100
#     Introduction: Communication Tasks, Communication Model, Network Architecture, ISO/OSI Reference Model.
#     Network Routing: Routing Characteristics, Routing Algorithms-Shortest Path algorithm: Dijkstra's Algorithm.
#     Transport layer Protocols UDP, TCP: Services; TCP Flow Control.
#     """
#     parsed_data = parse_syllabus_text(sample_syllabus_text)
#     print(json.dumps(parsed_data, indent=2))

#     # You can also test with a real file
#     # try:
#     #     with open('MultipleFiles/2.1.2_2019_Syllabus_CurriculumWise.docx.pdf', 'rb') as f:
#     #         # This requires pdf2image and pytesseract setup
#     #         from pdf2image import convert_from_bytes
#     #         import pytesseract
#     #         images = convert_from_bytes(f.read())
#     #         full_text = ""
#     #         for img in images:
#     #             full_text += pytesseract.image_to_string(img) + "\n"
#     #         parsed_data_from_pdf = parse_syllabus_text(full_text)
#     #         print("\n--- Parsed from PDF ---")
#     #         print(json.dumps(parsed_data_from_pdf, indent=2))
#     # except Exception as e:
#     #     print(f"Could not test PDF parsing: {e}")


