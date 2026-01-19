
# === 設定 ===
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 40
FPS = 60
GRAVITY = 0.05

WHITE = (255, 255, 255)
RED = (255, 100, 100)
Z_TEXT_COLOR = (0, 0, 0)
COLORS = [
    (220, 220, 220), (160, 180, 255), (110, 140, 255),
    (60, 100, 230), (120, 160, 220), (100, 120, 200),
    (80, 90, 180), (50, 60, 160)
]
SHORT_PRESS_MAX = 15  # 幀數內放開視為「短按」
REPRESS_INTERVAL = 15  # 放開後多少幀內再按下視為「連按」→ run
STEP_PRESS_MAX_FRAME = 5  # 或你喜歡的值，表示「step」最大時間
STEP_EFFECT_FRAME = 10  # 你可以依照滑行效果長短調整這個值
STEP_PRESS_MAX_FRAME = 10  # 最長按多久算短擊
STEP_STATE_DURATION = 10  # step狀態持續幾幀

STEP_TO_RUN_WINDOW = 60  # 以 frame 為單位

Z_DRAW_OFFSET = 10  # 每層 Z 軸對應視覺高度差（像素）
Z_FALL_OFSSET = Z_DRAW_OFFSET/15    #每一個Z =15掉落frame

ON_HIT_SHORT_STUN_TIME = 15
ON_GUARD_STUN_TIME = 7
ON_GUARD_MAX_WINDOW = 10    #可以觸發guard的最大時間


