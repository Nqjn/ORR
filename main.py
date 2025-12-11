from Excel import * # Pokud používáš, jinak můžeš smazat
from GUI import create_window
from MyOCR import MyOCR

def main():
    # 1. Spustíme GUI a počkáme, až uživatel vybere a potvrdí oblasti
    data_z_gui = create_window()

    if data_z_gui:
        print("\n--- ZPRACOVÁNÍ VÝSLEDKŮ ---")
        print(f"Vybraný soubor: {data_z_gui['filepath']}")
        
        # 2. Inicializujeme OCR engine (díky Singletonu se model nenačítá znovu, pokud už je v paměti)
        ocr_engine = MyOCR()
        
        # Cesta k obrázku
        path = data_z_gui['filepath']

        # --- CENA ---
        price_coords = data_z_gui.get('price_coords')
        if price_coords:
            print(f"Používám souřadnice pro Cenu: {price_coords}")
            # Tady voláme tu novou funkci pro výřez!
            final_price_text = ocr_engine.get_text_from_region(path, price_coords)
            print(f"-> PŘEČTENÁ CENA Z VÝŘEZU: '{final_price_text}'")
        else:
            print("Cena nebyla označena.")

        print("-" * 30)

        # --- DATUM ---
        date_coords = data_z_gui.get('date_coords')
        if date_coords:
            print(f"Používám souřadnice pro Datum: {date_coords}")
            # Tady voláme tu novou funkci pro výřez!
            final_date_text = ocr_engine.get_text_from_region(path, date_coords)
            print(f"-> PŘEČTENÉ DATUM Z VÝŘEZU: '{final_date_text}'")
        else:
            print("Datum nebylo označeno.")

        # Zde případně můžeš volat ukládání do Excelu
        # save_to_excel(final_price_text, final_date_text) ...

    else:
        print("Aplikace byla ukončena bez výběru dat.")

if __name__ == "__main__":
    main()