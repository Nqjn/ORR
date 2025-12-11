from GUI import create_window
from MyOCR import MyOCR
from ExcelHandler import ExcelHandler
import os

def main():
    # 1. Run GUI to select file and coords
    gui_data = create_window()

    if gui_data:
        print("\n--- PROCESSING DATA ---")
        filepath = gui_data['filepath']
        
        # 2. Extract text using OCR on specific regions
        ocr_engine = MyOCR()
        
        final_price = None
        final_date = None

        # Get Price Text
        if gui_data.get('price_coords'):
            final_price = ocr_engine.get_text_from_region(filepath, gui_data['price_coords'])
            print(f"Price Found: {final_price}")
        
        # Get Date Text
        if gui_data.get('date_coords'):
            final_date = ocr_engine.get_text_from_region(filepath, gui_data['date_coords'])
            print(f"Date Found: {final_date}")

        # 3. Prepare Data for Excel
        excel_data = {
            'price': final_price,
            'date': final_date,
            'filename': os.path.basename(filepath)
        }

        # 4. Generate Excel
        # Make sure you have a file named 'template.xlsx' in your folder!
        template_file = "template.xlsx" 
        
        # Create output filename (e.g., "Invoice_originalName.xlsx")
        output_filename = f"Invoice_{os.path.splitext(os.path.basename(filepath))[0]}.xlsx"
        
        handler = ExcelHandler(template_file)
        handler.create_invoice(output_filename, excel_data)

    else:
        print("No data selected.")

if __name__ == "__main__":
    main()