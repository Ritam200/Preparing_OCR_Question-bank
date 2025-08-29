import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import json
import io
import re
import pandas as pd
from fuzzywuzzy import fuzz

# --- Tesseract OCR Configuration (IMPORTANT: Adjust this path if Tesseract is not in your system PATH) ---
# Example for Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Example for Linux/macOS (often not needed if installed via package manager):
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- Helper Functions for OCR and Text Extraction ---

def extract_text_from_image(image_bytes):
    """Extracts text from image bytes using Tesseract OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        st.error(f"Error processing image with OCR: {e}")
        return None

def extract_text_from_pdf(pdf_bytes):
    """Extracts text from PDF bytes using Tesseract OCR (converts to images first)."""
    try:
        # Convert PDF to a list of images
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for i, image in enumerate(images):
            st.info(f"Processing page {i+1} of PDF...")
            full_text += pytesseract.image_to_string(image) + "\n\n" # Add newlines between pages
        return full_text
    except Exception as e:
        st.error(f"Error processing PDF with OCR: {e}. Make sure poppler is installed and in PATH for pdf2image.")
        return None

def process_uploaded_file(uploaded_file):
    """Handles different file types for OCR processing."""
    file_type = uploaded_file.type
    file_bytes = uploaded_file.getvalue()

    if file_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)
    elif file_type in ["image/png", "image/jpeg", "image/jpg"]:
        return extract_text_from_image(file_bytes)
    elif file_type == "application/json":
        try:
            # For JSON, assume it's already structured text or data
            return json.loads(file_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")
            return None
    else:
        st.warning(f"Unsupported file type: {file_type}. Please upload PDF, PNG, JPG, JPEG, or JSON.")
        return None

# --- Syllabus Parsing and Question Analysis (CORE AI/NLP LOGIC) ---

def parse_syllabus(syllabus_text):
    """
    Parses the syllabus text to extract structured information.
    This implementation uses regex and heuristics to extract subject details,
    semester, year, and topics.
    """
    st.subheader("Syllabus Parsing")
    st.info("Parsing the syllabus to extract structured data like subject codes, names, semesters, and topics.")

    parsed_syllabus = {}
    
    # Regex to find semester/year headers (e.g., "2nd Year 1st Semester")
    semester_year_pattern = re.compile(r"(\d\s*(?:nd|rd|th)\s*Year\s*\d\s*(?:st|nd|rd|th)\s*Semester)", re.IGNORECASE)

    # Regex to extract table row data: Subject Code, Subject Name, Category, Type, Contact (L T P), Credit, Marks
    # This pattern is designed to capture the tabular data at the beginning of each semester section.
    table_row_pattern = re.compile(
        r"^(IT/[A-Z]{2}/[A-Z]/[A-Z]/[0-9]{3}[A-Z]?)\s+"  # Subject Code (e.g., IT/PC/B/T/211)
        r"([A-Za-z\s&+-]+?)\s+"                         # Subject Name (non-greedy, until next field)
        r"([A-Z]{2})\s+"                                # Category (e.g., PC, BS)
        r"([A-Za-z]+)\s+"                               # Type (e.g., Basic, Honours)
        r"(\d)\s+(\d)\s+(\d)\s+"                        # Contact L T P
        r"(\d+\.?\d*)\s+"                               # Credit (e.g., 3, 1.5)
        r"(\d+)$"                                       # Marks (e.g., 100)
    )

    lines = syllabus_text.split('\n')
    current_semester_year = "Unknown Semester/Year"
    
    # First pass: Extract table data and semester/year information
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Update current semester/year
        semester_match = semester_year_pattern.search(line)
        if semester_match:
            current_semester_year = semester_match.group(1).strip()
            continue

        # Try to parse table rows for subject details
        table_match = table_row_pattern.match(line)
        if table_match:
            code = table_match.group(1)
            name = table_match.group(2).strip()
            category = table_match.group(3)
            type_ = table_match.group(4)
            contact_l = table_match.group(5)
            contact_t = table_match.group(6)
            contact_p = table_match.group(7)
            credit = table_match.group(8)
            marks = table_match.group(9)

            parsed_syllabus[code] = {
                "Subject Name": name,
                "Category": category,
                "Type": type_,
                "Contact (L-T-P)": f"{contact_l}-{contact_t}-{contact_p}",
                "Credit": float(credit),
                "Marks": int(marks),
                "Semester": current_semester_year,
                "Year": current_semester_year.split(' ')[0] if current_semester_year != "Unknown Semester/Year" else "Unknown",
                "Subject Code": code,
                "Course Outcomes": [], # To be extracted in the second pass if available
                "Topics": []
            }
    
    # Second pass: Populate topics and Course Outcomes for each subject
    # This requires careful handling of blocks of text following subject headers.
    # We split the entire syllabus text by the subject header pattern to get content blocks.
    syllabus_blocks = re.split(r"^\((IT/[A-Z]{2}/[A-Z]/[A-Z]/[0-9]{3}[A-Z]?)\)\s*", syllabus_text, flags=re.MULTILINE)

    # The first element of syllabus_blocks will be text before the first subject, ignore it.
    # Then, it will be code, then content, code, content, etc.
    for i in range(1, len(syllabus_blocks), 2):
        code = syllabus_blocks[i].strip()
        content = syllabus_blocks[i+1].strip()

        if code in parsed_syllabus:
            topic_lines = []
            current_topic_buffer = []

            # Heuristic for identifying topic headers within the subject content.
            # This pattern is a long regex that tries to capture common starting phrases
            # for topics/sections in the syllabus.
            topic_start_patterns = [
                r"^(Introduction|Vector Algebra|Vector calculus|Ordinary Differential Equation|Linear programming|Transportation Problem|Assignment Problem|Data Model|Database Design|SQL|Data Storage and Querying|Transaction Management|Advanced Topics|Basic Concepts|Enhancements over Procedural Languages|Classes and Objects|Inheritance and Polymorphism|Operator Overloading|Basic I/O and File I/O|Exception handling|Generic Programming|Namespace|Recapitulation of Digital Logic and Circuits|Overview of Computer Organization and Architecture|Data Representation and Arithmetic Algorithms|Processor Organization and Architecture|Memory and I/O Organization|Introduction to Parallel Processing System|Relevance of Java in Distributed Programming Environment|Input/Output|Package and Nested Classes|Thread Programming|Introspection as a capability to develop software component|Distributed Software Development|Introduction to UML|Object Oriented Design and Analysis|Software Re-usability|Probability|Random Variables|Special Distributions|Statistics|Applied Statistics|Operation Research|Game Theory|Inventory Control|Queuing Theory|Project Management|Introduction to SDLC|Requirements Engineering|Software Design|Coding Standards and Guidelines|Software Testing and Verification|Software Measurements and Metrics|Software configuration management|Software quality assurance|Standards|Graph Theory|Operations on graph|Connectivity/ cutest|Planar graph|Graph Coloring|Graph Matching|Graph representation|Directed Graphs|Trees|Cobminatorics|Basic counting rules|Pigeonhole principle|Principle of inclusion and exclusion|Generating functions|Recurrence relation|Error Detection and Correction Techniques|Flow control|Data Link Control protocols|MAC and LLC Sublayers|Collision Free Protocols|IEEE 802 Standards for LAN and MANs|Network Layer|Network Routing|Adaptive Routing|Congestion|Network Layer Protocols|Transport layer Protocols|Overview of graphics system|Raster scan Graphics|Geometric transformation|Curve and Surfaces|Clipping|Hidden line and hidden surfaces|Intensity and colour models|Rendering|Geometric modeling|Applications or advance topics|Introduction to Cloud Computing|Virtualization Technologies|Cloud Services and Platforms|Management of Cloud Resources|Cloud Security|Basics of sensor network|Communication Protocols in sensor networks|Topology Control|Routing|Transport Layer and Quality of Service, Coverage and Deployment, Reliable Data Transport, Single packet Delivery and Block delivery, Congestion Control and Rate Control|Attacks and Security Issues|Overview|Intelligent agents|Heuristic Search|Constraint satisfaction problems|Knowledge representation, Reasoning and Expert System|Logic programming|Planning|Representing and Reasoning with Uncertain Knowledge|Decision-Making|Wireless Transmission and Media Access Control|Mobile Telecommunication Systems|Wireless LANs|Mobility Management|Mobile Adhoc Networks|Transport Protocols|Web Basics|HTML|Cascading Style Sheets|JavaScript|HTML5|JavaScript Object Notation|JQuery|XML Technologies|Document Type Definition|W3C XML Schema|XPath|XQuery|Finite Automata|Regular language|Context free grammar|Push Down Automata|Turing machines|Recursively enumerable languages|UnDecidability|Overview of Compiler structure|Lexical analysis|Syntax analysis|Intermediate code generation|Run time system|Introduction to Code optimization|System Structure|Process Management|CPU scheduling|Process Synchronization|Deadlock|Storage Management|Virtual Memory|File Systems|I/O Management|Introduction to analysis|Quick review of basic data structures and algorithms|Sorting and Selection algorithms|Hashing|Union-Find problem|Design Techniques|String processing|Analysis of graph algorithms|Complexity classes|Overview and Security Attacks|Basics of Cryptography|Mathematics of cryptography|Symmetric Key Encryption|Public-Key Encryption|Integrity, Authentication and Key management|Image Encryption|Server-side Programming|Java Server Pages|Database Connectivity|CGI|Advanced Topics|Overview of J2EE|Multimedia Overview|Components of Multimedia|Lossless Compression Techniques|Lossy Compression Techniques|Elements of Image Compression System and Standards|Video Coding and Compressing Standards|Audio compression Standards|Multimedia communication and Retrieval|Multimedia architecture|Fuzzy logic|Fuzzy logic based controller design|Evolutionary Computing|Evolutionary Algorithm|Genetic Algorithm|Differential Evolution|Bio inspired Optimization Algorithms|Hybrid approaches|Introduction to Big Data|HDFS CONCEPTS|HADOOP Architecture|MAP-REDUCE|NOSQL Basics|Hadoop Eco System|Mobile OS|Opensource Platform using Android|Basic app development|Network apps|Sensors|Wi-Fi connections|Bluetooth communication|Geographical location|Cloud/Web services|Graphics and Multimedia support|Security and Permissions|Introduction to Machine Learning|Evaluating Hypotheses|Bayesian Learning|Artificial Neural Networks|Feedforward neural network|Back-propagation|Conditional Random Fields|Probabilistic Neural Network|Modern Practical Deep Networks|Classification and Clustering|Reinforcement Learning|Policy Gradient Methods|Dynamic Programming and Monte carlo methods|Temporal Difference Methods|Data Warehousing and Business Analysis|Introduction to Data Mining|Patterns of Data Mining|Data Preprocessing|Classical Data Mining approaches|Data Classification and Prediction|Cluster Analysis and outlier detection|Overview of application oriented mining|Defining IoT, characteristics of IoT, challenges of IoT, Technologies leading to IoT, Functional blocks of IoT, M2M vs IoT. IoT Ecosystem: 7 layer model and protocols|IoT data link protocols|Network layer|Transport and session layer|IoT Management protocols|IoT Applications|Next generation Networks|Fundamental of Cell Biology|Bioinformatics databases|Functional proteomics and genomics|Sequence alignment and database searching|Pattern Analysis|Evolutionary trees|Some advanced topics|Markov chains and applications|Some Tasks in Computational Biology|Fundamental concepts|Clocks and Event Ordering|Global state and snapshot recording algorithms|Termination detection|Fundamental Algorithms|Distributed Mutual exclusion|Deadlock detection|Distributed File System|Distributed Transactions|Distributed Concurrency Control|Introduction to Network Security|Security at the Application layer|Security at the Transport layer|Security at the Network layer|Firewalls|Access Control and Authorization|Authentication|IEEE 802.11 Wireless LAN Security|Types of attacks, their analysis and mitigations|Web Services Security|Introduction to Data Science|Statistical Inference|Data Science Tools and Techniques|Information Retrieval and Web Search|Business Intelligence and Financial Analysis|Social Network and Sentiment Analysis|Data Visualization|Time Series|Principles of managements|Personal Management|Plant Management|Marketing Management|Material Management|Financial Management|Module I: Introduction and mathematical preliminaries|Module II: Classification techniques|Module III: Clustering techniques|Module IV: Feature Extraction & Selection|Module V: Advancement and application of pattern recognition|Basics of NLP|Morphology and Finite State Transducers|Introduction to N-grams|Hidden Markov Models and Parts Of Speech Tagging|Semantics analysis|Text Mining|Information Retrieval and Extraction|Question Answering and Textual Entailment|Text Summarization|Performance Measure|Introduction to Computer Forensics|Overview of hardware and operating systems|Data recovery|Digital evidence controls|Computer Forensic tools|Network Forensic|Mobile Network Forensic|Software Reverse Engineering|Dealing with bad (legacy) application code|Malicious Software and Software Security|Mobile platform security models|Basic web security model|Web Application Security|Computer crime and Legal issues|Fundamentals|Image Transform|Image Enhancement|Image Segmentation|Morphological Image Processing|Image representation & description|Image Compression):"
            ]
            
            current_topic = None
            for line_in_content in content.split('\n'):
                line_in_content = line_in_content.strip()
                if not line_in_content:
                    continue

                is_new_topic_start = False
                for pattern in topic_start_patterns:
                    if re.match(pattern, line_in_content, re.IGNORECASE):
                        if current_topic_buffer:
                            topic_lines.append(" ".join(current_topic_buffer).strip())
                        current_topic_buffer = [line_in_content]
                        current_topic = line_in_content.split(':')[0].strip() # Use the first part as topic name
                        is_new_topic_start = True
                        break
                
                if not is_new_topic_start:
                    if current_topic_buffer:
                        current_topic_buffer.append(line_in_content)
                    else: # If no topic header found yet, just append to a general "Introduction" or first topic
                        if not topic_lines:
                            current_topic_buffer.append(line_in_content)
                        else:
                            # Append to the last topic if it seems like a continuation
                            topic_lines[-1] += " " + line_in_content


            if current_topic_buffer:
                topic_lines.append(" ".join(current_topic_buffer).strip())

            parsed_syllabus[code]["Topics"] = topic_lines
            
            # Attempt to extract Course Outcomes (COs) if they follow a pattern like CO1, CO2 etc.
            # This pattern looks for "CO" followed by a digit, then optional colon/period, then the text.
            co_pattern = re.compile(r"CO\d+\s*[:\.]?\s*(.+)", re.IGNORECASE)
            cos = []
            for line_in_content in content.split('\n'):
                co_match = co_pattern.match(line_in_content.strip())
                if co_match:
                    cos.append(co_match.group(0).strip()) # Capture the whole CO line
            parsed_syllabus[code]["Course Outcomes"] = cos

    return parsed_syllabus

def analyze_questions_against_syllabus(parsed_syllabus, questions_text):
    """
    Analyzes questions against the parsed syllabus to determine origin.
    It uses fuzzy string matching and keyword overlap to find the best match.
    """
    st.subheader("Question Analysis")
    st.info("Analyzing questions using fuzzy matching and keyword overlap to identify relevant subjects, topics, and course outcomes.")

    # Split questions based on common question numbering patterns (e.g., a., b., c., 1., 2., Q1., Q2.)
    # This regex tries to capture questions that start with a number/letter followed by a dot/parenthesis
    # and then the question text, until the next similar pattern or end of string.
    question_split_pattern = re.compile(r'(?:^|\n\s*)([a-zA-Z0-9]+\s*[\.\)])\s*(.*?)(?=\n\s*[a-zA-Z0-9]+\s*[\.\)]|\Z)', re.DOTALL)
    
    raw_questions = question_split_pattern.findall(questions_text)
    questions = [f"{num} {text.strip()}" for num, text in raw_questions]

    if not questions: # Fallback if the above pattern doesn't work well
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
        # Filter out very short lines that are unlikely to be full questions
        questions = [q for q in questions if len(q.split()) > 5]


    results = []

    for i, question_text_full in enumerate(questions):
        best_match = {
            "question_id": f"Q{i+1}",
            "question_text": question_text_full,
            "matched_subject_code": "N/A",
            "matched_subject_name": "N/A",
            "matched_semester": "N/A",
            "matched_year": "N/A",
            "matched_chapter_or_section": "N/A",
            "matched_course_outcome": "N/A",
            "confidence_score": 0.0,
            "analysis_notes": "No strong match found."
        }

        # Normalize question text for better matching
        normalized_question = question_text_full.lower()
        
        # Iterate through parsed syllabus to find the best match
        for subject_code, details in parsed_syllabus.items():
            subject_name = details.get("Subject Name", "").lower()
            topics = details.get("Topics", [])
            course_outcomes = details.get("Course Outcomes", [])

            current_subject_score = 0.0
            
            # 1. Subject Name Matching (using fuzzy matching for robustness)
            subject_name_ratio = fuzz.partial_ratio(normalized_question, subject_name)
            if subject_name_ratio > 60: # Threshold for a decent partial match
                current_subject_score = subject_name_ratio / 100.0
                best_match.update({
                    "matched_subject_code": subject_code,
                    "matched_subject_name": details.get("Subject Name"),
                    "matched_semester": details.get("Semester", "N/A"),
                    "matched_year": details.get("Year", "N/A"),
                    "analysis_notes": f"Subject name fuzzy match ({subject_name_ratio}%)."
                })

            # 2. Topic Matching (more specific, higher confidence)
            for topic_full_text in topics:
                normalized_topic = topic_full_text.lower()
                topic_ratio = fuzz.partial_ratio(normalized_question, normalized_topic)
                
                # Also check for direct keyword overlap
                question_keywords = set(re.findall(r'\b\w+\b', normalized_question))
                topic_keywords = set(re.findall(r'\b\w+\b', normalized_topic))
                common_keywords = len(question_keywords.intersection(topic_keywords))
                
                # Combine fuzzy ratio and keyword overlap for a heuristic score
                # A stronger match if topic_ratio is high OR if there's significant keyword overlap and a decent topic_ratio
                if topic_ratio > 75 or (common_keywords > 2 and topic_ratio > 50):
                    score = (topic_ratio / 100.0 + min(common_keywords / 5, 1.0)) / 2 # Heuristic score
                    if score > current_subject_score: # If this topic match is better than previous best
                        current_subject_score = score
                        best_match.update({
                            "matched_subject_code": subject_code,
                            "matched_subject_name": details.get("Subject Name"),
                            "matched_semester": details.get("Semester", "N/A"),
                            "matched_year": details.get("Year", "N/A"),
                            "matched_chapter_or_section": topic_full_text.split(':')[0].strip() if ':' in topic_full_text else topic_full_text[:100] + "...",
                            "analysis_notes": f"Strong topic fuzzy match ({topic_ratio}%) and keyword overlap."
                        })
                        
            # 3. Course Outcome Matching (if COs are extracted)
            for co_text in course_outcomes:
                normalized_co = co_text.lower()
                co_ratio = fuzz.partial_ratio(normalized_question, normalized_co)
                if co_ratio > 80: # Very strong match for CO
                    score = co_ratio / 100.0
                    if score > current_subject_score:
                        current_subject_score = score
                        best_match.update({
                            "matched_subject_code": subject_code,
                            "matched_subject_name": details.get("Subject Name"),
                            "matched_semester": details.get("Semester", "N/A"),
                            "matched_year": details.get("Year", "N/A"),
                            "matched_course_outcome": co_text,
                            "analysis_notes": f"Very strong course outcome fuzzy match ({co_ratio}%)."
                        })

            # Update best_match's confidence score if a better match was found in this subject
            if current_subject_score > best_match["confidence_score"] / 100.0:
                best_match["confidence_score"] = round(current_subject_score * 100, 2)
                # The other fields are already updated within the loops above

        results.append(best_match)
    return results

# --- Streamlit UI Layout ---

st.set_page_config(
    page_title="Jadavpur University Question Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 Jadavpur University Question Analyzer")
st.markdown("---")
st.header("Project Title: OCR-based Question Bank Preparation")
st.markdown("""
    This application helps students analyze questions against their syllabus.
    Upload your syllabus and question papers (PDF, images, or JSON), and the system will
    attempt to identify the subject, semester, year, chapter/section, subject code, and course outcome for each question.
