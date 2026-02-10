import os
import math
import time
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
import random

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Error", "Library Pillow tidak ditemukan.\nJalankan: pip install Pillow")
    exit()

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    messagebox.showerror("Error", "Library Matplotlib tidak ditemukan.\nJalankan: pip install matplotlib")
    exit()

def arnold_cat_map(image_array, iterasi):
    """Mengacak posisi piksel menggunakan ACM dengan parameter a=1, b=1."""
    a, b = 1, 1
    n = image_array.shape[0]
    processed_array = np.copy(image_array)
    for _ in range(iterasi):
        temp_array = np.zeros_like(processed_array)
        for y in range(n):
            for x in range(n):
                x_baru = (x + a * y) % n
                y_baru = (b * x + (a * b + 1) * y) % n
                temp_array[y_baru, x_baru] = processed_array[y, x]
        processed_array = temp_array
    return processed_array

def inverse_arnold_cat_map(image_array, iterasi):
    """Mengembalikan posisi piksel menggunakan invers ACM dengan parameter a=1, b=1."""
    a, b = 1, 1
    n = image_array.shape[0]
    processed_array = np.copy(image_array)
    for _ in range(iterasi):
        temp_array = np.zeros_like(processed_array)
        for y in range(n):
            for x in range(n):
                x_baru = ((a * b + 1) * x - a * y) % n
                y_baru = (-b * x + y) % n
                temp_array[y_baru, x_baru] = processed_array[y, x]
        processed_array = temp_array
    return processed_array

def generate_keystream_duffing_map(n, x0, y0, channels=3):
    """Menghasilkan keystream menggunakan Duffing Map untuk jumlah kanal yang sesuai."""
    duffing_a, duffing_b = 2.75, 0.2
    total_values = n * n * channels
    keystream_sequence = []
    x, y = x0, y0
    
    # "Warm-up" iterasi
    for _ in range(1000):
        x_new = y
        y_new = -duffing_b * x + duffing_a * y - y**3
        x, y = x_new, y_new
        
    # Generate nilai untuk keystream
    for _ in range(total_values):
        x_new = y
        y_new = -duffing_b * x + duffing_a * y - y**3
        x, y = x_new, y_new
        key_val = int(abs(y) % 1 * 256)
        keystream_sequence.append(key_val)
        
    keystream_array = np.array(keystream_sequence, dtype=np.uint8)
    if channels == 1:
        return keystream_array.reshape((n, n))
    else:
        return keystream_array.reshape((n, n, 3))

def calculate_pixel_correlation(image_array, num_pixels=5000):
    if image_array.ndim == 3:
        image_array = np.array(Image.fromarray(image_array).convert('L'))
    h, w = image_array.shape

    x_h, y_h, x_v, y_v, x_d, y_d = [], [], [], [], [], []
    num_pixels = min(num_pixels, (w - 1) * (h - 1))
    if num_pixels <= 0: return (0,0,0)

    for _ in range(num_pixels):
        x = random.randint(0, w - 2); y = random.randint(0, h - 2)
        x_h.append(image_array[y, x]); y_h.append(image_array[y, x + 1])
        x_v.append(image_array[y, x]); y_v.append(image_array[y + 1, x])
        x_d.append(image_array[y, x]); y_d.append(image_array[y + 1, x + 1])
    
    corr_h = np.corrcoef(x_h, y_h)[0, 1] if len(x_h) > 1 else 0
    corr_v = np.corrcoef(x_v, y_v)[0, 1] if len(x_v) > 1 else 0
    corr_d = np.corrcoef(x_d, y_d)[0, 1] if len(x_d) > 1 else 0
    return corr_h, corr_v, corr_d

def calculate_entropy(image_array):
    if image_array.ndim == 2: channels = [image_array]
    else: channels = [image_array[:, :, i] for i in range(3)]
    total_entropy = 0
    for channel in channels:
        counts = np.histogram(channel, bins=256, range=(0, 256))[0]
        total_pixels = counts.sum()
        if total_pixels == 0: continue
        probabilities = counts / total_pixels
        channel_entropy = -np.sum(probabilities[probabilities > 0] * np.log2(probabilities[probabilities > 0]))
        total_entropy += channel_entropy
    return total_entropy / len(channels)

def format_file_size(size_bytes):
    if size_bytes == 0: return "0 B"
    try:
        size_names = ("B", "KB", "MB", "GB", "TB"); i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
        p = math.pow(1024, i); s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    except (ValueError, IndexError): return "N/A"

