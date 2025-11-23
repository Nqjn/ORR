import customtkinter as ctk
from tkinter import filedialog
import os

# --- Nastavení vzhledu (volitelné) ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class VyberSouboruApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Zde budeme ukládat výsledek, ke kterému přistoupíme po skončení mainloop
        self.vybrana_cesta = None 

        self.title("Aplikace pro výběr souboru")
        self.geometry("600x250")

        # 1. Instrukce
        self.label_instrukce = ctk.CTkLabel(self, text="Vyberte prosím soubor ke zpracování:", font=("Arial", 16))
        self.label_instrukce.pack(pady=(30, 10))

        # 2. Tlačítko pro výběr
        self.btn_vybrat = ctk.CTkButton(self, text="Vybrat soubor...", command=self.otevrit_dialog)
        self.btn_vybrat.pack(pady=10)

        # 3. Label pro zobrazení cesty
        self.label_cesta = ctk.CTkLabel(self, text="Zatím nic nevybráno...", text_color="gray")
        self.label_cesta.pack(pady=10)

        # 4. Tlačítko pro potvrzení/zavření (objeví se až po výběru, nebo může být stále)
        self.btn_potvrdit = ctk.CTkButton(
            self, 
            text="Potvrdit a Zavřít", 
            command=self.ukoncit_aplikaci,
            fg_color="green", 
            hover_color="darkgreen"
        )
        # Zatím ho skryjeme, nebo ho necháme disable, dokud není vybráno
        self.btn_potvrdit.pack(pady=20)
        self.btn_potvrdit.configure(state="disabled") 

    def otevrit_dialog(self):
        cesta = filedialog.askopenfilename(
            title="Vyberte soubor",
            filetypes=[("PNG files", "*.png"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if cesta:
            self.vybrana_cesta = cesta
            # Aktualizace GUI
            nazev_souboru = os.path.basename(cesta)
            self.label_cesta.configure(text=f"Vybráno: {nazev_souboru}", text_color=("black", "white"))
            
            # Povolíme tlačítko pro ukončení
            self.btn_potvrdit.configure(state="normal")

    def ukoncit_aplikaci(self):
        # Tato metoda ukončí mainloop a zavře okno
        self.destroy()


def vyrobit_okno() -> str | None:
    """
    Tato funkce vytvoří instanci okna, spustí ho a počká na jeho zavření.
    Poté vrátí vybranou cestu zpět do main.py.
    """
    app = VyberSouboruApp()
    
    # mainloop() zde ZASTAVÍ vykonávání kódu v main.py, dokud se okno nezavře
    app.mainloop()
    
    # Jakmile uživatel okno zavře (křížkem nebo tlačítkem "Potvrdit"),
    # kód pokračuje zde a my vrátíme uloženou hodnotu.
    return app.vybrana_cesta
