import pygame
import numpy as np
import pandas as pd
import os

# === 設定參數 ===
TILE_SIZE = 40  # 參考 Config.py
MAP_PATH = "..\\Assets_Drive\\map.csv"
BG_PATH = "..\\Assets_Drive\\background_field1a.png"
SAVE_PATH = "..\\Assets_Drive\\map.csv"  # 直接覆蓋原檔或另存 edited_map.csv

# === 初始化 Pygame ===
pygame.init()
font = pygame.font.SysFont("arial", 16)

# === 1. 取得背景資訊並建立基準 ===
if not os.path.exists(BG_PATH):
    print(f"找不到背景圖: {BG_PATH}")
    pygame.quit()
    exit()

bg_image_raw = pygame.image.load(BG_PATH).convert()
img_w, img_h = bg_image_raw.get_size()

# 根據圖片像素計算地圖矩陣的寬與高
MAP_WIDTH = img_w // TILE_SIZE
MAP_HEIGHT = img_h // TILE_SIZE

# 縮放背景圖以符合格線
bg_image = pygame.transform.scale(bg_image_raw, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
screen = pygame.display.set_mode((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
pygame.display.set_caption(f"熱血引擎地圖編輯器 - 模式: {MAP_WIDTH}x{MAP_HEIGHT}")

# === 2. 載入並校準 map.csv 資料 ===
terrain = np.zeros((MAP_HEIGHT, MAP_WIDTH), dtype=int)

if os.path.exists(MAP_PATH):
    try:
        loaded_data = pd.read_csv(MAP_PATH, header=None).values
        # 自動對齊尺寸：截取或填充
        h, w = min(MAP_HEIGHT, loaded_data.shape[0]), min(MAP_WIDTH, loaded_data.shape[1])
        terrain[:h, :w] = loaded_data[:h, :w]
        print(f"成功載入並校準地圖資料: {loaded_data.shape} -> {(MAP_HEIGHT, MAP_WIDTH)}")
    except Exception as e:
        print(f"載入 CSV 失敗，建立新地圖: {e}")
else:
    print("未發現原始 map.csv，將建立全新資料庫。")


def draw_grid():
    # 繪製背景
    screen.blit(bg_image, (0, 0))
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            # 畫格線
            pygame.draw.rect(screen, (100, 100, 100), rect, 1)

            # 取得 Z 值
            z = terrain[y, x]
            # 若高度差大於等於 2，文字標示為紅色（對應遊戲中的牆壁判定）
            color = (255, 0, 0) if z >= 2 else (200, 200, 200)
            text = font.render(str(z), True, color)
            screen.blit(text, (x * TILE_SIZE + 5, y * TILE_SIZE + 5))


def save_map():
    pd.DataFrame(terrain).to_csv(SAVE_PATH, header=False, index=False)
    print(f"地圖已成功對齊並儲存至: {SAVE_PATH}")


# === 主迴圈 ===
running = True
clock = pygame.time.Clock()

while running:
    draw_grid()
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_map()
            running = False

        # 滑鼠操作
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            grid_x = mx // TILE_SIZE
            grid_y = my // TILE_SIZE

            if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
                if event.button == 1:  # 左鍵：增加高度
                    terrain[grid_y, grid_x] += 1
                elif event.button == 3:  # 右鍵：減少高度
                    terrain[grid_y, grid_x] = max(0, terrain[grid_y, grid_x] - 1)

        # 鍵盤快捷鍵
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                save_map()
            elif event.key == pygame.K_c:  # 清空當前畫面（危險操作）
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    terrain.fill(0)
                    print("地圖已重置為 0")

    clock.tick(60)

pygame.quit()