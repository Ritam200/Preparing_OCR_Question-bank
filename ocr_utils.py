
# ocr_utils.py
import os
import io
import pytesseract
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_bytes

# ---- Set Tesseract Path (Windows) ----

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ensure_tesseract(path_override=""):
    """
    Check and set Tesseract path.
    Priority:
      1. override from user
      2. env var
      3. common system locations
    """
    if path_override and os.path.exists(path_override):
        pytesseract.pytesseract.tesseract_cmd = path_override
        return pytesseract.pytesseract.tesseract_cmd

    env_path = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        return pytesseract.pytesseract.tesseract_cmd

    common = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for p in common:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return p

    return pytesseract.pytesseract.tesseract_cmd

def preprocess_image(img_cv, use_adaptive=True):
    """
    Preprocess OpenCV image to improve OCR accuracy.
    Steps:
      - Convert grayscale
      - Denoise
      - Adaptive thresholding (or Otsu)
      - Morphological noise removal
    """
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    if use_adaptive:
        processed = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 2
        )
    else:
        _, processed = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

    return processed

def image_bytes_to_text(image_bytes, lang="eng"):
    """Extract text from image bytes (JPG/PNG)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    processed = preprocess_image(img_cv)
    text = pytesseract.image_to_string(processed, lang=lang, config="--oem 3 --psm 6")
    return text

def pdf_bytes_to_text(pdf_bytes, dpi=300, lang="eng", max_pages=None):
    """Extract text from PDF (multi-page)."""
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=dpi)
    except Exception as e:
        raise RuntimeError(f"PDF->image conversion failed: {e}")

    all_text = []
    for i, img in enumerate(pages):
        if max_pages and i >= max_pages:
            break
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        processed = preprocess_image(img_cv)
        text = pytesseract.image_to_string(processed, lang=lang, config="--oem 3 --psm 6")
        all_text.append(text)
    return "\n\n".join(all_text)



# # ocr_utils.py
# import os
# import io
# from PIL import Image, ImageOps
# import pytesseract
# import cv2
# import numpy as np
# from pdf2image import convert_from_bytes
# import tempfile

# def ensure_tesseract(cmd_override=None):
#     """
#     Configure pytesseract.tesseract_cmd. Accepts:
#      - cmd_override: explicit path (string)
#      - else checks TESSERACT_CMD env var
#      - else tries common locations
#     """
#     if cmd_override:
#         pytesseract.pytesseract.tesseract_cmd = cmd_override
#         return pytesseract.pytesseract.tesseract_cmd

#     env_path = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
#     if env_path:
#         pytesseract.pytesseract.tesseract_cmd = env_path
#         return pytesseract.pytesseract.tesseract_cmd

#     common = [
#         r"C:\Program Files\Tesseract-OCR\tesseract.exe",
#         r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
#         "/usr/bin/tesseract",
#         "/usr/local/bin/tesseract",
#     ]
#     for p in common:
#         if os.path.exists(p):
#             pytesseract.pytesseract.tesseract_cmd = p
#             return p
#     # leave default — it may work if in PATH
#     return pytesseract.pytesseract.tesseract_cmd

# def preprocess_pil_image(pil_img, do_threshold=True):
#     """Convert to grayscale, optionally threshold, and return PIL image."""
#     img = pil_img.convert("RGB")
#     arr = np.array(img)
#     gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
#     # bilateral filter to remove noise while keeping edges
#     denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
#     if do_threshold:
#         _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#     else:
#         thresh = denoised
#     # convert back to PIL
#     pil_out = Image.fromarray(thresh)
#     return pil_out

# def image_bytes_to_text(image_bytes):
#     """Accepts image bytes (png/jpg) -> returns OCR text."""
#     try:
#         img = Image.open(io.BytesIO(image_bytes))
#     except Exception:
#         return ""
#     img = preprocess_pil_image(img)
#     # use page segmentation mode 6 (assume block of text)
#     custom_config = r'--oem 3 --psm 6'
#     text = pytesseract.image_to_string(img, config=custom_config, lang='eng')
#     return text

# def pdf_bytes_to_text(pdf_bytes, dpi=300, max_pages=None):
#     """
#     Convert PDF -> images -> OCR each page -> return concatenated text.
#     max_pages: optionally restrict number of pages to process.
#     """
#     texts = []
#     try:
#         pages = convert_from_bytes(pdf_bytes, dpi=dpi)
#     except Exception as e:
#         raise RuntimeError(f"PDF->image conversion failed: {e}")
#     for i, pil_img in enumerate(pages):
#         if max_pages and i >= max_pages:
#             break
#         img = preprocess_pil_image(pil_img)
#         custom_config = r'--oem 3 --psm 6'
#         txt = pytesseract.image_to_string(img, config=custom_config, lang='eng')
#         texts.append(txt)
#     return "\n\n".join(texts)