""")
st.markdown("---")

# Sidebar for instructions and Tesseract info
with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    1.  **Upload Syllabus:** Provide your syllabus document (PDF, PNG, JPG, JPEG, or JSON).
    2.  **Upload Questions:** Provide your question paper document (PDF, PNG, JPG, JPEG, or JSON).
    3.  **Analyze:** Click the "Analyze Questions" button to process and get the results.
    4.  **Download:** Download the analysis in JSON format.
    """)
    st.markdown("---")
    st.header("Important Note on OCR")
    st.warning("""
    This application relies on **Tesseract OCR**. For optimal performance, ensure:
    -   Tesseract is installed on your system.
    -   For PDF processing, `poppler` utilities are also installed and in your system's PATH.
    -   The quality of your uploaded documents (clear text, good resolution) directly impacts OCR accuracy.
    """)
    st.markdown("---")
    st.info("Developed by a Jadavpur University IT Department Student for Final Year Project.")

# Main content area
col1, col2 = st.columns(2)

syllabus_text_raw = None
questions_text_raw = None

with col1:
    st.subheader("Upload Syllabus")
    syllabus_file = st.file_uploader(
        "Choose a syllabus file (PDF, PNG, JPG, JPEG, JSON)",
        type=["pdf", "png", "jpg", "jpeg", "json"],
        key="syllabus_uploader"
    )
    if syllabus_file:
        with st.spinner("Processing syllabus with OCR..."):
            syllabus_text_raw = process_uploaded_file(syllabus_file)
        if syllabus_text_raw:
            st.success("Syllabus processed successfully!")
            if isinstance(syllabus_text_raw, str):
                st.text_area("Extracted Syllabus Text (for review)", syllabus_text_raw, height=300, key="syllabus_display")
            else: # Assuming JSON input
                st.json(syllabus_text_raw)
        else:
            st.error("Failed to extract text from syllabus. Please check file format and quality.")

