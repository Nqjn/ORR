from GUI import create_window
from ExcelHandler import ExcelHandler
import os

# Import s ochranou (stejně jako v GUI)
try:
    from MyOCR import MyOCR
except ImportError:
    print("WARNING: MyOCR nebylo nalezeno.")
    MyOCR = None 

def main():
    # 1. Spustíme GUI (vrací seznam souborů)
    gui_data_list = create_window()

    if gui_data_list:
        print(f"\n--- ZPRACOVÁVÁM {len(gui_data_list)} SOUBORŮ ---")
        
        # 2. Inicializujeme OCR engine
        ocr_engine = None
        if MyOCR:
            ocr_engine = MyOCR()
        
        template_file = "template.xlsx"
        final_output_file = "Vysledny_export.xlsx"
        
        handler = ExcelHandler(template_file)

        # 3. Cyklus přes všechny obrázky
        for item in gui_data_list:
            filepath = item['filepath']
            filename = os.path.basename(filepath)
            print(f"\nProcessing: {filename}")

            final_price = None
            final_date = None

            # Získání textu pomocí OCR
            if ocr_engine:
                if item.get('price_coords'):
                    final_price = ocr_engine.get_text_from_region(filepath, item['price_coords'])
                    print(f"  -> Cena text: {final_price}")
                
                if item.get('date_coords'):
                    final_date = ocr_engine.get_text_from_region(filepath, item['date_coords'])
                    print(f"  -> Datum text: {final_date}")
            else:
                print("  -> OCR engine není dostupný.")

            # 4. Příprava dat
            excel_data = {
                'price': final_price,
                'date': final_date,
                'filename': filename
            }

            # 5. Zápis do Excelu (s formátováním)
            handler.add_invoice_entry(final_output_file, excel_data)

        print("\n--- HOTOVO ---")

    else:
        print("Operace zrušena.")

if __name__ == "__main__":
    main()