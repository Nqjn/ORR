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
            return "".join([str(x) for x in results])
        except Exception as e:
            print(f"Error during OCR on the cropped region: {e}")
            return ""
    
    def get_price_coords(self):
        """Returns the price coordinates from the current OCR data."""
        return ReturnPriceCoords(self.current_data)

    def get_date_coords(self):
        """Returns the date coordinates from the current OCR data."""
        return ReturnDateCoords(self.current_data)
    
    def get_vendor_coords(self):
        """Returns the vendor coordinates from the current OCR data."""
        return ReturnVendorCoords(self.current_data)
    


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


def _make_string(data):
    """Internal helper to concatenate all recognized text."""
    if not data:
        return ""
    texts = [res[1] for res in data if isinstance(res[1], str)]
    return " ".join(texts)


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

# --- 1. Generátor chytrého regexu (ten už máme) ---
def make_fuzzy_entity_regex(terms):
    patterns = []
    for term in terms:
        clean = term.replace('.', '').replace(' ', '')
        fuzzy_pattern = r'[\.\,\s]*'.join(list(clean)) + r'[\.\,\s]*'
        patterns.append(fuzzy_pattern)
    return r'(?:\s|^)(' + '|'.join(patterns) + r').*'

def ReturnVendorCoords(data):
    if not data:
        return None
        
    legal_entities = ['s.r.o', 'a.s', 'spol', 'spol. s r.o', 'k.s', 'gmbh']

    keywords = [
    # Potraviny a supermarkety
    'tesco', 'kaufland', 'lidl', 'aldi', 'billa', 'albert', 'penny', 'globus', 
    'makro', 'coop', 'hruska', 'norma', 'zabka', 'terno', 'tamda', 'flop', 
    'jip', 'enapo', 'cba', 

    # Drogerie a lékárny
    'dm drogerie', 'rossmann', 'teta', 'dr.max', 'benu', 'pilulka', 'drmax',

    # Hobby markety, nábytek a zahrada
    'obi', 'hornbach', 'bauhaus', 'baumax', 'uni hobby', 'ikea', 'jysk', 
    'xxllutz', 'mobelix', 'siko', 'mountfield', 'hecht', 'decodom', 'asko',

    # Elektro
    'alza', 'czc', 'datart', 'electro world', 'planeo', 'okay', 'smarty', 
    'istyle', 'mironet', 'tsbohemia', 

    # Oblečení, obuv a sport
    'decathlon', 'sportisimo', 'h&m', 'c&a', 'zara', 'pepco', 'kik', 'takko', 
    'action', 'tedi', 'new yorker', 'deichmann', 'ccc', 'bata', 'humanic', 
    'a3 sport', 'intersport', 'alpine pro',

    # Čerpací stanice (často na účtenkách)
    'shell', 'omv', 'benzina', 'orlen', 'mol', 'eurooil', 'tank ono', 
    'robin oil', 'km prona',

    # Fast food a kavárny
    'mcdonald', 'kfc', 'burger king', 'starbucks', 'costa coffee', 
    'bageterie boulevard', 'paul', 'ugova cerstva stava'
    ]
    
    for i in range(len(data)):
        item = data[i]
        text_original = item[1] 
        text_lower = text_original.lower()

        if any(entity in text_lower for entity in keywords):
            return _clean_coords_helper(item[0])

    # Přidáme 'spol' samostatně, protože v OCR se často 's.r.o' oddělí
    pattern_str = make_fuzzy_entity_regex(legal_entities)
    regex = re.compile(pattern_str, re.IGNORECASE)

    for i in range(len(data)):
        item = data[i]
        text_original = item[1] # Celý text řádku, např: "BILLA BILLA SPOL , S R.o ..."
        
        # Použijeme search, který vrátí "match object"
        match = regex.search(text_original)
        
        if match:
            # Získáme index, kde začíná nalezené klíčové slovo (např. kde začíná "SPOL")
            start_index = match.start()
            
            # Vezmeme text PŘED tímto indexem
            vendor_candidate = text_original[:start_index].strip()
            
            # KROK A: Je před 's.r.o.' nějaký text na stejném řádku?
            if len(vendor_candidate) > 1: # >1 aby to nebyl jen šum
                
                return vendor_candidate 
                
            # KROK B: Na řádku před s.r.o nic není (s.r.o je na začátku řádku)
            elif i > 0:
                # Vrátíme předchozí řádek ze seznamu
                return _clean_coords_helper(data[i-1][0])
                
    return None



    # 2. Priorita: Klíčové slovo "Dodavatel"
    for i, item in enumerate(data):
        text_lower = item[1].lower()
        if 'dodavatel' in text_lower or 'prodávající' in text_lower:
            # Pokud řádek obsahuje víc textu (např. "Dodavatel: Tesco a.s."), vrátíme ho
            if len(item[1]) > 12: 
                return _clean_coords_helper(item[0])
            # Pokud je to jen nadpis "Dodavatel:", vrátíme NÁSLEDUJÍCÍ řádek
            elif i + 1 < len(data):
                return _clean_coords_helper(data[i+1][0])

    # 3. Priorita: Najít IČO/DIČ a vzít řádek PŘED ním
    # (Firmy často píší Název a hned pod to IČO)
    for i, item in enumerate(data):
        text_lower = item[1].lower()
        # Hledáme patterny IČ/DIČ
        if 'ič:' in text_lower or 'ičo:' in text_lower or 'dič:' in text_lower or 'cz' in text_lower:
            # Pokud nejsme na úplně prvním řádku, vrátíme ten předchozí
            if i > 0:
                return _clean_coords_helper(data[i-1][0])

    # 4. Fallback: Pokud jsme nic nenašli, vrátíme první nalezený text, 
    # který vypadá jako název (není číslo a je dost dlouhý), ale to je riskantní.
    # Raději vrátíme None a necháme uživatele vybrat ručně.
    return None
    
