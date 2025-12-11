from Excel import *
from GUI import *
from MyOCR import *


def main():
    res = vyrobit_okno()
    print(f"Vybraný soubor z GUI: {res}")

    if res:
        final_txt = ReturnPrice(res)
        coords = ReturnPriceCoords(res)

        date_coords = ReturnDateCoords(res)
        print(f"Souřadnice data: {date_coords}")

        date_value = ReturnDate(res)
        print(f"Nalezené datum: {date_value}")


        print(f"Souřadnice nalezené ceny: {coords}")
        print(f"Získaná data: {final_txt}")
        #print(f"Získaná data: {data}")
    else:
        print("Nebyl vybrán žádný soubor.")
        
    

if __name__ == "__main__":
    main()