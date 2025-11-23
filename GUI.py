import customtkinter as ctk
from tkinter import filedialog
import os
from PIL import Image, ImageDraw, ImageOps


# --- Nastavení vzhledu (volitelné) ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class VyberSouboruApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Zde budeme ukládat výsledek, ke kterému přistoupíme po skončení mainloop
        self.vybrana_cesta = None 

        self.title("Aplikace pro výběr souboru")
        self.geometry("800x700")


        #Left side frame for controls
        self.frame_control = ctk.CTkFrame(self, width=250)
        self.frame_control.pack(side ="left", fill="y", padx=10, pady=10)
        # 1. Instrukce
        self.label_instrukce = ctk.CTkLabel(self, text="Vyberte prosím soubor ke zpracování:", font=("Arial", 16))
        self.label_instrukce.pack(pady=(30, 10))

        # 2. Tlačítko pro výběr
        self.btn_vybrat = ctk.CTkButton(self, text="Vybrat soubor...", command=self.open_dialog)
        self.btn_vybrat.pack(pady= 10)

        # 3. Label pro zobrazení cesty
        self.label_cesta = ctk.CTkLabel(self, text="Zatím nic nevybráno...", text_color="gray")
        self.label_cesta.pack(pady= 10)
        # 4. Tlačítko pro potvrzení/zavření (objeví se až po výběru, nebo může být stále)
        self.btn_compile = ctk.CTkButton(
            self.frame_control,
            text="Potvrdit a Zpracovat", 
            #command =self.
            fg_color="green", 
            hover_color="darkgreen",
            state="disabled"
        )
        self.btn_compile.pack(pady=30) 

        # Right side frame for image preview
        self.frame_image = ctk.CTkFrame(self)
        self.frame_image.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.image_label = ctk.CTkLabel(self.frame_image, text="Náhled obrázku bude zde", font=("Arial", 14, "bold"))
        self.image_label.pack(fill = "both", expand=True, padx=10, pady=10)




    def open_dialog(self):
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
            self.btn_compile.configure(state="normal")

        if cesta.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(cesta)
                self.show_image_preview(img)
                try:
                    img = ImageOps.exif_transpose(img)
                except:
                    pass
                self.show_image_preview(img)
            except Exception as e:
                print(f"Chyba při načítání obrázku: {e}")
                self.show_image_preview(None)
        else:
            self.show_image_preview(None)





    def ukoncit_aplikaci(self):
        # Tato metoda ukončí mainloop a zavře okno
        self.destroy()

    def show_image_preview(self, pil_image):
        if pil_image is None:
            self.image_label.configure(text="Náhled obrázku bude zde", image=None)
            return
        
        # Copmute the size to fit in the frame while maintaining aspect ratio
        frame_width = 500
        w_percent = (frame_width / float(pil_image.size[0]))
        h_size = int((float(pil_image.size[1]) * float(w_percent)))

        ctk_img_obj = ctk.CTkImage(light_image = pil_image, dark_image= pil_image, size=(frame_width, h_size))
        self.image_label.configure(image=ctk_img_obj, text="")
        # Keep a reference to avoid garbage collection; store on the app instance instead of CTkLabel
        self._image_ref = ctk_img_obj


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


def DrawRectangleOnImage(image_path: str, coords: list, output_path: str):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Nakreslíme obdélník
    draw.polygon(coords, outline="red", width=5)
    
    # Uložíme nový obrázek
    img.save(output_path)
