import openpyxl
import os
from datetime import datetime
import re
# NEW: Import Cell to fix the Pylance "MergedCell" error
from openpyxl.cell.cell import Cell 

class ExcelHandler:
    def __init__(self, template_path):
        self.template_path = template_path

    def _clean_price(self, price_text):
        """Vyčistí cenu na float. Zvládne '1 200,50 Kč', '1.200', atd."""
        if not price_text: return 0.0
        text = str(price_text).strip()
        # Odstranit měnu a mezery
        text = text.replace("Kč", "").replace("EUR", "").replace("€", "").replace(" ", "")
        # Čárky na tečky
        text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _parse_date(self, date_text):
        """
        Najde datum pomocí Regexu. 
        Opraví chyby jako ':2.3.2017' nebo '07,05,17' nebo čas navíc.
        """
        if not date_text: return None
        text = str(date_text).strip()
        # Nahradit čárky tečkami (častá chyba OCR)
        text = text.replace(",", ".")
        
        # Regex: Hledá D.M.RRRR nebo D.M.RR (např. 1.2.2023)
        # Ignoruje vše okolo (dvojtečky, čas atd.)
        match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
        
        if match:
            d, m, y = match.groups()
            # Oprava roku na 4 místa (17 -> 2017)
            if len(y) == 2: y = "20" + y 
            
            try:
                return datetime.strptime(f"{d}.{m}.{y}", "%d.%m.%Y")
            except ValueError: 
                pass
        return None

    def add_invoice_entry(self, output_path, data_dict):
        # 1. Načtení sešitu
        file_to_load = self.template_path
        if os.path.exists(output_path):
            file_to_load = output_path
        elif not os.path.exists(self.template_path):
            print(f"(!) CHYBA: Nenalezena šablona: {self.template_path}")
            return False

        try:
            wb = openpyxl.load_workbook(file_to_load)
            
            # 2. Výběr listu (Bezpečně)
            sheet_name = "Příjmy a výdaje"
            ws = None
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                ws = wb.active # Fallback

            # Ochrana: Pokud se list nenačetl, skončíme
            if ws is None:
                print("(!) CHYBA: Excel nemá žádný aktivní list.")
                return False

            # 3. Hledání prvního volného řádku
            row = 79
            # Použijeme cyklus s ochranou
            while True:
                # cell(row, col) vrací objekt buňky. .value je hodnota.
                val = ws.cell(row=row, column=3).value
                if val is None:
                    break
                row += 1
            
            print(f"   (Zapisuji na řádek {row})")

            # 4. Zápis dat
            
            # -- CENA (Sloupec 3) --
            if data_dict.get('price'):
                val_price = self._clean_price(data_dict['price'])
                c_cell = ws.cell(row=row, column=3)
                
                # FIX: Ověříme, že buňka není MergedCell (sloučená), jinak Pylance hlásí chybu
                if isinstance(c_cell, Cell):
                    c_cell.value = val_price
                    c_cell.number_format = '#,##0.00 "Kč"'
                else:
                    print(f"(!) POZOR: Buňka {row},3 je sloučená. Nelze zapsat cenu.")

            # -- DATUM (Sloupec 5) --
            if data_dict.get('date'):
                val_date = self._parse_date(data_dict['date'])
                e_cell = ws.cell(row=row, column=5)
                
                # FIX: Ověříme typ buňky
                if isinstance(e_cell, Cell):
                    if val_date:
                        e_cell.value = val_date
                        e_cell.number_format = 'd.m.yyyy'
                    else:
                        # Pokud převod selhal, zapíšeme text
                        e_cell.value = str(data_dict['date'])
                else:
                    print(f"(!) POZOR: Buňka {row},5 je sloučená. Nelze zapsat datum.")

            # -- NÁZEV SOUBORU (Sloupec 6) --
            if data_dict.get('filename'):
                f_cell = ws.cell(row=row, column=6)
                if isinstance(f_cell, Cell):
                    f_cell.value = data_dict['filename']

            # 5. Uložení
            wb.save(output_path)
            return True

        except PermissionError:
            print(f"(!) CHYBA: Soubor '{output_path}' je otevřený! Zavřete Excel.")
            return False
        except Exception as e:
            print(f"(!) CHYBA ExcelHandler: {e}")
            return False