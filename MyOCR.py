import easyocr
import os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import re
import numpy as np
from typing import List, Any, Optional, Tuple


# ==========================================
# PRECOMPILED REGEX PATTERNS (module-level)
# ==========================================

# --- Price patterns ---
_PRICE_KEYWORDS = re.compile(
    r"(?:celkem|suma|k platbě|spolu k úhradě|k úhradě"
    r"|celková částka|celkový součet"
    r"|total|amount due|amount payable|total amount|sum total"
    r"|grand total|invoice total|balance due|total due|total payable"
    r"|celkem k úhradě|částka k úhradě|částka celkem"
    r"|fakturováno celkem|fakturováno k úhradě)",
    re.IGNORECASE,
)

_PRICE_NUMBER = re.compile(r"\d[\d\s.,]*[.,]\d{2}\b")

_PRICE_FULL = re.compile(
    r"(?:celkem|suma|k platbě|spolu k úhradě|k úhradě"
    r"|celková částka|celkový součet"
    r"|total|amount due|amount payable|total amount|sum total"
    r"|grand total|invoice total|balance due|total due|total payable"
    r"|celkem k úhradě|částka k úhradě|částka celkem"
    r"|fakturováno celkem|fakturováno k úhradě)"
    r".*?(\d[\d\s.,]*[.,]\d{2}\b)",
    re.IGNORECASE,
)

# Lines containing these words are NOT the final total (tax, discount, …)
_PRICE_BLACKLIST = re.compile(
    r"(?:dph|daň|sleva|záloha|tax|vat|discount|subtotal|mezisoučet)",
    re.IGNORECASE,
)

# --- Date patterns (precompiled) ---
_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}\s*[.,]\s*\d{1,2}\s*[.,]\s*\d{2,4}"),   # DD.MM.YYYY
    re.compile(r"\b\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{2,4}"),    # DD-MM-YYYY
    re.compile(r"\b\d{4}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}"),  # YYYY-MM-DD
    re.compile(r"\b\d{1,2}\s+\d{1,2}\s+\d{4}"),                     # Spaced
]

_DATE_KEYWORDS = re.compile(
    r"(?:datum|dne|date|den vystavení|vystaveno|dat\.|day)",
    re.IGNORECASE,
)

# --- Vendor patterns (precompiled) ---
_VENDOR_KNOWN_BRANDS = [
    # Grocery stores and supermarkets
    'tesco', 'kaufland', 'lidl', 'aldi', 'billa', 'albert', 'penny', 'globus',
    'makro', 'coop', 'hruska', 'norma', 'zabka', 'terno', 'tamda', 'flop',
    'jip', 'enapo', 'cba',
    # Drugstores and pharmacies
    'dm drogerie', 'rossmann', 'teta', 'dr.max', 'benu', 'pilulka', 'drmax',
    # Hobby markets, furniture and garden
    'obi', 'hornbach', 'bauhaus', 'baumax', 'uni hobby', 'ikea', 'jysk',
    'xxllutz', 'mobelix', 'siko', 'mountfield', 'hecht', 'decodom', 'asko',
    # Electronics
    'alza', 'czc', 'datart', 'electro world', 'planeo', 'okay', 'smarty',
    'istyle', 'mironet', 'tsbohemia',
    # Clothing and sport
    'decathlon', 'sportisimo', 'h&m', 'c&a', 'zara', 'pepco', 'kik', 'takko',
    'action', 'tedi', 'new yorker', 'deichmann', 'ccc', 'bata', 'humanic',
    'a3 sport', 'intersport', 'alpine pro',
    # Gas stations
    'shell', 'omv', 'benzina', 'orlen', 'mol', 'eurooil', 'tank ono',
    'robin oil', 'km prona',
    # Fast food and cafes
    'mcdonald', 'kfc', 'burger king', 'starbucks', 'costa coffee',
    'bageterie boulevard', 'paul', 'ugova cerstva stava',
]

# Short brands need word-boundary match; long brands can use substring
_VENDOR_SHORT_BRANDS = sorted(
    [k for k in _VENDOR_KNOWN_BRANDS if len(k) <= 3], key=len, reverse=True
)
_VENDOR_LONG_BRANDS = [k for k in _VENDOR_KNOWN_BRANDS if len(k) > 3]

