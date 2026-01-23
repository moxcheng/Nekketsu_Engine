
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

# === 物理系統全局參數 ===

# --- 1. 水平位移與摩擦 ---
FRICTION_AIR = 0.85       # 非飛行狀態下的水平速度衰減
FRICTION_GROUND = 0.6    # 落地彈跳時的水平摩擦力
STOP_THRESHOLD = 0.05    # 速度低於此值則歸零

# --- 2. 撞牆與反彈 ---
WALL_BOUNCE_REBOUND = 0.3 # 撞牆後的反向速度係數
WALL_BOUNCE_UP_VZ = 0.15   # 撞牆後的向上微彈力

# --- 3. 拋物線與重力 ---
FLY_GRAVITY_MULT = 0.5   # 飛行物件受重力的加權係數
GROUND_BOUNCE_REBOUND = 0.4 # 觸地彈跳的垂直反彈係數
BOUNCE_THRESHOLD_VZ = 0.1 # 觸地時 vz 超過此值才觸發彈跳

# --- 4. 動量與碰撞損耗 ---
UNIT_IMPACT_MOMENTUM_LOSS_MAX = 0.8 # 撞擊人物時的最大動量損失
UNIT_IMPACT_UP_VZ_FACTOR = 0.2      # 撞擊人物後的垂直彈起係數

# --- 5. 環境傷害門檻 (擬真化建議值) ---
WALL_IMPACT_DAMAGE_THRESHOLD = 0.2  # 撞牆受傷的速度門檻
WALL_IMPACT_DAMAGE_MULT = 15        # 撞牆傷害倍率
FALL_DAMAGE_THRESHOLD = 0.3         # 墜地受傷的垂直速度門檻
FALL_DAMAGE_MULT = 20               # 墜地傷害倍率

# Config.py
CLASH_REBOUND_FORCE = 0.25      # 拼招時的後退力道
CLASH_HITSTOP_FRAMES = 2        # 拼招產生的極短時停