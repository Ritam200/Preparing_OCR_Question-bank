# app.py
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import os
import io
import json
import re
import pandas as pd

from ocr_utils import ensure_tesseract, image_bytes_to_text, pdf_bytes_to_text
from syllabus_parser import parse_syllabus_text, validate_syllabus_json
from gemini_handler import analyze_question

st.set_page_config(page_title="Jadavpur University Question Analyzer", layout="wide")
st.title("Jadavpur University Question Analyzer")
st.markdown("## Preparing a Question Bank using OCR")

st.sidebar.header("Upload Files & Settings")
st.sidebar.write("Upload a syllabus file and a question paper (PDF/image/JSON supported).")

syllabus_file = st.sidebar.file_uploader("Upload Syllabus (pdf/png/jpg/jpeg/json)", type=["pdf","png","jpg","jpeg","json"])
question_file = st.sidebar.file_uploader("Upload Question Paper (pdf/png/jpg/jpeg,json)", type=["pdf","png","jpg","jpeg","json"])
tess_override = st.sidebar.text_input("Optional: TESSERACT exe path (leave blank to auto-detect)", value="")
max_questions = st.sidebar.number_input("Max questions to analyze (for testing)", min_value=1, max_value=1000, value=200)
run_button = st.sidebar.button("Run Analysis")

# configure tesseract
tpath = ensure_tesseract(tess_override)  # sets pytesseract location if found
st.sidebar.write(f"Using Tesseract: `{tpath}`")

def split_questions_from_text(text):
    if not text or text.strip() == "":
        return []
    # normalize some common headers
    text = text.replace("\r", "\n")
    # split using patterns like 1., 1), Q.1, Q1., (a) for subparts
    parts = re.split(r'\n\s*(?=(?:\d{1,3}\.|Q\.\s*\d{1,3}|\d{1,3}\)))', text)
    # further split when paragraphs contain multiple numbered items
    questions = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # if it contains multiple "1." inside, split internal too
        inner = re.split(r'(?<=\S)\n\s*(?=\d{1,3}\.)', p)
        for it in inner:
            if it.strip():
                questions.append(it.strip())
    # final cleanup: keep those with some length
    out = [q for q in questions if len(q) > 10]
    return out[:max_questions]

