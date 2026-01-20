import easyocr
import os 
from PIL import Image, ImageOps
import re
import numpy as np
from typing import List, Any, Optional

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
            img = ImageOps.exif_transpose(img)
            img = img.convert('L') # Grayscale

            if img.format != 'PNG':
                new_path = os.path.splitext(path)[0] + "_converted.png"
                img.save(new_path, format='PNG')
                path_to_ocr = new_path
            else:
                path_to_ocr = path
        except Exception as e:
            print(f"(-)Error while preparing image: {e}")
            return None

        print(f"(+)Processing OCR for file: {path}")
        
        # 2. Run OCR
        try:
            self.current_data = self.reader.readtext(path_to_ocr)
        except Exception as e:
            print(f"(-)ERROR: {e}")
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

            img = img.convert('L') # Convert to grayscale
            
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
            results = self.reader.readtext(img_np,)
            return _make_string(results)
            
            # Join found lines into a single text
        #     return "".join([str(x) for x in results])
        except Exception as e:
            print(f"Error during OCR on the cropped region: {e}")
            return ""
    
    def get_price_coords(self):
        """Returns the price coordinates from the current OCR data."""
        return ReturnPrice(self.current_data)

    def get_date(self):
        """Returns (coords, text) from the current OCR data."""
        return ReturnDate(self.current_data)
    
    def get_vendor_coords(self):
        """Returns the vendor coordinates from the current OCR data."""
        return ReturnVendor(self.current_data)
    


# ==========================================
# STANDALONE HELPER FUNCTIONS (Logic Only)
# ==========================================

def ReturnPrice(data):
    """Parses the raw OCR list to find price coordinates."""
    if not data:
        return None, ""
    


    
    keywords = r"(?:celkem|suma|k platbě|spolu|spolu k úhradě|k úhradě|celková částka|celkový součet|total|amount due|amount payable|total amount|sum total|grand total|invoice total|balance due|total due|total payable|total amount due|total amount payable|celkem k úhradě|částka k úhradě|částka celkem|fakturováno celkem|fakturováno k úhradě)"
    price_pattern = r"\d[\d\s.,]*\d"

    full_pattern = f"(?i){keywords}.*?({price_pattern})"

    keywords_only_pattern = re.compile(f"(?i){keywords}")

    for i, item in enumerate(data):
        coords = item[0]
        text_original = item[1]

        if not isinstance(text_original, str): continue

        match = re.search(full_pattern, text_original)
        if match:
            raw_price = match.group(1)
            final_price = _clean_price_string(raw_price)

            if final_price:
                # Found full match with price
                return _clean_coords_helper(coords), str(final_price)
            
        # If only keywords matched, look at next line for price    
        if keywords_only_pattern.search(text_original):
            if i +1 < len(data):
                next_item = data[i+1]
                next_text = next_item[1]

                if any (char.isdigit() for char in next_text):

                    cleaned_next = _clean_price_string(next_text)
                    if cleaned_next:
                        return _clean_coords_helper(next_item[0]), str(cleaned_next)
    return None, ""


def ReturnDate(data):
    """Parses the raw OCR list to find date coordinates."""
    if not data:
        return None, ""
    
    print(_make_string(data))

    
    patterns = [
        r"\b\d{1,2}\s*[.,]\s*\d{1,2}\s*[.,]\s*\d{2,4}", # DD.MM.YYYY
        r"\b\d{1,2}\s*[\-/]\s*\d{1,2}\s*[\-/]\s*\d{2,4}", # DD-MM-YYYY
        r"\b\d{4}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}", # YYYY-MM-DD
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}" # Spaced
    ]

    
    for i, res in enumerate(data):
        txt_original = res[1]
        if not isinstance(txt_original, str): continue

        for pat in patterns:
            match = re.search(pat, txt_original)
            if match:
                found_text = match.group(0)
                print(f"Date Simple Match: {found_text}, Original: {txt_original}")
                return _clean_coords_helper(res[0]), found_text
            
    return None, ""


