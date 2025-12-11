import openpyxl
import os

class ExcelHandler:
    def __init__(self, template_path):
        self.template_path = template_path

    def create_invoice(self, output_path, data_dict):
        # 1. Kontrola existence souboru
        if not os.path.exists(self.template_path):
            print(f"CHYBA: Šablona nebyla nalezena: {self.template_path}")
            return False

        try:
            # Načtení sešitu
            wb = openpyxl.load_workbook(self.template_path)
            
            # 2. Výběr konkrétního listu podle jména
            target_sheet_name = "Příjmy a výdaje"
            
            if target_sheet_name in wb.sheetnames:
                ws = wb[target_sheet_name]
            else:
                print(f"CHYBA: List '{target_sheet_name}' v šabloně neexistuje.")
                print(f"Dostupné listy: {wb.sheetnames}")
                return False
            
            # --- ZÁPIS DAT ---
            # Zde si upravte souřadnice buněk podle vašeho Excelu (např. C50, D50...)
            
            # Příklad: Cena
            if data_dict.get('price'):
                try:
                    # Pokus o převod na číslo (odstranění mezer, Kč atd.)
                    clean_price = str(data_dict['price']).replace(" ", "").replace("Kč", "").replace(",", ".")
                    # Zde zadejte buňku, kam má přijít cena (např. C50 podle vašeho obrázku?)
                    ws['C79'] = float(clean_price) 
                except ValueError:
                    ws['C79'] = data_dict['price']

            # Příklad: Datum
            if data_dict.get('date'):
                # Zde zadejte buňku pro datum
                ws['E79'] = data_dict['date']

            # Příklad: Název souboru / Poznámka
            if data_dict.get('filename'):
                ws['F79'] = data_dict['filename'] # Např. sloupec Poznámka
                
            # 3. Uložení
            wb.save(output_path)
            print(f"Excel úspěšně vytvořen: {output_path}")
            return True

        except Exception as e:
            print(f"Chyba při práci s Excelem: {e}")
            return False