class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        tk.Label(self, text="Aplikasi Kriptografi Citra", font=controller.title_font).pack(side="top", fill="x", pady=20)
        tk.Label(self, text="Pilih menu di bawah ini untuk memulai", font=("Arial", 12)).pack(side="top", fill="x", pady=5)
        button_frame = tk.Frame(self); button_frame.pack(pady=20)
        button_width = 45
        tk.Button(button_frame, text="Enkripsi Gambar", width=button_width, height=2, command=lambda: controller.show_frame("EncryptionPage")).pack(pady=4)
        tk.Button(button_frame, text="Dekripsi Gambar", width=button_width, height=2, command=lambda: controller.show_frame("DecryptionPage")).pack(pady=4)
        tk.Button(button_frame, text="Analisis Statistik", width=button_width, height=2, command=lambda: controller.show_frame("AnalysisPage")).pack(pady=4)
        tk.Button(button_frame, text="Keluar", width=button_width, height=2, command=self.controller.destroy).pack(pady=4)

class BasePage(tk.Frame):
    def setup_key_widgets(self, parent_frame):
        params_frame = tk.LabelFrame(parent_frame, text="Atur Kunci", padx=5, pady=5)
        params_frame.pack(side="left")
        
        tk.Label(params_frame, text="Iterasi ACM:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_iterasi = tk.Entry(params_frame, width=12); self.entry_iterasi.grid(row=0, column=1, pady=2); self.entry_iterasi.insert(0, "10")
        tk.Label(params_frame, text="a:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_x0 = tk.Entry(params_frame, width=12); self.entry_x0.grid(row=1, column=1, pady=2); self.entry_x0.insert(0, "0.1")
        tk.Label(params_frame, text="b:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_y0 = tk.Entry(params_frame, width=12); self.entry_y0.grid(row=2, column=1, pady=2); self.entry_y0.insert(0, "0.1")

class EncryptionPage(BasePage):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent); self.controller = controller
        self.fpath, self.fpath2 = "", ""; self.photo_asli, self.photo_enkripsi = None, None
        self.setup_widgets()

    def setup_widgets(self):
        tk.Label(self, text="Halaman Enkripsi", font=self.controller.title_font).pack(side="top", fill="x", pady=10)
        control_frame = tk.Frame(self, padx=10, pady=10); control_frame.pack(fill="x")
        path_frame = tk.LabelFrame(control_frame, text="Pilih File & Folder Output", padx=5, pady=5); path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.label_file = tk.Label(path_frame, text="File Input: (Belum dipilih)", anchor="w"); self.label_file.grid(row=0, column=0, sticky="ew")
        tk.Button(path_frame, text="Browse...", command=self.browse_file).grid(row=0, column=1, padx=5)
        self.label_folder = tk.Label(path_frame, text="Folder Output: (Belum dipilih)", anchor="w"); self.label_folder.grid(row=1, column=0, sticky="ew")
        tk.Button(path_frame, text="Browse...", command=self.browse_output_folder).grid(row=1, column=1, padx=5)
        path_frame.columnconfigure(0, weight=1)
        self.setup_key_widgets(control_frame)
        preview_frame = tk.Frame(self, padx=10, pady=10); preview_frame.pack(fill="both", expand=True)
        frame_asli = tk.LabelFrame(preview_frame, text="Citra Asli", font=("Arial", 10, "bold")); frame_asli.pack(side="left", fill="both", expand=True, padx=5)
        self.panel_asli = tk.Label(frame_asli, text="Pilih gambar input", bg="lightgrey"); self.panel_asli.pack(fill="both", expand=True)
        frame_enkripsi = tk.LabelFrame(preview_frame, text="Citra Terenkripsi", font=("Arial", 10, "bold")); frame_enkripsi.pack(side="left", fill="both", expand=True, padx=5)
        self.panel_enkripsi = tk.Label(frame_enkripsi, text="Hasil enkripsi akan tampil di sini", bg="lightgrey"); self.panel_enkripsi.pack(fill="both", expand=True)
        status_frame = tk.LabelFrame(self, text="Status Proses Terakhir", padx=10, pady=5); status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        self.status_label = tk.Label(status_frame, text="Belum ada proses yang dijalankan."); self.status_label.pack()
        action_frame = tk.Frame(self); action_frame.pack(side="bottom", fill="x", pady=5)
        tk.Button(action_frame, text="ENKRIPSI GAMBAR", height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.encrypt_image).pack(side="right", padx=10)
        tk.Button(action_frame, text="Kembali ke Menu", height=2, command=lambda: self.controller.show_frame("HomePage")).pack(side="left", padx=10)

    def browse_file(self):
        fpath = filedialog.askopenfilename(filetypes=(("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")))
        if fpath: self.fpath = fpath; self.label_file.config(text="Input: " + os.path.basename(fpath)); self.display_image(self.fpath, self.panel_asli, "photo_asli"); self.panel_enkripsi.config(image=None, text="Hasil enkripsi akan tampil di sini"); self.photo_enkripsi = None
    
    def browse_output_folder(self):
        fpath2 = filedialog.askdirectory();
        if fpath2: self.fpath2 = fpath2; self.label_folder.config(text="Output: " + fpath2)
    
    def display_image(self, fp, target, attr):
        try: img = Image.open(fp); img.thumbnail((350, 350), Image.LANCZOS); photo = ImageTk.PhotoImage(img); target.config(image=photo, text=""); setattr(self, attr, photo)
        except Exception as e: messagebox.showerror("Error Tampil Gambar", f"Gagal memuat gambar: {e}")

    def encrypt_image(self):
        if not self.fpath or not self.fpath2:
            messagebox.showerror("Error", "Pilih file input dan folder output.")
            return
        try:
            iterasi = int(self.entry_iterasi.get())
            x0, y0 = float(self.entry_x0.get()), float(self.entry_y0.get())
        except ValueError:
            messagebox.showerror("Error Input", "Pastikan semua parameter kunci diisi dengan benar (angka).")
            return
            
        try:
            start_time = time.time()
            img = Image.open(self.fpath)
            
            original_mode = img.mode
            if original_mode not in ['L', 'RGB']:
                img = img.convert('RGB')
                original_mode = 'RGB'

            w, h = img.size
            if w != h: 
                size = min(w, h)
                img = img.resize((size, size), Image.LANCZOS)
                if img.mode != original_mode:
                    img = img.convert(original_mode)
            
            arr = np.array(img)
            channels = 1 if arr.ndim == 2 else 3

            permuted_arr = arnold_cat_map(arr, iterasi)
            keystream = generate_keystream_duffing_map(permuted_arr.shape[0], x0, y0, channels=channels)
            final_arr = np.bitwise_xor(permuted_arr, keystream)

            encrypted_img = Image.fromarray(final_arr.astype('uint8'), mode=original_mode)
            
            base = os.path.basename(self.fpath)
            name, _ = os.path.splitext(base)
            out_fn = "Encrypted_" + name + ".png"
            saved_path = os.path.join(self.fpath2, out_fn)
            encrypted_img.save(saved_path, format='PNG')
            
            self.display_image(saved_path, self.panel_enkripsi, "photo_enkripsi")
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.status_label.config(text=f"Waktu Proses: {elapsed_time:.2f} detik. File disimpan di {out_fn}")
            messagebox.showinfo("Sukses", f"Gambar berhasil dienkripsi!\nDisimpan sebagai: {out_fn}\nWaktu Proses: {elapsed_time:.2f} detik.")
        except Exception as e:
            messagebox.showerror("Error Enkripsi", f"Proses enkripsi gagal: {e}")

class DecryptionPage(BasePage):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent); self.controller = controller
        self.fpath, self.fpath2 = "", ""; self.photo_enkripsi, self.photo_dekripsi = None, None
        self.setup_widgets()
        
    def setup_widgets(self):
        tk.Label(self, text="Halaman Dekripsi", font=self.controller.title_font).pack(side="top", fill="x", pady=10)
        control_frame = tk.Frame(self, padx=10, pady=10); control_frame.pack(fill="x")
        path_frame = tk.LabelFrame(control_frame, text="Pilih File Terenkripsi & Folder Output", padx=5, pady=5); path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.label_file = tk.Label(path_frame, text="File Input: (Belum dipilih)", anchor="w"); self.label_file.grid(row=0, column=0, sticky="ew")
        tk.Button(path_frame, text="Browse...", command=self.browse_file).grid(row=0, column=1, padx=5)
        self.label_folder = tk.Label(path_frame, text="Folder Output: (Belum dipilih)", anchor="w"); self.label_folder.grid(row=1, column=0, sticky="ew")
        tk.Button(path_frame, text="Browse...", command=self.browse_output_folder).grid(row=1, column=1, padx=5)
        path_frame.columnconfigure(0, weight=1)
        self.setup_key_widgets(control_frame)
        preview_frame = tk.Frame(self, padx=10, pady=10); preview_frame.pack(fill="both", expand=True)
        frame_enkripsi = tk.LabelFrame(preview_frame, text="Citra Terenkripsi", font=("Arial", 10, "bold")); frame_enkripsi.pack(side="left", fill="both", expand=True, padx=5)
        self.panel_enkripsi = tk.Label(frame_enkripsi, text="Pilih gambar terenkripsi", bg="lightgrey"); self.panel_enkripsi.pack(fill="both", expand=True)
        frame_dekripsi = tk.LabelFrame(preview_frame, text="Citra Terdekripsi", font=("Arial", 10, "bold")); frame_dekripsi.pack(side="left", fill="both", expand=True, padx=5)
        self.panel_dekripsi = tk.Label(frame_dekripsi, text="Hasil dekripsi akan tampil di sini", bg="lightgrey"); self.panel_dekripsi.pack(fill="both", expand=True)
        status_frame = tk.LabelFrame(self, text="Status Proses Terakhir", padx=10, pady=5); status_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        self.status_label = tk.Label(status_frame, text="Belum ada proses yang dijalankan."); self.status_label.pack()
        action_frame = tk.Frame(self); action_frame.pack(side="bottom", fill="x", pady=5)
        tk.Button(action_frame, text="DEKRIPSI GAMBAR", height=2, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), command=self.decrypt_image).pack(side="right", padx=10)
        tk.Button(action_frame, text="Kembali ke Menu", height=2, command=lambda: self.controller.show_frame("HomePage")).pack(side="left", padx=10)
    
    def browse_file(self):
        fpath = filedialog.askopenfilename(filetypes=(("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")))
        if fpath: self.fpath = fpath; self.label_file.config(text="Input: " + os.path.basename(fpath)); self.display_image(self.fpath, self.panel_enkripsi, "photo_enkripsi"); self.panel_dekripsi.config(image=None, text="Hasil dekripsi akan tampil di sini"); self.photo_dekripsi = None
    
    def browse_output_folder(self):
        fpath2 = filedialog.askdirectory();
        if fpath2: self.fpath2 = fpath2; self.label_folder.config(text="Output: " + fpath2)
    
    def display_image(self, fp, target, attr):
        try: img = Image.open(fp); img.thumbnail((350, 350), Image.LANCZOS); photo = ImageTk.PhotoImage(img); target.config(image=photo, text=""); setattr(self, attr, photo)
        except Exception as e: messagebox.showerror("Error Tampil Gambar", f"Gagal memuat gambar: {e}")

    def decrypt_image(self):
        if not self.fpath or not self.fpath2:
            messagebox.showerror("Error", "Pilih file terenkripsi dan folder output.")
            return
        try:
            iterasi = int(self.entry_iterasi.get())
            x0, y0 = float(self.entry_x0.get()), float(self.entry_y0.get())
        except ValueError:
            messagebox.showerror("Error Input", "Pastikan semua parameter kunci diisi dengan benar (angka).")
            return
        try:
            start_time = time.time()
            img = Image.open(self.fpath)
            original_mode = img.mode
            
            encrypted_arr = np.array(img)
            channels = 1 if encrypted_arr.ndim == 2 else 3

            keystream = generate_keystream_duffing_map(encrypted_arr.shape[0], x0, y0, channels=channels)
            undiffused_arr = np.bitwise_xor(encrypted_arr, keystream)
            decrypted_arr = inverse_arnold_cat_map(undiffused_arr, iterasi)
            
            decrypted_img = Image.fromarray(decrypted_arr.astype('uint8'), mode=original_mode)
            
            base = os.path.basename(self.fpath)
            out_fn = "Decrypted_" + base[10:] if base.startswith("Encrypted_") else "Decrypted_" + base
            saved_path = os.path.join(self.fpath2, out_fn)
            decrypted_img.save(saved_path)
            
            self.display_image(saved_path, self.panel_dekripsi, "photo_dekripsi")
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.status_label.config(text=f"Waktu Proses: {elapsed_time:.2f} detik. File disimpan.")
            messagebox.showinfo("Sukses", f"Gambar berhasil didekripsi!")
        except Exception as e:
            messagebox.showerror("Error Dekripsi", f"Proses dekripsi gagal: {e}")

class AnalysisPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent); self.controller = controller
        self.fpath_asli, self.fpath_enkripsi = "", ""
        self.photo_asli_preview, self.photo_enkripsi_preview = None, None
        self.setup_widgets()

    def setup_widgets(self):
        tk.Label(self, text="Halaman Analisis Statistik", font=self.controller.title_font).pack(side="top", fill="x", pady=5)
        top_control_frame = tk.Frame(self, padx=10, pady=5); top_control_frame.pack(fill="x")
        self.label_asli = tk.Label(top_control_frame, text="Citra Asli: (Belum dipilih)", width=50, anchor='w'); self.label_asli.pack(side="left", padx=5)
        tk.Button(top_control_frame, text="Browse Citra Asli...", command=self.browse_original).pack(side="left")
        self.label_enkripsi = tk.Label(top_control_frame, text="Citra Terenkripsi: (Belum dipilih)", width=50, anchor='w'); self.label_enkripsi.pack(side="left", padx=10)
        tk.Button(top_control_frame, text="Browse Citra Terenkripsi...", command=self.browse_encrypted).pack(side="left")
        action_frame = tk.Frame(self); action_frame.pack(side="bottom", fill="x", pady=10, padx=10)
        tk.Button(action_frame, text="LAKUKAN ANALISIS", height=2, bg="#007BFF", fg="white", font=("Arial", 10, "bold"), command=self.perform_analysis).pack(side="right")
        tk.Button(action_frame, text="Kembali ke Menu", height=2, command=lambda: self.controller.show_frame("HomePage")).pack(side="left")
        content_frame = tk.Frame(self, padx=10, pady=5); content_frame.pack(fill="both", expand=True); content_frame.columnconfigure(0, weight=1); content_frame.rowconfigure(1, weight=1)
        preview_frame = tk.Frame(content_frame); preview_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame_asli = tk.LabelFrame(preview_frame, text="Pratinjau Asli", font=("Arial", 9)); frame_asli.pack(side="left", padx=5, fill="both", expand=True)
        self.panel_asli_preview = tk.Label(frame_asli, text="Pilih citra asli", bg="lightgrey"); self.panel_asli_preview.pack(fill="both", expand=True)
        frame_enkripsi = tk.LabelFrame(preview_frame, text="Pratinjau Terenkripsi", font=("Arial", 9)); frame_enkripsi.pack(side="left", padx=5, fill="both", expand=True)
        self.panel_enkripsi_preview = tk.Label(frame_enkripsi, text="Pilih citra terenkripsi", bg="lightgrey"); self.panel_enkripsi_preview.pack(fill="both", expand=True)
        plot_frame = tk.LabelFrame(content_frame, text="Visualisasi Histogram", padx=5, pady=5); plot_frame.grid(row=1, column=0, sticky="nsew")
        self.fig = Figure(figsize=(4, 1.5), dpi=80); self.ax1 = self.fig.add_subplot(121); self.ax2 = self.fig.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame); self.fig.subplots_adjust(left=0.1, right=0.9, bottom=0.2, top=0.8, wspace=0.4)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True); self.canvas.draw()
        metrics_frame = tk.LabelFrame(content_frame, text="Analisis Kuantitatif", padx=2, pady=2); metrics_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        metrics_frame.columnconfigure((1, 2), weight=1)
        tk.Label(metrics_frame, text="Properti/Metrik", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(metrics_frame, text="Citra Asli", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(metrics_frame, text="Citra Terenkripsi", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5)
        self.metric_labels = {}
        metrics = ["Ukuran File:", "Dimensi:", "Entropi:", "Korelasi Horizontal:", "Korelasi Vertikal:", "Korelasi Diagonal:"]
        for i, metric in enumerate(metrics, start=1):
            tk.Label(metrics_frame, text=metric, font=("Arial", 9, "bold")).grid(row=i, column=0, sticky="w", pady=1, padx=5)
            self.metric_labels[metric] = {"asli": tk.Label(metrics_frame, text="-", anchor="w"), "enkripsi": tk.Label(metrics_frame, text="-", anchor="w")}
            self.metric_labels[metric]["asli"].grid(row=i, column=1, sticky="w", padx=5)
            self.metric_labels[metric]["enkripsi"].grid(row=i, column=2, sticky="w", padx=5)

    def display_image(self, fp, target, attr):
        try: img = Image.open(fp); img.thumbnail((250, 250), Image.LANCZOS); photo = ImageTk.PhotoImage(img); target.config(image=photo, text=""); setattr(self, attr, photo)
        except Exception as e: messagebox.showerror("Error Tampil Gambar", f"Gagal memuat gambar: {e}")

    def browse_original(self):
        fpath = filedialog.askopenfilename(title="Pilih Citra Asli")
        if fpath: self.fpath_asli = fpath; self.label_asli.config(text="Asli: " + os.path.basename(fpath)); self.display_image(self.fpath_asli, self.panel_asli_preview, "photo_asli_preview")

    def browse_encrypted(self):
        fpath = filedialog.askopenfilename(title="Pilih Citra Terenkripsi")
        if fpath: self.fpath_enkripsi = fpath; self.label_enkripsi.config(text="Terenkripsi: " + os.path.basename(fpath)); self.display_image(self.fpath_enkripsi, self.panel_enkripsi_preview, "photo_enkripsi_preview")
    
    def perform_analysis(self):
        if not self.fpath_asli or not self.fpath_enkripsi:
            messagebox.showwarning("Peringatan", "Harap pilih kedua file.")
            return
        try:
            img_asli = Image.open(self.fpath_asli)
            arr_asli = np.array(img_asli)
            img_enkripsi = Image.open(self.fpath_enkripsi)
            arr_enkripsi = np.array(img_enkripsi)
            
            self.metric_labels["Ukuran File:"]["asli"].config(text=format_file_size(os.path.getsize(self.fpath_asli)))
            self.metric_labels["Ukuran File:"]["enkripsi"].config(text=format_file_size(os.path.getsize(self.fpath_enkripsi)))
            self.metric_labels["Dimensi:"]["asli"].config(text=f"{img_asli.width}x{img_asli.height}")
            self.metric_labels["Dimensi:"]["enkripsi"].config(text=f"{img_enkripsi.width}x{img_enkripsi.height}")
            
            self.metric_labels["Entropi:"]["asli"].config(text=f"{calculate_entropy(arr_asli):.4f}")
            self.metric_labels["Entropi:"]["enkripsi"].config(text=f"{calculate_entropy(arr_enkripsi):.4f}")

            corr_asli = calculate_pixel_correlation(arr_asli)
            corr_enkripsi = calculate_pixel_correlation(arr_enkripsi)
            self.metric_labels["Korelasi Horizontal:"]["asli"].config(text=f"{corr_asli[0]:.4f}")
            self.metric_labels["Korelasi Horizontal:"]["enkripsi"].config(text=f"{corr_enkripsi[0]:.4f}")
            self.metric_labels["Korelasi Vertikal:"]["asli"].config(text=f"{corr_asli[1]:.4f}")
            self.metric_labels["Korelasi Vertikal:"]["enkripsi"].config(text=f"{corr_enkripsi[1]:.4f}")
            self.metric_labels["Korelasi Diagonal:"]["asli"].config(text=f"{corr_asli[2]:.4f}")
            self.metric_labels["Korelasi Diagonal:"]["enkripsi"].config(text=f"{corr_enkripsi[2]:.4f}")

            self.ax1.clear(); self.ax2.clear()
            self.ax1.set_title("Histogram Citra Asli")
            if arr_asli.ndim == 2:
                self.ax1.hist(arr_asli.flatten(), bins=256, color='gray')
            else:
                colors = ('red', 'green', 'blue')
                for i, color in enumerate(colors):
                    self.ax1.hist(arr_asli[:, :, i].flatten(), bins=256, color=color, alpha=0.7)
            
            self.ax2.set_title("Histogram Citra Terenkripsi")
            if arr_enkripsi.ndim == 2:
                self.ax2.hist(arr_enkripsi.flatten(), bins=256, color='gray')
            else:
                colors = ('red', 'green', 'blue')
                for i, color in enumerate(colors):
                    self.ax2.hist(arr_enkripsi[:, :, i].flatten(), bins=256, color=color, alpha=0.7)
            
            self.fig.tight_layout(); self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Error Analisis", f"Gagal melakukan analisis: {e}")

class CryptoApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("Aplikasi Kriptografi Citra v1.2 (Final Fix)")
        self.geometry("1100x850")
        self.title_font = ("Arial", 18, "bold")
        container = tk.Frame(self); container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1); container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (HomePage, EncryptionPage, DecryptionPage, AnalysisPage):
            page_name = F.__name__; frame = F(container, self); self.frames[page_name] = frame; frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("HomePage")
    
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

if __name__ == "__main__":
    app = CryptoApp()
    app.mainloop()