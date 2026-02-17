import pygame
import random
from State_enum import *
from Characters import *
from CharactersConfig import PLAYER_KONOMI_CONFIG, PLAYER_REN_128_CONFIG
from Config import *
import numpy as np
from scene_manager import SceneManager  # 💡 引入真實的 SceneManage


# 定義配色常數
COLOR_TITLE = (25, 25, 112)    # Midnight Blue
COLOR_BODY = (51, 51, 51)     # Charcoal
COLOR_HIGHLIGHT = (74, 14, 14) # Dark Burgundy

class CharacterSelectMenu:
    def __init__(self, screen, background_img):
        self.screen = screen
        self.choices = [PLAYER_REN_128_CONFIG, PLAYER_KONOMI_CONFIG]
        self.index = 0
        self.background = background_img
        self.font = pygame.font.SysFont("Microsoft JhengHei", 24, bold=True)
        self.idle_timer = 0
        self.ui_alpha = 0
        self.INFO_DELAY = 60
        # 💡 確保在呼叫 rebuild 前 numpy 陣列已準備好
        self.preview_unit = self.rebuild_preview_unit()
        # ... 原有代碼 ...
        self.demo_skills = []  # 🟢 持久化的技能袋
        self.demo_play_actions = 0
        self.avail_pool = [
            AttackType.PUNCH, AttackType.KICK, AttackType.SLASH,
            AttackType.PUSH, AttackType.BASH,
            AttackType.SPECIAL_KICK, AttackType.SPECIAL_PUNCH
        ]

        self.focus_polygons = [
            [(508, 22), (535, 130), (535, 308), (486, 448), (266, 448), (217, 308), (217, 130), (266, 22)], #戀
            [(508, 22), (546, 0), (799, 0), (799, 30), (548,118)],  # 木乃實
            [(548, 129), (799, 45), (799, 230), (548, 230)],  # 貝兒
            [(548, 241), (799,241), (799, 394), (532, 332)], #天花
            # ... 依此類推 ...
        ]

    def _refresh_demo_skills(self):
        """洗牌並填充袋子"""
        self.demo_skills = self.avail_pool.copy()
        random.shuffle(self.demo_skills)
    # 在 rebuild_preview_unit 中順便預載立繪（或在 __init__ 處理）
    def rebuild_preview_unit(self):
        cfg = self.choices[self.index]
        # 💡 CSIE 建議：將載入後的 Surface 存入 cfg 避免重複讀取磁碟
        if "tachie_surface" not in cfg and cfg.get("preview_tachie"):
            cfg["tachie_surface"] = pygame.image.load(cfg["preview_tachie"]).convert_alpha()
        cfg = self.choices[self.index]

        # 1. 建立最基礎的地圖數據
        dummy_terrain = np.zeros((1, 1), dtype=int)
        dummy_map = [dummy_terrain, 1, 1]

        # 2. 宣告一個不帶背景圖的 SceneManager 實體
        # 傳入地圖的高、寬與地形數據
        # 這樣它就具備了 hit_stop_timer 與 env_manager
        minimal_scene = SceneManager(map_h=1, map_w=1, terrain=dummy_terrain)

        # 3. 初始化 Player
        unit = Player(0, 0, dummy_map, cfg)
        unit.anim_speed = 30  # 原本是 8，調大數值會讓動畫換圖變慢
        unit.scene = minimal_scene  # 🟢 掛載真實 Scene 確保屬性齊全
        unit.z = 0.0

        unit.state = MoveState.STAND
        return unit

    def update(self):
        # 1. 基礎計時與動畫更新
        self.idle_timer += 1

        # 🟢 修正：選單簡易物理步進 (防止跳躍卡住)
        # 由於選單沒有 resolve_world_physics，我們手動處理重力
        if self.preview_unit.jump_z > 0 or self.preview_unit.vz != 0:
            GRAVITY = 0.015  # 選單專用微重力
            self.preview_unit.vz -= GRAVITY*10
            self.preview_unit.jump_z += self.preview_unit.vz

            # 落地判定
            if self.preview_unit.jump_z <= 0:
                self.preview_unit.jump_z = 0
                self.preview_unit.vz = 0
                self.preview_unit.into_normal_state()
                self.preview_unit.state = MoveState.STAND

        self.preview_unit.update()  # 驅動 Player 類別的邏輯，包含 attack_state 影格推進

        if self.idle_timer > self.INFO_DELAY:
            self.ui_alpha = min(255, self.ui_alpha + 15)  # 快速漸顯

            # 3. 隨機動作播放 (重點：模擬動作)
            # 邏輯：當玩家停下 1.5 秒後，每隔 2 秒隨機展示一次動作
            if self.idle_timer > self.INFO_DELAY + 30:
                if self.idle_timer % 120 == 0:
                    # 🟢 增加動作池：包含攻擊、跳躍、倒地、跑步
                    self.preview_unit.remove_component("aura_effect")
                    self.preview_unit.attack_state = None
                    self.preview_unit.jump_z = 0.0
                    self.preview_unit.vz = 0.0
                    self.preview_unit.down_to_ground()
                    self.preview_unit.into_normal_state()

                    if self.demo_play_actions%8==0:
                        self.preview_unit.state = MoveState.STAND
                    else:
                        if not self.demo_skills:
                            self._refresh_demo_skills()
                        self.preview_unit.attack(self.demo_skills.pop())
                    self.demo_play_actions += 1

    def draw(self):
        # 1. 繪製 800x600 底圖
        self.screen.blit(self.background, (0, 0))

        cfg = self.choices[self.index]
        color = cfg.get("neon_color", (255, 255, 255))

        # 2. 繪製選中的不規則多邊形高亮框
        import math
        glow = (math.sin(pygame.time.get_ticks() * 0.005) * 50) + 150

        if self.index < len(self.focus_polygons):
            # 呼叫您寫好的多邊形渲染方法
            self.draw_neon_polygon(self.screen, self.focus_polygons[self.index], color, glow)

        # 3. 繪製下方的資訊看板
        self.draw_bottom_ui()

    def draw_neon_polygon(self, surface, points, color, glow_intensity):
        """繪製多邊形霓虹框"""
        # 繪製 3 層不同寬度與透明度的多邊形
        for i in range(3):
            alpha = max(0, glow_intensity - i * 40)
            s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            # draw.polygon 支援繪製不規則形狀
            pygame.draw.polygon(s, (*color, alpha), points, 6 + i * 3)
            surface.blit(s, (0, 0))

    def draw_bottom_ui(self):
        BAR_Y = 480
        cfg = self.choices[self.index]
        color = cfg.get("neon_color", (255, 255, 255))

        # 1. 繪製人物全彩立繪 (靠左，稍微超出 Bar 邊界增加層次感)
        tachie_path = cfg.get("preview_tachie")
        if tachie_path and self.ui_alpha > 50:
            tachie_img = pygame.image.load(tachie_path).convert_alpha()
            # 調整高度讓立繪看起來是從下方邊緣「探頭」出來
            self.screen.blit(tachie_img, (-20, HEIGHT - tachie_img.get_height() + 20))

        # 2. 繪製遊戲內動畫格 (居中)
        # 🟢 修正：為了讓人物出現在下方 Bar (y=480~600)，我們需要大幅調整 cam_y
        # 因為 map_h 只有 1，所以 py 基礎值很小。我們用負值 cam_y 把他推下來。
        # 建議目標螢幕位置 (x=300, y=560)
        target_screen_x = 320
        target_screen_y = 630

        # 計算 cam 補正 (根據 Characters.py 的公式反推)
        fake_cam_x = -target_screen_x + 24  # 24 為 width 修正
        fake_cam_y = -target_screen_y + 32  # 32 為 height 修正

        self.preview_unit.draw(self.screen, fake_cam_x, fake_cam_y, 0)

        # 修改 draw_bottom_ui 內的文字部分
        text_x, text_y = 400, 460
        if self.ui_alpha > 0:
            # 名稱 (大字)
            name_txt = self.font.render(cfg.get("display_name", ""), True, COLOR_TITLE)
            name_txt.set_alpha(self.ui_alpha)
            self.screen.blit(name_txt, (text_x, text_y))

            # 技能說明 (強調色)
            skill_txt = self.font.render(cfg.get("skill_info", ""), True, COLOR_HIGHLIGHT)  # 綠色強調
            skill_txt.set_alpha(self.ui_alpha)
            self.screen.blit(skill_txt, (text_x+10, text_y+35))

            # 長描述 (自動換行)
            desc_lines = self.wrap_text(cfg.get("description", ""), 340)
            for i, line in enumerate(desc_lines):
                txt = self.font.render(line, True, COLOR_BODY)
                txt.set_alpha(self.ui_alpha)
                self.screen.blit(txt, (text_x+10, text_y+70 + i * 25))

    def wrap_text(self, text, max_width):
        """借用 SpeechBubble 的邏輯"""
        words = list(text)  # 中文按字拆分
        lines, current = [], ""
        for word in words:
            test = current + word
            if self.font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines