
import pygame
import sys
import numpy as np
import pandas as pd
from Characters import Player, Enemy, Ally, BigEnemy
from Config import *
from scene_manager import SceneManager, SpeechBubble
from Items import Rock
from Component import HoldableComponent

# ========= 通關顯示 / 畫面變暗控制 =========
SCENE_DARKEN_ENABLED = True  # True: 照原本邏輯變暗 / False: 停止變暗

def draw_center_text(win, text, font, color=(255, 255, 255), outline_color=(0, 0, 0)):
    """在畫面中央印一行字（加簡單外框避免吃背景顏色）"""
    surf = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    x = (WIDTH - surf.get_width()) // 2
    y = (HEIGHT - surf.get_height()) // 2

    # 簡單外框
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        win.blit(outline, (x + dx, y + dy))
    win.blit(surf, (x, y))
# ==========================================


# ========= 通關顯示 / 畫面變暗控制 =========
SCENE_DARKEN_ENABLED = True  # True: 照原本邏輯變暗 / False: 停止變暗


class JoystickKeyState:
    """
    把搖桿狀態包裝成「看起來像 pygame.key.get_pressed() 回傳值」的物件，
    讓 Player.handle_input 一樣用 keys[pygame.K_*] 來讀取。
    """
    def __init__(self, kb_keys, joystick, deadzone=0.2):
        self.kb_keys = kb_keys      # 原本鍵盤的 get_pressed()
        self.joystick = joystick    # pygame.joystick.Joystick
        self.deadzone = deadzone

    def __getitem__(self, key):
        # 先看鍵盤本身有沒有按
        val = self.kb_keys[key]

        if not self.joystick:
            return val

        # === 方向鍵：用左類比 + 十字鍵 ===
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            hat_x = hat_y = 0
            if self.joystick.get_numhats() > 0:
                hat_x, hat_y = self.joystick.get_hat(0)

            axis_x = self.joystick.get_axis(0) if self.joystick.get_numaxes() > 0 else 0.0
            axis_y = self.joystick.get_axis(1) if self.joystick.get_numaxes() > 1 else 0.0

            pressed = 0
            if key == pygame.K_LEFT:
                if hat_x < 0 or axis_x < -self.deadzone:
                    pressed = 1
            elif key == pygame.K_RIGHT:
                if hat_x > 0 or axis_x > self.deadzone:
                    pressed = 1
            elif key == pygame.K_UP:
                # 類比搖桿通常「向上 = 負值」
                if hat_y > 0 or axis_y < -self.deadzone:
                    pressed = 1
            elif key == pygame.K_DOWN:
                if hat_y < 0 or axis_y > self.deadzone:
                    pressed = 1

            return val or pressed  # 鍵盤 or 搖桿 只要有一個按下就是 1

        # === 攻擊 / 跳躍鍵：把搖桿按鈕 OR 進來 ===
        # F310 (XInput) 按鈕編號：A=0, B=1, X=2, Y=3
        if key in (pygame.K_z, pygame.K_x, pygame.K_c, pygame.K_SPACE):
            btnA = self.joystick.get_button(0)
            btnB = self.joystick.get_button(1)
            btnX = self.joystick.get_button(2)
            btnY = self.joystick.get_button(3)
            pressed = 0
            if key == pygame.K_z and btnX:       # X → Z 攻擊
                pressed = 1
            elif key == pygame.K_x and btnA:     # A → X 攻擊
                pressed = 1
            elif key == pygame.K_c and btnB:     # B → C 攻擊
                pressed = 1
            elif key == pygame.K_SPACE and btnY: # Y → 跳躍
                pressed = 1

            return val or pressed

        # 其他按鍵維持原樣
        return val


# 讀取地形高度地圖
def load_terrain_map(csv_path="..\\Assets_Drive\\map.csv", flip_vertical=True):
    df = pd.read_csv(csv_path, header=None)
    terrain = df.values.astype(int)
    if flip_vertical:
        terrain = np.flipud(terrain)
    return [terrain, terrain.shape[1], terrain.shape[0]]



# 計算落差大的區域（可視為斷崖 cliff）
def compute_cliff_map(terrain, threshold=2):
    h, w = terrain.shape
    cliff_map = np.zeros_like(terrain, dtype=bool)

    for y in range(h):
        for x in range(w):
            z = terrain[y, x]
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    neighbor_z = terrain[ny, nx]
                    if abs(z - neighbor_z) >= threshold:
                        cliff_map[y, x] = True
                        break
    return cliff_map




def find_start_position(terrain, MAP_WIDTH,MAP_HEIGHT):
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if terrain[y, x] == 0:
                return x + 0.5, y + 0.5
    return 1.0, 1.0