if run_button:
    if not syllabus_file or not question_file:
        st.error("Please upload BOTH a syllabus file and a question paper.")
        st.stop()

    # 1) Read & parse syllabus
    syllabus_structured = []
    try:
        if syllabus_file.type == "application/json" or syllabus_file.name.lower().endswith(".json"):
            raw = syllabus_file.read().decode("utf-8")
            parsed = json.loads(raw)
            syllabus_structured = validate_syllabus_json(parsed)
            st.success(f"Syllabus JSON loaded with {len(syllabus_structured)} subject entries.")
        elif syllabus_file.type == "application/pdf" or syllabus_file.name.lower().endswith(".pdf"):
            with st.spinner("Performing OCR on syllabus PDF (this may take a moment)..."):
                pdf_bytes = syllabus_file.read()
                text = pdf_bytes_to_text(pdf_bytes, dpi=300)
            st.text_area("Syllabus OCR preview (first 3000 chars)", value=text[:3000], height=220)
            syllabus_structured = parse_syllabus_text(text)
            st.success(f"Extracted {len(syllabus_structured)} subject blocks from syllabus.")
        elif syllabus_file.type.startswith("image") or syllabus_file.name.lower().endswith((".png",".jpg",".jpeg")):
            with st.spinner("Performing OCR on syllabus image..."):
                b = syllabus_file.read()
                text = image_bytes_to_text(b)
            st.text_area("Syllabus OCR preview (first 3000 chars)", value=text[:3000], height=220)
            syllabus_structured = parse_syllabus_text(text)
            st.success(f"Extracted {len(syllabus_structured)} subject blocks from syllabus image.")
        else:
            st.error("Unsupported syllabus file type.")
            st.stop()
    except Exception as e:
        st.error(f"Syllabus processing failed: {e}")
        st.stop()

    if not syllabus_structured:
        st.error("No structured syllabus could be extracted — provide a JSON syllabus for best results.")
        st.stop()

    # 2) Read & OCR question file
    try:
        if question_file.type == "application/json" or question_file.name.lower().endswith(".json"):
            rawq = question_file.read().decode("utf-8")
            question_text = rawq
        elif question_file.type == "application/pdf" or question_file.name.lower().endswith(".pdf"):
            with st.spinner("Performing OCR on question PDF..."):
                pdf_bytes = question_file.read()
                question_text = pdf_bytes_to_text(pdf_bytes, dpi=300)
        elif question_file.type.startswith("image") or question_file.name.lower().endswith((".png",".jpg",".jpeg")):
            with st.spinner("Performing OCR on question image..."):
                b = question_file.read()
                question_text = image_bytes_to_text(b)
        else:
            st.error("Unsupported question file type.")
            st.stop()
        st.text_area("Question OCR preview (first 3000 chars)", question_text[:3000], height=220)
    except Exception as e:
        st.error(f"Question file OCR failed: {e}")
        st.stop()

    # 3) split questions
    questions = split_questions_from_text(question_text)
    if not questions:
        st.error("No questions could be extracted from OCR text. Try better scan or upload as JSON.")
        st.stop()
    st.success(f"Identified {len(questions)} questions (showing up to max set).")

    # 4) Analyze each question with Gemini or fallback
    results = []
    progress = st.progress(0)
    status = st.empty()
    for i, q in enumerate(questions, start=1):
        status.text(f"Analyzing question {i}/{len(questions)}")
        try:
            analysis = analyze_question(q, syllabus_structured)
        except Exception as e:
            analysis = {"question_text": q, "error_message": str(e)}
        analysis["index"] = i
        results.append(analysis)
        progress.progress(i / len(questions))
    status.success("Analysis complete.")

    # 5) Show DataFrame
    df = pd.DataFrame(results)
    st.subheader("AI Suggested Mapping")
    st.dataframe(df.fillna(""), height=350)

    # 6) Manual review UI
    st.subheader("Manual Review & Edit")
    edited = []
    for row in results:
        with st.expander(f"Q{row['index']}: {row['question_text'][:80]}..."):
            qtxt = st.text_area("Question text", value=row.get("question_text",""), key=f"q_{row['index']}")
            subj = st.text_input("Subject Name", value=row.get("subject_name",""), key=f"subj_{row['index']}")
            code = st.text_input("Subject Code", value=row.get("subject_code",""), key=f"code_{row['index']}")
            year = st.text_input("Year", value=row.get("year",""), key=f"year_{row['index']}")
            sem = st.text_input("Semester", value=row.get("semester",""), key=f"sem_{row['index']}")
            topic = st.text_input("Probable Topic", value=row.get("probable_topic",""), key=f"topic_{row['index']}")
            co = st.text_input("Course Outcome", value=row.get("course_outcome",""), key=f"co_{row['index']}")
            qtype = st.selectbox("Question Type", ["MCQ","Short Answer","Broad Answer","Other"],
                                 index=0 if row.get("question_type") not in ["MCQ","Short Answer","Broad Answer","Other"] else ["MCQ","Short Answer","Broad Answer","Other"].index(row.get("question_type")),
                                 key=f"type_{row['index']}")
            conf = st.slider("Confidence Score", min_value=0.0, max_value=1.0, value=float(row.get("confidence_score",0.0)), step=0.01, key=f"conf_{row['index']}")
            edited.append({
                "index": row["index"],
                "question_text": qtxt,
                "subject_name": subj,
                "subject_code": code,
                "year": year,
                "semester": sem,
                "probable_topic": topic,
                "course_outcome": co,
                "question_type": qtype,
                "confidence_score": conf
            })

    # 7) Download final
    st.subheader("Download Final Question Bank")
    final_json = json.dumps(edited, ensure_ascii=False, indent=2)
    st.download_button("Download JSON", data=final_json.encode("utf-8"), file_name="question_bank.json", mime="application/json")
    csv_bytes = pd.DataFrame(edited).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="question_bank.csv", mime="text/csv")

    st.success("You can now download the final, reviewed question bank.")




# import streamlit as st
# from PIL import Image
# import pytesseract
# import re
# import json
# import pandas as pd
# from pdf2image import convert_from_bytes # For PDF handling
# import io # For handling file-like objects
# import os # For path operations

# # Import custom modules
# from gemini_handler import analyze_question_with_gemini
# from syllabus_parser import parse_syllabus_text

# # --- Tesseract OCR Path Configuration (IMPORTANT for Windows users) ---
# # If you're on Windows, you need to specify the path to the tesseract.exe executable.
# # Example: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# # For macOS/Linux, Tesseract should be in your PATH if installed via brew/apt.
# # Uncomment and modify the line below if you face TesseractNotFound error on Windows:
# # pytesseract.pytesseract.tesseract_cmd = r'YOUR_TESSERACT_PATH\tesseract.exe'

# # --- Streamlit App Configuration ---
# st.set_page_config(page_title="Jadavpur University Question Analyzer", layout="wide", icon="📚")
# st.title("📚 Jadavpur University Question Analyzer")
# st.header("Preparing a Question Bank using OCR and AI")
# st.markdown("""
#     Upload your syllabus (PDF, Image, or JSON) and question paper (PDF or Image) to automatically extract,
#     categorize, and map questions to your syllabus using Google Gemini AI.
# """)

