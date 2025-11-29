import easyocr
import os 
from PIL import Image, ImageOps
import re
from typing import List, Tuple, Any, Optional

class MyOCR:
    def __init__(self):
        print("Inicializace OCR modelu...")
        self.reader = easyocr.Reader(['en', 'cs'], gpu=True)
        self.current_data: Optional[List[Any]] = None
        self.current_image_path = None

    def analyze_image(self, path: str):
        self.current_image_path = path
        
        # 1. Preprocessing
        _ , suffix = os.path.splitext(path)
        is_jpg = suffix.lower() in ['.jpg', '.jpeg']
        path_to_ocr = path

        try:
            # Create temp converted file if needed
            if is_jpg:
                img = Image.open(path)
                img = ImageOps.exif_transpose(img)
                new_path = os.path.splitext(path)[0] + "_converted.png"
                img.save(new_path, format="PNG")
                path_to_ocr = new_path
        except Exception as e:
            print(f"Chyba při přípravě obrázku: {e}")
            return None

        print(f"Zpracovávám OCR pro soubor: {path}")
        
        # 2. Run OCR
        try:
            self.current_data = self.reader.readtext(path_to_ocr)
        except Exception as e:
            print(f"Chyba při čtení textu: {e}")
            self.current_data = None
        finally:
            if path_to_ocr != path and os.path.exists(path_to_ocr):
                os.remove(path_to_ocr)

        return self.current_data

    # --- Methods that use the Standalone Functions below ---
    def get_price(self):
        return ReturnPrice(self.current_data)

    def get_price_coords(self):
        return ReturnPriceCoords(self.current_data)

    def get_date_coords(self):
        return ReturnDateCoords(self.current_data)


# ==========================================
# STANDALONE HELPER FUNCTIONS (Logic Only)
# These run instantly (no AI loading)
# ==========================================

def ReturnPrice(data):
    """Parses the raw OCR list to find the price value."""
    if not data:
        return None
    
    keywords = ['celkem', 'celkcm', 'platbě', 'platbe', 'k platbě', 'k platbe']

    for i, res in enumerate(data):
        txt_original = res[1]
        txt_lowered = txt_original.lower()

        if any(keyword in txt_lowered for keyword in keywords):
            if i + 1 < len(data):
                value = data[i+1][1]
                return value
    return None

def ReturnPriceCoords(data):
    """Parses the raw OCR list to find price coordinates."""
    if not data:
        return None
    
    keywords = ['celkem', 'celkcm', 'platbě', 'platbe', 'k platbě', 'k platbe']
    found_raw_coords = None

    for i, res in enumerate(data):
        txt_lowered = res[1].lower()
        if any(keyword in txt_lowered for keyword in keywords):
            if i + 1 < len(data):
                found_raw_coords = data[i+1][0] # Coords of the value
                break
            else:
                found_raw_coords = res[0] # Coords of the label (fallback)
                break

    return _clean_coords_helper(found_raw_coords)

def ReturnDateCoords(data):
    """Parses the raw OCR list to find date coordinates."""
    if not data:
        return None

    found_raw_coords = None
    pattern = r"\b(\d{1,2})\s*[\.\-]\s*(\d{1,2})\s*[\.\-]\s*(\d{4})\b"
    iso_date_pattern = re.compile(r'\b\d{4}\s*[.,\-/]\s*\d{1,2}\s*[.,\-/]\s*\d{1,2}\b')
    keywords = ['datum', 'dne', 'date', 'time', 'duzp']

    for i, res in enumerate(data):
        box = res[0]
        txt_original = res[1]
        if not isinstance(txt_original, str): continue
        txt_lowered = txt_original.lower()

        is_date_format = re.search(pattern, txt_original) or iso_date_pattern.search(txt_original)
        is_keyword = any(k in txt_lowered for k in keywords)

        if is_keyword or is_date_format:
            found_raw_coords = box
            if is_keyword and (i + 1 < len(data)):
                next_item = data[i+1]
                next_txt = next_item[1]
                if re.search(pattern, next_txt) or iso_date_pattern.search(next_txt):
                    found_raw_coords = next_item[0]
            break
            
    return _clean_coords_helper(found_raw_coords)

def _clean_coords_helper(raw_box):
    """Internal helper to format coordinates."""
    if not raw_box:
        return None
    try:
        cleaned = []
        for point in raw_box:
            cleaned.append([int(point[0]), int(point[1])])
        return cleaned
    except Exception:
        return None