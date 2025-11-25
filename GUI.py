import customtkinter as ctk
from tkinter import filedialog
import os
from PIL import Image, ImageDraw, ImageOps
import threading

from MyOCR import ReturnPrice

# Import logiky z MyOCR.py
try:
    from MyOCR import ReadData, ReturnPriceCoords
except ImportError:
    print("POZOR: Soubor MyOCR.py nebyl nalezen.")

# Nastavení vzhledu
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class VyberSouboruApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.vybrana_cesta = None
        self.ocr_finall_data = None 
        self._image_ref = None 
        
        # Proměnné pro přenos dat z vlákna
        self._thread_result_image = None 
        self._thread_result_msg = ""
        self._ocr_thread = None 

        self.title("ORR - Výběr souboru")
        self.geometry("1000x700")

        # --- OVLÁDÁNÍ ---
        self.frame_control = ctk.CTkFrame(self, width=250)
        self.frame_control.pack(side="left", fill="y", padx=10, pady=10)
        
        self.label_instrukce = ctk.CTkLabel(self.frame_control, text="Vyberte soubor:", font=("Arial", 16))
        self.label_instrukce.pack(pady=(30, 10))

        self.btn_vybrat = ctk.CTkButton(self.frame_control, text="Vybrat soubor...", command=self.open_dialog)
        self.btn_vybrat.pack(pady=10)

        self.label_cesta = ctk.CTkLabel(self.frame_control, text="...", text_color="gray", wraplength=230)
        self.label_cesta.pack(pady=10)

        self.btn_compile = ctk.CTkButton(
            self.frame_control,
            text="Potvrdit a Zpracovat", 
            command=self.start_ocr_process, 
            fg_color="green", 
            hover_color="darkgreen",
            state="disabled"
        )
        self.btn_compile.pack(pady=30) 

        self.progress_bar = ctk.CTkProgressBar(self.frame_control, width=200)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        self.progress_bar.pack_forget()

        self.lable_status = ctk.CTkLabel(self.frame_control, text="")
        self.lable_status.pack(pady=5)

        # --- NÁHLED ---
        self.frame_image = ctk.CTkFrame(self)
        self.frame_image.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.image_label = ctk.CTkLabel(self.frame_image, text="Náhled obrázku bude zde")
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

    def open_dialog(self):
        cesta = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg"), ("Excel", "*.xlsx"), ("All", "*.*")]
        )
        if cesta:
            self.vybrana_cesta = cesta
            self.label_cesta.configure(text=f"Vybráno: {os.path.basename(cesta)}")
            self.btn_compile.configure(state="normal")

            if cesta.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img = Image.open(cesta)
                    try:
                        img = ImageOps.exif_transpose(img)
                    except:
                        pass
                    # První náhled (bez resize, show_image_preview si to zmenší samo)
                    self.show_image_preview(img)
                except Exception as e:
                    print(f"Chyba náhledu: {e}")
            else:
                self.show_image_preview(None)

    def start_ocr_process(self):
        """Spustí vlákno a začne ho sledovat (Polling)."""
        self.btn_compile.configure(state="disabled", text="Zpracovávám...")
        self.btn_vybrat.configure(state="disabled")
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()
        self.lable_status.configure(text="OCR běží...")

        # Vyčistíme staré výsledky
        self._thread_result_image = None
        self._thread_result_msg = "Probíhá..."

        # Spustíme vlákno
        self._ocr_thread = threading.Thread(target=self.thread_ocr_logic)
        self._ocr_thread.start()

        # Spustíme sledování vlákna (každých 100ms)
        self.monitor_ocr_thread()

    def monitor_ocr_thread(self):
        """
        Toto běží v hlavním vlákně.
        Kontroluje, zda vlákno stále běží. Pokud ne, aktualizuje GUI.
        """
        if self._ocr_thread is not None and self._ocr_thread.is_alive():
            # Vlákno stále běží, zkontrolujeme znovu za 100ms
            self.after(100, self.monitor_ocr_thread)
        else:
            # Vlákno skončilo! Můžeme bezpečně aktualizovat GUI.
            self.finalize_gui_update()

    def draw_rect_on_image(self, coords = None):
        actual_path = self.vybrana_cesta

        if actual_path is None:
            return
        
        raw_data = ReadData(actual_path)
        self.ocr_finall_data = raw_data 

        if coords is None:
            coords = ReadData(actual_path)
        poly_coords = []

        
        try:
            original_image = Image.open(actual_path)
            try:
                original_image = ImageOps.exif_transpose(original_image)
            except:
                pass

            original_image = original_image.convert("RGB")
            draw = ImageDraw.Draw(original_image) 

            for point in coords:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    poly_coords.append((point[0], point[1]))
                    
            if len(poly_coords) >= 2:
                draw.polygon(poly_coords, outline="red", width=10)
            return original_image
        except Exception as e:
            print(f"Chyba při kreslení na obrázek: {e}")
    
    def _load_image(self, path: str):
        try:
            img = Image.open(path)
            try:
                img = ImageOps.exif_transpose(img)
            except:
                pass
            return img.convert("RGB")
        except Exception as e:
            print(f"Chyba při načítání obrázku: {e}")
            return None
        
    def _draw_rect(self, img, coords):
        if self.vybrana_cesta is None:
            return img

        if coords is None:
            coords = ReturnPriceCoords(ReadData(self.vybrana_cesta))
        
        try:
            draw = ImageDraw.Draw(img) 
            poly_coords = []
            if coords is None:
                return img
            
            for point in coords:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    poly_coords.append((point[0], point[1]))
                    
            if len(poly_coords) >= 2:
                draw.polygon(poly_coords, outline="red", width=10)
            return img
        except Exception as e:
            print(f"Chyba při kreslení na obrázek: {e}")
            return img
    
    def _resize_image(self, img, target_width=600):
        w_percent = (target_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        
        # Kompatibilita verzí Pillow
        try:
            resample_mode = Image.Resampling.BILINEAR
        except AttributeError:
            resample_mode = 2 

        return img.resize((target_width, h_size), resample_mode)

    def thread_ocr_logic(self):
        actual_path = self.vybrana_cesta

        if actual_path is None:
            return
        
        try:
            raw_data = ReadData(actual_path)
            self.ocr_finall_data = raw_data 
            coords = ReturnPriceCoords(raw_data)

            if coords:
                original_image = self._load_image(actual_path)
                marked_image = self._draw_rect(original_image, coords)
                resized_image = self._resize_image(marked_image, target_width=600)
                self._thread_result_image = resized_image
            self._thread_result_msg = f"OCR dokončeno. Cena je: {ReturnPrice(raw_data)}"
        except Exception as e:
            print(f"Chyba v OCR vlákně: {e}")
            import traceback
            traceback.print_exc()
            self._thread_result_msg = f"Chyba během OCR: {e}"

    def finalize_gui_update(self):
        """
        Tato metoda se zavolá v hlavním vlákně, jakmile 'monitor' zjistí, že vlákno skončilo.
        """
        # 1. Zobrazit obrázek (pokud byl vytvořen)
        if self._thread_result_image:
            self.show_image_preview(self._thread_result_image, resize=False)
            self._thread_result_image = None # Úklid
        
        # 2. Status a Tlačítka
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.lable_status.configure(text=self._thread_result_msg)
        
        self.btn_compile.configure(state="normal", text="Ukončit a Použít data", command=self.ukoncit_aplikaci)
        self.btn_vybrat.configure(state="normal")

    def ukoncit_aplikaci(self):
        self.destroy()

    def show_image_preview(self, pil_image, resize=True):
        if pil_image is None:
            self.image_label.configure(text="Náhled není k dispozici", image=None)
            self._image_ref = None
            return
        
        try:
            if resize:
                # Resize pokud je to surový obrázek z disku
                frame_width = 500
                w_percent = (frame_width / float(pil_image.size[0]))
                h_size = int((float(pil_image.size[1]) * float(w_percent)))
                img_to_show = pil_image
                ctk_size = (frame_width, h_size)
            else:
                # Už zmenšeno z vlákna
                img_to_show = pil_image
                ctk_size = pil_image.size

            ctk_img_obj = ctk.CTkImage(light_image=img_to_show, dark_image=img_to_show, size=ctk_size)
            
            self.image_label.configure(image=ctk_img_obj, text="")
            self._image_ref = ctk_img_obj 
            
            self.image_label.update()
        except Exception as e:
            print(f"Chyba při zobrazování obrázku: {e}")


def vyrobit_okno() -> list | None:
    app = VyberSouboruApp()
    app.mainloop()
    return app.ocr_finall_data