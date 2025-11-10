# Preparing_OCR_Question-bank
# 📘 Preparing a Question Bank using OCR

This project automates the extraction, analysis, and classification of exam questions from scanned documents (PDF or image format) using Optical Character Recognition (OCR) and Natural Language Processing (NLP). It maps each question to the appropriate subject, unit, semester, and course outcome based on the official Jadavpur University IT syllabus. The application provides a simple UI using Streamlit and stores processed data in an SQLite database for future access.

---

## 🎯 Objective

To assist students and faculty in preparing an organized, searchable, and syllabus-aligned digital question bank from existing question papers by using OCR and AI-driven semantic analysis.

---

## 🚀 Key Features

- 📄 *OCR-based question extraction* from PDFs and images  
- ✂ *Question segmentation* using regex and NLP techniques  
- 🧠 *Topic matching* to syllabus using TF-IDF and cosine similarity  
- 🗂 *Structured syllabus mapping* including subject, unit, semester, and course outcomes  
- 💾 *SQLite database* storage of extracted questions and metadata  
- 🖥 *Interactive Streamlit UI* for question upload and real-time categorization  
- 📚 Support for *Jadavpur University IT syllabus (2019 regulation)*

---

## 🧰 Tech Stack

| Component      | Technology             |
|----------------|------------------------|
| OCR Engine     | Tesseract OCR          |
| UI Framework   | Streamlit              |
| PDF/Image      | PyMuPDF, Pillow        |
| Text Processing| NLTK, Regex            |
| Semantic Match | scikit-learn (TF-IDF)  |
| Storage        | json                 |
| Language       | Python 3.x             |

---

## 📁 Project Structure
---

## ⚙ Installation & Setup

### 🔧 Prerequisites
- Python 3.8 or higher
- [Tesseract OCR installed](https://github.com/tesseract-ocr/tesseract)
- pip

### 🧪 Clone & Install Dependencies

```bash
git clone https://github.com/Ritam200/Preparing_OCR_Question-bank
pip install -r requirements.txt
streamlit run app.py
