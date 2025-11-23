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


def ReturnData(result):

    all_words = []
    if result is None or len(result) == 0:
        return None
    
    for i, res in enumerate(result):
        txt_original = res[1]
        txt_lowered = txt_original.lower()
        all_words.append(txt_lowered)
        print(f"Slovo {i}: {txt_original} (lowered: {txt_lowered})")

        if 'celkem' in txt_lowered or 'celkcm' in txt_lowered or 'platbě' in txt_lowered or 'platbe' in txt_lowered or 'k platbě' in txt_lowered or 'k platbe' in txt_lowered:
            if i >0:
                value = result[i+1][1]
                print(f"Nalezeno hledané Heslo na pozici {i}, vracím následující hodnotu: {value}")
                return value
            else:
                print("Nalezeno hledané Heslo na poslední pozici, není nadcházející hodnota k vrácení.")
                return None
    return all_words