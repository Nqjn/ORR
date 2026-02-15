from GUI import create_window
from ExcelHandler import ExcelHandler
import os

def main():

    print("Spouštím aplikaci...")
    

    gui_results = create_window()

    if not gui_results:
        print("Uživatel zrušil akci nebo nevybral data.")
        
        return

    print(f"\n--- UKLÁDÁM DATA PRO {len(gui_results)} SOUBORŮ ---")
    
    template_file = "template.xlsx"       
    output_file = "Vysledny_export.xlsx"
    

    handler = ExcelHandler(template_file)
    saved_count = 0

    for item in gui_results:
        filename = os.path.basename(item['filepath'])
        print(f"\nZpracovávám: {filename}")
        

        vendor = item.get('vendor_text', "") 
        price = item.get('price_text', "")
        date = item.get('date_text', "")

        print(f"  -> Prodejce: {vendor}")
        print(f"  -> Cena: {price}")
        print(f"  -> Datum: {date}")

        excel_data = {
            'vendor': vendor,  
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