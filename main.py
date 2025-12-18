from GUI import create_window
from ExcelHandler import ExcelHandler
import os

def main():
    # 1. Spustíme GUI
    # Uživatel zde provede OCR, opraví text v okénkách a klikne "Uložit"
    print("Spouštím aplikaci...")
    
    # GUI vrací seznam slovníků: [{'filepath':..., 'price_text':..., 'date_text':...}, ...]
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
        
        # Data bereme přímo z GUI (uživatel je mohl ručně opravit)
        # Používáme .get('', "") pro případ, že by klíč chyběl
        price = item.get('price_text', "")
        date = item.get('date_text', "")

        print(f"  -> Cena: {price}")
        print(f"  -> Datum: {date}")

        # Data pro Excel
        excel_data = {
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