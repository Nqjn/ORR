from GUI import create_window
from ExcelHandler import ExcelHandler
import os

def main():
    # 1. Spustíme GUI
    print("Spouštím aplikaci...")
    
    # GUI vrací seznam výsledků
    # Očekáváme, že v item bude i klíč 'vendor_text' (nebo 'vendor')
    gui_results = create_window()

    if not gui_results:
        print("Uživatel zrušil akci nebo nevybral data.")
        return

    print(f"\n--- UKLÁDÁM DATA PRO {len(gui_results)} SOUBORŮ ---")
    
    template_file = "template.xlsx"       
    output_file = "Vysledny_export.xlsx"
    
    # Inicializace handleru
    handler = ExcelHandler(template_file)
    saved_count = 0

    for item in gui_results:
        filename = os.path.basename(item['filepath'])
        print(f"\nZpracovávám: {filename}")
        
        # --- ZDE JSOU ZMĚNY ---
        # 1. Načteme prodejce z dat, která nám vrátilo GUI
        # (Předpokládáme, že GUI ukládá název pod klíčem 'vendor_text')
        vendor = item.get('vendor_text', "") 
        price = item.get('price_text', "")
        date = item.get('date_text', "")

        print(f"  -> Prodejce: {vendor}") # Kontrolní výpis
        print(f"  -> Cena: {price}")
        print(f"  -> Datum: {date}")

        # 2. Přidáme prodejce do slovníku pro Excel
        excel_data = {
            'vendor': vendor,  # <--- TOTO JE KLÍČOVÉ PRO EXCELHANDLER
            'price': price,
            'date': date,
            'filename': filename
        }

        # Zápis
        if handler.add_invoice_entry(output_file, excel_data):
            print("  -> OK")
            saved_count += 1
        else:
            print("  -> CHYBA (zkontrolujte výpis výše)")

    print(f"\n--- HOTOVO ({saved_count}/{len(gui_results)}) ---")
    print(f"Soubor: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    main()