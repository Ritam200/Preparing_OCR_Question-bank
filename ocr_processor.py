# import pytesseract
# from pdf2image import convert_from_path
# import re

# # Function to convert PDF to images
# def pdf_to_images(pdf_path):
#     return convert_from_path(pdf_path)

# # OCR function
# def extract_text_from_image(image):
#     return pytesseract.image_to_string(image)

# # Extract specific components using Regular Expressions
# def extract_syllabus_info(text):
#     subject_pattern = r'Subject: (.+)'
#     semester_pattern = r'Semester: (.+)'
#     chapter_pattern = r'Chapter: (.+)'

#     subject = re.findall(subject_pattern, text)
#     semester = re.findall(semester_pattern, text)
#     chapter = re.findall(chapter_pattern, text)

#     return {
#         "subjects": subject,
#         "semesters": semester,
#         "chapters": chapter
#     }

# # Main workflow
# def main(pdf_path):
#     images = pdf_to_images(pdf_path)
#     syllabus_text = ''
    
#     for image in images:
#         syllabus_text += extract_text_from_image(image) + '\n'
    
#     extracted_info = extract_syllabus_info(syllabus_text)
#     print(extracted_info)

# # Insert your PDF file path
# main("path_to_your_syllabus.pdf")