with col2:
    st.subheader("Upload Questions")
    questions_file = st.file_uploader(
        "Choose a question paper file (PDF, PNG, JPG, JPEG, JSON)",
        type=["pdf", "png", "jpg", "jpeg", "json"],
        key="questions_uploader"
    )
    if questions_file:
        with st.spinner("Processing questions with OCR..."):
            questions_text_raw = process_uploaded_file(questions_file)
        if questions_text_raw:
            st.success("Questions processed successfully!")
            if isinstance(questions_text_raw, str):
                st.text_area("Extracted Questions Text (for review)", questions_text_raw, height=300, key="questions_display")
            else: # Assuming JSON input
                st.json(questions_text_raw)
        else:
            st.error("Failed to extract text from questions. Please check file format and quality.")

st.markdown("---")

# The first "Analyze Questions" button
if st.button("🚀 Analyze Questions (JSON Output)", type="primary", key="analyze_json_button"):
    if syllabus_text_raw and questions_text_raw:
        with st.spinner("Analyzing questions against syllabus... This may take a while for complex analysis."):
            # Step 1: Parse the syllabus
            parsed_syllabus_data = parse_syllabus(syllabus_text_raw)
            
            # Step 2: Analyze questions using the parsed syllabus
            analysis_results = analyze_questions_against_syllabus(parsed_syllabus_data, questions_text_raw)
            
            st.success("Analysis Complete!")
            st.subheader("Analysis Results (JSON Output)")
            
            json_output = json.dumps(analysis_results, indent=4, ensure_ascii=False)
            st.json(analysis_results)
            
            st.download_button(
                label="📥 Download Analysis Results (JSON)",
                data=json_output.encode('utf-8'),
                file_name="question_analysis_results.json",
                mime="application/json"
            )
            
            st.markdown("---")
            st.subheader("Detailed Syllabus Structure (for your reference)")
            st.json(parsed_syllabus_data)

    else:
        st.warning("Please upload both a syllabus and a question paper to perform the analysis.")

