# gemini_handler.py
import os
import json
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Try import google.generativeai — if not installed the app falls back to keyword matcher
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    genai = None

import re

PROMPT_TEMPLATE = """
You are an expert question-to-syllabus mapper.
Given a single question and a syllabus (as JSON list of subjects with subject, subject_code, year, semester, topics, course_outcomes),
return a STRICT JSON object (only JSON) with the keys:
question_text, question_type, probable_topic, course_outcome, subject_name, subject_code, year, semester, confidence_score

If something cannot be determined, set its string value to "Not Found" and confidence_score to 0.0.
question_type should be one of: "MCQ", "Short Answer", "Broad Answer", "Other".

Syllabus JSON:
{syllabus_json}

Question:
\"\"\"{question_text}\"\"\"

Return only JSON.
"""

def _call_gemini(question_text, syllabus):
    if not genai:
        raise RuntimeError("Gemini client not available.")
    prompt = PROMPT_TEMPLATE.format(syllabus_json=json.dumps(syllabus, ensure_ascii=False), question_text=question_text)
    # Use a conservative setting
    try:
        resp = genai.generate_text(model="gemini-2.5-pro", prompt=prompt, max_output_tokens=512, temperature=0.0)
    except Exception as e:
        # try alternate API shape
        try:
            resp = genai.generate(prompt=prompt, model="gemini-2.5-pro")
        except Exception as e2:
            raise
    # response parsing
    raw = ""
    if hasattr(resp, "text"):
        raw = resp.text
    elif isinstance(resp, dict):
        raw = resp.get("candidates", [{}])[0].get("content") or str(resp)
    else:
        raw = str(resp)
    # Trim code fences
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        # find JSON-looking part
        for p in parts:
            if p.strip().startswith("{"):
                raw = p
                break
    try:
        parsed = json.loads(raw)
        return parsed, raw
    except Exception:
        # sometimes model returns text+json — try to find JSON substring
        m = re.search(r'(\{[\s\S]*\})', raw)
        if m:
            try:
                parsed = json.loads(m.group(1))
                return parsed, raw
            except Exception:
                pass
    raise ValueError(f"Unable to parse Gemini output as JSON. Raw output: {raw[:500]}")

def _keyword_matcher(question_text, syllabus):
    """
    Simple fallback: find best subject/topic by counting keyword occurrence.
    Returns a mapping dict similar to Gemini output but with lower confidence.
    """
    qlow = question_text.lower()
    best = {
        "question_text": question_text,
        "question_type": "Other",
        "probable_topic": "Not Found",
        "course_outcome": "Not Found",
        "subject_name": "Not Found",
        "subject_code": "Not Found",
        "year": "Not Found",
        "semester": "Not Found",
        "confidence_score": 0.0
    }
    # simple heuristics for question type
    if re.search(r'\bdefine\b|\bwhat is\b|\bwhat are\b', qlow):
        best["question_type"] = "Short Answer"
    if re.search(r'\bexplain\b|\bdescribe\b|\bdiscuss\b|\belaborate\b', qlow):
        best["question_type"] = "Broad Answer"
    if re.search(r'\bchoose\b|\boption\b|\bmcq\b|\ba\)\b', qlow):
        best["question_type"] = "MCQ"

    # scan syllabus topics and subject names
    max_score = 0
    for subj in syllabus:
        score = 0
        # match subject name & code
        if subj.get("subject"):
            name = subj["subject"].lower()
            for tok in name.split():
                if tok and tok in qlow:
                    score += 2
        if subj.get("subject_code") and subj["subject_code"].lower() in qlow:
            score += 2
        # topics
        for t in subj.get("topics", []):
            t0 = t.lower()
            # check if topic phrase appears
            if t0 and t0 in qlow:
                score += 5
            else:
                # partial token match
                for w in t0.split():
                    if w and w in qlow:
                        score += 1
        # course outcomes
        for c in subj.get("course_outcomes", []):
            c0 = c.lower()
            for w in c0.split():
                if w and w in qlow:
                    score += 1
        if score > max_score:
            max_score = score
            best["subject_name"] = subj.get("subject") or "Not Found"
            best["subject_code"] = subj.get("subject_code") or "Not Found"
            best["probable_topic"] = ", ".join(subj.get("topics")[:2]) if subj.get("topics") else "Not Found"
            best["course_outcome"] = subj.get("course_outcomes")[0] if subj.get("course_outcomes") else "Not Found"
            best["year"] = subj.get("year", "Not Found")
            best["semester"] = subj.get("semester", "Not Found")
    # set confidence based on score
    best["confidence_score"] = min(0.95, 0.1 + max_score*0.05)
    return best

