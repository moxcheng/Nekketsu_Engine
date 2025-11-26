import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
from sklearn.cluster import KMeans

class PixelArtFixer:
    def __init__(self, root):
        self.root = root
        self.root.title("像素圖片修整工具（支援透明背景）")

        # 初始化參數
        self.img_path = None
        self.ref_path = None
        self.corrected_path = None
        self.block_size = 8
        self.zoom_percent = 100

        # Scrollable Canvas 建立
        self.scroll_frame = tk.Frame(root)
        self.scroll_frame.grid(row=0, column=0, columnspan=2)
        self.canvas = tk.Canvas(self.scroll_frame, width=1280, height=720)
        self.scrollbar_y = tk.Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = tk.Scrollbar(self.scroll_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.canvas.grid(row=0, column=0)
        self.scrollbar_y.grid(row=0, column=1, sticky='ns')
        self.scrollbar_x.grid(row=1, column=0, sticky='we')
        self.image_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.image_frame, anchor='nw')

        # 左右圖片顯示區
        self.label_original = tk.Label(self.image_frame, text="原始圖片")
        self.label_corrected = tk.Label(self.image_frame, text="修整後圖片")
        self.label_original.grid(row=0, column=0, padx=10)
        self.label_corrected.grid(row=0, column=1, padx=10)

        # 控制按鈕與滑桿
        self.btn_load_img = tk.Button(root, text="載入圖片", command=self.load_image)
        self.btn_load_ref = tk.Button(root, text="載入範例圖片", command=self.load_reference)
        self.btn_process = tk.Button(root, text="修整色彩", command=self.process_image)
        self.btn_save = tk.Button(root, text="儲存修整圖片", command=self.save_corrected_image)

        self.btn_load_img.grid(row=1, column=0)
        self.btn_load_ref.grid(row=1, column=1)
        self.btn_process.grid(row=2, column=0, columnspan=2)
        self.btn_save.grid(row=3, column=0, columnspan=2)

        self.slider_block = tk.Scale(root, from_=2, to=32, orient=tk.HORIZONTAL,
                                     label="區塊大小", command=self.update_block_size)
        self.slider_block.set(self.block_size)
        self.slider_block.grid(row=4, column=0, columnspan=2)

        self.slider_zoom = tk.Scale(root, from_=50, to=200, orient=tk.HORIZONTAL,
                                    label="縮放比例 (%)", command=self.update_zoom)
        self.slider_zoom.set(self.zoom_percent)
        self.slider_zoom.grid(row=5, column=0, columnspan=2)

    def load_image(self):
        self.img_path = filedialog.askopenfilename()
        self.show_image(self.img_path, self.label_original)

    def load_reference(self):
        self.ref_path = filedialog.askopenfilename()

    def update_block_size(self, val):
        self.block_size = int(val)

    def update_zoom(self, val):
        self.zoom_percent = int(val)
        if self.img_path:
            self.show_image(self.img_path, self.label_original)
        if self.corrected_path:
            self.show_image(self.corrected_path, self.label_corrected)

    def show_image(self, path, container):
        img = Image.open(path).convert('RGBA')
        w, h = img.size
        new_size = (w * self.zoom_percent // 100, h * self.zoom_percent // 100)
        img_resized = img.resize(new_size)
        img_tk = ImageTk.PhotoImage(img_resized)
        container.config(image=img_tk)
        container.image = img_tk
        self.image_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def process_image(self):
        if not self.img_path or not self.ref_path:
            print("請先載入圖片與範例圖片")
            return
        palette = self.extract_palette(self.ref_path)
        corrected_img = self.apply_color_correction(self.img_path, palette, self.block_size)
        self.corrected_path = "corrected_preview_rgba.png"
        corrected_img.save(self.corrected_path)
        self.show_image(self.corrected_path, self.label_corrected)

    def extract_palette(self, image_path, num_colors=8):
        img = Image.open(image_path).convert('RGB')  # 色盤不需透明
        img_small = img.resize((64, 64))
        pixels = np.array(img_small).reshape(-1, 3)
        kmeans = KMeans(n_clusters=num_colors, random_state=42).fit(pixels)
        return kmeans.cluster_centers_.astype(int)

    def apply_color_correction(self, image_path, palette, block_size):
        img = Image.open(image_path).convert('RGBA')
        img_np = np.array(img)
        h, w = img_np.shape[:2]
        output = np.zeros_like(img_np)

        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                block = img_np[y:y+block_size, x:x+block_size]
                # 排除完全透明區塊
                alpha_block = block[:, :, 3]
                if np.all(alpha_block == 0):
                    output[y:y+block_size, x:x+block_size] = block
                    continue
                avg_color = block.reshape(-1, 4).mean(axis=0)
                corrected_rgb = self.closest_color(avg_color[:3], palette)
                corrected_pixel = np.array([*corrected_rgb, avg_color[3]])  # 保留透明度
                output[y:y+block_size, x:x+block_size] = corrected_pixel

        return Image.fromarray(output.astype(np.uint8), 'RGBA')

    def closest_color(self, color, palette):
        distances = [np.linalg.norm(color - p) for p in palette]
        return palette[np.argmin(distances)]

    def save_corrected_image(self):
        if not self.corrected_path:
            print("尚未有修整圖片")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"),
                                                            ("All files", "*.*")])
        if save_path:
            Image.open(self.corrected_path).save(save_path)
            print(f"已儲存圖片：{save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PixelArtFixer(root)
    root.mainloop()