# # --- File Uploaders ---
# st.sidebar.header("Upload Files")
# syllabus_file = st.sidebar.file_uploader(
#     "Upload Syllabus File (PDF, PNG, JPG, JPEG, JSON)",
#     type=["pdf", "png", "jpg", "jpeg", "json"],
#     help="Upload your syllabus. PDF/Image files will be OCR'd. JSON files will be parsed directly."
# )
# question_file = st.sidebar.file_uploader(
#     "Upload Question Paper (PDF, PNG, JPG, JPEG)",
#     type=["pdf", "png", "jpg", "jpeg"],
#     help="Upload an image or PDF file containing your exam questions."
# )

# # --- Helper function for OCR ---
# def perform_ocr(uploaded_file):
#     """Performs OCR on an uploaded file (PDF or Image) and returns text."""
#     all_extracted_text = ""
#     images_for_ocr = []

#     file_type = uploaded_file.type
#     file_bytes = uploaded_file.read()

#     if file_type == "application/pdf":
#         try:
#             images_for_ocr = convert_from_bytes(file_bytes, dpi=300)
#             st.info(f"Converted {len(images_for_ocr)} pages from PDF for OCR.")
#         except Exception as e:
#             st.error(f"Error converting PDF: {e}. Make sure `poppler` is installed and in your PATH.")
#             return None
#     elif file_type.startswith("image/"):
#         try:
#             images_for_ocr = [Image.open(io.BytesIO(file_bytes))]
#             st.info("Processing image file for OCR.")
#         except Exception as e:
#             st.error(f"Error opening image file: {e}. Please ensure it's a valid image.")
#             return None
#     else:
#         st.error(f"Unsupported file type for OCR: {file_type}")
#         return None

#     with st.spinner("Performing OCR... This might take a moment for large files."):
#         for i, img in enumerate(images_for_ocr):
#             # Basic image preprocessing for better OCR
#             img_gray = img.convert('L')
#             img_processed = img_gray.point(lambda x: 0 if x < 128 else 255, '1') # Binarization

#             page_text = pytesseract.image_to_string(img_processed, config='--oem 3 --psm 6')
#             all_extracted_text += f"\n--- Page {i+1} ---\n" + page_text

#     return all_extracted_text

# # --- Main Application Logic ---
# if syllabus_file and question_file:
#     st.success("Files uploaded successfully! Processing...")

#     # 1. Process Syllabus File
#     syllabus_raw_text = ""
#     syllabus_structured_data = []

#     if syllabus_file.type == "application/json":
#         try:
#             syllabus_content = syllabus_file.read().decode("utf-8")
#             syllabus_structured_data = json.loads(syllabus_content)
#             st.sidebar.success("Syllabus JSON loaded directly.")
#             # Display a snippet for verification
#             st.sidebar.json(syllabus_structured_data[:min(len(syllabus_structured_data), 2)])
#         except json.JSONDecodeError as e:
#             st.error(f"Invalid JSON format in syllabus file: {e}. Please ensure the file contains valid JSON data.")
#             st.error("Check `sample_syllabus.json` for the correct format.")
#             st.stop()
#         except Exception as e:
#             st.error(f"An unexpected error occurred while loading syllabus JSON: {e}")
#             st.stop()
#     else: # PDF or Image syllabus
#         st.info("Performing OCR on syllabus file...")
#         syllabus_raw_text = perform_ocr(syllabus_file)
#         if syllabus_raw_text is None:
#             st.stop()
#         st.subheader("📝 Raw Extracted Text (from Syllabus OCR)")
#         st.text_area("Review Syllabus OCR Output", syllabus_raw_text, height=200)

#         with st.spinner("Structuring syllabus data..."):
#             syllabus_structured_data = parse_syllabus_text(syllabus_raw_text)
#             if not syllabus_structured_data:
#                 st.warning("Could not extract structured data from syllabus. Please ensure it follows a recognizable format or provide a JSON file.")
#                 st.stop()
#             st.sidebar.success("Syllabus structured successfully.")
#             # Display a snippet for verification
#             st.sidebar.json(syllabus_structured_data[:min(len(syllabus_structured_data), 2)])


#     # 2. Process Question Paper
#     question_paper_text = perform_ocr(question_file)
#     if question_paper_text is None:
#         st.stop()

#     st.subheader("📝 Raw Extracted Text (from Question Paper OCR)")
#     st.text_area("Review Question Paper OCR Output", question_paper_text, height=300)