def analyze_question(question_text, syllabus):
    """
    Main wrapper. Tries Gemini if configured, otherwise fallback to keyword matcher.
    Returns a dict with the fields described.
    """
    out = {
        "question_text": question_text,
        "question_type": "Not Found",
        "probable_topic": "Not Found",
        "course_outcome": "Not Found",
        "subject_name": "Not Found",
        "subject_code": "Not Found",
        "year": "Not Found",
        "semester": "Not Found",
        "confidence_score": 0.0,
        "ai_raw_output": None,
        "error_message": None
    }
    # prefer Gemini if configured
    if genai and GEMINI_API_KEY:
        try:
            parsed, raw = _call_gemini(question_text, syllabus)
            out.update({k: parsed.get(k, out[k]) for k in out.keys() if k in parsed})
            out["ai_raw_output"] = raw
            try:
                out["confidence_score"] = float(parsed.get("confidence_score", out["confidence_score"]))
            except Exception:
                out["confidence_score"] = out.get("confidence_score", 0.0)
            return out
        except Exception as e:
            out["error_message"] = f"Gemini error: {e}"
            # fallback to keyword matcher
    # fallback
    try:
        kb = _keyword_matcher(question_text, syllabus)
        out.update(kb)
    except Exception as e:
        out["error_message"] = f"Fallback matcher error: {e}"
    return out






# import google.generativeai as genai
# import json
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Configure Gemini API with your key
# # It's recommended to load the API key from environment variables for security
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in a .env file or directly.")

# genai.configure(api_key=GEMINI_API_KEY)

# model = genai.GenerativeModel("gemini-2.5-pro")

# def analyze_question_with_gemini(question_text: str, syllabus_data: dict) -> dict:
#     """
#     Analyzes a given question using Gemini AI based on the provided syllabus data.

#     Args:
#         question_text (str): The text of the question to be analyzed.
#         syllabus_data (dict): A dictionary containing the syllabus information.

#     Returns:
#         dict: A dictionary containing the analyzed question's metadata (type, topic, CO, etc.).
#               Returns an error dictionary if analysis fails or JSON is invalid.
#     """
#     # Construct a detailed prompt for Gemini AI
#     # Emphasize strict JSON output and handling of 'Not Found'
#     prompt = f"""
#     You are an intelligent university exam question analyzer. Your task is to categorize a given question based on the provided syllabus.

#     Here is the question:
#     "{question_text}"

#     Here is the syllabus information (structured as a list of subject dictionaries):
#     {json.dumps(syllabus_data, indent=2)}

#     Based on the question and the syllabus, identify the following attributes.
#     For 'probable_topic', find the most relevant specific topic/sub-topic from the syllabus.
#     For 'course_outcome', find the most relevant CO from the syllabus.
#     If a direct match for 'probable_topic', 'course_outcome', 'subject_name', 'subject_code', 'year', or 'semester' is not found,
#     state 'Not Found' for that specific attribute.

#     Output the result in a strict JSON format with the following keys:
#     - "question_text": The original question text.
#     - "question_type": Categorize as "MCQ", "Short Answer", "Broad Answer", or "Other" based on the question's nature.
#     - "probable_topic": The most relevant specific topic or sub-topic from the syllabus.
#     - "course_outcome": The corresponding Course Outcome (CO) from the syllabus.
#     - "subject_name": The subject name from the syllabus.
#     - "subject_code": The subject code from the syllabus.
#     - "year": The academic year (e.g., 2, 3, 4) from the syllabus.
#     - "semester": The academic semester (e.g., 1, 2) from the syllabus.
#     - "confidence_score": A score from 0.0 to 1.0 indicating confidence in the analysis.

#     Example of expected JSON output:
#     {{
#       "question_text": "Explain the working of Link State Routing algorithm.",
#       "question_type": "Broad Answer",
#       "probable_topic": "Network Routing: Routing Algorithms-Shortest Path algorithm",
#       "course_outcome": "Not Found",
#       "subject_name": "Computer Networks",
#       "subject_code": "IT/PC/B/T/225",
#       "year": 2,
#       "semester": 2,
#       "confidence_score": 0.95
#     }}
#     """

#     try:
#         # Generate content using Gemini model
#         response = model.generate_content(prompt)
#         # Extract text from the response
#         ai_output_text = response.text.strip()

#         # Attempt to parse the AI's response as JSON
#         # Sometimes Gemini might include markdown code blocks (