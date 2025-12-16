import openpyxl
import os
from datetime import datetime
import re

class ExcelHandler:
    def __init__(self, template_path):
        self.template_path = template_path

    def _clean_price(self, price_text):
        """
        Vyčistí cenu. Zvládne '1.200,50', '1 200.50' i '150 Kč'.
        Vrací float nebo 0.0.
        """
        if not price_text:
            return 0.0
        
        text = str(price_text).strip()
        # Odstraníme měnu a mezery
        text = text.replace("Kč", "").replace("EUR", "").replace(" ", "")
        
        # Nahradíme čárku tečkou, POKUD to vypadá jako desetinná čárka
        # (jednoduchá logika: nahradíme všechny čárky tečkami)
        text = text.replace(",", ".")
        
        # Ochrana: Odstraníme vše, co není číslice nebo tečka (např. překlepy OCR)
        try:
            # Zkusíme převod
            return float(text)
        except ValueError:
            return 0.0

    def _parse_date(self, date_text):
        """
        Agresivní čištění data. Najde datum i v textu ':2.3.2017' nebo '07,05,17'.
        """
        if not date_text:
            return None
            
        text = str(date_text).strip()
        
        # 1. Nahradíme čárky tečkami (častá chyba OCR: 07,05,17 -> 07.05.17)
        text = text.replace(",", ".")
        
        # 2. Hledáme vzor data pomocí regulárního výrazu (Regex)
        # Hledá: 1-2 číslice TEČKA 1-2 číslice TEČKA 2-4 číslice
        match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
        
        if match:
            day, month, year = match.groups()
            
            # Oprava roku na 4 číslice (pokud je "17", uděláme z toho "2017")
            if len(year) == 2:
                year = "20" + year
                
            clean_date_str = f"{day}.{month}.{year}"
            
            try:
                # Převedeme na skutečný objekt data
                return datetime.strptime(clean_date_str, "%d.%m.%Y")
            except ValueError:
                pass 
        
        # Pokud se nepovedlo datum najít, vrátíme None (raději prázdno než nesmyslný text)
        return None

    def add_invoice_entry(self, output_path, data_dict):
        file_to_load = self.template_path
        if os.path.exists(output_path):
            file_to_load = output_path
        elif not os.path.exists(self.template_path):
            print(f"(-) ERROR: Šablona nenalezena: {self.template_path}")
            return False

        try:
            wb = openpyxl.load_workbook(file_to_load)
            
            # Výběr listu
            target_sheet_name = "Příjmy a výdaje"
            ws = None
            if target_sheet_name in wb.sheetnames:
                ws = wb[target_sheet_name]
            else:
                ws = wb.active # Fallback

            # Ochrana proti None (fix pro Pylance error z vašeho obrázku)
            if ws is None: 
                print("(-) Chyba: List nelze načíst.")
                return False

            # --- Najít první volný řádek od 79 ---
            row = 79
            # Používáme ws[f'C{row}'] místo ws.cell(...) aby Pylance nehlásil chybu s MergedCell
            while ws[f'C{row}'].value is not None:
                row += 1
            
            print(f"(-) Zapisuji na řádek: {row}")

            # --- 1. CENA (Sloupec C) ---
            if data_dict.get('price'):
                val_price = self._clean_price(data_dict['price'])
                cell = ws[f'C{row}']
                cell.value = val_price
                
                # Vynutíme formát měny, pokud tam není
                if cell.number_format == 'General':
                    cell.number_format = '#,##0.00 "Kč"'

            # --- 2. DATUM (Sloupec E) ---
            if data_dict.get('date'):
                val_date = self._parse_date(data_dict['date'])
                cell = ws[f'E{row}']
                
                if val_date:
                    cell.value = val_date
                    cell.number_format = 'd.m.yyyy' # Excel si to naformátuje správně
                else:
                    # Pokud se datum nepovedlo rozluštit, dáme tam původní text, ale označíme ho
                    # cell.value = str(data_dict['date']) # Volitelné
                    pass

            # --- 3. NÁZEV SOUBORU (Sloupec F) ---
            if data_dict.get('filename'):
                ws[f'F{row}'] = data_dict['filename']
                
            wb.save(output_path)
            return True

        except Exception as e:
            print(f"Chyba ExcelHandler: {e}")
            return False