def create_transition_mask(terrain, MAP_WIDTH, MAP_HEIGHT):
    mask = np.zeros_like(terrain, dtype=bool)
    for y in range(1, MAP_HEIGHT - 1):
        for x in range(1, MAP_WIDTH - 1):
            z = terrain[y, x]
            neighbors = [terrain[y + 1, x], terrain[y - 1, x], terrain[y, x + 1], terrain[y, x - 1]]
            if any(abs(z - nz) >= 2 for nz in neighbors):
                mask[y, x] = True
    return mask


# def draw_map(win, cam_x, cam_y, font, tile_offset_y):
#     for y in range(MAP_HEIGHT):
#         for x in range(MAP_WIDTH):
#             z = terrain[y, x]
#             color = COLORS[z % len(COLORS)]
#             screen_x = x * TILE_SIZE - cam_x
#             screen_y = (MAP_HEIGHT - y - 1) * TILE_SIZE - cam_y + tile_offset_y
#             pygame.draw.rect(win, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
#             pygame.draw.rect(win, (0, 0, 0), (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 1)
#             label = font.render(str(z), True, Z_TEXT_COLOR)
#             win.blit(label, (screen_x + 2, screen_y + 2))
#
#     # # 加在 draw_map() 或 draw_tiles() 中地圖繪製後
#     for y in range(MAP_HEIGHT - 1):  # 避免超出下界
#         for x in range(MAP_WIDTH):
#             z1 = terrain[y, x]
#             z2 = terrain[y + 1, x]
#             if abs(z2 - z1) >= 2:
#                 px = x * TILE_SIZE - cam_x
#                 py = (MAP_HEIGHT - (y + 1)) * TILE_SIZE - cam_y + tile_offset_y
#                 pygame.draw.rect(win, (139, 69, 19), (px, py, TILE_SIZE, TILE_SIZE))  # 棕色牆面

