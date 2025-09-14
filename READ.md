# Jadavpur University Question Analyzer

This project aims to create a question bank by analyzing uploaded syllabus and question papers. It uses Optical Character Recognition (OCR) to convert image-based documents (PDF, PNG, JPG, JPEG) into text and then attempts to match questions to relevant sections of the syllabus.

## Features

*   **OCR Integration:** Converts PDF and image files into searchable text using `pytesseract`.
*   **File Uploads:** Supports uploading syllabus and question papers in PDF, PNG, JPG, JPEG, and JSON formats.
*   **Syllabus Parsing:** Extracts subject codes, names, year/semester, and topics from the syllabus.
*   **Question Matching:** Attempts to match questions to subjects and topics within the syllabus based on text similarity.
*   **JSON Output:** Generates a downloadable JSON file containing each question and its matched syllabus details (subject code, name, year/semester, and the specific topic/line from the syllabus).

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd JadavpurUniversityQuestionAnalyzer
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Tesseract OCR Engine:**
    `pytesseract` is a Python wrapper for Tesseract OCR. You need to install the Tesseract OCR engine separately on your system.

    *   **Windows:** Download and install the `tesseract-ocr-w64-setup-vX.XX.exe` from the [Tesseract GitHub releases page](https://tesseract-ocr.github.io/tessdoc/Downloads.html). Make sure to add Tesseract to your system's PATH during installation or manually.
    *   **macOS:**
        ```bash
        brew install tesseract
        ```
    *   **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt update
        sudo apt install tesseract-ocr
        ```

5.  **Install Poppler (for PDF processing):**
    `pdf2image` requires Poppler to be installed.

    *   **Windows:** Download the Poppler for Windows release (e.g., `poppler-X.XX.X_x86.7z`) from a reliable source like [https://github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases). Extract the contents and add the `bin` directory to your system's PATH.
    *   **macOS:**
        ```bash
        brew install poppler
        ```
    *   **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt install poppler-utils
        ```

## Running the Application

1.  **Start the Flask application:**
    ```bash
    python app.py
    ```

2.  **Access the application:**
    Open your web browser and go to `http://127.0.0.1:5000/`.

## Usage

1.  **Upload Syllabus:** Click "Choose File" next to "Syllabus" and select your syllabus file (PDF, PNG, JPG, JPEG, or JSON).
2.  **Upload Questions:** Click "Choose File" next to "Questions" and select your question paper file (PDF, PNG, JPG, JPEG, or JSON).
3.  **Submit:** Click the "Submit" button.
4.  **Download Result:** A JSON file named `question_bank.json` will be downloaded, containing the analysis of each question and its matched syllabus details.

## Output JSON Format

The downloaded JSON file will have a structure similar to this:

```json
[
  {
    "index": 1,
    "question": "State Bay's Rule. With a Relevant Numerical Example, explain Bay's Rule.",
    "matched_subject_code": "IT/BS/B/T/222",
    "matched_subject_name": "Mathematics for IT-II",
    "matched_year_semester": "2 Year 2 Semester",
    "matched_topic_or_section": "Probability: Introduction to probability : Sample space, Classical, and axiomatic definitions of probability, addition rule and conditional probability, multiplication rule, total probability, Bayes’ Theorem and independence, problems.",
    "matched_syllabus_line": "Introduction to probability : Sample space, Classical,   and axiomatic definitions of probability, addition rule and conditional probability, multiplication  rule, total probability, Bayes’ Theorem and independence, problems.",
    "match_confidence_score": 0.65
  },
  {
    "index": 2,
    "question": "What is the Expected Value and Standard Deviation of X?",
    "matched_subject_code": "IT/BS/B/T/222",
    "matched_subject_name": "Mathematics for IT-II",
    "matched_year_semester": "2 Year 2 Semester",
    "matched_topic_or_section": "Random Variables: Discrete, continuous and mixed random variables, probability mass, probability density and cumulative distribution functions, expectation, variance & Standard Deviation, Chebyshev’s inequality.",
    "matched_syllabus_line": "Discrete, continuous and mixed random variables, probability mass, probability density and cumulative distribution functions,  expectation, variance & Standard Deviation, Chebyshev’s inequality.",
    "match_confidence_score": 0.7
  }
  // ... more questions
]