def ReturnVendor(data):
    if not data:
        return None, ""
        
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

    # 1. Priorita: Přímé shody s klíčovými slovy (známé řetězce)

    strict_keywords = [k for k in keywords if len(k) <= 3]
    lossy_keywords = [k for k in keywords if len(k) > 3]

    strict_pattern = None
    if strict_keywords:
        strict_sorted = sorted(strict_keywords, key=len, reverse=True)
        strict_pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in strict_sorted) + r')\b', re.IGNORECASE)

    for i, res in enumerate(data):
        txt_original = res[1]
        if not isinstance(txt_original, str): continue
        txt_lower = txt_original.lower()

        # Long words 
        for brand in lossy_keywords:
            if brand in txt_lower:
                return _clean_coords_helper(res[0]), brand
        
        # Short words - strict match
        if strict_pattern:
            match = strict_pattern.search(txt_lower)
            if match:
                normalized_brand = match.group(1).lower()
                return _clean_coords_helper(res[0]), normalized_brand
    
        
    # 2. Priorita: Hledání právních forem (s.r.o., a.s., spol., etc.)
    pattern_str = make_fuzzy_entity_regex(legal_entities)
    pattern = re.compile(pattern_str, re.IGNORECASE)

    for i in range(len(data)):
        item = data[i]
        text_original = item[1] # Celý text řádku, např: "BILLA BILLA SPOL , S R.o ..."
        
        # Použijeme search, který vrátí "match object"
        match = pattern.search(text_original)
        
        if match:
            # Získáme index, kde začíná nalezené klíčové slovo (např. kde začíná "SPOL")
            start_index = match.start()
            
            # Vezmeme text PŘED tímto indexem
            vendor_candidate = text_original[:start_index].strip()
            
            # KROK A: Je před 's.r.o.' nějaký text na stejném řádku?
            if len(vendor_candidate) > 1: # >1 aby to nebyl jen šum
                
                return  _clean_coords_helper(item[0]), vendor_candidate 
                
            # KROK B: Na řádku před s.r.o nic není (s.r.o je na začátku řádku)
            elif i > 0:
                # Vrátíme předchozí řádek ze seznamu
                return _clean_coords_helper(data[i-1][0]), data[i-1][1]

    # 3. Priorita: Klíčové slovo "Dodavatel"
    for i, item in enumerate(data):
        text_lower = item[1].lower()
        if 'dodavatel' in text_lower or 'prodávající' in text_lower:
            # Pokud řádek obsahuje víc textu (např. "Dodavatel: Tesco a.s."), vrátíme ho
            if len(item[1]) > 12: 
                return _clean_coords_helper(item[0]), item[1]
            # Pokud je to jen nadpis "Dodavatel:", vrátíme NÁSLEDUJÍCÍ řádek
            elif i + 1 < len(data):
                return _clean_coords_helper(data[i+1][0]), data[i+1][1]


    # 4. Priorita: Najít IČO/DIČ a vzít řádek PŘED ním
    for i, item in enumerate(data):
        text_lower = item[1].lower()
        # Hledáme patterny IČ/DIČ
        if 'ič:' in text_lower or 'ičo:' in text_lower or 'dič:' in text_lower or 'cz' in text_lower:
            # Pokud nejsme na úplně prvním řádku, vrátíme ten předchozí
            if i > 0:
                return _clean_coords_helper(data[i-1][0]), data[i-1][1]

    return None, ""
    
def _make_string(data):
    """Internal helper to concatenate all recognized text."""
    if not data:
        return ""
    texts = [res[1] for res in data if isinstance(res[1], str)]
    return "".join(texts)


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

def make_fuzzy_entity_regex(terms):
    """
    Helpers to create fuzzy regex patterns for legal entity terms.
    Args:
        terms (list): List of legal entity terms (e.g., ['s.r.o', 'a.s']).
    Returns:
        str: Compiled regex pattern string.
    """
    replacements = {
        'o': '[o0]',       # Písmeno o a nula
        '0': '[o0]',       
        'i': '[i1l|]',     # i, jedna, malé L, svislítko
        'l': '[i1l|]',
        '1': '[i1l|]',
        's': '[s5]',       # s a pětka
        'z': '[z2]',       # z a dvojka
        'b': '[b8]',       # b a osmička
    }

    patterns = []

    for term in terms:
        clean = term.lower().replace('.', '').replace(' ', '')

        char_pattern = []
        for char in clean:
            char_pattern.append(replacements.get(char, char))
            
        fuzzy_pattern = r'[\.\,\s]*'.join(char_pattern) + r'[\.\,\s]*'
        patterns.append(fuzzy_pattern)
    return r'(?:\s|^)(' + '|'.join(patterns) + r').*'

def _clean_price_string(price_str: str) -> Optional[float]:
    """
    Pomocná funkce pro čištění stringu ceny.
    Převede "1 200,50" -> 1200.5
    """
    if not price_str:
        return None

    # 1. Odstraníme vše kromě číslic, čárky a tečky
    # (Odstraní to 'Kč', 'EUR', písmena, znaky měny)
    clean = re.sub(r"[^\d.,]", "", price_str)
    
    # 2. Nahrazení desetinné čárky tečkou
    if "," in clean:
        clean = clean.replace(",", ".")
    
    # 3. Ošetření více teček (např. 1.200.50 -> 1200.50)
    # Logika: Všechny tečky kromě té poslední jsou oddělovače tisíců -> smazat
    if clean.count(".") > 1:
        parts = clean.split(".")
        # Spojíme vše kromě posledního dílu, pak přidáme poslední díl s tečkou
        clean = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(clean)
    except ValueError:
        return None
    