# The second "Analyze Questions" button with a unique key
if st.button("🚀 Analyze Questions (Detailed View)", type="secondary", key="analyze_detailed_button"):
    if syllabus_text_raw and questions_text_raw:
        with st.spinner("Analyzing questions against syllabus... This may take a while for complex analysis."):
            # Step 1: Parse the syllabus
            parsed_syllabus_data = parse_syllabus(syllabus_text_raw)
            
            # Step 2: Analyze questions using the parsed syllabus
            analysis_results = analyze_questions_against_syllabus(parsed_syllabus_data, questions_text_raw)
            
            st.success("Analysis Complete!")
            st.subheader("Analysis Results (Detailed View)")

            # Display each question with its analysis
            for result in analysis_results:
                st.markdown(f"**Question ID:** {result['question_id']}")
                st.markdown(f"**Question Text:** {result['question_text']}")
                st.markdown(f"**Matched Subject Code:** {result['matched_subject_code']}")
                st.markdown(f"**Matched Subject Name:** {result['matched_subject_name']}")
                st.markdown(f"**Matched Semester:** {result['matched_semester']}")
                st.markdown(f"**Matched Year:** {result['matched_year']}")
                st.markdown(f"**Matched Chapter/Section:** {result['matched_chapter_or_section']}")
                st.markdown(f"**Matched Course Outcome:** {result['matched_course_outcome']}")
                st.markdown(f"**Confidence Score:** {result['confidence_score']}%")
                st.markdown(f"**Analysis Notes:** {result['analysis_notes']}")
                st.markdown("---")
    else:
        st.warning("Please upload both a syllabus and a question paper to perform the analysis.")








