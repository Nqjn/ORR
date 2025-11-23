import easyocr
import os 
from PIL import Image, ImageOps

def ReadData(path: str):
    _ , suffix = os.path.splitext(path)
    is_jpg = suffix.lower() in ['.jpg', '.jpeg']

    img = Image.open(path)

    try:
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        print(f"Chyba při úpravě orientace obrázku: {e}")

    new_path = os.path.splitext(path)[0] + "_converted.png" if is_jpg else path
    img.save(new_path, format="PNG" if is_jpg else img.format)
        
    path_to_ocr = new_path

    print(f"Zpracovávám OCR pro soubor: {path}")
    reader = easyocr.Reader(['en', 'cs'], gpu=True)
    result = reader.readtext(path_to_ocr)
    os.remove(path_to_ocr) if path_to_ocr.endswith("_converted.png") else None
    return result


def ReturnPrice(result):

    all_words = []
    if result is None or len(result) == 0:
        return None
    
    for i, res in enumerate(result):
        txt_original = res[1]
        txt_lowered = txt_original.lower()
        all_words.append(txt_lowered)
        print(f"Slovo {i}: {txt_original} (lowered: {txt_lowered})")

        keywords = ['celkem', 'celkcm', 'platbě', 'platbe', 'k platbě', 'k platbe']
        if any(keyword in txt_lowered for keyword in keywords):
            if i +1 < len(result):
                value = result[i+1][1]
                print(f"Nalezeno hledané Heslo na pozici {i}, vracím následující hodnotu: {value}")
                return value
            else:
                print("Nalezeno hledané Heslo na poslední pozici, není nadcházející hodnota k vrácení.")
                return None
    return all_words

def ReturnPriceCoords(result):
    cleaned_coords = []
    found_raw_coords =  None
    
    keywords = ['celkem', 'celkcm', 'platbě', 'platbe', 'k platbě', 'k platbe']

    if result is None or len(result) == 0:
        return None
    
    for i, res in enumerate(result):
        txt_original = res[1]
        txt_lowered = txt_original.lower()
        


        if any(keyword in txt_lowered for keyword in keywords):
            if i +1 < len(result):
                found_raw_coords = result[i+1][0]
                print(f"Nalezeno heslo '{res[1]}', beru souřadnice následující ceny.")
                break
            else:
                found_raw_coords = res  [0]
                break

    if found_raw_coords:
        for coord in found_raw_coords:
            cleaned_coord = [int(coord[0]), int(coord[1])]
            cleaned_coords.append(cleaned_coord)
        return cleaned_coord
    else:
        return None