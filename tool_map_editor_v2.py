
import pygame
import numpy as np
import pandas as pd

# === 設定參數 ===
TILE_SIZE = 40
MAP_PATH = "map.csv"
BG_PATH = "background.png"
SAVE_PATH = "edited_map.csv"

# === 載入地圖資料 ===
terrain = pd.read_csv(MAP_PATH, header=None).values
MAP_HEIGHT, MAP_WIDTH = terrain.shape

# === 初始化 Pygame ===
pygame.init()
screen = pygame.display.set_mode((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
pygame.display.set_caption("地圖編輯器")

# === 載入與縮放背景圖 ===
bg_image_raw = pygame.image.load(BG_PATH).convert()
bg_image = pygame.transform.scale(bg_image_raw, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

# === 設定字型 ===
font = pygame.font.SysFont("arial", 16)

def draw_grid():
    screen.blit(bg_image, (0, 0))
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)
            z = terrain[y, x]
            color = (255, 0, 0) if z >= 2 else (0, 0, 0)
            text = font.render(str(z), True, color)
            screen.blit(text, (x * TILE_SIZE + 5, y * TILE_SIZE + 5))

def save_map():
    pd.DataFrame(terrain).to_csv(SAVE_PATH, header=False, index=False)
    print(f"已儲存至 {SAVE_PATH}")

def update_screen():
    global screen, bg_image
    screen = pygame.display.set_mode((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
    bg_image = pygame.transform.scale(bg_image_raw, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

# === 主迴圈 ===
running = True
while running:
    draw_grid()
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_map()
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = pygame.mouse.get_pos()
            grid_x = x // TILE_SIZE
            grid_y = y // TILE_SIZE
            if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
                if event.button == 1:  # 左鍵
                    terrain[grid_y, grid_x] += 1
                elif event.button == 3:  # 右鍵
                    terrain[grid_y, grid_x] -= 1
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                save_map()
            elif event.key == pygame.K_a:  # 增加欄
                terrain = np.hstack([terrain, np.zeros((MAP_HEIGHT, 1), dtype=int)])
                MAP_WIDTH += 1
                update_screen()
            elif event.key == pygame.K_d and MAP_WIDTH > 1:  # 刪除欄
                terrain = terrain[:, :-1]
                MAP_WIDTH -= 1
                update_screen()
            elif event.key == pygame.K_w:  # 增加列
                terrain = np.vstack([terrain, np.zeros((1, MAP_WIDTH), dtype=int)])
                MAP_HEIGHT += 1
                update_screen()
            elif event.key == pygame.K_x and MAP_HEIGHT > 1:  # 刪除列
                terrain = terrain[:-1, :]
                MAP_HEIGHT -= 1
                update_screen()

pygame.quit()