def draw_map(win, cam_x, cam_y, font, tile_offset_y):
    # 貼背景圖（根據攝影機位置修正）
    win.blit(background_img, (-cam_x, -cam_y + tile_offset_y))

    if False:
        # 繪製網格與 Z 值文字
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                screen_x = x * TILE_SIZE - cam_x
                screen_y = (MAP_HEIGHT - y - 1) * TILE_SIZE - cam_y + tile_offset_y

                # 網格線
                pygame.draw.rect(win, (80, 80, 80), (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 1)

                # Z 值標示
                z = terrain[y, x]
                label = font.render(str(z), True, (255, 255, 0))
                win.blit(label, (screen_x + 2, screen_y + 2))

        # 顯示 cliff（高度差大）的位置，可選擇開關
        for y in range(MAP_HEIGHT - 1):
            for x in range(MAP_WIDTH):
                z1 = terrain[y, x]
                z2 = terrain[y + 1, x]
                if abs(z2 - z1) >= 2:
                    px = x * TILE_SIZE - cam_x
                    py = (MAP_HEIGHT - (y + 1)) * TILE_SIZE - cam_y + tile_offset_y
                    #pygame.draw.rect(win, (139, 69, 19), (px, py, TILE_SIZE, TILE_SIZE), 0)
                    # 建立半透明表面（用來畫牆面區域）
                    overlay = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    overlay.fill((139, 69, 19, 128))  # RGBA，第4個值是透明度 0~255

                    win.blit(overlay, (px, py))


def scene_test(win, font):
    map_info = load_terrain_map(flip_vertical=True)
    terrain, MAP_WIDTH, MAP_HEIGHT = map_info[0], map_info[1], map_info[2]
    transition_zone_mask = create_transition_mask(terrain, MAP_WIDTH, MAP_HEIGHT)

    global background_img
    background_img = pygame.image.load("..\\Assets_Drive\\background.png").convert()
    background_img = pygame.transform.scale(background_img, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

    clock = pygame.time.Clock()

    #宣告場景
    scene = SceneManager()
    #宣告單位
    tile_offset_y = 0
    px, py = find_start_position(terrain, MAP_WIDTH, MAP_HEIGHT)
    player = Player(px, py, map_info, "..//Assets_Drive//Character_white_24frame_96.png")

    player.name='player'
    #掛載component
    player.add_component("holdable", HoldableComponent(player))
    enemy = Enemy(px + 1, py +2, terrain[int(py), int(px)], map_info, "..\\Assets_Drive\\Character_red_24frame_96.png")
    enemy2 = BigEnemy(px + 3, py + 2, terrain[int(py), int(px)], map_info, "..\\Assets_Drive\\Iwasato_24frame_96.png", 1.5)
    enemy.name = 'enemy'
    enemy2.name ='enemy2'
    #enemy2.dummy = True
    enemy2.max_hp=2000
    enemy2.health=2000
    rock=Rock(x=player.x-1.5, y=player.y, map_info=map_info)


    #註冊單位

    #    def register_unit(self, unit, side=None, tags=None, type=None):
    player.scene = scene
    enemy.scene = scene  # ✅ 敵人也能互動（例如撿取道具）
    enemy2.scene = scene

    rock.scene = scene #scene加入道具, 以擴充地雷等會被動互動物件

    scene.register_unit(player, side='player_side', tags=['player','interactable'], type='character')
    scene.register_unit(enemy, side='enemy_side', tags=['enemy','interactable'], type='character')
    scene.register_unit(rock, side='netural', tags=['item','interactable'], type='item')
    scene.register_unit(enemy2, side='enemy_side', tags=['enemy', 'boss'], type='character')

    ally = Ally(px-2, py,terrain[int(py), int(px)], map_info, "..\\Assets_Drive\\takina1_24frame_96.png")
    ally.add_component("holdable", HoldableComponent(ally))
    scene.register_unit(ally, side='player_side', tags=['ally', 'interactable'], type='character')

    #scene.register_item(item1)  # 未來可新增的 item 類
    bubble = SpeechBubble(player, "歐斯，歐拉狗哭！", 120)
    scene.speech_bubbles = [bubble]

    while True:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                player.on_key_down(event.key)
            elif event.type == pygame.KEYUP:
                player.on_key_up(event.key)

        player.handle_input(keys)
        scene.update_all()  # 這會更新所有註冊單位
        if len(scene.get_units_by_side('player_side')) == 0:
            print('no player left, game over')
            break



        # 例如按 Enter 啟動腳本
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            # from Skill import AttackType
            # test_script = [
            #     {"type": "say", "target": "enemy", "text": "你來啦，終於找到你了..."},
            #     {"type": "wait", "duration": 60},
            #     {"type": "move", "target": "enemy", "to": [player.x - 1, player.y]},
            #     {"type": "wait", "duration": 30},
            #     {"type": "say", "target": "player", "text": "你是誰！？"},
            #     {"type": "wait", "duration": 30},
            #     {"type": "attack", "target": "enemy", "skill": AttackType.SLASH},
            #     {"type": "wait", "duration": 10},
            #     {"type": "say", "target": "enemy", "text": "猛虎...硬爬山！"},
            #     {"type": "wait", "duration": 30},
            #     {"type": "knockback", "target": "player", "vx": 0.5, "vz": 0.7},
            #     {"type": "wait", "duration": 90},
            # ]
            # scene.script_runner.load(test_script)
            print('enter!!')
            #player.enable_super_move()
            scene.env_manager.set_dim(True)

        cam_x = int((player.x + 0.5) * TILE_SIZE - WIDTH // 2)
        cam_y = int((MAP_HEIGHT - player.y - 0.5) * TILE_SIZE - HEIGHT // 2 + tile_offset_y)
        cam_x = max(0, min(cam_x, MAP_WIDTH * TILE_SIZE - WIDTH))
        cam_y = max(0, min(cam_y, MAP_HEIGHT * TILE_SIZE - HEIGHT))
        pygame.draw.rect(win, (255, 0, 0), (WIDTH // 2 - 5, HEIGHT // 2 - 5, 10, 10))  # 中心點

        win.fill(WHITE)
        draw_map(win, cam_x, cam_y, font, tile_offset_y)
        scene.draw_all(win, cam_x, cam_y, tile_offset_y)
        pygame.display.update()
        clock.tick(FPS)

black_enemy_list = ['head0', 'head1', 'head9']
yellow_enemy_list = ['head2', 'head6', 'head7']
red_enemy_list = ['head3', 'head4']
high_enemy_list = ['head5', 'head8']
all_enemy_list = ['head0','head1','head2','head3','head4','head5','head6','head7','head8','head9']

def input_joypad_handler(player: Player, joystick, joy_axis_left, joy_axis_right, kb_keys, joy_buttons_prev):
    # 如果有搖桿，就包成 JoystickKeyState，讓 handle_input 看到「鍵盤+搖桿」
    if joystick is not None:
        keys = JoystickKeyState(kb_keys, joystick)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            player.on_key_down(event.key)
        elif event.type == pygame.KEYUP:
            player.on_key_up(event.key)

    # === 搖桿按鈕 → 模擬 KEYDOWN/KEYUP（用在攻擊 & 跳躍） ===
    if joystick is not None:
        num_buttons = joystick.get_numbuttons()
        buttons = [joystick.get_button(i) for i in range(num_buttons)]

        # F310 (XInput) 的基本 mapping：
        # X(2) -> Z 攻擊, A(0) -> X 攻擊, B(1) -> C 攻擊, Y(3) -> Space 跳躍
        button_to_key = {
            2: pygame.K_z,  # X → punch / z_attack
            0: pygame.K_x,  # A → x_attack
            1: pygame.K_c,  # B → c_attack
            3: pygame.K_SPACE,  # Y → jump
        }

        for btn_idx, keycode in button_to_key.items():
            if btn_idx >= num_buttons:
                continue

            now = buttons[btn_idx]
            prev = joy_buttons_prev[btn_idx]

            # 剛按下 → 當成 KEYDOWN
            if now and not prev:
                player.on_key_down(keycode)

            # 剛放開 → 當成 KEYUP（特別是 SPACE 要解除 jump_key_block）
            if not now and prev:
                player.on_key_up(keycode)

        new_prev = buttons

    # === 搖桿方向（蘑菇頭 Axis + 十字鍵 Hat）→ 模擬 LEFT/RIGHT keydown/up，用於 double-tap 跑步 ===
    if joystick is not None:
        # 讀取左類比 X 軸（蘑菇頭）
        axis_x = 0.0
        if joystick.get_numaxes() > 0:
            axis_x = joystick.get_axis(0)

        # 讀取十字鍵（Hat）
        hat_x = 0
        if joystick.get_numhats() > 0:
            hat_x, _ = joystick.get_hat(0)

        DEADZONE = 0.4  # 類比搖桿死區

        # 判斷是否視為「左方向被按住」或「右方向被按住」
        # 只要 蘑菇頭 or 十字鍵 有其一達成，就算該方向有按
        dir_left = False
        dir_right = False

        if axis_x < -DEADZONE or hat_x < 0:
            dir_left = True
        elif axis_x > DEADZONE or hat_x > 0:
            dir_right = True

        # ---- LEFT 邊緣觸發 ----
        if dir_left and not joy_axis_left:
            # 剛從「非左」→「左」：當成 K_LEFT keydown
            player.on_key_down(pygame.K_LEFT)
        if not dir_left and joy_axis_left:
            # 剛從「左」→「非左」：當成 K_LEFT keyup
            player.on_key_up(pygame.K_LEFT)

        # ---- RIGHT 邊緣觸發 ----
        if dir_right and not joy_axis_right:
            player.on_key_down(pygame.K_RIGHT)
        if not dir_right and joy_axis_right:
            player.on_key_up(pygame.K_RIGHT)

        # 更新目前狀態
    return keys, dir_left, dir_right, new_prev

def is_player_alive(scene):
    return len(scene.get_units_by_side('player_side')) > 0
def scene_1(win, font, clear_font, backgroung_path="..\\Assets_Drive\\background.png"):
    # === 搖桿初始化 ===
    joystick = None
    joy_buttons_prev = []
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[JOYPAD] 使用搖桿: {joystick.get_name()}")
        joy_buttons_prev = [0] * joystick.get_numbuttons()
    else:
        print("[JOYPAD] 沒有偵測到搖桿，維持鍵盤操作")
    joy_axis_left = False
    joy_axis_right = False
    # === 搖桿初始化 ===


    # 地圖資訊化
    map_info = load_terrain_map(flip_vertical=True)
    terrain, MAP_WIDTH, MAP_HEIGHT = map_info[0], map_info[1], map_info[2]
    transition_zone_mask = create_transition_mask(terrain, MAP_WIDTH, MAP_HEIGHT)

    global background_img
    background_img = pygame.image.load(backgroung_path).convert()
    background_img = pygame.transform.scale(background_img, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

    clock = pygame.time.Clock()




    #宣告場景
    scene = SceneManager()
    scene.set_clear_font(clear_font)
    scene.reset_overlay()   # 如果你希望每次進這個場景都從 0 開始變暗
    stage_cleared = False
    #宣告玩家單位
    tile_offset_y = 0
    px, py = find_start_position(terrain, MAP_WIDTH, MAP_HEIGHT)
    #player = Player(px, py, map_info, "..\\Assets_Drive\\Character_white_24frame_96.png")
    #player = Player(px, py, map_info, "..//Assets_Drive//yamashiro_96.png")
    player = Player(px, py, map_info, "..//Assets_Drive//yamashiro_96.png")
    player.name='player'
    #掛載component
    player.add_component("holdable", HoldableComponent(player))
    player.scene = scene
    scene.register_unit(player, side='player_side', tags=['player', 'interactable'], type='character')
    #scene.register_item(item1)  # 未來可新增的 item 類
    bubble = SpeechBubble(player, "場景1開始！", 120)
    scene.speech_bubbles = [bubble]

    #小兵清單
    enemy_list = []
    total_enemy = 7
    created_enemy = 0
    current_enemy = 0
    max_enemy = 3
    phase = 0
    #產生小兵list
    import random
    for i in range(total_enemy):
        head = random.choice(all_enemy_list)
        rng = random.Random()  # 自動用系統 entropy seed
        x_dis = random.randint(0,9)
        y_dis = random.randint(-1, 1)
        e = Enemy(px+x_dis, py+y_dis, terrain[int(py), int(px)], map_info, f"..\\Assets_Drive\\common_enemy\\{head}_body0_yellow_sheet.png")
        e.name = f'enemy{i}'
        e.scene=scene
        enemy_list.append(e)
        #scene.register_unit(e, side='enemy_side', tags=['enemy', 'interactable'], type='character')

    while True:
        current_enemy = len(scene.get_units_by_side('enemy_side'))
        if created_enemy < total_enemy and current_enemy < max_enemy:
            enemy_to_add = max_enemy-current_enemy
            for i in range(enemy_to_add):
                print(f'加入{enemy_list[created_enemy].name} ({created_enemy}/{total_enemy}), 現在{current_enemy} enemy_to_add{enemy_to_add}')
                scene.register_unit(enemy_list[created_enemy], side='enemy_side', tags=['enemy', 'interactable'], type='character')
                created_enemy += 1
                current_enemy += 1

        kb_keys = pygame.key.get_pressed()
        if 'joystick' in locals() and joystick is not None:
            keys, joy_axis_left, joy_axis_right, joy_buttons_prev = input_joypad_handler(player, joystick, joy_axis_left, joy_axis_right,kb_keys, joy_buttons_prev)
        else:
            keys = kb_keys


        # === 原本的邏輯 ===
        player.handle_input(keys)
        if len(scene.get_units_by_side('player_side')) > 0:
            scene.update_all()  # 這會更新所有註冊單位
        if phase == 0:
            if created_enemy == total_enemy and current_enemy == 0:
                #scene.say('player', 'enemy clear!')
                scr = [
                {"type": "say", "target": "player", "text": "Phase 1結束！"},
                {"type": "wait", "duration": 180},
                ]
                scene.script_runner.load(scr)
                phase = 1
                enemy2 = BigEnemy(px + 3, py + 2, terrain[int(py), int(px)], map_info,
                                  "..\\Assets_Drive\\Iwasato_24frame_96.png", 1.5)
                enemy2.name = 'boss'
                # enemy2.dummy = True
                enemy2.max_hp = 600
                enemy2.health = 600
                enemy2.scene=scene
                scene.register_unit(enemy2, side='enemy_side', tags=['enemy', 'boss'], type='character')
                scr = [
                    {"type": "say", "target": "boss", "text": "Boss來了!"},
                    {"type": "wait", "duration": 30},
                ]
                scene.script_runner.load(scr)

        elif phase == 1:
            if len(scene.get_units_by_side('enemy_side')) == 0:
                print('清除敵人')
                stage_cleared = True
                phase = 2


        #if len(scene.get_units_by_side('player_side')) == 0:
        #print(f'player jump block {player.jump_key_block}')
        if not is_player_alive(scene):
            print('no player left, game over')
            stage_cleared = True
        if stage_cleared == True and scene.scene_end_countdown < 0:
            if is_player_alive(scene):
                result = 'CLEAR'
            else:
                result = 'FAIL'
            scene.trigger_clear(f"SCENE 1 {result}", 180)
            scene.darken_enabled = True
        if scene.scene_end_countdown == 0:
            print('scene end')
            break

        cam_x = int((player.x + 0.5) * TILE_SIZE - WIDTH // 2)
        cam_y = int((MAP_HEIGHT - player.y - 0.5) * TILE_SIZE - HEIGHT // 2 + tile_offset_y)
        cam_x = max(0, min(cam_x, MAP_WIDTH * TILE_SIZE - WIDTH))
        cam_y = max(0, min(cam_y, MAP_HEIGHT * TILE_SIZE - HEIGHT))
        pygame.draw.rect(win, (255, 0, 0), (WIDTH // 2 - 5, HEIGHT // 2 - 5, 10, 10))  # 中心點

        win.fill(WHITE)
        draw_map(win, cam_x, cam_y, font, tile_offset_y)
        scene.draw_all(win, cam_x, cam_y, tile_offset_y)
        pygame.display.update()
        clock.tick(FPS)

from CharactersConfig import *
def scene_mato(win, font, clear_font, backgroung_path="..\\Assets_Drive\\madou\\7thTeam.png", player_config = PLAYER_REN_128_CONFIG):

    # === 搖桿初始化 ===
    joystick = None
    joy_buttons_prev = []
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[JOYPAD] 使用搖桿: {joystick.get_name()}")
        joy_buttons_prev = [0] * joystick.get_numbuttons()
    else:
        print("[JOYPAD] 沒有偵測到搖桿，維持鍵盤操作")
    joy_axis_left = False
    joy_axis_right = False
    # === 搖桿初始化 ===


    # 地圖資訊化
    map_info = load_terrain_map(flip_vertical=True)
    terrain, MAP_WIDTH, MAP_HEIGHT = map_info[0], map_info[1], map_info[2]
    transition_zone_mask = create_transition_mask(terrain, MAP_WIDTH, MAP_HEIGHT)

    global background_img
    background_img = pygame.image.load(backgroung_path).convert()
    background_img = pygame.transform.scale(background_img, (MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))

    clock = pygame.time.Clock()




    #宣告場景
    scene = SceneManager(MAP_HEIGHT, MAP_WIDTH, terrain, end_cuts = ["..\\Assets_Drive\\madou\\end_cut0.png","..\\Assets_Drive\\madou\\end_cut.png"], bg_path=backgroung_path)
    scene.set_clear_font(clear_font)
    scene.reset_overlay()   # 如果你希望每次進這個場景都從 0 開始變暗
    stage_cleared = False
    #宣告玩家單位
    tile_offset_y = 0
    #px, py = find_start_position(terrain, MAP_WIDTH, MAP_HEIGHT)
    px, py = 16.0, 2.0
    #player = Player(px, py, map_info, "..\\Assets_Drive\\Character_white_24frame_96.png")
    #player = Player(px, py, map_info, "..//Assets_Drive//konomi_test_42frame.png", super_move_material="..//Assets_Drive//yamashiro_super_move_96.png")
    #player = Player(px, py, map_info, PLAYER_KONOMI_CONFIG)

    player = Player(px, py, map_info, player_config)

    player.name='player'
    #掛載component
    player.health=500
    player.max_hp = 500
    player.mp=3
    player.add_component("holdable", HoldableComponent(player))
    player.scene = scene
    scene.register_unit(player, side='player_side', tags=['player', 'interactable'], type='character')
    #scene.register_item(item1)  # 未來可新增的 item 類
    bubble = SpeechBubble(player, "場景1開始！", 120)
    scene.speech_bubbles = [bubble]
    boss_barserker = False

    rock = Rock(x=player.x - 1.5, y=player.y, map_info=map_info)
    rock.scene=scene
    scene.register_unit(rock, side='netural', tags=['item', 'interactable'], type='item')


    #小兵清單
    enemy_list = []
    total_enemy = 10
    created_enemy = 0
    current_enemy = 0
    destroyed_enemy = 0
    phase = 0
    #產生小兵list
    import random
    #shuki_list = [['shuki0_96.png', 7/4],['shuki1_96.png',5/4],['shuki2_96.png',6/4],['shuki3_96.png',1.0]]
    #shuki_list = [NPC_SHUKI_0_CONFIG, NPC_SHUKI_1_CONFIG, NPC_SHUKI_2_CONFIG, NPC_SHUKI_3_CONFIG, ]
    shuki_list = [NPC_SHUKI_0_CONFIG, NPC_SHUKI_1_CONFIG, NPC_SHUKI_2_CONFIG, NPC_SHUKI_3_CONFIG, NPC_SHUKI_NEW_1_CONFIG]
    x_pool = list(range(-1*total_enemy, total_enemy))
    random.shuffle(x_pool)
    for i in range(total_enemy):
        rng = random.Random()  # 自動用系統 entropy seed
        choosed_idx = random.randint(0,4)
        x_dis = x_pool[i]
        y_dis = random.randint(-1, 1)
        e = Enemy(px+x_dis, py+y_dis, terrain[int(py), int(px)], map_info, config_dict = shuki_list[choosed_idx])
        e.attack_cooldown = random.randint(40, 50)
        e.max_hp = e.health = int(40*(shuki_list[choosed_idx].get("scale", 1.0)))
        e.name = f'enemy{i}'
        e.scene=scene
        enemy_list.append(e)
        #scene.register_unit(e, side='enemy_side', tags=['enemy', 'interactable'], type='character')
    enemy_popup_latency = 8
    enemy_popup_cooldown = 0
    #a=input('press to start')
    while True:
        current_enemy = len(scene.get_units_by_side('enemy_side'))
        max_enemy = 3+destroyed_enemy
        enemy_popup_cooldown -= 1
        if created_enemy < total_enemy and current_enemy < max_enemy and enemy_popup_cooldown <= 0:
            enemy_to_add = max_enemy-current_enemy
            for i in range(enemy_to_add):
                print(f'加入{enemy_list[created_enemy].name} ({created_enemy}/{total_enemy}), 現在{current_enemy} enemy_to_add{enemy_to_add}')
                scene.register_unit(enemy_list[created_enemy], side='enemy_side', tags=['enemy', 'interactable'], type='character')
                created_enemy += 1
                current_enemy += 1
                enemy_popup_cooldown = enemy_popup_latency
                if created_enemy >= total_enemy:
                    break



        kb_keys = pygame.key.get_pressed()
        if 'joystick' in locals() and joystick is not None:
            keys, joy_axis_left, joy_axis_right, joy_buttons_prev = input_joypad_handler(player, joystick, joy_axis_left, joy_axis_right,kb_keys, joy_buttons_prev)
        else:
            keys = kb_keys
            # --- 在這裡檢查 Enter ---
        if kb_keys[pygame.K_RETURN]:
            print('Enter is being held!')
            #player.enable_super_move()
            # player.activate_stand()
            # scene.toggle_highlight_test(player)
            # scene.toggle_highlight_test(player.stand)
            # scene.trigger_za_warudo(player, 540)

            # player.try_use_ability('stand')
            # player.try_use_ability('timestop')

            #player.enable_super_move()
            #player.try_use_ability('haste')
            from Skill import ABILITY_DATA
            from Component import AbilityComponent
            #player.add_component("ability_haste", AbilityComponent(ABILITY_DATA["haste"]))
            #player.add_component("ability_stand", AbilityComponent(ABILITY_DATA["stand"]))
            #player.try_use_ability('stand')

            #stage_cleared=True

        player.handle_input(keys)



        if len(scene.get_units_by_side('player_side')) > 0:
            destroyed_enemy += scene.update_all()  # 這會更新所有註冊單位

        if phase == 0:
            if created_enemy == total_enemy and current_enemy == 0:
                #scene.say('player', 'enemy clear!')
                scr = [
                {"type": "say", "target": "player", "text": "Phase 1結束！"},
                {"type": "wait", "duration": 180},
                ]
                scene.script_runner.load(scr)
                phase = 1
                # enemy2 = BigEnemy(px + 3, py + 2, terrain[int(py), int(px)], map_info,
                #                   "..\\Assets_Drive\\madou\\shuki_boss_96.png", 2)
                px, py = player.x, player.y
                # enemy2 = Enemy(px + 3, py + 2, terrain[int(py), int(px)], map_info,
                #                    "..\\Assets_Drive\\madou\\shuki_boss_96.png", scale=2, name='boss', popup=["landing","shake"], ai_move_speed=0.15, attack_cooldown=30)
                enemy2 = Enemy(px + 3, py, terrain[int(py), int(px)], map_info, config_dict=NPC_SHUKI_BOSS_CONFIG)
                # enemy2.dummy = True
                enemy2.max_hp = 300
                enemy2.health = 300
                enemy2.scene=scene
                scene.register_unit(enemy2, side='enemy_side', tags=['enemy', 'boss'], type='character')
                scr = [
                    {"type": "say", "target": "boss", "text": "嘎!!!"},
                    {"type": "wait", "duration": 30},
                ]
                scene.script_runner.load(scr)

        elif phase == 1:
            boss_list = scene.get_units_by_name('boss')
            for boss in boss_list:
                if boss.health <= 150:
                    scr = [
                        {"type": "say", "target": "boss", "text": "嘎啊啊啊啊!!!"},
                        {"type": "wait", "duration":30}
                    ]
                    scene.script_runner.load(scr)
                    for i in range(3):
                        rng = random.Random()  # 自動用系統 entropy seed
                        if i%2==0:
                            x_dis = random.randint(0, 10)
                        else:
                            x_dis = random.randint(-10, 0)
                        y_dis = random.randint(0, 2)
                        px, py = player.x, player.y
                        # e = Enemy(player.x + x_dis, player.y + y_dis, terrain[int(py), int(px)], map_info,
                        #                "..\\Assets_Drive\\madou\\shuki_boss_96.png", scale=2, name=f'fantom{i}',
                        #                popup=["landing", "shake"], ai_move_speed=0.25, attack_cooldown=45)
                        e = Enemy(player.x + x_dis, player.y + y_dis, terrain[int(py), int(px)], map_info, config_dict=NPC_SHUKI_BOSS_CONFIG)
                        e.scale=2.0
                        e.name=f'fantom{i}'
                        e.attack_cooldown=45
                        e.ai_move_speed=0.3
                        scene.register_unit(e, side='enemy_side', tags=['enemy'], type='character')
                        print('summon boss fantom')
                    phase = 2
        elif phase == 2:
            if len(scene.get_units_by_side('enemy_side')) == 0:
                print('清除敵人')
                stage_cleared = True
                phase = 3



        #if len(scene.get_units_by_side('player_side')) == 0:
        #print(f'player jump block {player.jump_key_block}')
        if not is_player_alive(scene):
            print('no player left, game over')
            stage_cleared = True
        if stage_cleared == True and scene.scene_end_countdown < 0:
            if is_player_alive(scene):
                result = 'CLEAR'
            else:
                result = 'FAIL'
            scene.trigger_clear(f"SCENE MATO {result}", 360)
            # scene.darken_enabled = True
            #scene.trigger_scene_end()
        #print(f'main: scene end countdown={scene.scene_end_countdown}')

        if scene.scene_end_countdown == 0:
            print('scene end')
            break

        # main.py 的 scene_madou 迴圈內

        # 1. 先根據角色位置計算基礎攝影機座標
        base_cam_x = int((player.x + 0.5) * TILE_SIZE - WIDTH // 2)
        base_cam_y = int((MAP_HEIGHT - player.y - 0.5) * TILE_SIZE - HEIGHT // 2 + tile_offset_y)

        # 2. 進行地圖邊界限制 (Clamp)，確保基礎背景座標不越界
        base_cam_x = max(0, min(base_cam_x, MAP_WIDTH * TILE_SIZE - WIDTH))
        base_cam_y = max(0, min(base_cam_y, MAP_HEIGHT * TILE_SIZE - HEIGHT))

        # 3. 取得震動偏移量
        ox, oy = scene.get_camera_offset()

        # 4. 最終繪製用的 cam_x/y 等於「基礎座標」加上「震動偏移」
        # 注意：這裡不要再做一次邊界限制，否則震動會被擋住
        cam_x = base_cam_x + ox
        cam_y = base_cam_y + oy

        # --- 接下來進行繪圖 ---
        win.fill(WHITE)
        #draw_map(win, cam_x, cam_y, font, tile_offset_y)
        scene.draw_all(win, cam_x, cam_y, tile_offset_y)

        #pygame.draw.rect(win, (255, 0, 0), (WIDTH // 2 - 5, HEIGHT // 2 - 5, 10, 10))  # 中心點
        pygame.display.update()
        clock.tick(FPS)


def selection_menu():
    from MenuManager import CharacterSelectMenu
    # 1. 初始化
    pygame.init()
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
    for j in joysticks: j.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    bg_image = pygame.image.load("..\\Assets_Drive\\madou\\CharacterSelectBackground.png").convert()
    bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))

    menu = CharacterSelectMenu(screen, bg_image)
    selected_config = None
    running = True

    # 手把按鈕映射 (A, B, X 均視為確認)
    CONFIRM_BUTTONS = [0, 1, 2]

    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --- 鍵盤輸入處理 ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    menu.index = (menu.index - 1) % len(menu.choices)
                    menu.preview_unit = menu.rebuild_preview_unit()
                    menu.idle_timer = 0
                    menu.ui_alpha = 0
                elif event.key == pygame.K_RIGHT:
                    menu.index = (menu.index + 1) % len(menu.choices)
                    menu.preview_unit = menu.rebuild_preview_unit()
                    menu.idle_timer = 0
                    menu.ui_alpha = 0
                # 🟢 支援 Z/X/C 作為 Enter
                elif event.key in [pygame.K_RETURN, pygame.K_z, pygame.K_x, pygame.K_c]:
                    selected_config = menu.choices[menu.index]
                    running = False

            # --- 🟢 手把輸入處理 ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONFIRM_BUTTONS:
                    selected_config = menu.choices[menu.index]
                    running = False

            if event.type == pygame.JOYHATMOTION:
                hat_x, _ = event.value
                if hat_x == -1:  # 左
                    menu.index = (menu.index - 1) % len(menu.choices)
                    menu.preview_unit = menu.rebuild_preview_unit()
                    menu.idle_timer = 0
                    menu.ui_alpha = 0
                elif hat_x == 1:  # 右
                    menu.index = (menu.index + 1) % len(menu.choices)
                    menu.preview_unit = menu.rebuild_preview_unit()
                    menu.idle_timer = 0
                    menu.ui_alpha = 0

        menu.update()
        menu.draw()
        pygame.display.flip()

    return selected_config


def main():
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont(None, 18)
    clear_font = pygame.font.SysFont(None, 48)
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("熱血引擎")
    selected_player = selection_menu()
    scene_mato(win, font, clear_font, player_config=selected_player)


main()