# import streamlit as st
# import pytesseract
# import pdf2image
# from PIL import Image
# import json
# import re
# import io
# import tempfile
# import os
# from datetime import datetime

# # Configure Streamlit page
# st.set_page_config(
#     page_title="Jadavpur University Question Analyzer",
#     page_icon="🎓",
#     layout="wide"
# )

# # Custom CSS for better styling
# st.markdown("""
# <style>
#     .main-header {
#         text-align: center;
#         color: #1f4e79;
#         font-size: 2.5rem;
#         font-weight: bold;
#         margin-bottom: 0.5rem;
#     }
#     .sub-header {
#         text-align: center;
#         color: #2c5aa0;
#         font-size: 1.5rem;
#         margin-bottom: 2rem;
#     }
#     .upload-section {
#         background-color: #f0f2f6;
#         padding: 1rem;
#         border-radius: 10px;
#         margin: 1rem 0;
#     }
#     .success-message {
#         background-color: #d4edda;
#         color: #155724;
#         padding: 1rem;
#         border-radius: 5px;
#         border: 1px solid #c3e6cb;
#     }
#     .error-message {
#         background-color: #f8d7da;
#         color: #721c24;
#         padding: 1rem;
#         border-radius: 5px;
#         border: 1px solid #f5c6cb;
#     }
#     .info-box {
#         background-color: #e7f3ff;
#         padding: 1rem;
#         border-radius: 5px;
#         border-left: 4px solid #2196F3;
#         margin: 1rem 0;
#     }
# </style>
# """, unsafe_allow_html=True)

