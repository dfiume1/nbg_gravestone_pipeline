import cv2
import pytesseract
import easyocr
import os
from PIL import Image
import numpy as np
import pandas as pd
    

# Tesseract (Google) - TLDR, doesn't work too well on gravestones
def preprocess_tesseract(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # Histogram Equalization to enhance contrast
    image = cv2.equalizeHist(image)

    # Denoise
    image = cv2.GaussianBlur(image, (3, 3), 0)

    # Adaptive or OTSU thresholding
    _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morphological closing to solidify letters
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    return thresh


def extract_tesseract(image_path):
    try:
        preprocessed = preprocess_tesseract(image_path)
        # Convert back to PIL for pytesseract
        pil_img = Image.fromarray(preprocessed)

        # Sanity check
        cv2.imwrite("../output/debug_output.png", preprocessed)

        # Try different Page Segmentation Mode (PSM)
        custom_config =  r'--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-+ '
        text = pytesseract.image_to_string(pil_img, config=custom_config, lang='eng')
        return text
    
    except Exception as e:
        return f"Error processing {image_path}: {e}"

def tesseract_ocr(folder_path):
    results = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            full_path = os.path.join(folder_path, filename)
            print(f"Processing {filename}...")
            text = extract_tesseract(full_path)
            results.append({"Image Name": filename, "OCR Transcription": text})

    df = pd.DataFrame(results)
    return df 