_VENDOR_SHORT_PATTERN: Optional[re.Pattern] = (
    re.compile(
        r'\b(' + '|'.join(re.escape(k) for k in _VENDOR_SHORT_BRANDS) + r')\b',
        re.IGNORECASE,
    )
    if _VENDOR_SHORT_BRANDS
    else None
)

_VENDOR_LEGAL_ENTITIES = ['s.r.o', 'a.s', 'spol', 'spol. s r.o', 'k.s', 'gmbh']

# IČO/DIČ — require "CZ" followed by 8-10 digits (bare "cz" is too loose)
_VENDOR_ICO_DIC = re.compile(
    r"(?:ič\s*:|ičo\s*:|dič\s*:|cz\s*\d{8,10})",
    re.IGNORECASE,
)


# ==========================================
# MyOCR CLASS
# ==========================================

class MyOCR:
    """
    Wrapper class for EasyOCR with image caching and preprocessing.

    Attributes:
        reader (easyocr.Reader): The shared EasyOCR reader instance.
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
        self.current_image_path: Optional[str] = None
        self._cached_image_np: Optional[np.ndarray] = None
        self._cached_image_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Image preprocessing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess_pil(img: Image.Image) -> np.ndarray:
        """
        Convert a PIL image to a preprocessed grayscale numpy array.

        Steps: EXIF fix -> grayscale -> contrast boost -> light sharpen.
        """
        img = ImageOps.exif_transpose(img)
        img = img.convert('L')

        # Boost contrast (helps with faded receipts)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Mild sharpen to help EasyOCR with blurry photos
        img = img.filter(ImageFilter.SHARPEN)

        return np.array(img)

    def _get_image_np(self, path: str) -> Optional[np.ndarray]:
        """Return preprocessed numpy array for *path*, using cache when possible."""
        if self._cached_image_path == path and self._cached_image_np is not None:
            return self._cached_image_np

        if not os.path.exists(path):
            return None

        try:
            img = Image.open(path)
            arr = self._preprocess_pil(img)
            self._cached_image_np = arr
            self._cached_image_path = path
            return arr
        except Exception as e:
            print(f"(-) Chyba při přípravě obrázku: {e}")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_image(self, path: str) -> Optional[List[Any]]:
        """
        Analyze the image at *path* and perform full-page OCR.

        The preprocessed image is cached so that subsequent
        ``get_text_from_region`` calls skip disk I/O.

        Args:
            path: Path to the image file.
        Returns:
            OCR result list or None on failure.
        """
        if not os.path.exists(path):
            print(f"(-) Soubor neexistuje: {path}")
            return None

        self.current_image_path = path
        img_np = self._get_image_np(path)
        if img_np is None:
            return None

        print(f"(+) Zpracovávám OCR pro soubor: {path}")

        try:
            self.current_data = self.reader.readtext(img_np)
        except Exception as e:
            print(f"(-) CHYBA: {e}")
            self.current_data = None

        return self.current_data

    def get_text_from_region(self, path: str, coords: List[List[int]]) -> str:
        """
        Run OCR on a specific region of the image defined by *coords*.

        Uses the cached preprocessed image when available, avoiding
        redundant disk reads and conversions.

        Args:
            path: Path to the image file.
            coords: Bounding polygon [[x1,y1], [x2,y1], [x2,y2], [x1,y2]].
        Returns:
            Recognized text as a single string (empty on failure).
        """
        img_np = self._get_image_np(path)
        if img_np is None:
            return "(-) Soubor neexistuje."

        try:
            h, w = img_np.shape[:2]

            xs = [pt[0] for pt in coords]
            ys = [pt[1] for pt in coords]

            min_x = max(0, min(xs))
            min_y = max(0, min(ys))
            max_x = min(w, max(xs))
            max_y = min(h, max(ys))

            # Skip accidental single-pixel selections
            if (max_x - min_x) < 5 or (max_y - min_y) < 5:
                return ""

            cropped = img_np[min_y:max_y, min_x:max_x]
            results = self.reader.readtext(cropped)
            return _make_string(results)

        except Exception as e:
            print(f"Chyba OCR na výřezu: {e}")
            return ""

    def get_price_coords(self) -> Tuple[Optional[List], str]:
        """Returns (coords, text) tuple for the detected price."""
        return ReturnPrice(self.current_data)

    def get_date(self) -> Tuple[Optional[List], str]:
        """Returns (coords, text) tuple for the detected date."""
        return ReturnDate(self.current_data)

    def get_vendor_coords(self) -> Tuple[Optional[List], str]:
        """Returns (coords, text) tuple for the detected vendor."""
        return ReturnVendor(self.current_data)


# ==========================================
# STANDALONE HELPER FUNCTIONS (Logic Only)
# ==========================================

def ReturnPrice(data: Optional[List]) -> Tuple[Optional[List], str]:
    """
    Find the total price in OCR results.

    Strategy:
      1. Search BOTTOM-UP (totals are near the end of receipts).
      2. Prefer lines where a keyword + price appear together.
      3. Fall back to keyword-only line and grab price from the next 1-2 lines.
      4. Skip lines containing blacklisted words (DPH, sleva, …).
    """
    if not data:
        return None, ""

    # Pass 1: bottom-up scan for keyword+price on the same line
    for i in range(len(data) - 1, -1, -1):
        item = data[i]
        text = item[1]
        if not isinstance(text, str):
            continue

        if _PRICE_BLACKLIST.search(text):
            continue

        match = _PRICE_FULL.search(text)
        if match:
            raw_price = match.group(1)
            if _clean_price_string(raw_price):
                return _clean_coords_helper(item[0]), raw_price

    # Pass 2: keyword on one line, price on the next 1-2 lines
    for i, item in enumerate(data):
        text = item[1]
        if not isinstance(text, str):
            continue

        if _PRICE_BLACKLIST.search(text):
            continue

        if _PRICE_KEYWORDS.search(text):
            for offset in (1, 2):
                if i + offset < len(data):
                    next_text = data[i + offset][1]
                    if not isinstance(next_text, str):
                        continue
                    price_match = _PRICE_NUMBER.search(next_text)
                    if price_match:
                        raw_next = price_match.group(0)
                        if _clean_price_string(raw_next):
                            return _clean_coords_helper(data[i + offset][0]), raw_next

    return None, ""


def ReturnDate(data: Optional[List]) -> Tuple[Optional[List], str]:
    """
    Find the invoice/receipt date in OCR results.

    Strategy:
      1. First pass: look for a date on a line that also contains a date-
         related keyword ("datum", "dne", "date", …).  This avoids picking
         up unrelated dates (print timestamps, expiry dates, etc.).
      2. Second pass: fall back to the first date-like string in the data.
    """
    if not data:
        return None, ""

    # Pass 1: date on a line with a keyword (high confidence)
    for res in data:
        txt = res[1]
        if not isinstance(txt, str):
            continue

        if _DATE_KEYWORDS.search(txt):
            for pat in _DATE_PATTERNS:
                match = pat.search(txt)
                if match:
                    return _clean_coords_helper(res[0]), match.group(0)

    # Pass 2: first date anywhere (fallback)
    for res in data:
        txt = res[1]
        if not isinstance(txt, str):
            continue

        for pat in _DATE_PATTERNS:
            match = pat.search(txt)
            if match:
                return _clean_coords_helper(res[0]), match.group(0)

    return None, ""


def ReturnVendor(data: Optional[List]) -> Tuple[Optional[List], str]:
    """
    Find the vendor/seller name in OCR results.

    Priority order:
      1. Known chain brand names (exact match).
      2. Legal entity suffixes (s.r.o., a.s., spol., gmbh).
      3. Keywords "dodavatel" / "prodávající".
      4. IČO/DIČ line — take the line before it.
    """
    if not data:
        return None, ""

    # --- Priority 1: Known brand names ---
    for res in data:
        txt = res[1]
        if not isinstance(txt, str):
            continue
        txt_lower = txt.lower()

        # Long brands — substring match is safe
        for brand in _VENDOR_LONG_BRANDS:
            if brand in txt_lower:
                return _clean_coords_helper(res[0]), brand

        # Short brands — word-boundary match to avoid false positives
        if _VENDOR_SHORT_PATTERN:
            m = _VENDOR_SHORT_PATTERN.search(txt_lower)
            if m:
                return _clean_coords_helper(res[0]), m.group(1).lower()

    # --- Priority 2: Legal entity suffixes ---
    entity_pattern = _get_legal_entity_pattern()
    for i, item in enumerate(data):
        txt = item[1]
        if not isinstance(txt, str):
            continue

        m = entity_pattern.search(txt)
        if m:
            vendor_candidate = txt[:m.start()].strip()
            # A: vendor name is before the suffix on the same line
            if len(vendor_candidate) > 1:
                return _clean_coords_helper(item[0]), vendor_candidate
            # B: suffix at the start — vendor is on the previous line
            elif i > 0:
                prev = data[i - 1]
                return _clean_coords_helper(prev[0]), prev[1]

    # --- Priority 3: "dodavatel" / "prodávající" keywords ---
    for i, item in enumerate(data):
        txt_lower = item[1].lower() if isinstance(item[1], str) else ""
        if 'dodavatel' in txt_lower or 'prodávající' in txt_lower:
            if len(item[1]) > 12:
                return _clean_coords_helper(item[0]), item[1]
            elif i + 1 < len(data):
                nxt = data[i + 1]
                return _clean_coords_helper(nxt[0]), nxt[1]

    # --- Priority 4: IČO/DIČ — take the preceding line ---
    for i, item in enumerate(data):
        txt = item[1]
        if not isinstance(txt, str):
            continue
        if _VENDOR_ICO_DIC.search(txt):
            if i > 0:
                prev = data[i - 1]
                return _clean_coords_helper(prev[0]), prev[1]

    return None, ""


# ==========================================
# INTERNAL HELPERS
# ==========================================

def _make_string(data: Optional[List]) -> str:
    """Concatenate all recognized text fragments into one string."""
    if not data:
        return ""
    return " ".join(res[1] for res in data if isinstance(res[1], str))


def _clean_coords_helper(raw_box) -> Optional[List[List[int]]]:
    """Convert EasyOCR coordinate tuples to a clean list of [x, y] ints."""
    if not raw_box:
        return None
    try:
        return [[int(pt[0]), int(pt[1])] for pt in raw_box]
    except Exception:
        return None


# Cache the compiled legal-entity regex (built once on first call)
_legal_entity_regex_cache: Optional[re.Pattern] = None


def _get_legal_entity_pattern() -> re.Pattern:
    """Return (and cache) the fuzzy regex for legal entity suffixes."""
    global _legal_entity_regex_cache
    if _legal_entity_regex_cache is None:
        _legal_entity_regex_cache = re.compile(
            _make_fuzzy_entity_regex(_VENDOR_LEGAL_ENTITIES),
            re.IGNORECASE,
        )
    return _legal_entity_regex_cache


def _make_fuzzy_entity_regex(terms: List[str]) -> str:
    """
    Build a fuzzy regex string for legal entity terms.

    Accounts for common OCR misreads (o/0, s/5, i/1/l, etc.)
    and flexible punctuation between characters.
    """
    replacements = {
        'o': '[o0]',
        '0': '[o0]',
        'i': '[i1l|]',
        'l': '[i1l|]',
        '1': '[i1l|]',
        's': '[s5]',
        'z': '[z2]',
        'b': '[b8]',
    }

    parts: List[str] = []
    for term in terms:
        clean = term.lower().replace('.', '').replace(' ', '')
        char_classes = [replacements.get(c, re.escape(c)) for c in clean]
        fuzzy = r'[\.\,\s]*'.join(char_classes) + r'[\.\,\s]*'
        parts.append(fuzzy)

    return r'(?:\s|^)(' + '|'.join(parts) + r').*'


def _clean_price_string(price_str: str) -> Optional[float]:
    """
    Clean a price string and convert it to float.

    Examples: "1 200,50" -> 1200.5, "99.90 Kč" -> 99.9
    """
    if not price_str:
        return None

    # 1. Strip everything except digits, commas, and dots
    clean = re.sub(r"[^\d.,]", "", price_str)

    # 2. Replace decimal comma with dot
    if "," in clean:
        clean = clean.replace(",", ".")

    # 3. Multiple dots: all except the last are thousand separators
    if clean.count(".") > 1:
        parts = clean.split(".")
        clean = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(clean)
    except ValueError:
        return None