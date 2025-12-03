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
    
    patterns = [
        r"\b\d{1,2}\s*[.,]\s*\d{1,2}\s*[.,]\s*\d{2,4}", # DD.MM.YYYY
        r"\b\d{1,2}\s*[\-/]\s*\d{1,2}\s*[\-/]\s*\d{2,4}", # DD-MM-YYYY
        r"\b\d{4}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}", # YYYY-MM-DD
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}" # Spaced
    ]

    keywords = ['datum', 'dne', 'date', 'time', 'duzp', 'vystaveni']



    
    for i, res in enumerate(data):
        txt_original = res[1]
        if not isinstance(txt_original, str): continue
        txt_lowered = txt_original.lower()

        for pat in patterns:
            if re.search(pat, txt_original):
                print(f"Date Simple Match: {txt_original}")
                return _clean_coords_helper(res[0])
            
    
            
    if any (k in txt_lowered for k in keywords):
            print(f"Date Keyword Match: {txt_original}")
            
            merged_text = ' '
            involved_boxes = []

            search_depth = 3
            
            for offset in range(0, search_depth):
                current_index = i + offset
                if current_index < len(data): break

                item = data[current_index]
                text = item[1]
                box = item[0]

                if not isinstance(text, str): continue

                merged_text += text + ' '
                involved_boxes.append(box)

                for pat in patterns:
                    if re.search(pat, merged_text):
                        print(f"Date Merged Match: {merged_text}")
                        union_box = _get_union_coords(involved_boxes)
                        return _clean_coords_helper(union_box)
    return None


             
def _get_union_coords(boxes_list):
    if not boxes_list:
        return None
    
    min_x  = float('inf')
    min_y  = float('inf')
    max_x  = float('-inf')
    max_y  = float('-inf')

    for box in boxes_list:
        for point in box:
            x, y = point
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y
    return[
        [min_x, min_y],
        [max_x, min_y],
        [max_x, max_y],
        [min_x, max_y]

    ]


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
    
