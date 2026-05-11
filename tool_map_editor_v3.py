import pygame
import numpy as np
import pandas as pd
import os
import tkinter as tk
from tkinter import simpledialog

# === 設定參數 ===
TILE_SIZE = 40
MAP_PATH = "..\\Assets_Drive\\map.csv"
BG_PATH = "..\\Assets_Drive\\background_field1a.png"
SAVE_PATH = "..\\Assets_Drive\\background_field1a_map_map.csv"

# === 初始化 Pygame ===
pygame.init()
font = pygame.font.SysFont("arial", 16)

# === 1. 取得背景資訊並建立基準 ===
if not os.path.exists(BG_PATH):
    print(f"找不到背景圖: {BG_PATH}")
    pygame.quit()
    exit()

# 修正：先加載圖片，稍後在 set_mode 後執行 convert()
bg_image_raw = pygame.image.load(BG_PATH)
img_w, img_h = bg_image_raw.get_size()

# MAP_WIDTH = img_w // TILE_SIZE
# MAP_HEIGHT = img_h // TILE_SIZE
MAP_WIDTH=44
MAP_HEIGHT=18

screen = pygame.display.set_mode((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
bg_image = pygame.transform.scale(bg_image_raw.convert(), (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

pygame.display.set_caption(f"熱血引擎地圖編輯器 - 模式: {MAP_WIDTH}x{MAP_HEIGHT}")

# === 2. 載入地圖資料 ===
terrain = np.zeros((MAP_HEIGHT, MAP_WIDTH), dtype=int)

if os.path.exists(MAP_PATH):
    try:
        loaded_data = pd.read_csv(MAP_PATH, header=None).values
        h, w = min(MAP_HEIGHT, loaded_data.shape[0]), min(MAP_WIDTH, loaded_data.shape[1])
        terrain[:h, :w] = loaded_data[:h, :w]
    except Exception as e:
        print(f"載入 CSV 失敗: {e}")


def draw_grid():
    screen.blit(bg_image, (0, 0))
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, (100, 100, 100), rect, 1)
            z = terrain[y, x]
            color = (255, 0, 0) if z >= 2 else (200, 200, 200)
            text = font.render(str(z), True, color)
            screen.blit(text, (x * TILE_SIZE + 5, y * TILE_SIZE + 5))


def save_map():
    pd.DataFrame(terrain).to_csv(SAVE_PATH, header=False, index=False)
    print(f"地圖已儲存至: {SAVE_PATH}")


# === 主迴圈變數 ===
running = True
clock = pygame.time.Clock()
selecting = False
start_pos = None
end_pos = None

while running:
    draw_grid()

    # 繪製框選視覺回饋
    if selecting and start_pos and end_pos:
        rect_x = min(start_pos[0], end_pos[0])
        rect_y = min(start_pos[1], end_pos[1])
        rect_w = abs(start_pos[0] - end_pos[0])
        rect_h = abs(start_pos[1] - end_pos[1])
        pygame.draw.rect(screen, (0, 255, 255), (rect_x, rect_y, rect_w, rect_h), 2)

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_map()
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左鍵：開始框選
                selecting = True
                start_pos = pygame.mouse.get_pos()
                end_pos = start_pos
            elif event.button == 3:  # 右鍵：減少單格高度
                mx, my = pygame.mouse.get_pos()
                grid_x, grid_y = mx // TILE_SIZE, my // TILE_SIZE
                if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
                    terrain[grid_y, grid_x] = max(0, terrain[grid_y, grid_x] - 1)

        elif event.type == pygame.MOUSEMOTION:
            if selecting:
                end_pos = pygame.mouse.get_pos()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and selecting:
                selecting = False
                # 計算格子範圍
                gx1, gy1 = start_pos[0] // TILE_SIZE, start_pos[1] // TILE_SIZE
                gx2, gy2 = end_pos[0] // TILE_SIZE, end_pos[1] // TILE_SIZE

                min_x, max_x = max(0, min(gx1, gx2)), min(MAP_WIDTH - 1, max(gx1, gx2))
                min_y, max_y = max(0, min(gy1, gy2)), min(MAP_HEIGHT - 1, max(gy1, gy2))

                # 彈出輸入視窗
                root = tk.Tk()
                root.withdraw()
                new_z = simpledialog.askinteger("批次修改", f"輸入區域 ({min_x},{min_y})~({max_x},{max_y}) 的 Z 值:",
                                                initialvalue=0)
                root.destroy()

                if new_z is not None:
                    terrain[min_y:max_y + 1, min_x:max_x + 1] = new_z

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                save_map()
            elif event.key == pygame.K_c and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                terrain.fill(0)
                print("地圖已重置")

    clock.tick(60)

pygame.quit()

