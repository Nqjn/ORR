import tkinter
import customtkinter as ctk
from tkinter import filedialog
import os
from PIL import Image, ImageOps, ImageTk 
import threading
from typing import Any, List, Optional

# --- IMPORT MyOCR ---
try:
    from MyOCR import MyOCR
except ImportError:
    print("WARNING: MyOCR.py file not found.")
    MyOCR = None

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class FileSelectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- DATA ---
        self.images_data: List[dict] = [] 
        self.current_index = -1 

        self.original_image = None 
        self._tk_image_ref = None
        self.scale_ratio = 1.0
        
        # Uchováváme reference na widgety (aby šly mazat a číst)
        self.active_widgets = {} # { "price": {...}, "date": {...}, "vendor": {...} }
        
        self.drag_data = {
            "x": 0, "y": 0, "item": None, "mode": None, "group_tag": None, "corner": None
        }
        
        self.final_output_data = None 
        self._thread_result_msg = ""
        self._ocr_thread = None 

        # --- GUI SETUP ---
        self.title("OCR - Editor s korekturou")
        self.geometry("1200x800")

        self.ocr_engine = None
        if MyOCR:
            try: self.ocr_engine = MyOCR()
            except: pass

        # === LEVÝ PANEL ===
        self.control_frame = ctk.CTkFrame(self, width=250)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.control_frame, text="Soubory & Navigace:", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        ctk.CTkButton(self.control_frame, text="Nahrát obrázky...", command=self.open_file_dialog).pack(pady=10)
        
        self.counter_label = ctk.CTkLabel(self.control_frame, text="0 / 0", font=("Arial", 14, "bold"))
        self.counter_label.pack(pady=(10, 0))
        
        self.path_label = ctk.CTkLabel(self.control_frame, text="...", text_color="gray", wraplength=230)
        self.path_label.pack(pady=5)

        # Navigace
        self.nav_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.nav_frame.pack(pady=10)
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="< Zpět", width=80, command=lambda: self.change_image(-1), state="disabled")
        self.btn_prev.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(self.nav_frame, text="Další >", width=80, command=lambda: self.change_image(1), state="disabled")
        self.btn_next.pack(side="left", padx=5)

        ctk.CTkLabel(self.control_frame, text="Akce:", font=("Arial", 14, "bold")).pack(pady=(20, 5))

        self.process_btn = ctk.CTkButton(
            self.control_frame, text="Spustit OCR (Vše)", command=self.start_ocr_process, 
            state="disabled", fg_color="green"
        )
        self.process_btn.pack(pady=10) 
        
        self.progress_bar = ctk.CTkProgressBar(self.control_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.status_label = ctk.CTkLabel(self.control_frame, text="", wraplength=230)
        self.status_label.pack(pady=5)

        # Manuální nástroje
        self.frame_manual = ctk.CTkFrame(self.control_frame)
        self.frame_manual.pack(pady=20, fill="x", padx=5)
        ctk.CTkLabel(self.frame_manual, text="Přidat oblast:", font=("Arial", 12, "bold")).pack(pady=5)
        
        # TLAČÍTKA PRO PŘIDÁNÍ OBLASTÍ
        ctk.CTkButton(self.frame_manual, text="+ Cena", fg_color="red", 
                      command=lambda: self.add_manual_box("price", "red")).pack(pady=5, padx=5, fill="x")
        ctk.CTkButton(self.frame_manual, text="+ Datum", fg_color="blue", 
                      command=lambda: self.add_manual_box("date", "blue")).pack(pady=5, padx=5, fill="x")
        # NOVÉ TLAČÍTKO PRO PRODEJCE
        ctk.CTkButton(self.frame_manual, text="+ Název (Prodejce)", fg_color="green", 
                      command=lambda: self.add_manual_box("vendor", "green")).pack(pady=5, padx=5, fill="x")

        self.finish_all_btn = ctk.CTkButton(self.control_frame, text="Uložit vše do Excelu", command=self.finalize_and_close, fg_color="darkblue")
        self.finish_all_btn.pack(side="bottom", pady=20)

        # === PRAVÝ PANEL (CANVAS) ===
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.canvas = tkinter.Canvas(self.image_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=0, pady=0)
        self.text_id = self.canvas.create_text(0, 0, text="Náhled", fill="gray", font=("Arial", 16))

        # Binds
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)
        self.canvas.bind("<Motion>", self.on_mouse_move)

    # --- CANVAS & ENTRY LOGIC ---
    def on_resize(self, event):
        self.canvas.coords(self.text_id, self.canvas.winfo_width()/2, self.canvas.winfo_height()/2)
        if self.original_image:
            self._save_current_entries_text()
            self.show_image_on_canvas()

    def show_image_on_canvas(self):
        if self.original_image is None: return
        
        # 1. Vyčistit vše
        self.active_widgets = {} 
        self.canvas.delete("all")

        # 2. Vykreslit obrázek
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10: return
        img_w, img_h = self.original_image.size
        self.scale_ratio = min(cw / img_w, ch / img_h)
        new_w, new_h = int(img_w * self.scale_ratio), int(img_h * self.scale_ratio)
        
        resized_pil = self.original_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self._tk_image_ref = ImageTk.PhotoImage(resized_pil)
        self.canvas.create_image(0, 0, image=self._tk_image_ref, anchor="nw")

        # 3. Vykreslit boxy a widgety
        if self.current_index >= 0:
            data = self.images_data[self.current_index]
            
            # --- CENA (RED) ---
            if data["coords"].get("price"):
                self.create_interactive_box(data["coords"]["price"], "red", "price")
                val = data["final_values"].get("price")
                self.create_text_entry("price", data["coords"]["price"], val, "red")

            # --- DATUM (BLUE) ---
            if data["coords"].get("date"):
                self.create_interactive_box(data["coords"]["date"], "blue", "date")
                val = data["final_values"].get("date")
                self.create_text_entry("date", data["coords"]["date"], val, "blue")

            # --- PRODEJCE (GREEN) ---
            if data["coords"].get("vendor"):
                self.create_interactive_box(data["coords"]["vendor"], "green", "vendor")
                val = data["final_values"].get("vendor")
                self.create_text_entry("vendor", data["coords"]["vendor"], val, "green")

    def create_text_entry(self, type_key, coords, text_value, color):
        if not coords: return
        
        ys = [pt[1] for pt in coords]
        xs = [pt[0] for pt in coords]
        target_x = min(xs) * self.scale_ratio
        target_y = max(ys) * self.scale_ratio + 5 
        
        container = ctk.CTkFrame(self.canvas, fg_color="transparent", width=160, height=30)
        
        entry = ctk.CTkEntry(container, width=120, height=25, border_color=color, 
                             fg_color="#333333", text_color="white")
        entry.insert(0, str(text_value) if text_value else "")
        entry.pack(side="left", padx=(0, 2))

        refresh_btn = ctk.CTkButton(container, text="↻", width=25, height=25, 
                                    fg_color="#555555", hover_color="#777777",
                                    command=lambda: self.run_single_box_ocr(type_key))
        refresh_btn.pack(side="left")

        self.canvas.create_window(target_x, target_y, window=container, anchor="nw")
        self.active_widgets[type_key] = {"entry": entry, "frame": container}

    def run_single_box_ocr(self, type_key):
        if self.ocr_engine is None or self.current_index == -1: return

        current_coords = self._get_coords(type_key)
        if not current_coords: return

        self.images_data[self.current_index]["coords"][type_key] = current_coords
        filepath = self.images_data[self.current_index]["path"]

        self.status_label.configure(text=f"Skenuji {type_key}...")
        self.update() 

        try:
            new_text = self.ocr_engine.get_text_from_region(filepath, current_coords)
            if type_key in self.active_widgets:
                entry = self.active_widgets[type_key]["entry"]
                entry.delete(0, "end")
                entry.insert(0, new_text)
            
            self.images_data[self.current_index]["final_values"][type_key] = new_text
            self.status_label.configure(text=f"OCR pro {type_key} hotovo.")

        except Exception as e:
            self.status_label.configure(text=f"Chyba OCR: {e}")

    def create_interactive_box(self, raw_coords, color, type_key):
        group_tag = f"group_{type_key}"
        if raw_coords:
            xs = [pt[0] for pt in raw_coords]
            ys = [pt[1] for pt in raw_coords]
            x1, y1 = min(xs) * self.scale_ratio, min(ys) * self.scale_ratio
            x2, y2 = max(xs) * self.scale_ratio, max(ys) * self.scale_ratio
        else:
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            x1, y1, x2, y2 = cw/2 - 50, ch/2 - 20, cw/2 + 50, ch/2 + 20

        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags=(group_tag, "rect", "movable"))
        for corner in ["NW", "NE", "SE", "SW"]:
            self._draw_handle(x1, y1, x2, y2, group_tag, corner, color)

    def _draw_handle(self, x1, y1, x2, y2, group_tag, corner, color):
        size = 6
        cx, cy = {"NW":(x1,y1), "NE":(x2,y1), "SE":(x2,y2), "SW":(x1,y2)}[corner]
        self.canvas.create_rectangle(cx-size, cy-size, cx+size, cy+size, fill=color, outline="white", 
                                     tags=(group_tag, "handle", f"corner_{corner}", "movable"))

    def add_manual_box(self, type_key, color):
        if self.original_image:
            self.canvas.delete(f"group_{type_key}")
            self.create_interactive_box(None, color, type_key)
            self.images_data[self.current_index]["final_values"][type_key] = ""
            self._save_coords_from_canvas()
            self.show_image_on_canvas()
        else:
            self.status_label.configure(text="Nejprve nahrajte obrázek.")

    # --- INTERAKCE (S OPRAVOU KLIKNUTÍ DOVNITŘ) ---
    def _get_target_at_position(self, x, y, threshold=10):
        # 1. Rohy (resize)
        items = self.canvas.find_overlapping(x-threshold, y-threshold, x+threshold, y+threshold)
        for item in items:
            tags = self.canvas.gettags(item)
            if "handle" in tags:
                group = next((t for t in tags if t.startswith("group_")), None)
                corner = next((t.split("_")[1] for t in tags if t.startswith("corner_")), None)
                if group and corner:
                    return group, "RESIZE", corner

        # 2. Vnitřek (move)
        rects = self.canvas.find_withtag("rect")
        for r_id in reversed(rects):
            x1, y1, x2, y2 = self.canvas.coords(r_id)
            if x1 <= x <= x2 and y1 <= y <= y2:
                tags = self.canvas.gettags(r_id)
                group = next((t for t in tags if t.startswith("group_")), None)
                if group:
                    return group, "MOVE", None
        return None, None, None

    def on_mouse_move(self, event):
        if self.drag_data["mode"]: return 
        _, mode, _ = self._get_target_at_position(event.x, event.y)
        if mode == "RESIZE": self.canvas.configure(cursor="crosshair")
        elif mode == "MOVE": self.canvas.configure(cursor="fleur")
        else: self.canvas.configure(cursor="")

    def on_drag_start(self, event):
        group, mode, corner = self._get_target_at_position(event.x, event.y)
        if group and mode:
            self.drag_data.update({"mode": mode, "group_tag": group, "corner": corner, "x": event.x, "y": event.y})
            if mode == "MOVE": self.canvas.configure(cursor="fleur")

    def on_drag_motion(self, event):
        if not self.drag_data["group_tag"]: return
        group = self.drag_data["group_tag"]
        dx, dy = event.x - self.drag_data["x"], event.y - self.drag_data["y"]
        
        if self.drag_data["mode"] == "MOVE":
            self.canvas.move(group, dx, dy)
            self.drag_data["x"], self.drag_data["y"] = event.x, event.y
            
        elif self.drag_data["mode"] == "RESIZE":
            rect = self.canvas.find_withtag(f"{group}&&rect")[0]
            x1, y1, x2, y2 = self.canvas.coords(rect)
            c = self.drag_data["corner"]
            
            if c == "NW": x1, y1 = event.x, event.y
            elif c == "NE": x2, y1 = event.x, event.y
            elif c == "SE": x2, y2 = event.x, event.y
            elif c == "SW": x1, y2 = event.x, event.y
            
            nx1, nx2 = min(x1, x2), max(x1, x2)
            ny1, ny2 = min(y1, y2), max(y1, y2)
            
            self.canvas.coords(rect, nx1, ny1, nx2, ny2)
            s = 6
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NW")[0], nx1-s, ny1-s, nx1+s, ny1+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NE")[0], nx2-s, ny1-s, nx2+s, ny1+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SE")[0], nx2-s, ny2-s, nx2+s, ny2+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SW")[0], nx1-s, ny2-s, nx1+s, ny2+s)

    def on_drag_stop(self, event):
        self._save_current_entries_text()
        self._save_coords_from_canvas()
        self.show_image_on_canvas()
        self.drag_data = {"x":0, "y":0, "item":None, "mode":None, "group_tag":None, "corner":None}
        self.canvas.configure(cursor="")

    # --- FILE & DATA ---
    def open_file_dialog(self):
        paths = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All", "*")])
        if paths:
            self.images_data = []
            for p in paths:
                img = self._load_image(p)
                if img:
                    self.images_data.append({
                        "path": p, "image": img, 
                        # INIT s klíčem 'vendor'
                        "coords": {"price": None, "date": None, "vendor": None}, 
                        "final_values": {"price": None, "date": None, "vendor": None},
                        "ocr_done": False
                    })
            if self.images_data:
                self.current_index = 0
                self.load_image_by_index(0)
                self.process_btn.configure(state="normal")
            self.update_gui_labels()

    def _load_image(self, path):
        try: return ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        except: return None

    def change_image(self, direction):
        if not self.images_data: return
        self._save_current_entries_text() 
        self._save_coords_from_canvas()   
        new_idx = self.current_index + direction
        if 0 <= new_idx < len(self.images_data):
            self.current_index = new_idx
            self.load_image_by_index(new_idx)
            self.update_gui_labels()

    def load_image_by_index(self, idx):
        data = self.images_data[idx]
        self.original_image = data["image"]
        self.show_image_on_canvas()

    def _save_current_entries_text(self):
        if self.current_index == -1: return
        for key, widgets in self.active_widgets.items():
            text_val = widgets["entry"].get()
            self.images_data[self.current_index]["final_values"][key] = text_val

    def _save_coords_from_canvas(self):
        if self.current_index == -1: return
        self.images_data[self.current_index]["coords"]["price"] = self._get_coords("price")
        self.images_data[self.current_index]["coords"]["date"] = self._get_coords("date")
        self.images_data[self.current_index]["coords"]["vendor"] = self._get_coords("vendor")

    def _get_coords(self, key):
        rects = self.canvas.find_withtag(f"group_{key}&&rect")
        if not rects: return None
        x1, y1, x2, y2 = self.canvas.coords(rects[0])
        if self.scale_ratio > 0:
            return [[int(x/self.scale_ratio), int(y/self.scale_ratio)] for x,y in [(x1,y1), (x2,y1), (x2,y2), (x1,y2)]]
        return None

    def update_gui_labels(self):
        total = len(self.images_data)
        self.counter_label.configure(text=f"{self.current_index + 1} / {total}")
        self.path_label.configure(text=os.path.basename(self.images_data[self.current_index]["path"]) if total else "")
        self.btn_prev.configure(state="normal" if self.current_index > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_index < total - 1 else "disabled")

    # --- OCR THREAD ---
    def start_ocr_process(self):
        if self.ocr_engine is None: return
        self._save_coords_from_canvas()
        
        self.process_btn.configure(state="disabled")
        self.progress_bar.pack(pady=10); self.progress_bar.start()
        self.status_label.configure(text="OCR běží (automaticky)...")
        
        self._ocr_thread = threading.Thread(target=self.ocr_thread_logic)
        self._ocr_thread.start()
        self.monitor_ocr_thread()

    
    def ocr_thread_logic(self):
        if self.ocr_engine is None: return
        data = self.images_data[self.current_index]
        try:
            self.ocr_engine.analyze_image(data["path"])
            
            # --- AUTOMATICKÉ NASTAVENÍ SOUŘADNIC ---
            # Pokud nemáme boxy, načteme automatické (price, date)
            if not data["coords"]["price"]: data["coords"]["price"] = self.ocr_engine.get_price_coords()
            if not data["coords"]["date"]: data["coords"]["date"] = self.ocr_engine.get_date_coords()
            # Vendor zatím nemá auto-detekci, ale metoda existuje (vrátí None)
            if not data["coords"]["vendor"]: data["coords"]["vendor"] = self.ocr_engine.get_vendor_coords()
            
            # --- ZÍSKÁNÍ TEXTU ---
            p_text = self.ocr_engine.get_text_from_region(data["path"], data["coords"]["price"]) if data["coords"]["price"] else ""
            d_text = self.ocr_engine.get_text_from_region(data["path"], data["coords"]["date"]) if data["coords"]["date"] else ""
            v_text = self.ocr_engine.get_text_from_region(data["path"], data["coords"]["vendor"]) if data["coords"]["vendor"] else ""

            data["final_values"]["price"] = p_text
            data["final_values"]["date"] = d_text
            data["final_values"]["vendor"] = v_text
            
            data["ocr_done"] = True
            self._thread_result_msg = "(+)OCR done."
        except Exception as e:
            self._thread_result_msg = f"(-)ERROR: {e}"

    def monitor_ocr_thread(self):
        if self._ocr_thread and self._ocr_thread.is_alive():
            self.after(100, self.monitor_ocr_thread)
        else:
            self.progress_bar.stop(); self.progress_bar.pack_forget()
            self.status_label.configure(text=self._thread_result_msg)
            self.process_btn.configure(state="normal")
            self.show_image_on_canvas()

    # --- EXPORT ---
    def finalize_and_close(self):
        self._save_current_entries_text()
        export_list = []
        for item in self.images_data:
            export_list.append({
                "filepath": item["path"],
                "price_text": item["final_values"]["price"],
                "date_text": item["final_values"]["date"],
                "vendor_text": item["final_values"]["vendor"] # Export prodejce
            })
        self.final_output_data = export_list
        self.destroy()

def create_window():
    app = FileSelectorApp()
    app.mainloop()
    return app.final_output_data

if __name__ == "__main__":
    create_window()