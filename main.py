from Excel import *
from GUI import *
from MyOCR import *


def main():
    res = vyrobit_okno()
    print(f"Vybraný soubor z GUI: {res}")
    if res is not None:
        r = ReadData(res)
        final_txt = ReturnData(r)
        print(f"Získaná data: {final_txt}")
        #print(f"Získaná data: {data}")
    else:
        print("Nebyl vybrán žádný soubor.")
    

if __name__ == "__main__":
    main()