#     # 3. Split Extracted Text into Individual Questions
#     # This regex attempts to split questions based on common numbering patterns
#     # It captures the numbering (e.g., "1.", "a)", "(i)") and the text following it.
#     question_pattern = re.compile(r'(\n\s*\d+\.\s*|\n\s*[a-zA-Z]\)\s*|\n\s*\([ivx]+\)\s*|\n\s*\(\d+\)\s*)')
#     split_parts = question_pattern.split(question_paper_text)

#     individual_questions = []
#     # The split_parts list will contain [pre_match_text, match1, text1, match2, text2, ...]
#     # We want to combine matchX and textX
#     for i in range(1, len(split_parts), 2):
#         if i + 1 < len(split_parts):
#             question_with_prefix = split_parts[i].strip() + split_parts[i+1].strip()
#             if question_with_prefix:
#                 individual_questions.append(question_with_prefix)
#         elif i < len(split_parts) and split_parts[i].strip(): # Handle case where last part is just a number/prefix
#              individual_questions.append(split_parts[i].strip())


#     if not individual_questions:
#         st.warning("No individual questions could be identified. Please check the OCR output and your question numbering format.")
#         st.stop()

#     st.subheader(f"🔍 Identified {len(individual_questions)} Individual Questions")
#     for i, q in enumerate(individual_questions):
#         st.markdown(f"**Question {i+1}:** {q[:200]}...") # Show first 200 chars

#     # 4. Analyze Each Question with Gemini AI
#     st.subheader("🤖 Analyzing Questions with Gemini AI")
#     st.info("This step uses Gemini AI to categorize each question based on your syllabus. This may take some time depending on the number of questions and API rate limits.")

#     analyzed_results = []
#     progress_bar = st.progress(0)
#     status_text = st.empty()

#     for i, question_text in enumerate(individual_questions):
#         status_text.text(f"Analyzing question {i+1}/{len(individual_questions)}: {question_text[:70]}...")

#         # Call Gemini AI for analysis
#         analysis_output = analyze_question_with_gemini(question_text, syllabus_structured_data)

#         # Add original question text and index to the result
#         analysis_output['original_question_index'] = i + 1
#         analysis_output['original_question_text'] = question_text
#         analyzed_results.append(analysis_output)

#         progress_bar.progress((i + 1) / len(individual_questions))

#     status_text.success("Analysis complete!")

#     # 5. Display Results in a DataFrame
#     if analyzed_results:
#         df_results = pd.DataFrame(analyzed_results)

#         # Reorder columns for better readability
#         desired_columns = [
#             "original_question_index",
#             "original_question_text",
#             "question_type",
#             "subject_name",
#             "subject_code",
#             "year",
#             "semester",
#             "probable_topic",
#             "course_outcome",
#             "confidence_score",
#             "error_message", # Include error message column for failed AI analyses
#             "ai_raw_output" # Include raw AI output for debugging
#         ]
#         # Ensure all desired columns exist, fill missing with None/NaN
#         for col in desired_columns:
#             if col not in df_results.columns:
#                 df_results[col] = None

#         # Filter out columns that are entirely None if they were just placeholders
#         df_results = df_results.dropna(axis=1, how='all')

#         st.subheader("📊 Analyzed Question Bank")
#         st.dataframe(df_results, height=400)

#         # 6. Provide Download Option
#         csv_output = df_results.to_csv(index=False).encode('utf-8')
#         st.download_button(
#             label="📥 Download Question Bank as CSV",
#             data=csv_output,
#             file_name='analyzed_question_bank.csv',
#             mime='text/csv',
#             help="Download the categorized questions in CSV format."
#         )

#         json_output = json.dumps(analyzed_results, indent=2).encode('utf-8')
#         st.download_button(
#             label="📥 Download Question Bank as JSON",
#             data=json_output,
#             file_name='analyzed_question_bank.json',
#             mime='application/json',
#             help="Download the categorized questions in JSON format."
#         )

#     else:
#         st.warning("No analysis results to display. Please check the OCR output and Gemini API response.")

# else:
#     st.info("Please upload both a syllabus file and a question paper file to begin the analysis.")
#     st.markdown("---")
#     st.markdown("### How to Use:")
#     st.markdown("1. **Upload Syllabus File:** Select your syllabus in PDF, image (JPG, PNG), or JSON format.")
#     st.markdown("2. **Upload Question Paper:** Select your question paper in PDF or image (JPG, PNG) format.")
#     st.markdown("3. The app will perform OCR on image/PDF files, structure the syllabus, split questions, and use Gemini AI to categorize them based on your syllabus.")
#     st.markdown("4. View the results in a table and download them as CSV or JSON.")








