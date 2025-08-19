import cv2
import pytesseract
import easyocr
import os
from PIL import Image
import numpy as np
import pandas as pd

# Trying out EasyOCR

OUTPUT_FOLDER = "../data/output/"

def preprocess_for_easyocr(image_path):
    
    # Grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr0.png"
    cv2.imwrite(debug_path, img)

    # Contrast
    img_eq = cv2.equalizeHist(img)
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr1.png"
    cv2.imwrite(debug_path, img_eq)

    # Gaussian Blur
    img_blur = cv2.GaussianBlur(img_eq, (3, 3), 0)
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr2.png"
    cv2.imwrite(debug_path, img_blur)

    # Thresholding 
    _, thresh = cv2.threshold(img_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr3.png"
    cv2.imwrite(debug_path, thresh)

    # Morphological Closing 
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr4.png"
    cv2.imwrite(debug_path, morph)

    # Invert
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr5_inverted.png"
    inverted = cv2.bitwise_not(morph)
    cv2.imwrite(debug_path, inverted)

    # Auto-cropping the largest contour region (likely to be text)
    contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Find bounding box around all contours
        x_min, y_min, x_max, y_max = np.inf, np.inf, 0, 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x + w)
            y_max = max(y_max, y + h)
        
        # Apply crop with some padding (optional)
        padding = 10
        x_min = max(x_min - padding, 0)
        y_min = max(y_min - padding, 0)
        x_max = min(x_max + padding, inverted.shape[1])
        y_max = min(y_max + padding, inverted.shape[0])

        cropped = inverted[y_min:y_max, x_min:x_max]
    else:
        cropped = inverted  # fallback

    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr6_cropped.png"
    cv2.imwrite(debug_path, cropped)

    return cropped


def easy_ocr(image_path, confidence_threshold):
    # Preprocess the image
    preprocessed = preprocess_for_easyocr(image_path)

    # Save or display preprocessed result for sanity check
    debug_path = OUTPUT_FOLDER + "preprocessed_easyocr.png"
    cv2.imwrite(debug_path, preprocessed)

    # Run EasyOCR on the preprocessed image
    reader = easyocr.Reader(['en'], gpu=True)
    result = reader.readtext(preprocessed)

    # Extract and print detected text
    extracted_text = []
    print("\n🔎 OCR Output:")
    for detection in result:
        bbox, text, conf = detection
        
        if conf >= confidence_threshold:
            print(f"✅ {text} (Confidence: {conf:.2f})")
            extracted_text.append(text)
        else:
            print(f"❌ {text} (Confidence: {conf:.2f}) - REJECTED")
    
    return " ".join(extracted_text)
    


def process_easy_ocr(folder_path):
    results = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            full_path = os.path.join(folder_path, filename)
            print(f"Processing {filename}...")
            text = easy_ocr(full_path, 0.1)
            results.append({"Image Name": filename, "OCR Transcription": text})

    df = pd.DataFrame(results)
    return df 
    

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