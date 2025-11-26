from PIL import Image, ImageDraw

# 圖片尺寸與格子大小
width, height = 1280, 1920
grid_size = 320

# 建立全透明底圖
img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 畫格線（每320像素）
for x in range(0, width, grid_size):
    draw.line([(x, 0), (x, height)], fill=(0, 0, 0, 128), width=2)
for y in range(0, height, grid_size):
    draw.line([(0, y), (width, y)], fill=(0, 0, 0, 128), width=2)

# 儲存為PNG（含透明背景）
img.save("transparent_grid_1280x1920.png")
