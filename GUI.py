import tkinter
import customtkinter as ctk
from tkinter import filedialog
import os
from PIL import Image, ImageOps, ImageTk 
import threading
from typing import Any, List, Optional

# --- IMPORT MyOCR (volitelné) ---
try:
    from MyOCR import MyOCR
except ImportError:
    print("WARNING: MyOCR.py file not found. OCR features will not work.")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class FileSelectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- DATA STORAGE ---
        # Seznam slovníků pro každý nahraný obrázek
        self.images_data: List[dict] = [] 
        self.current_index = -1 

        # Proměnné pro zobrazení
        self.original_image = None 
        self._tk_image_ref = None
        self.scale_ratio = 1.0
        
        # Drag & Drop proměnné
        self.drag_data = {
            "x": 0, "y": 0, 
            "item": None,
            "mode": None,
            "group_tag": None,
            "corner": None
        }
        
        self.final_output_data = None 

        # Vlákna
        self._thread_result_msg = ""
        self._ocr_thread = None 

        # --- GUI SETUP ---
        self.title("OCR - Multi-Image Editor")
        self.geometry("1200x800")

        # Inicializace OCR Enginu
        self.ocr_engine = None
        try:
            self.ocr_engine = MyOCR()
        except: pass

        # === LEVÝ PANEL ===
        self.control_frame = ctk.CTkFrame(self, width=250)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.control_frame, text="Soubory & Navigace:", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        
        # Tlačítko nahrání
        self.select_btn = ctk.CTkButton(self.control_frame, text="Nahrát obrázky...", command=self.open_file_dialog)
        self.select_btn.pack(pady=10)

        # Počítadlo
        self.counter_label = ctk.CTkLabel(self.control_frame, text="0 / 0", font=("Arial", 14, "bold"))
        self.counter_label.pack(pady=(10, 0))
        
        self.path_label = ctk.CTkLabel(self.control_frame, text="Žádný soubor", text_color="gray", wraplength=230)
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
            self.control_frame, text="Spustit OCR (Aktuální)", command=self.start_ocr_process, 
            state="disabled", fg_color="green"
        )
        self.process_btn.pack(pady=10) 
        
        self.progress_bar = ctk.CTkProgressBar(self.control_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.status_label = ctk.CTkLabel(self.control_frame, text="", wraplength=230)
        self.status_label.pack(pady=5)

        # Manuální opravy
        self.frame_manual = ctk.CTkFrame(self.control_frame)
        self.frame_manual.pack(pady=20, fill="x", padx=5)
        ctk.CTkLabel(self.frame_manual, text="Manuální boxy:", font=("Arial", 12, "bold")).pack(pady=5)
        ctk.CTkButton(self.frame_manual, text="+ Box Ceny", fg_color="red", 
                      command=lambda: self.add_manual_box("price", "red")).pack(pady=5, padx=5, fill="x")
        ctk.CTkButton(self.frame_manual, text="+ Box Data", fg_color="blue", 
                      command=lambda: self.add_manual_box("date", "blue")).pack(pady=5, padx=5, fill="x")

        # Tlačítko Dokončit
        self.finish_all_btn = ctk.CTkButton(self.control_frame, text="Dokončit vše & Export", command=self.finalize_and_close, fg_color="darkblue")
        self.finish_all_btn.pack(side="bottom", pady=20)

        # === PRAVÝ PANEL (CANVAS) ===
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.canvas = tkinter.Canvas(self.image_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=0, pady=0)
        
        self.text_id = self.canvas.create_text(
            0, 0, text="Náhled", fill="gray", font=("Arial", 16), anchor="center"
        )

        # Binds
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)
        self.canvas.bind("<Motion>", self.on_mouse_move) # Pro změnu kurzoru

    # --- CANVAS LOGIC ---
    def on_resize(self, event):
        self._center_placeholder()
        if self.original_image:
            self.show_image_on_canvas(draw_boxes=True)

    def _center_placeholder(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.coords(self.text_id, w/2, h/2)

    def show_image_on_canvas(self, draw_boxes=False):
        if self.original_image is None: return
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10: return

        self.canvas.delete("all")

        img_w, img_h = self.original_image.size
        self.scale_ratio = min(cw / img_w, ch / img_h)
        
        new_w = int(img_w * self.scale_ratio)
        new_h = int(img_h * self.scale_ratio)

        resized_pil = self.original_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self._tk_image_ref = ImageTk.PhotoImage(resized_pil)
        self.canvas.create_image(0, 0, image=self._tk_image_ref, anchor="nw")

        if draw_boxes and self.current_index >= 0:
            current_coords = self.images_data[self.current_index]["coords"]
            if current_coords.get("price"):
                self.create_interactive_box(current_coords["price"], "red", "price")
            if current_coords.get("date"):
                self.create_interactive_box(current_coords["date"], "blue", "date")

    def create_interactive_box(self, raw_coords, color, type_key):
        group_tag = f"group_{type_key}"
        self.canvas.delete(group_tag)

        if raw_coords:
            xs = [pt[0] for pt in raw_coords]
            ys = [pt[1] for pt in raw_coords]
            x1, y1 = min(xs) * self.scale_ratio, min(ys) * self.scale_ratio
            x2, y2 = max(xs) * self.scale_ratio, max(ys) * self.scale_ratio
        else:
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            x1, y1 = cw/2 - 50, ch/2 - 20
            x2, y2 = cw/2 + 50, ch/2 + 20

        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags=(group_tag, "rect", "movable"))
        for corner in ["NW", "NE", "SE", "SW"]:
            self._draw_handle(x1, y1, x2, y2, group_tag, corner, color)

    def _draw_handle(self, x1, y1, x2, y2, group_tag, corner, color):
        size = 6
        cx, cy = 0, 0
        if corner == "NW": cx, cy = x1, y1
        elif corner == "NE": cx, cy = x2, y1
        elif corner == "SE": cx, cy = x2, y2
        elif corner == "SW": cx, cy = x1, y2
        
        self.canvas.create_rectangle(cx-size, cy-size, cx+size, cy+size, fill=color, outline="white", 
                                     tags=(group_tag, "handle", f"corner_{corner}", "movable"))

    def add_manual_box(self, type_key, color):
        if self.original_image:
            self.create_interactive_box(None, color, type_key)
        else:
            self.status_label.configure(text="Nejprve nahrajte obrázek.")

    # --- INTERACTION & MAGNETIC CORNERS ---
    def _check_corner_proximity(self, x, y, threshold=15):
        rect_ids = self.canvas.find_withtag("rect")
        for r_id in rect_ids:
            tags = self.canvas.gettags(r_id)
            group = next((t for t in tags if t.startswith("group_")), None)
            if not group: continue
            
            x1, y1, x2, y2 = self.canvas.coords(r_id)
            corners = {"NW": (x1,y1), "NE": (x2,y1), "SE": (x2,y2), "SW": (x1,y2)}
            
            for c_name, (cx, cy) in corners.items():
                if abs(x - cx) < threshold and abs(y - cy) < threshold:
                    return group, c_name
        return None

    def on_mouse_move(self, event):
        if self.drag_data["mode"]: return # Pokud táhneme, neměníme
        
        if self._check_corner_proximity(event.x, event.y, 15):
            self.canvas.configure(cursor="crosshair")
        else:
            item = self.canvas.find_withtag("current")
            if item and "rect" in self.canvas.gettags(item[0]):
                self.canvas.configure(cursor="fleur")
            else:
                self.canvas.configure(cursor="")

    def on_drag_start(self, event):
        # 1. Magnetická detekce rohů (Priorita)
        prox = self._check_corner_proximity(event.x, event.y, 15)
        if prox:
            group, corner = prox
            self.drag_data.update({"mode": "RESIZE", "group_tag": group, "corner": corner, "x": event.x, "y": event.y})
            return

        # 2. Posun celého objektu
        closest = self.canvas.find_closest(event.x, event.y)
        if not closest: return
        tags = self.canvas.gettags(closest[0])
        
        if "movable" in tags:
            group = next((t for t in tags if t.startswith("group_")), None)
            self.drag_data.update({"mode": "MOVE", "group_tag": group, "x": event.x, "y": event.y})
            self.canvas.configure(cursor="fleur")

    def on_drag_motion(self, event):
        if not self.drag_data["group_tag"]: return
        group = self.drag_data["group_tag"]
        
        if self.drag_data["mode"] == "MOVE":
            dx, dy = event.x - self.drag_data["x"], event.y - self.drag_data["y"]
            self.canvas.move(group, dx, dy)
            self.drag_data["x"], self.drag_data["y"] = event.x, event.y
            
        elif self.drag_data["mode"] == "RESIZE":
            rect = self.canvas.find_withtag(f"{group}&&rect")[0]
            x1, y1, x2, y2 = self.canvas.coords(rect)
            corner = self.drag_data["corner"]
            
            # Update coords based on corner
            if corner == "NW": x1, y1 = event.x, event.y
            elif corner == "NE": x2, y1 = event.x, event.y
            elif corner == "SE": x2, y2 = event.x, event.y
            elif corner == "SW": x1, y2 = event.x, event.y
            
            # Normalizace (aby x1 bylo vždy vlevo)
            nx1, nx2 = min(x1, x2), max(x1, x2)
            ny1, ny2 = min(y1, y2), max(y1, y2)
            
            self.canvas.coords(rect, nx1, ny1, nx2, ny2)
            # Překreslení handle bodů
            s = 6
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NW")[0], nx1-s, ny1-s, nx1+s, ny1+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NE")[0], nx2-s, ny1-s, nx2+s, ny1+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SE")[0], nx2-s, ny2-s, nx2+s, ny2+s)
            self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SW")[0], nx1-s, ny2-s, nx1+s, ny2+s)

    def on_drag_stop(self, event):
        self.drag_data = {"x":0, "y":0, "item":None, "mode":None, "group_tag":None, "corner":None}
        self.canvas.configure(cursor="")

    # --- FILE & DATA MANAGEMENT ---
    def open_file_dialog(self):
        paths = filedialog.askopenfilenames(filetypes=[("Obrázky", "*.png;*.jpg;*.jpeg"), ("Vše", "*.*")])
        if paths:
            self.images_data = []
            for p in paths:
                img = self._load_image(p)
                if img:
                    self.images_data.append({
                        "path": p, "image": img, "coords": {"price": None, "date": None}, 
                        "ocr_done": False, "ocr_msg": ""
                    })
            
            if self.images_data:
                self.current_index = 0
                self.load_image_by_index(0)
                self.process_btn.configure(state="normal")
            
            self.update_gui_labels()

    def _load_image(self, path):
        try:
            img = Image.open(path)
            try: img = ImageOps.exif_transpose(img)
            except: pass
            return img.convert("RGB")
        except: return None

    def change_image(self, direction):
        if not self.images_data: return
        self._save_current_canvas_state()
        
        new_idx = self.current_index + direction
        if 0 <= new_idx < len(self.images_data):
            self.current_index = new_idx
            self.load_image_by_index(new_idx)
            self.update_gui_labels()

    def load_image_by_index(self, idx):
        data = self.images_data[idx]
        self.original_image = data["image"]
        self.status_label.configure(text=data["ocr_msg"] if data["ocr_done"] else "Připraveno na OCR")
        self.show_image_on_canvas(draw_boxes=True)

    def _save_current_canvas_state(self):
        if self.current_index == -1: return
        self.images_data[self.current_index]["coords"]["price"] = self._get_coords("price")
        self.images_data[self.current_index]["coords"]["date"] = self._get_coords("date")

    def _get_coords(self, key):
        rects = self.canvas.find_withtag(f"group_{key}&&rect")
        if not rects: return None
        x1, y1, x2, y2 = self.canvas.coords(rects[0])
        if self.scale_ratio > 0:
            return [[int(x/self.scale_ratio), int(y/self.scale_ratio)] 
                    for x,y in [(x1,y1), (x2,y1), (x2,y2), (x1,y2)]]
        return None

    def update_gui_labels(self):
        total = len(self.images_data)
        self.counter_label.configure(text=f"{self.current_index + 1} / {total}")
        if 0 <= self.current_index < total:
            self.path_label.configure(text=os.path.basename(self.images_data[self.current_index]["path"]))
        
        self.btn_prev.configure(state="normal" if self.current_index > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_index < total - 1 else "disabled")

    # --- OCR THREAD ---
    def start_ocr_process(self):
        if self.ocr_engine is None: return
        self.process_btn.configure(state="disabled")
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()
        self.status_label.configure(text="Pracuji...")
        
        self._ocr_thread = threading.Thread(target=self.ocr_thread_logic)
        self._ocr_thread.start()
        self.monitor_ocr_thread()

    def ocr_thread_logic(self):
        if self.ocr_engine is None: return
        
        data = self.images_data[self.current_index]
        try:
            self.ocr_engine.analyze_image(data["path"])
            data["coords"]["price"] = self.ocr_engine.get_price_coords()
            data["coords"]["date"] = self.ocr_engine.get_date_coords()
            price = self.ocr_engine.get_price()
            data["ocr_done"] = True
            data["ocr_msg"] = f"Hotovo. Cena: {price}"
            self._thread_result_msg = data["ocr_msg"]
        except Exception as e:
            self._thread_result_msg = f"Chyba: {e}"

    def monitor_ocr_thread(self):
        if self._ocr_thread and self._ocr_thread.is_alive():
            self.after(100, self.monitor_ocr_thread)
        else:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.status_label.configure(text=self._thread_result_msg)
            self.show_image_on_canvas(draw_boxes=True)
            self.process_btn.configure(state="normal")

    # --- FINALIZE ---
    def finalize_and_close(self):
        self._save_current_canvas_state()
        export_list = []
        for item in self.images_data:
            export_list.append({
                "filepath": item["path"],
                "price_coords": item["coords"]["price"],
                "date_coords": item["coords"]["date"]
            })
        self.final_output_data = export_list
        self.destroy()

def create_window():
    app = FileSelectorApp()
    app.mainloop()
    return app.final_output_data

if __name__ == "__main__":
    create_window()