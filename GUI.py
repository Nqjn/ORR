import tkinter
import customtkinter as ctk
from tkinter import filedialog
import os
from PIL import Image, ImageOps, ImageTk 
import threading
from typing import Any, List, Optional

# --- IMPORT VLASTNÍHO OCR ---
try:
    from MyOCR import MyOCR, ReturnPriceCoords, ReturnPrice
except ImportError:
    print("WARNING: MyOCR.py file not found. OCR features will not work.")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class FileSelectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- DATA ---
        self.selected_path = None
        self.ocr_raw_data = None 
        
        # Zde budeme držet originální PIL obrázek pro opakované zmenšování
        self.original_image = None 
        self._tk_image_ref = None # Reference pro tkinter (aby ji nesmazal GC)
        
        self.scale_ratio = 1.0
        
        # Drag & Drop proměnné
        self.drag_data = {
            "x": 0, "y": 0, 
            "item": None,
            "mode": None,
            "group_tag": None,
            "corner": None
        }
        
        self.detected_coords: dict[str, Any] = {"price": None, "date": None}
        self.final_output_data = None 

        # Vlákna
        self._thread_result_image = None 
        self._thread_result_msg = ""
        self._ocr_thread = None 

        # --- GUI ---
        self.title("OCR - File Selection (Responsive)")
        self.geometry("1200x800")

        # Inicializace OCR
        self.ocr_engine = None
        try:
            self.ocr_engine = MyOCR()
        except: pass

        # === LEFT PANEL ===
        self.control_frame = ctk.CTkFrame(self, width=250)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.control_frame, text="Select File:", font=("Arial", 16)).pack(pady=(20, 10))
        
        self.select_btn = ctk.CTkButton(self.control_frame, text="Open Image...", command=self.open_file_dialog)
        self.select_btn.pack(pady=10)

        self.path_label = ctk.CTkLabel(self.control_frame, text="...", text_color="gray", wraplength=230)
        self.path_label.pack(pady=5)

        self.process_btn = ctk.CTkButton(
            self.control_frame, text="Start OCR", command=self.start_ocr_process, 
            state="disabled", fg_color="green"
        )
        self.process_btn.pack(pady=20) 
        
        self.progress_bar = ctk.CTkProgressBar(self.control_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

        self.status_label = ctk.CTkLabel(self.control_frame, text="", wraplength=230)
        self.status_label.pack(pady=5)

        # MANUAL CONTROLS
        self.frame_manual = ctk.CTkFrame(self.control_frame)
        self.frame_manual.pack(pady=20, fill="x", padx=5)
        ctk.CTkLabel(self.frame_manual, text="Manual Correction:", font=("Arial", 12, "bold")).pack(pady=5)
        ctk.CTkButton(self.frame_manual, text="+ Add Price Box", fg_color="red", 
                      command=lambda: self.add_manual_box("price", "red")).pack(pady=5, padx=5, fill="x")
        ctk.CTkButton(self.frame_manual, text="+ Add Date Box", fg_color="blue", 
                      command=lambda: self.add_manual_box("date", "blue")).pack(pady=5, padx=5, fill="x")

        # === RIGHT PANEL (IMAGE CANVAS) ===
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Canvas
        self.canvas = tkinter.Canvas(self.image_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Placeholder text
        self.text_id = self.canvas.create_text(
            400, 300, text="Image Preview", fill="gray", font=("Arial", 16)
        )

        # === BINDING EVENTS ===
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)
        
        # DŮLEŽITÉ: Bindování změny velikosti okna
        self.canvas.bind("<Configure>", self.on_resize)

    # --- RESIZING LOGIC ---
    def on_resize(self, event):
        """Volá se automaticky, když se změní velikost okna/canvasu."""
        if self.original_image:
            # Překreslíme obrázek podle nové velikosti canvasu
            self.show_image_on_canvas(draw_boxes=True)

    def show_image_on_canvas(self, draw_boxes=False):
        """Vypočítá novou velikost a vykreslí obrázek i boxy."""
        if self.original_image is None: return

        # Zjistíme aktuální rozměry canvasu
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Pokud je canvas příliš malý (např. při startu), nic neděláme
        if canvas_width < 10 or canvas_height < 10: return

        self.canvas.delete("all")

        # --- MATEMATIKA FIT-TO-WINDOW ---
        img_w, img_h = self.original_image.size
        
        # Spočítáme poměry
        ratio_w = canvas_width / img_w
        ratio_h = canvas_height / img_h
        
        # Vybereme menší poměr -> obrázek se vejde celý (contain)
        self.scale_ratio = min(ratio_w, ratio_h)
        
        new_w = int(img_w * self.scale_ratio)
        new_h = int(img_h * self.scale_ratio)

        # Změníme velikost obrázku (používáme originál jako zdroj!)
        resized_pil = self.original_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self._tk_image_ref = ImageTk.PhotoImage(resized_pil)

        # Vykreslíme (zarovnáno vlevo nahoře 0,0 - nejjednodušší pro souřadnice)
        self.canvas.create_image(0, 0, image=self._tk_image_ref, anchor="nw")

        # Pokud máme zapnuté boxy, vykreslíme je na nových pozicích
        if draw_boxes:
            if self.detected_coords.get("price"):
                self.create_interactive_box(self.detected_coords["price"], "red", "price")
            if self.detected_coords.get("date"):
                self.create_interactive_box(self.detected_coords["date"], "blue", "date")

    # --- CANVAS BOX LOGIC ---
    def create_interactive_box(self, raw_coords, color, type_key):
        group_tag = f"group_{type_key}"
        self.canvas.delete(group_tag)

        if raw_coords:
            xs = [pt[0] for pt in raw_coords]
            ys = [pt[1] for pt in raw_coords]
            x1 = min(xs) * self.scale_ratio
            y1 = min(ys) * self.scale_ratio
            x2 = max(xs) * self.scale_ratio
            y2 = max(ys) * self.scale_ratio
        else:
            # Default na střed obrazovky
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            w, h = 100, 40
            x1, y1 = (cw/2 - w/2), (ch/2 - h/2)
            x2, y2 = (cw/2 + w/2), (ch/2 + h/2)

        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags=(group_tag, "rect", "movable"))
        self._draw_handle(x1, y1, group_tag, "NW", color)
        self._draw_handle(x2, y1, group_tag, "NE", color)
        self._draw_handle(x2, y2, group_tag, "SE", color)
        self._draw_handle(x1, y2, group_tag, "SW", color)

    def _draw_handle(self, x, y, group_tag, corner, color):
        size = 6 
        self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            fill=color, outline="white",
            tags=(group_tag, "handle", f"corner_{corner}", "movable")
        )

    def add_manual_box(self, type_key, color):
        if self.original_image:
            self.create_interactive_box(None, color, type_key)
        else:
            self.status_label.configure(text="Load image first.")

    # --- DRAG & DROP LOGIC ---
    def on_drag_start(self, event):
        closest = self.canvas.find_closest(event.x, event.y)
        if not closest: return
        item_id = closest[0]
        tags = self.canvas.gettags(item_id)
        if "movable" not in tags: return

        group_tag = next((t for t in tags if t.startswith("group_")), None)
        self.drag_data.update({"item": item_id, "x": event.x, "y": event.y, "group_tag": group_tag})

        if "handle" in tags:
            self.drag_data["mode"] = "RESIZE"
            self.drag_data["corner"] = next((t.split("_")[1] for t in tags if t.startswith("corner_")), None)
            self.canvas.configure(cursor="crosshair")
        else:
            self.drag_data["mode"] = "MOVE"
            self.canvas.configure(cursor="fleur")

    def on_drag_motion(self, event):
        if not self.drag_data["group_tag"]: return
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        group = self.drag_data["group_tag"]

        if self.drag_data["mode"] == "MOVE":
            self.canvas.move(group, dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        elif self.drag_data["mode"] == "RESIZE":
            rect_ids = self.canvas.find_withtag(f"{group}&&rect")
            if not rect_ids: return
            x1, y1, x2, y2 = self.canvas.coords(rect_ids[0])
            corner = self.drag_data["corner"]
            
            if corner == "NW": x1, y1 = event.x, event.y
            elif corner == "NE": x2, y1 = event.x, event.y
            elif corner == "SE": x2, y2 = event.x, event.y
            elif corner == "SW": x1, y2 = event.x, event.y
            
            nx1, nx2 = min(x1, x2), max(x1, x2)
            ny1, ny2 = min(y1, y2), max(y1, y2)
            
            self.canvas.coords(rect_ids[0], nx1, ny1, nx2, ny2)
            self._update_handles(group, nx1, ny1, nx2, ny2)

    def _update_handles(self, group, x1, y1, x2, y2):
        s = 6
        self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NW")[0], x1-s, y1-s, x1+s, y1+s)
        self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_NE")[0], x2-s, y1-s, x2+s, y1+s)
        self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SE")[0], x2-s, y2-s, x2+s, y2+s)
        self.canvas.coords(self.canvas.find_withtag(f"{group}&&corner_SW")[0], x1-s, y2-s, x1+s, y2+s)

    def on_drag_stop(self, event):
        self.drag_data["item"] = None
        self.drag_data["group_tag"] = None
        self.canvas.configure(cursor="")

    # --- FILE & OCR LOGIC ---
    def open_file_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg"), ("All", "*.*")])
        if path:
            self.selected_path = path
            self.path_label.configure(text=f"Selected: {os.path.basename(path)}")
            self.process_btn.configure(state="normal")
            
            # Load raw image
            self.detected_coords = {"price": None, "date": None}
            self.original_image = self._load_image(path) # Save original!
            self.show_image_on_canvas()

    def _load_image(self, path):
        try:
            img = Image.open(path)
            try: img = ImageOps.exif_transpose(img)
            except: pass
            return img.convert("RGB")
        except Exception as e:
            print(f"Error loading: {e}")
            return None

    def start_ocr_process(self):
        if self.ocr_engine is None: return
        self.process_btn.configure(state="disabled")
        self.select_btn.configure(state="disabled")
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()
        self.status_label.configure(text="Running OCR...")
        
        self._ocr_thread = threading.Thread(target=self.ocr_thread_logic)
        self._ocr_thread.start()
        self.monitor_ocr_thread()

    def ocr_thread_logic(self):
        if not self.ocr_engine or not self.selected_path: return
        try:
            self.ocr_raw_data = self.ocr_engine.analyze_image(self.selected_path)
            self.detected_coords["price"] = self.ocr_engine.get_price_coords()
            self.detected_coords["date"] = self.ocr_engine.get_date_coords()
            price = self.ocr_engine.get_price()
            self._thread_result_msg = f"Done. Price: {price}"
        except Exception as e:
            self._thread_result_msg = f"Error: {e}"

    def monitor_ocr_thread(self):
        if self._ocr_thread and self._ocr_thread.is_alive():
            self.after(100, self.monitor_ocr_thread)
        else:
            self.finalize_gui_update()

    def finalize_gui_update(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text=self._thread_result_msg)
        # Refresh canvas with new boxes
        self.show_image_on_canvas(draw_boxes=True)
        self.process_btn.configure(state="normal", text="Finish", command=self.finalize_and_close)
        self.select_btn.configure(state="normal")

    def _get_coords_from_canvas(self, type_key):
        group = f"group_{type_key}"
        rects = self.canvas.find_withtag(f"{group}&&rect")
        if not rects: return None
        x1, y1, x2, y2 = self.canvas.coords(rects[0])
        
        # Convert back to original scale
        if self.scale_ratio > 0:
            rx1 = int(x1 / self.scale_ratio)
            ry1 = int(y1 / self.scale_ratio)
            rx2 = int(x2 / self.scale_ratio)
            ry2 = int(y2 / self.scale_ratio)
            return [[rx1, ry1], [rx2, ry1], [rx2, ry2], [rx1, ry2]]
        return None

    def finalize_and_close(self):
        new_price = self._get_coords_from_canvas("price")
        new_date = self._get_coords_from_canvas("date")
        self.final_output_data = {
            "price_coords": new_price,
            "date_coords": new_date,
            "filepath": self.selected_path
        }
        print(f"Final Data: {self.final_output_data}")
        self.destroy()

def create_window():
    app = FileSelectorApp()
    app.mainloop()
    return app.final_output_data if hasattr(app, 'final_output_data') else None

if __name__ == "__main__":
    create_window()