# class QuestionAnalyzer:
#     def __init__(self):
#         self.syllabus_keywords = {}
#         self.subjects = []
#         self.chapters = []
        
#     def extract_text_from_file(self, uploaded_file):
#         """Extract text from uploaded file using OCR"""
#         text = ""
#         try:
#             if uploaded_file.type == "application/pdf":
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
#                     tmp_file.write(uploaded_file.getvalue())
#                     tmp_file_path = tmp_file.name
                
#                 images = pdf2image.convert_from_path(tmp_file_path)
                
#                 for i, image in enumerate(images):
#                     page_text = pytesseract.image_to_string(image, config='--psm 6')
#                     text += f"\n--- Page {i+1} ---\n{page_text}\n"
                
#                 os.unlink(tmp_file_path)
#             else:
#                 image = Image.open(uploaded_file)
#                 text = pytesseract.image_to_string(image, config='--psm 6')
            
#             return self.clean_text(text)
#         except Exception as e:
#             st.error(f"Error extracting text: {str(e)}")
#             return None
    
#     def clean_text(self, text):
#         """Clean and preprocess extracted text"""
#         if not text:
#             return ""
        
#         text = re.sub(r'\s+', ' ', text)
#         text = re.sub(r'[^\w\s\.\,\;\:\?\!\-\(\)]', '', text)
#         return text.strip()
    
#     def parse_syllabus(self, syllabus_text):
#         """Parse syllabus to extract subjects, semesters, and chapters"""
#         if not syllabus_text:
#             return
        
#         subject_patterns = [
#             r'Subject\s*:\s*([^\n]+)',
#             r'Course\s*:\s*([^\n]+)',
#             r'Paper\s*:\s*([^\n]+)',
#         ]
        
