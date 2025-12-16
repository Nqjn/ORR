import openpyxl
import os

class ExcelHandler:
    def __init__(self, template_path):
        self.template_path = template_path

    def create_invoice(self, output_path, data_dict):
        # 1. Check if the template file exists
        if not os.path.exists(self.template_path):
            print(f"(-)ERROR: Template not found: {self.template_path}")
            return False

        try:
            # Load the workbook
            wb = openpyxl.load_workbook(self.template_path)
            
            # 2. Select the specific sheet by name
            target_sheet_name = "Příjmy a výdaje"
            
            if target_sheet_name in wb.sheetnames:
                ws = wb[target_sheet_name]
            else:
                print(f"(-)ERROR: Sheet '{target_sheet_name}' does not exist in the template.")
                print(f"Available sheets: {wb.sheetnames}")
                return False
            
            # --- WRITE DATA ---
            # Adjust the cell coordinates according to your Excel (e.g., C50, D50...)
            
            # Example: Price
            if data_dict.get('price'):
                try:
                    # Attempt to convert to a number (remove spaces, Kč, etc.)
                    clean_price = str(data_dict['price']).replace(" ", "").replace("Kč", "").replace(",", ".")
                    # Specify the cell for the price (e.g., C50 according to your image?)
                    ws['C79'] = float(clean_price) 
                except ValueError:
                    ws['C79'] = data_dict['price']

            # Example: Date
            if data_dict.get('date'):
                # Specify the cell for the date
                ws['E79'] = data_dict['date']

            # Example: Filename / Note
            if data_dict.get('filename'):
                ws['F79'] = data_dict['filename'] # For example, the Note column
                
            # 3. Save the modified workbook
            wb.save(output_path)
            print(f"Excel úspěšně vytvořen: {output_path}")
            return True

        except Exception as e:
            print(f"Chyba při práci s Excelem: {e}")
            return False