import easyocr
import os 
from PIL import Image, ImageOps
import re
import numpy as np
from typing import List, Tuple, Any, Optional

class MyOCR:
    """
    Wrapper class for EasyOCR with additional functionalities.
    
    Attributes:
        reader (easyocr.Reader): The EasyOCR reader instance.
        current_data (list): The last OCR result data.
        current_image_path (str): The path of the last processed image.
    """
    _reader = None

    def __init__(self):
        if MyOCR._reader is None:
            print("Inicializace OCR modelu...")
            MyOCR._reader = easyocr.Reader(['en', 'cs'], gpu=True)


        self.reader = MyOCR._reader
        self.current_data: Optional[List[Any]] = None
        self.current_image_path = None

    def analyze_image(self, path: str):
        """
        Analyzes the image at the given path and performs OCR.
        Args:
            path (str): Path to the image file.
        Returns:
            List[Any] | None: OCR result data."""
        if not os.path.exists(path):
            print(f"(-)File does not exist: {path}")
            return None
        
        self.current_image_path = path
        
        # 1. Preprocess Image if needed
        try:
            img  = Image.open(path)
            ig = ImageOps.exif_transpose(img)

            if img.format != 'PNG':
                new_path = os.path.splitext(path)[0] + "_converted.png"
                img.save(new_path, format='PNG')
                path_to_ocr = new_path
            else:
                path_to_ocr = path
        except Exception as e:
            print(f"(-)Error while preparing image: {e}")
            return None

        print(f"Processing OCR for file: {path}")
        
        # 2. Run OCR
        try:
            self.current_data = self.reader.readtext(path_to_ocr)
        except Exception as e:
            print(f"Chyba při čtení textu: {e}")
            self.current_data = None
        finally:
            # 3. Clean up temporary file if created
            if path_to_ocr != path and os.path.exists(path_to_ocr):
                os.remove(path_to_ocr)

        return self.current_data
    
    def get_text_from_region(self, path: str, coords: List[List[int]]) -> str:
        """
        Provede OCR pouze na vybraném výřezu obrázku definovaném souřadnicemi.
        
        Args:
            path (str): Path to the image file.
            coords (list): List of points [[x1, y1], [x2, y1], [x2, y2], [x1, y2]] 
                           or just a bounding box.
        
        Returns:
            str: Found text joined into a single string.
        """
        if not os.path.exists(path):
            return "(-)File does not exist."

        try:
            # 1. Load Image
            img = Image.open(path)
            img = ImageOps.exif_transpose(img) # Rotate according to EXIF data
            
            # 2. Calculate Bounding Box (min_x, min_y, max_x, max_y)
            # This ensures it works whether you send 4 points (polygon) or just 2 points (bounding box)
            xs = [point[0] for point in coords]
            ys = [point[1] for point in coords]
            
            min_x = max(0, min(xs))
            min_y = max(0, min(ys))
            max_x = min(img.width, max(xs))
            max_y = min(img.height, max(ys))

            # If selection is too small (e.g., accidentally clicked), return empty
            if (max_x - min_x) < 5 or (max_y - min_y) < 5:
                return ""

            # 3. Crop Image to the defined region
            cropped_img = img.crop((min_x, min_y, max_x, max_y))

            # 4. Convert for EasyOCR (PIL -> Numpy Array)
            img_np = np.array(cropped_img)

            # 5. Run OCR on the cropped image
            # detail=0 returns a list of strings without coordinates and confidence score
            results = self.reader.readtext(img_np, detail=0)
            
            # Join found lines into a single text
            return " ".join([str(x) for x in results])
        except Exception as e:
            print(f"Error during OCR on the cropped region: {e}")
            return ""

    # --- Methods that use the Standalone Functions below ---
    def get_price(self):
        """Returns the price value from the current OCR data."""
        return ReturnPrice(self.current_data)
    
    def get_price_coords(self):
        """Returns the price coordinates from the current OCR data."""
        return ReturnPriceCoords(self.current_data)

    def get_date_coords(self):
        """Returns the date coordinates from the current OCR data."""
        return ReturnDateCoords(self.current_data)

    def get_date(self):
        """Returns the date value from the current OCR data."""
        return ReturnDate(self.current_data)

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
    
    print(_make_string(data))

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


        for pat in patterns:
            if re.search(pat, txt_original):
                print(f"Date Simple Match: {txt_original}")
                return _clean_coords_helper(res[0])
            
    return None

def ReturnDate(data):
    """Parses the raw OCR list to find date value."""
    if not data:
        return None
    
    patterns = [
        r"\b\d{1,2}\s*[.,]\s*\d{1,2}\s*[.,]\s*\d{2,4}", # DD.MM.YYYY
        r"\b\d{1,2}\s*[\-/]\s*\d{1,2}\s*[\-/]\s*\d{2,4}", # DD-MM-YYYY
        r"\b\d{4}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}", # YYYY-MM-DD
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}" # Spaced
    ]

    text_data = _make_string(data)
    for pat in patterns:
        match = re.search(pat, text_data)
        if match:
            return match.group(0)
        
    return None

def _make_string(data):
    """Internal helper to concatenate all recognized text."""
    if not data:
        return ""
    texts = [res[1] for res in data if isinstance(res[1], str)]
    return '.'.join(texts)


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
    
