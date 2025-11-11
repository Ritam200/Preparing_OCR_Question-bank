# ai_cleaner.py
import os
import google.generativeai as genai

# Load Gemini API key from environment
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def clean_text_with_ai(raw_text: str) -> str:
    """
    Uses Gemini AI to clean OCR extracted text:
    - Fix spelling errors
    - Remove unnecessary line breaks
    - Keep original meaning intact
    - Format into readable clean text
    """
    if not raw_text or raw_text.strip() == "":
        return ""

    prompt = f"""
    You are a text-cleaning assistant.
    The following text is extracted from an image/PDF using OCR.
    OCR makes spelling mistakes, breaks lines unnecessarily, and may miss punctuation.
    Your task:
    - Correct all spelling/typos
    - Restore proper English grammar
    - Keep the meaning exactly same
    - Remove junk characters and extra line breaks
    - Output only the cleaned text
    OCR Text:
    {raw_text}
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[AI Cleaning Failed] {str(e)}"


# # ai_cleaner.py
# import os
# import google.generativeai as genai

# # Load Gemini API key from env
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# def clean_text_with_ai(raw_text: str) -> str:
#     """
#     Uses Gemini AI to clean OCR extracted text:
#     - Fix spelling errors
#     - Remove unnecessary line breaks
#     - Preserve exact meaning of text
#     """
#     if not raw_text or raw_text.strip() == "":
#         return ""

#     prompt = f"""
#     You are a text-cleaning assistant.
#     The following text is extracted from an image/PDF using OCR.
#     OCR makes spelling mistakes, breaks lines unnecessarily, and may miss punctuation.
#     Your task:
#     - Correct all spelling/typos
#     - Restore proper English grammar
#     - Keep the meaning exactly same
#     - Format as clean readable text
#     Input OCR Text:
#     {raw_text}
#     """

#     try:
#         model = genai.GenerativeModel("gemini-pro")
#         response = model.generate_content(prompt)
#         return response.text.strip()
#     except Exception as e:
#         return f"[AI Cleaning Failed] {str(e)}"