#         chapter_patterns = [
#             r'Chapter\s*\d+\s*[:\-]\s*([^\n]+)',
#             r'Unit\s*\d+\s*[:\-]\s*([^\n]+)',
#             r'Module\s*\d+\s*[:\-]\s*([^\n]+)',
#             r'\d+\.\s*([A-Z][^\n]+)',
#         ]
        
#         # Extract subjects
#         for pattern in subject_patterns:
#             matches = re.findall(pattern, syllabus_text, re.IGNORECASE)
#             self.subjects.extend([match.strip() for match in matches])
        
#         # Extract chapters/topics
#         for pattern in chapter_patterns:
#             matches = re.findall(pattern, syllabus_text, re.IGNORECASE)
#             self.chapters.extend([match.strip() for match in matches])
        
#         current_chapter = None
#         text_lines = syllabus_text.split('\n')
        
#         for line in text_lines:
#             line = line.strip()
#             if not line:
#                 continue
            
#             for pattern in chapter_patterns:
#                 match = re.match(pattern, line, re.IGNORECASE)
#                 if match:
#                     current_chapter = match.group(1).strip()
#                     break
            
#             if current_chapter and len(line.split()) > 2:
#                 keywords = self.extract_keywords(line)
#                 if current_chapter not in self.syllabus_keywords:
#                     self.syllabus_keywords[current_chapter] = []
#                 self.syllabus_keywords[current_chapter].extend(keywords)
    
#     def extract_keywords(self, text):
#         """Extract important keywords from text"""
#         stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
#         words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
#         keywords = [word for word in words if word not in stop_words]
#         return keywords
    
#     def analyze_questions(self, questions_text, syllabus_text):
#         """Analyze questions against syllabus and create mapping"""
#         if not questions_text or not syllabus_text:
#             return None
        
#         self.parse_syllabus(syllabus_text)
        
#         question_patterns = [
#             r'Q\d+[\.\)]\s*([^Q]+?)(?=Q\d+|$)',
#             r'\d+[\.\)]\s*([^0-9]+?)(?=\d+[\.\)]|$)',
#             r'Question\s*\d+\s*[:\-]\s*([^Q]+?)(?=Question|$)',
#         ]
        
#         questions = []
#         for pattern in question_patterns:
#             matches = re.findall(pattern, questions_text, re.IGNORECASE | re.DOTALL)
#             questions.extend([q.strip() for q in matches if q.strip()])
        
#         if not questions:
#             questions = [q.strip() for q in re.split(r'\n\s*\n|\.\s*\n', questions_text) if q.strip()]
        
#         analyzed_questions = []
#         for i, question in enumerate(questions[:20], 1):
#             if len(question) < 10:
#                 continue
                
#             analysis = self.match_question_to_syllabus(question)
            
#             analyzed_questions.append({
#                 "question_number": i,
#                 "question_text": question[:200] + "..." if len(question) > 200 else question,
#                 "matched_chapter": analysis.get("best_match", "Unknown"),
#                 "confidence_score": analysis.get("confidence", 0),
#                 "keywords_found": analysis.get("keywords", []),
#                 "subject": self.subjects[0] if self.subjects else "Not specified",
#             })
        
#         return {
#             "analysis_timestamp": datetime.now().isoformat(),
#             "total_questions_analyzed": len(analyzed_questions),
#             "syllabus_chapters_found": len(self.syllabus_keywords),
#             "subjects_identified": self.subjects,
#             "questions": analyzed_questions,
#             "syllabus_summary": {
#                 "chapters": list(self.syllabus_keywords.keys()),
#                 "total_keywords": sum(len(keywords) for keywords in self.syllabus_keywords.values())
#             }
#         }
    
#     def match_question_to_syllabus(self, question):
#         """Match a question to the most relevant chapter in syllabus"""
#         if not self.syllabus_keywords:
#             return {"best_match": "No syllabus data", "confidence": 0, "keywords": []}
        
#         question_keywords = self.extract_keywords(question)
        
#         chapter_scores = {}
        
#         for chapter, chapter_keywords in self.syllabus_keywords.items():
#             common_keywords = set(question_keywords) & set(chapter_keywords)
            
#             if chapter_keywords:
#                 similarity = len(common_keywords) / len(set(chapter_keywords))
#                 chapter_scores[chapter] = {
#                     "score": similarity,
#                     "common_keywords": list(common_keywords)
#                 }
        
#         if not chapter_scores:
#             return {"best_match": "No match found", "confidence": 0, "keywords": []}
        
#         best_chapter = max(chapter_scores.keys(), key=lambda x: chapter_scores[x]["score"])
#         best_score = chapter_scores[best_chapter]["score"]
        
#         return {
#             "best_match": best_chapter,
#             "confidence": round(best_score * 100, 2),
#             "keywords": chapter_scores[best_chapter]["common_keywords"]
#         }

# def main():
#     # Header
#     st.markdown('<h1 class="main-header">🎓 Jadavpur University Question Analyzer</h1>', unsafe_allow_html=True)
#     st.markdown('<h2 class="sub-header">Preparing a Question Bank Using OCR</h2>', unsafe_allow_html=True)
    
#     # Information box
#     st.markdown("""
#     <div class="info-box">
#         <strong>Instructions:</strong>
#         <ul>
#             <li>Upload your syllabus document (PDF, PNG, JPG, JPEG)</li>
#             <li>Upload your questions document (PDF, PNG, JPG, JPEG)</li>
#             <li>Click "Analyze Questions" to process the documents</li>
#             <li>Download the analysis results in JSON format</li>
#         </ul>
#     </div>
#     """, unsafe_allow_html=True)
    
#     # Initialize analyzer
#     analyzer = QuestionAnalyzer()
    
#     # Upload files
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown('<div class="upload-section">', unsafe_allow_html=True)
#         st.subheader("📄 Upload Syllabus")
#         syllabus_file = st.file_uploader("Choose syllabus file", type=["pdf", "png", "jpg", "jpeg"], help="Upload the syllabus document in PDF or image format")
#         st.markdown('</div>', unsafe_allow_html=True)
    
#     with col2:
#         st.markdown('<div class="upload-section">', unsafe_allow_html=True)
#         st.subheader("❓ Upload Questions")
#         questions_file = st.file_uploader("Choose questions file", type=["pdf", "png", "jpg", "jpeg"], help="Upload the questions document in PDF or image format")
#         st.markdown('</div>', unsafe_allow_html=True)
    
#     # Analyze questions
#     if st.button("🔍 Analyze Questions", type="primary", use_container_width=True):
#         if syllabus_file is not None and questions_file is not None:
#             with st.spinner("Processing documents... This may take a few minutes."):
                
#                 # Extract text from syllabus
#                 st.info("📖 Extracting text from syllabus...")
#                 syllabus_text = analyzer.extract_text_from_file(syllabus_file)
                
#                 if syllabus_text:
#                     st.success("✅ Syllabus text extracted successfully!")
#                     with st.expander("View Extracted Syllabus Text (First 500 characters)"):
#                         st.text(syllabus_text[:500] + "..." if len(syllabus_text) > 500 else syllabus_text)
#                 else:
#                     st.error("❌ Failed to extract text from syllabus")
#                     return
                
#                 # Extract text from questions
#                 st.info("❓ Extracting text from questions...")
#                 questions_text = analyzer.extract_text_from_file(questions_file)
                
#                 if questions_text:
#                     st.success("✅ Questions text extracted successfully!")
#                     with st.expander("View Extracted Questions Text (First 500 characters)"):
#                         st.text(questions_text[:500] + "..." if len(questions_text) > 500 else questions_text)
#                 else:
#                     st.error("❌ Failed to extract text from questions")
#                     return
                
#                 # Analyze questions
#                 st.info("🔍 Analyzing questions against syllabus...")
#                 analysis_result = analyzer.analyze_questions(questions_text, syllabus_text)
                
#                 if analysis_result:
#                     st.success("✅ Analysis completed successfully!")
                    
#                     # Summary display
#                     st.subheader("📊 Analysis Summary")
#                     col1, col2, col3 = st.columns(3)
#                     with col1:
#                         st.metric("Questions Analyzed", analysis_result["total_questions_analyzed"])
#                     with col2:
#                         st.metric("Chapters Found", analysis_result["syllabus_chapters_found"])
#                     with col3:
#                         st.metric("Subjects Identified", len(analysis_result["subjects_identified"]))
                    
#                     # Detailed results display
#                     st.subheader("📋 Question Analysis Results")
#                     for question in analysis_result["questions"]:
#                         with st.expander(f"Question {question['question_number']} (Confidence: {question['confidence_score']}%)"):
#                             st.write(f"**Question:** {question['question_text']}")
#                             st.write(f"**Matched Chapter:** {question['matched_chapter']}")
#                             st.write(f"**Confidence Score:** {question['confidence_score']}%")
#                             st.write(f"**Keywords Found:** {', '.join(question['keywords_found']) if question['keywords_found'] else 'None'}")
                    
#                     # JSON Download
#                     json_string = json.dumps(analysis_result, indent=2)
#                     st.download_button(
#                         label="📥 Download Analysis Results (JSON)",
#                         data=json_string,
#                         file_name=f"question_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
#                         mime="application/json",
#                         use_container_width=True
#                     )
                    
#                 else:
#                     st.error("❌ Failed to analyze questions")
#         else:
#             st.warning("⚠️ Please upload both syllabus and questions files before analyzing.")
    
#     # Footer
#     st.markdown("---")
#     st.markdown("""
#     <div style="text-align: center; color: #666; margin-top: 2rem;">
#         <p>Developed for Final Year Project | Bachelor of Engineering, Information Technology | Jadavpur University</p>
#     </div>
#     """, unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()



