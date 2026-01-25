# scene_manager.py
import pygame
from Config import *
from State_enum import *
import math



#新增EnvironmentManager，用於控制圖片插入/高亮/前後景渲染
class EnvironmentManager:
    def __init__(self):
        # 濾鏡層：處理變暗效果
        self.dim_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.dim_overlay.fill((0, 0, 0))
        self.dim_alpha = 0
        self.target_dim_alpha = 0

        # 插畫層：接管原本的 end_cuts
        self.cutscene_images = []
        self.image_alpha = 0
        self.image_target_alpha = 0

        # 權限管理：Step 2 預留
        self.highlight_units = set()

        #end cut用
        self.cutscene_images = []
        self.image_alpha = 0
        self.cutscene_timer = 0
        self.current_img_idx = 0
        self.fade_in_speed = 5
        # 演算法常數 (參考原 SceneManager 的邏輯)
        self.clear_text = ""
        self.clear_font = None
        self.text_alpha = 0

        # 演算法常數 (還原原 SceneManager 的邏輯)
        self.STAY_TIME = 120
        self.FADE_TIME = 60
        self.cutscene_timer = 0
        self.current_img_idx = 0

    def update(self):
        # 處理變暗漸變
        if self.dim_alpha < self.target_dim_alpha:
            self.dim_alpha = min(self.target_dim_alpha, self.dim_alpha + 15)
        elif self.dim_alpha > self.target_dim_alpha:
            self.dim_alpha = max(self.target_dim_alpha, self.dim_alpha - 15)

        # 處理插畫漸變 (Fade in)
        # 🟢 通關圖片時序演算法還原
        if self.cutscene_images:
            self.cutscene_timer += 1

            # 判斷目前進度決定 alpha (模仿原本 draw_overlay 的邏輯)
            # 假設每張圖循環週期 = FADE_TIME + STAY_TIME
            cycle_time = self.STAY_TIME + self.FADE_TIME
            progress = self.cutscene_timer % cycle_time

            if progress < self.FADE_TIME:
                # 淡入階段
                self.image_alpha = int((progress / self.FADE_TIME) * 255)
            else:
                # 停留階段 (維持全亮)
                self.image_alpha = 255

            # 切換下一張圖
            if self.cutscene_timer > 0 and progress == 0:
                self.current_img_idx = (self.current_img_idx + 1) % len(self.cutscene_images)

    def set_dim(self, active, alpha=160):
        self.target_dim_alpha = alpha if active else 0

    def set_cutscene(self, images, text=None, font=None):
        """啟動通關幻燈片與文字"""
        self.cutscene_images = images
        self.clear_text = text
        self.clear_font = font
        self.current_img_idx = 0
        self.cutscene_timer = 0
        self.image_alpha = 0

    def draw_filter(self, win):
        """繪製變暗濾鏡 (位於背景單位與高亮單位之間)"""
        if self.dim_alpha > 0:
            self.dim_overlay.set_alpha(self.dim_alpha)
            win.blit(self.dim_overlay, (0, 0))

    def draw_cutscenes(self, win):
        # 1. 繪製幻燈片 (確保居中)
        if self.cutscene_images and self.image_alpha > 0:
            img = self.cutscene_images[self.current_img_idx]
            img.set_alpha(self.image_alpha)
            # 修正圖片位置：取畫面中心點
            rect = img.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            win.blit(img, rect)

        # 2. 繪製通關文字 (原 draw_overlay 邏輯還原)
        if self.clear_text and self.clear_font:
            txt = self.clear_font.render(self.clear_text, True, (255, 255, 0))
            outline = self.clear_font.render(self.clear_text, True, (0, 0, 0))
            x = (WIDTH - txt.get_width()) // 2
            y = (HEIGHT - txt.get_height()) // 2

            # 繪製簡單外框
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                win.blit(outline, (x + dx, y + dy))
            win.blit(txt, (x, y))

class VisualEffect:
    def __init__(self, x, y, z, frames, anim_speed=4, alpha=255, flip = False):
        self.x = x
        self.y = y
        self.z = z
        self.frames = frames  # 這是已經預先切片好的打擊特效圖組
        self.anim_speed = anim_speed
        self.timer = 0
        self.alive = True
        self.alpha = alpha
        self.flip = flip

    def update(self):
        self.timer += 1
        # 當播放完所有動畫幀時，標記為死亡
        if self.timer >= len(self.frames) * self.anim_speed:
            self.alive = False

    def draw(self, win, cam_x, cam_y, tile_offset_y, map_h):
        if not self.alive: return

        # 計算當前應該顯示哪一幀
        frame_idx = self.timer // self.anim_speed
        frame = self.frames[frame_idx]

        # 轉換 2.5D 座標到螢幕 (參考 Characters.py 的 draw_anim 邏輯)
        px = int(self.x * TILE_SIZE) - cam_x
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        py = int((map_h - self.y) * TILE_SIZE - terrain_z_offset) - cam_y + tile_offset_y

        # 居中繪製
        frame.set_alpha(self.alpha)
        if self.flip:
            frame = pygame.transform.flip(frame, True, False)
        rect = frame.get_rect(center=(px, py))
        win.blit(frame, rect)

class SceneManager:
    def __init__(self, map_h, map_w, terrain, end_cuts=None, bg_path = None):
        self.interactables = []
        self.projectiles = []  # 可擴充的道具如飛鏢、火球等
        self.floating_texts = []  # 新增傷害文字列表
        self.to_be_removed = []  # 待移除物件清單
        self.speech_bubbles = []    # 對話泡泡框
        # 劇情器-->
        self.script_runner = StoryScriptRunner(self)
        self.script_controlled_units = set()  # 存放目前劇情控制角色
        self.lock_others_during_script = True  # 控制是否鎖定非劇情角色
        # ==== 新增：畫面變暗 / 通關相關狀態 ====
        #self.darken_enabled = False
        #self.darken_alpha = 0
        self.darken_alpha_max = 160
        self.darken_speed = 1

        self.cleared = False
        self.clear_text = ""
        self.clear_font = None  # 由外部設定（main 或 scene_1）
        self.scene_end_countdown = -1
        self.state =SceneState.NORMAL
        self.super_move_anim = None
        self.super_move_damage = None
        self.super_move_timer = 0
        self.super_move_max_timer = 0
        self.super_move_portrait_begin = 0
        self.super_move_pre_pose_background = None
        self.super_move_effect = None

        self.super_move_portrait = []  # 儲存 super_move_tachie.png
        self.super_move_portrait_images = [] #一次讀取並儲存
        self.super_move_caster = None  # 紀錄是誰放的大招
        self.super_move_full_frames = []  # 儲存全畫面特效動畫
        #self.end_cuts = []

        self.env_manager = EnvironmentManager()
        self.map_h = map_h
        self.map_w = map_w
        self.terrain = terrain
        self.background_img = None
        if bg_path:
            raw_img = pygame.image.load(bg_path).convert()
            # 根據地圖大小自動縮放
            self.background_img = pygame.transform.scale(
                raw_img, (self.map_w * TILE_SIZE, self.map_h * TILE_SIZE)
            )

        # if end_cuts:
        #     for cut in end_cuts:
        #         self.end_cuts.append(pygame.image.load(cut).convert_alpha())
        # 將 end_cuts 傳給 env_manager
        self.end_cuts = []
        if end_cuts:
            self.end_cuts = [pygame.image.load(c).convert_alpha() for c in end_cuts]
            #self.env_manager.set_cutscene(imgs)


        #打擊特效
        self.visual_effects = []  # 專門儲存打擊特效
        self.hit_effect_frames = self.load_effect_assets(path="..//Assets_Drive//on_hit_effect.png", frame_w=45, frame_h=45)  # 預載特效圖
        self.hitstop_effect_frames = self.load_effect_assets(path="..//Assets_Drive//hit_stop1.png", frame_w=128, frame_h=128)  # 預載特效圖
        self.brust_effect_frames = self.load_effect_assets(path="..//Assets_Drive//brust.png", frame_w=128,frame_h=128)  # 預載特效圖
        self.guard_effect_frames = self.load_effect_assets(path="..//Assets_Drive//guard_effect.png", frame_w=96,frame_h=96)  # 預載特效圖
        self.clash_effect_frames = self.load_effect_assets(path="..//Assets_Drive//clash_effect.png", frame_w=96,frame_h=96)  # 預載特效圖
        #def load_effect_assets(self, ):
        self.map_h = map_h
        self.shake_timer = 0
        self.shake_intensity = 0
        self.default_font_36 = pygame.font.SysFont("Arial Black", 36)   #預載入文字
        self.hit_stop_timer = 0
        #AI攻擊用
        self.attack_tokens = 3  # 同時最多敵人可以進攻
        self.token_holders = {}  # 紀錄目前持有權杖的單位
        self.frame_count = 0

    def trigger_scene_end(self):
        """
                當通關條件達成時呼叫。
                1. 讓背景全黑 (或很暗)
                2. 啟動插畫淡入
                """
        # 背景變暗 (alpha設高一點，營造終局感)
        self.env_manager.set_dim(True, alpha=220)
        #
        # # 傳入圖片清單並開始淡入
        # if self.end_cuts:
        #     # 如果傳入的是路徑，就在這裡載入 (依據你之前的直覺)
        #     loaded_imgs = []
        #     for path in end_cuts:
        #         img = pygame.image.load(path).convert_alpha()
        #         # 縮放到畫面大小
        #         img = pygame.transform.scale(img, (WIDTH, HEIGHT))
        #         loaded_imgs.append(img)
        #     self.env_manager.set_cutscene(loaded_imgs)
    def toggle_highlight_test(self, unit):
        """
        測試用：切換變暗效果，並決定是否讓特定單位跳脫黑幕。
        """
        if self.env_manager.dim_alpha == 0:
            # 🟢 啟動變暗，並讓傳入的單位高亮
            self.env_manager.set_dim(True, alpha=180)
            self.env_manager.highlight_units.add(unit)
            print(f"[TEST] {unit.name} 啟動高亮，環境變暗")
        else:
            # 🔴 恢復正常
            self.env_manager.set_dim(False)
            self.env_manager.highlight_units.clear()
            print("[TEST] 恢復環境亮度，清空高亮名單")

    def update_tokens(self):
        """每幀更新權杖狀態，處理過期回收"""
        expired_units = []
        for unit, timer in self.token_holders.items():
            # 減少計時器
            self.token_holders[unit] -= 1
            # 1. 檢查是否死亡或被移除，2. 檢查計時器是否歸零
            if not unit.is_alive() or self.token_holders[unit] <= 0:
                expired_units.append(unit)
        for unit in expired_units:
            print(f"[TOKEN] 回收 {unit.name} 的權杖 (超時或死亡)")
            del self.token_holders[unit]
        # --- 新增：強制作戰機制 ---
        # 如果目前沒有人領取權杖，但場上還有敵人
        token_holders = [e.name for e in self.token_holders]
        #print(f'SCENE [{self.frame_count}], TOKEN [{token_holders}]')
        if len(self.token_holders) == 0:
            enemies = self.get_units_by_side('enemy_side')
            alive_enemies = [e for e in enemies if e.is_alive()]

            if alive_enemies:
                # 隨機挑選一名幸運兒，無視其性格強制發放
                import random
                lucky_guy = random.choice(alive_enemies)
                self.request_token(lucky_guy)
                print(f"[TOKEN] 強制指派進攻權給: {lucky_guy.name}")
                #lucky_guy.say("我...我上就是了啊啊啊!")

    def request_token(self, unit):
        """AI 申請進攻權"""
        if unit in self.token_holders:
            return True  # 已經持有了

        if len(self.token_holders) < self.attack_tokens:
            self.token_holders[unit] = 300  # 給予 180 幀 (約 3 秒) 的進攻窗口
            print(f"[TOKEN] 發放權杖給 {unit.name}")
            return True
        return False

    def refresh_token(self, unit):
        """當 AI 攻擊時，重置其權杖計時器"""
        if unit in self.token_holders:
            self.token_holders[unit] = 300

    def trigger_hit_stop(self, frames):
        """觸發時間凍結"""
        self.hit_stop_timer = max(self.hit_stop_timer, frames)
    def create_effect(self, x, y, z, type='hit', flip=False):
        # 這裡的 z 通常是碰撞盒交疊的中心 z
        new_effect = None
        if type =='hit':
            new_effect = VisualEffect(x, y, z, self.hit_effect_frames, anim_speed=2, alpha=255)
        elif type == 'hitstop':
            new_effect = VisualEffect(x, y, z, self.hitstop_effect_frames, anim_speed=2, alpha=200, flip=flip)
        elif type == 'brust':
            new_effect = VisualEffect(x, y, z, self.brust_effect_frames, anim_speed=2, alpha=200)
        elif type == 'guard':
            new_effect = VisualEffect(x, y, z, self.guard_effect_frames, anim_speed=2, alpha=160)
        elif type == 'clash':
            new_effect = VisualEffect(x, y, z, self.clash_effect_frames, anim_speed=2, alpha=140)
        if new_effect:
            self.visual_effects.append(new_effect)

    def load_effect_assets(self, path="..//Assets_Drive//on_hit_effect.png", frame_w=45, frame_h=45):
        """
        載入打擊特效圖集並自動切片。
        """
        try:
            sheet = pygame.image.load(path).convert_alpha()  #
            sheet_w, sheet_h = sheet.get_size()
            cols = sheet_w // frame_w
            rows = sheet_h // frame_h

            frames = []
            for r in range(rows):
                for c in range(cols):
                    # 定義子區域並複製
                    rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                    frame = sheet.subsurface(rect).copy()  #
                    frames.append(frame)
            return frames
        except Exception as e:
            print(f"[ERROR] 載入特效失敗: {e}")
            # 回傳一個預設的紅色方塊，確保程式不崩潰
            surface = pygame.Surface((32, 32))
            surface.fill((255, 0, 0))
            return [surface]

    # --- 讓外部設定字型 ---
    def set_clear_font(self, font):
        self.clear_font = font

    # --- 重置變暗 / 通關狀態 ---
    def reset_overlay(self):
        self.darken_enabled = True
        self.darken_alpha = 0
        self.cleared = False
        self.clear_text = ""

    # --- 通關觸發 ---
    def trigger_clear(self, message="STAGE CLEAR", countdown=180):
        self.cleared = True
        self.clear_text = message
        self.scene_end_countdown = countdown

        # 同步推送到環境管理員
        self.env_manager.set_cutscene(self.end_cuts, message, self.clear_font)
        # 啟動變暗 (取代原本 scene_mato 裡的 darken_enabled = True)
        self.env_manager.set_dim(True, alpha=220)



    # --- 在每幀繪圖最後呼叫 ---
    # def draw_overlay(self, win):
    #     # 畫面變暗
    #     if self.darken_enabled and self.scene_end_countdown > 0:
    #         if self.darken_alpha < self.darken_alpha_max:
    #             self.darken_alpha = min(
    #                 self.darken_alpha_max,
    #                 self.darken_alpha + self.darken_speed
    #             )
    #         dark_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    #         dark_surface.fill((0, 0, 0, self.darken_alpha))
    #         win.blit(dark_surface, (0, 0))
    #
    #
    #
    #
    #     # 通關
    #     if self.cleared and self.clear_font and self.clear_text:
    #         txt = self.clear_font.render(self.clear_text, True, (255, 255, 0))
    #         outline = self.clear_font.render(self.clear_text, True, (0, 0, 0))
    #         x = (WIDTH - txt.get_width()) // 2
    #         y = (HEIGHT - txt.get_height()) // 2
    #
    #         for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
    #             win.blit(outline, (x + dx, y + dy))
    #         win.blit(txt, (x, y))
    #
    #         if len(self.end_cuts) > 0:
    #             cut_count = len(self.end_cuts)
    #             life_cycle = 180/cut_count
    #             cut_duration = int(life_cycle/2)
    #             fading = int(cut_duration/2)
    #             for i, cut in enumerate(self.end_cuts):
    #                 frame_fadein = (fading+cut_duration)*(cut_count-i)+fading
    #                 frame_highlight = frame_fadein-fading
    #                 frame_fadeout = frame_highlight-cut_duration
    #                 frame_disspear = frame_fadeout-fading
    #                 #print(f"[{self.scene_end_countdown}] endcut {i}, ({frame_fadein}, {frame_highlight}, {frame_fadeout}, {frame_disspear})")
    #                 if frame_fadein > self.scene_end_countdown >= frame_highlight:
    #                     alpha = min(255, max(0, int(255*(frame_fadein - self.scene_end_countdown)/fading)))
    #                 elif frame_highlight > self.scene_end_countdown >= frame_fadeout:
    #                     alpha=255
    #                 elif frame_fadeout > self.scene_end_countdown >= frame_disspear:
    #                     if i != cut_count-1:
    #                         alpha = min(255, max(0, int(255*(frame_fadeout-self.scene_end_countdown)/fading)))
    #                     else:
    #                         alpha=255
    #                 else:
    #                     alpha = 0
    #                 if alpha > 0:
    #                     cut.set_alpha(alpha)
    #                     win.blit(cut, (WIDTH // 2 - cut.get_width() // 2, HEIGHT // 2 - cut.get_height() // 2))
    #

    def draw_super_move_overlay(self, win, cam_x, cam_y, tile_offset_y):

        if self.state != SceneState.SUPER_MOVE:
            return

            # 計算當前進度 (1.0 -> 0.0)
        progress = self.super_move_timer / self.super_move_max_timer

        # 1. 繪製全畫面黑色半透明背景 (背景變暗)
        dark_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark_surface.fill((0, 0, 0, 180))
        win.blit(dark_surface, (0, 0))
        # 2. 繪製發動者 (讓他穿透黑幕，顯得亮眼)
        #先插入背景

        if self.super_move_pre_pose_background is not None and progress > self.super_move_portrait_begin:
            bkg_idx = int(len(self.super_move_pre_pose_background)*(1.0-progress)/(1.0 - self.super_move_portrait_begin)+0.5)
            if bkg_idx >= len(self.super_move_pre_pose_background):
                bkg_idx = -1
            img = self.super_move_pre_pose_background[bkg_idx]
            img.set_alpha(200)
            win.blit(img, (WIDTH // 2 - img.get_width() // 2, HEIGHT // 2 - img.get_height() // 2))

        # 這裡要呼叫 caster 的繪製邏輯，但位置不隨相機移動(特寫)或在原地
        # 建議讓發動者在原地播放 special_move.png 動畫
        if self.super_move_caster:
            self.super_move_caster.draw_super_move_character(win, cam_x, cam_y, tile_offset_y, show_period=1-self.super_move_portrait_begin)
        # 此處由 draw_all 邏輯決定，通常我們會把 caster 的繪製層級提高


        # 3. 繪製人物立繪 (Tachie) - 在特定時間點切入
        # # 假設在計時器剩餘 80% 到 30% 時顯示
        # if 0.15 < progress < 0.5:
        #     # 簡單的滑入動畫效果
        #     offset_x = (progress - 0.15) * 100 if progress > 0.15 else 0
        #     win.blit(self.super_move_portrait, (WIDTH // 2 - 200 + offset_x, HEIGHT // 2 - 200))
        for p_cfg in self.super_move_portrait:
            if p_cfg['end'] <= progress <= p_cfg['start']:
                img = p_cfg['image']

                # --- 計算該段立繪的局部進度 (0.0 到 1.0) ---
                # 當 progress 從 start 變到 end，local_p 會從 0.0 變到 1.0
                segment_duration = p_cfg['start'] - p_cfg['end']
                local_p = (p_cfg['start'] - progress) / segment_duration
                # 這裡的 300 是滑動距離，您可以根據需求調整
                slide_dist = 150
                if p_cfg.get('dir') == 'R2L':
                    # 從 右側(slide_dist) 滑到 中央(0)
                    #offset_x = slide_dist * (1 - local_p * 1.5)  # 1.5 倍速讓它快速到位後微移
                    offset_x = slide_dist * (1 - (1-local_p) * (1-local_p))
                    offset_x = max(0, offset_x)
                else:  # L2R
                    # 從 左側(-slide_dist) 滑到 中央(0)
                    offset_x = -slide_dist * (1 - (1-local_p) * (1-local_p))
                    offset_x = min(0, offset_x)
                # --- 計算最終座標 ---
                base_x = WIDTH // 2 - img.get_width() // 2
                base_y = HEIGHT // 2 - img.get_height() // 2 + p_cfg.get('offset_y', 0)

                # --- Alpha 漸顯效果 (Fade In) ---
                alpha = int(min(local_p * 5, 1.0) * 255)  # 快速漸顯
                img.set_alpha(alpha)

                win.blit(img, (base_x + offset_x, base_y))
                break


        # 4. 全畫面傷害特效 (當計時器快結束時)
        if progress < 0.15:
            # 將 0.5 改為 0.2，速度會變為原本的 2/5 (變慢)
            frequency = 0.3
            # 這裡只改第一個 0.5，後面的 0.5 + 0.5 是為了維持 0~255 的範圍，不要動它們
            alpha = int((math.sin(self.super_move_timer * frequency) * 0.5 + 0.5) * 255)
            img = self.super_move_effect
            img.set_alpha(alpha)
            win.blit(img, (WIDTH // 2 - img.get_width() // 2, HEIGHT // 2 - img.get_height() // 2))


    def draw_ui(self, win, font, color=(255, 255, 255), outline_color=(0, 0, 0)):
        players = self.get_units_by_name("player")
        if not players: return
        player = players[0]

        # --- 配置參數 ---
        UI_X, UI_Y = 20, HEIGHT - 80  # UI 左下角起始位置
        BAR_WIDTH = 200
        BAR_HEIGHT = 15

        # 1. 繪製血條 (HP) - 黃條紅底
        # 底色 (深紅)
        pygame.draw.rect(win, (100, 0, 0), (UI_X, UI_Y, BAR_WIDTH, BAR_HEIGHT))
        # 當前血量 (亮黃/橘)
        hp_visual_ratio = max(0, player.health_visual / player.max_hp)
        pygame.draw.rect(win, (255, 255, 255), (UI_X, UI_Y, int(BAR_WIDTH * hp_visual_ratio), BAR_HEIGHT))

        hp_ratio = max(0, player.health / player.max_hp)
        pygame.draw.rect(win, (255, 200, 0), (UI_X, UI_Y, int(BAR_WIDTH * hp_ratio), BAR_HEIGHT))
        # 外框
        pygame.draw.rect(win, (255, 255, 255), (UI_X, UI_Y, BAR_WIDTH, BAR_HEIGHT), 2)

        # 標籤文字
        hp_label = font.render(f"HP {player.health}/{player.max_hp}", True, (255, 255, 255))
        win.blit(hp_label, (UI_X, UI_Y - 30))

        # 2. 繪製魔力條 (MP) - 10格點陣式
        MP_Y = UI_Y + 25
        GRID_W = 15
        GRID_H = 10
        SPACING = 4
        MAX_MP = 10

        for i in range(MAX_MP):
            grid_x = UI_X + i * (GRID_W + SPACING)
            # 背景格 (半透明深藍)
            pygame.draw.rect(win, (0, 0, 50), (grid_x, MP_Y, GRID_W, GRID_H))

            # 填充格 (亮藍)
            if i < player.mp:
                pygame.draw.rect(win, (0, 191, 255), (grid_x, MP_Y, GRID_W, GRID_H))

            # 格子外框
            pygame.draw.rect(win, (200, 200, 200), (grid_x, MP_Y, GRID_W, GRID_H), 1)

        # 3. 繪製金錢 (GOLD)
        gold_label = font.render(f"GOLD: {player.money}", True, (255, 215, 0))
        win.blit(gold_label, (UI_X, MP_Y + 20))

    def mark_for_removal(self, unit):
        if unit not in self.to_be_removed:
            self.to_be_removed.append(unit)

    def register_unit(self, unit, side=None, tags=None, type=None):
        self.interactables.append(unit)
        unit.scene = self  # ✅ 確保每個單位都知道場景
        unit.side = side
        unit.tags = tags or []
        unit.type = type

    def unregister_unit(self, unit):
        if unit in self.interactables:
            self.interactables.remove(unit)
        unit.scene = None
        for c in unit.components.values():
            c.owner = None

    def update_all(self):
        self.frame_count+=1
        enemy_remove_count = 0
        # 如果處於 Hit Stop 期間，倒數計時並跳過邏輯更新
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= 1
            print(f'scene updateall: hit_stop_timer {self.hit_stop_timer}')
            return enemy_remove_count# 關鍵：直接回傳，不執行下方的 units.update()

        # 更新環境
        if self.cleared:
            # 1. 讓環境變暗
            self.env_manager.set_dim(True, alpha=220)
            # 2. 如果 env 尚未開始播放圖片，則初始化圖片
            if not self.env_manager.cutscene_images:
                self.env_manager.set_cutscene(self.end_cuts)

        self.env_manager.update()
        # 🟢 新增：全域碰撞攔截階段 (攔截 Clash 與傷害)
        # 在單位 update 之前執行，確保公平性
        self.update_collision_logic()

        self.script_runner.update()
        self.update_tokens()
        for unit in self.interactables:
            #如果劇情模式開啟，且這個單位不在受控名單中 → 跳過更新
            if self.script_runner.active and self.lock_others_during_script:
                if unit not in self.script_controlled_units:
                    continue
            unit.update_components()
            if self.state == SceneState.NPC_BLOCK:
                if "player" not in unit.name:
                    continue
            if self.state == SceneState.PLAYER_BLOCK:
                if "player" in unit.name:
                    continue
            if self.state == SceneState.SUPER_MOVE:
                if hasattr(unit, "unit_type"):
                    if unit.unit_type == "character":
                        continue
            unit.update()
        for text in self.floating_texts:
            text.update()
        self.floating_texts = [t for t in self.floating_texts if t.is_alive()]  # 自動清除結束的
        # 🔸移除所有標記為移除的物件
        for unit in self.to_be_removed:
            self.unregister_unit(unit)
            if unit.side == 'enemy_side':
                enemy_remove_count += 1
            print(f'scene_manager: 註銷{unit.name}')
        self.to_be_removed.clear()
        # 對話泡泡
        for bubble in self.speech_bubbles:
            bubble.update()
        self.speech_bubbles = [b for b in self.speech_bubbles if b.is_alive()]

        if self.state == SceneState.SUPER_MOVE:
            if self.super_move_timer == 1:
                self.execute_super_move_damage()
            if self.super_move_timer > 0:
                self.super_move_timer -= 1
            else:
                #結束魔法使用
                print('enhance damage and clear super move state')
                self.state = SceneState.NORMAL
                self.super_move_timer = 0
                self.super_move_damage = None
                self.super_move_anim = None
                self.super_move_caster.super_move_anim_timer = 0
                self.super_move_portrait_begin = 0
                self.super_move_portrait.clear()

        for vfx in self.visual_effects:
            vfx.update()
        self.visual_effects = [vfx for vfx in self.visual_effects if vfx.alive]

        if self.scene_end_countdown > 0:
            self.scene_end_countdown = self.scene_end_countdown -1
        if self.scene_end_countdown == 0:
            print('SceneManager: scene end')
        return enemy_remove_count

    def trigger_shake(self, duration=20, intensity=10):
        """觸發螢幕震動：duration 為持續幀數，intensity 為最大偏移像素"""
        self.shake_timer = duration
        self.shake_intensity = intensity

    def get_camera_offset(self):
        """
        計算並回傳當前的震動偏移 (ox, oy)。
        建議在 main.py 計算 cam_x/y 後累加。
        """
        if self.shake_timer > 0:
            import random
            # 隨時間衰減震動強度，讓演出更平滑
            decay = self.shake_timer / 20.0  # 假設預設持續 20 幀
            current_range = self.shake_intensity * decay

            ox = random.uniform(-current_range, current_range)
            oy = random.uniform(-current_range, current_range)

            self.shake_timer -= 1
            return int(ox), int(oy)
        return 0, 0
    def execute_super_move_damage(self):
        # 1. 取得所有敵人
        enemies = self.get_units_by_side('enemy_side')

        # 2. 準備一個威力強大的大招攻擊數據
        # 建議在 Skill.py 預定義一個 AttackType.SUPER_FINISH
        from Skill import attack_data_dict
        super_data = attack_data_dict.get(AttackType.SUPER_FINAL)
        super_data.damage = self.super_move_damage
        for enemy in enemies:
            if enemy.is_alive():
                # 觸發命中邏輯
                enemy.on_hit(self.super_move_caster, super_data)

                # 在敵人受擊中心點產生特效
                box = enemy.get_hurtbox()
                cx = (box['x1'] + box['x2']) / 2
                cy = (box['y1'] + box['y2']) / 2
                cz = (box['z1'] + box['z2']) / 2
                self.create_effect(cx, cy, cz,'hit')

        # 3. 觸發全畫面劇烈震動
        self.trigger_shake(duration=30, intensity=15)

    def get_all_units(self):
        return self.interactables

    def get_units_by_side(self, side):
        return [u for u in self.interactables if u.side == side]

    def get_units_with_tag(self, tag):
        return [u for u in self.interactables if tag in u.tags]

    def get_units_with_type(self, type):
        return [u for u in self.interactables if u.type == type]
    def get_units_by_name(self, name):
        return [u for u in self.interactables if u.name == name]

    def say(self, unit, text, duration=90, direction='up'):
        bubble = SpeechBubble(unit, text, duration, direction=direction)
        self.speech_bubbles.append(bubble)

    # def draw_all(self,win, cam_x, cam_y, tile_offset_y):
    #     all_drawables = []
    #
    #     # 包裝所有可繪製物件，加上 type 標記方便後續判斷
    #     for unit in self.interactables:
    #         if self.state == SceneState.SUPER_MOVE:
    #             #在draw_super_move_overlay繪製專用animator
    #             if unit == self.super_move_caster:
    #                 continue
    #         all_drawables.append(("unit", unit))
    #         #print(f'{unit.name}sY={unit.y}')
    #     for proj in self.projectiles:
    #         all_drawables.append(("projectile", proj))
    #
    #     font = get_cjk_font(20, prefer='tc')  # or 'tc'
    #     all_drawables.sort(key=lambda item: getattr(item[1], 'y', 0), reverse=True)
    #     for item_type, obj in all_drawables:
    #         if item_type == "text":
    #             obj.draw(win, cam_x, cam_y, tile_offset_y, font)
    #         else:
    #             obj.draw(win, cam_x, cam_y, tile_offset_y)
    #     # 2. 在所有角色畫完之後，額外「疊加」玩家剪影
    #     players = self.get_units_by_name("player")
    #     if players:
    #         player = players[0]
    #         # 建立一個半透明的影子 (Alpha 設為 100~128)
    #         # 這裡可以直接呼叫 player 的 draw，但內部需要支持 alpha 覆蓋
    #         player.draw_silhouette(win)
    #
    #
    #     for text in self.floating_texts:
    #         text.draw(win, cam_x, cam_y, tile_offset_y, self.default_font_36)  # 顯示傷害文字
    #
    #     # 2. 畫特效 (確保特效覆蓋在角色上方)
    #     for vfx in self.visual_effects:
    #         vfx.draw(win, cam_x, cam_y, tile_offset_y, self.map_h)
    #     # ✅ 繪製 SpeechBubble
    #     #font = pygame.font.SysFont(None, 18)
    #
    #     for bubble in self.speech_bubbles:
    #         bubble.draw(win, cam_x, cam_y, tile_offset_y, font)
    #
    #
    #
    #     self.draw_overlay(win)
    #     if self.state == SceneState.SUPER_MOVE:
    #         self.draw_super_move_overlay(win, cam_x, cam_y, tile_offset_y)
    #
    #     self.draw_ui(win, font)
    def draw_all(self, win, cam_x, cam_y, tile_offset_y):
        # --- 準備工作 ---
        font = get_cjk_font(20, prefer='tc')
        all_units = self.interactables

        # 1. 第一層：地圖背景 (正式從 main.py 移入)
        if hasattr(self, 'background_img') and self.background_img:
            win.blit(self.background_img, (-cam_x, -cam_y + tile_offset_y))

        # 2. 物件準備與排序 (Z-Sorting)
        all_drawables = []
        for unit in all_units:
            # 大招期間排除發動者 (因為發動者會在大招特寫層繪製)
            if self.state == SceneState.SUPER_MOVE and unit == self.super_move_caster:
                continue
            all_drawables.append(("unit", unit))

        for proj in self.projectiles:
            all_drawables.append(("projectile", proj))

        # 根據 Y 軸排序，確保前後遮擋正確
        all_drawables.sort(key=lambda item: getattr(item[1], 'y', 0), reverse=True)

        # 3. 第二層：一般物件繪製 (濾鏡下方)
        # 這裡只畫「沒被高亮」的單位
        is_dimming = self.env_manager.dim_alpha > 0
        for item_type, obj in all_drawables:
            if not is_dimming or obj not in self.env_manager.highlight_units:
                obj.draw(win, cam_x, cam_y, tile_offset_y)

        # 4. 第三層：環境變暗濾鏡 (Step 1 核心)
        # 這個遮罩會壓在一般單位與地圖上，但不會壓到高亮單位
        self.env_manager.draw_filter(win)

        # 5. 第四層：高亮物件繪製 (濾鏡上方)
        if is_dimming:
            for item_type, obj in all_drawables:
                if obj in self.env_manager.highlight_units:
                    obj.draw(win, cam_x, cam_y, tile_offset_y)

        # 6. 第五層：角色裝飾與世界空間特效 (不受濾鏡影響或在最上方)
        # 玩家剪影
        players = self.get_units_by_name("player")
        if players:
            players[0].draw_silhouette(win)

        # 傷害數字
        for text in self.floating_texts:
            text.draw(win, cam_x, cam_y, tile_offset_y, self.default_font_36)

        # 戰鬥特效 (Hit, Spark 等)
        for vfx in self.visual_effects:
            vfx.draw(win, cam_x, cam_y, tile_offset_y, self.map_h)

        # 對話氣泡
        for bubble in self.speech_bubbles:
            bubble.draw(win, cam_x, cam_y, tile_offset_y, font)

        # 7. 第六層：全螢幕演出層 (最上層)
        # 大招特寫 (內含自己的變暗邏輯與立繪)
        if self.state == SceneState.SUPER_MOVE:
            self.draw_super_move_overlay(win, cam_x, cam_y, tile_offset_y)

        # 通關插圖 (End Cuts) - 現在由 EnvironmentManager 接管
        self.env_manager.draw_cutscenes(win)

        # UI 永遠在最前方
        self.draw_ui(win, font)

    def add_floating_text(self, x, y, value, map_h, color, font_size=24):
        self.floating_texts.append(FloatingText(x, y, value, map_h, duration=60, color=color, font_size=font_size))

    def start_super_move(self, caster, super_move_dict):
        self.state = SceneState.SUPER_MOVE
        portraits = super_move_dict.get('portraits')
        effect = super_move_dict.get('effect')
        pre_pose_background = super_move_dict.get('pre_pose_background')
        #把anim_path讀取frames塞入super_move_anim
        self.super_move_caster = caster
        self.super_move_timer = super_move_dict['timer']
        self.super_move_damage = super_move_dict['damage']
        self.super_move_max_timer = super_move_dict['timer']
        self.super_move_portrait_begin = super_move_dict['portraits_begin']

        # 載入立繪與特效 (實際開發建議在 init 或啟動時預載)
        for portrait in portraits:
            portrait['image'] = pygame.image.load(portrait['path']).convert_alpha()
            self.super_move_portrait.append(portrait)
        if effect is not None:
            self.super_move_effect = pygame.image.load(effect).convert_alpha()
        if pre_pose_background is not None:
            self.super_move_pre_pose_background = []
            for pth in pre_pose_background:
                self.super_move_pre_pose_background.append(pygame.image.load(pth).convert_alpha())
        # 這裡可以加入載入全畫面特效圖組的邏輯

    def get_nearby_units_by_side(self, center_x, center_y, radius, side):
        """
        找出以 (center_x, center_y) 為中心，半徑 radius 內，屬於 side 陣營的單位。
        """
        nearby = []
        for unit in self.get_units_by_side(side):
            # 使用歐幾里得距離平方避開開根號運算，提升效能
            dx = unit.x - center_x
            dy = unit.y - center_y
            if (dx ** 2 + dy ** 2) <= radius ** 2:
                nearby.append(unit)
        return nearby

    # SceneManager.py
    # scene_manager.py

    def update_collision_logic(self):
        from PhysicsUtils import is_box_overlap
        all_units = self.get_all_units()
        # 忽略單位: stand
        all_units = [u for u in all_units if u.type != "stand"]
        clashed_pairs = set()

        # 1. 拼招判定 (Hitbox vs Hitbox)
        for u1 in all_units:
            # 🟢 修正點：只有在攻擊生效幀 (should_trigger_hit) 才算
            if not (u1.attack_state and u1.attack_state.should_trigger_hit()):
                continue
            if u1.attack_state.has_clashed:  # 🟢 限制一招一次
                continue

            box1 = u1.get_hitbox()
            for u2 in all_units:
                # 排除：自己、同陣營、或對方也沒在生效幀
                if u1 == u2 or u1.side == u2.side or (u1, u2) in clashed_pairs:
                    continue
                if not (u2.attack_state and u2.attack_state.should_trigger_hit()):
                    continue
                if u1.type == "stand" or u2.type == "stand":
                    continue
                if u2.attack_state.has_clashed:  # 🟢 限制一招一次
                    continue

                box2 = u2.get_hitbox()
                if is_box_overlap(box1, box2):
                    self.resolve_clash(u1, u2)
                    # 🟢 標記雙方此招已失效，不再觸發拼招
                    u1.attack_state.has_clashed = True
                    u2.attack_state.has_clashed = True

                    clashed_pairs.add((u1, u2))
                    clashed_pairs.add((u2, u1))

        # 2. 傷害判定 (Hitbox vs Hurtbox)
        for attacker in all_units:
            # 🟢 修正點：如果是 character 但還在前搖，或者根本沒攻擊，直接跳過
            can_hit = False
            if getattr(attacker, 'unit_type', '') == 'character':
                if attacker.attack_state and attacker.attack_state.should_trigger_hit():
                    can_hit = True
            elif getattr(attacker, 'unit_type', '') == 'item':
                if attacker.flying:  # 物品飛起來就有傷害
                    can_hit = True

            if not can_hit: continue

            atk_box = attacker.get_hitbox()
            for victim in all_units:
                # 🟢 修正點：加入 side 檢查解決 Friendly Fire
                if attacker == victim or attacker.side == victim.side or (attacker, victim) in clashed_pairs:
                    continue

                if is_box_overlap(atk_box, victim.get_hurtbox()):
                    if getattr(victim, 'unit_type', None) == 'character':
                        # 確保不重複命中
                        if hasattr(attacker, 'attack_state') and attacker.attack_state:
                            if victim not in attacker.attack_state.has_hit:
                                victim.on_hit(attacker, attacker.attack_state.data)
                        elif hasattr(attacker, 'attacker_attack_data') and attacker.attacker_attack_data:
                            # 處理 Fireball/Bullet
                            victim.on_hit(attacker, attacker.attacker_attack_data)

                    elif getattr(victim, 'unit_type', None) == 'item':
                        if hasattr(victim, 'on_be_hit'):
                            victim.on_be_hit(attacker)

    def resolve_clash(self, u1, u2):
        """
            當兩個攻擊判定(Hitbox)互相接觸時觸發。
            """
        from PhysicsUtils import get_overlap_center
        from Config import CLASH_HITSTOP_FRAMES, CLASH_REBOUND_FORCE

        # 1. 視覺與體感回饋
        # 觸發短暫的 Hit Stop (例如 2 幀) 增加碰撞的厚實感
        self.trigger_hit_stop(CLASH_HITSTOP_FRAMES)

        # 在兩個 Hitbox 重疊的中心點產生 (火花) 特效
        cx, cy, cz = get_overlap_center(u1.get_hitbox(), u2.get_hitbox())
        self.create_effect(cx, cy, cz, 'clash')

        # 2. 物理反饋：根據相對位置推開雙方
        # 誰在左邊就往左彈，誰在右邊就往右彈，這對 Item 或 Character 都通用
        push_dir = 0.5 if u1.x > u2.x else -0.5

        # 3. 施加震退力 (Rebound)
        u1.vel_x = push_dir * CLASH_REBOUND_FORCE
        u2.vel_x = -push_dir * CLASH_REBOUND_FORCE

        # 4. 針對 Item 的特殊處理
        for unit in [u1, u2]:
            if getattr(unit, 'unit_type', None) == 'item':
                unit.vz = 0.4  # 物品被打到時稍微向上彈起
                if hasattr(unit, 'hitting'):
                    unit.hitting = []  # 重置命中清單，讓它彈開後能再次產生判定


class FloatingText:
    def __init__(self, x, y, value, map_h, duration=60, color=(255, 0, 0), font_size=24):
        self.x = x
        self.y = y
        self.value = str(value)
        self.duration = duration
        self.color = color
        self.offset_y = 0  # 漂浮動畫用
        self.map_h = map_h
        self.font_size = font_size

    def update(self):
        self.duration -= 1
        speed = 0.3 if self.font_size < 36 else 0.15
        self.offset_y += speed

    def is_alive(self):
        return self.duration > 0

    def draw(self, win, cam_x, cam_y, tile_offset_y, font_ignored):
        # 增加外框效果讓大數字更顯眼
        # ❌ 注意：這裡不再使用傳進來的 font_ignored，而是根據 self.font_size 建立
        # 建議實作中將字體緩存，避免每幀執行 pygame.font.SysFont
        current_font = pygame.font.SysFont("Arial Black", self.font_size)
        screen_x = int(self.x * TILE_SIZE) - cam_x
        screen_y = int((self.map_h - self.y) * TILE_SIZE - cam_y + tile_offset_y - self.offset_y)
        outline = current_font.render(self.value, True, (0, 0, 0))
        label = current_font.render(self.value, True, self.color)
        win.blit(outline, (screen_x + 2, screen_y + 2))  # 簡單陰影
        win.blit(label, (screen_x, screen_y))


class StoryScriptRunner:
    def __init__(self, scene):
        self.scene = scene
        self.script = []
        self.index = 0
        self.wait_timer = 0
        self.active = False
        self.reset_done = set()  # ✅ 記錄已重置過狀態的角色

    def load(self, script_data):
        self.script = script_data
        self.index = 0
        self.wait_timer = 0
        self.active = True
        self.reset_done.clear()
        self.scene.script_controlled_units.clear()


    def update(self):
        def add_unit_into_checking_list(unit):
            if unit not in self.reset_done:
                unit.clear_autonomous_behavior()
                self.reset_done.add(unit)
            self.scene.script_controlled_units.add(unit)

        if not self.active or self.wait_timer > 0:
            #print(f'script runner: {self.wait_timer}')
            self.wait_timer = max(0, self.wait_timer - 1)
            return

        if self.index >= len(self.script):
            self.active = False
            return

        cmd = self.script[self.index]
        self.index += 1  # 先遞增以便支援 wait 中斷式指令

        # 指令解讀
        if cmd['type'] == 'move':
            unit = self.find_unit(cmd['target'])
            if unit:
                # if unit not in self.reset_done:
                #     unit.clear_autonomous_behavior()
                #     self.reset_done.add(unit)
                # self.scene.script_controlled_units.add(unit)
                add_unit_into_checking_list(unit)
                unit.set_external_control({
                    'action': 'move',
                    'to': cmd['to'],
                    'duration': cmd.get('duration', 60)
                })

        elif cmd['type'] == 'attack':
            unit = self.find_unit(cmd['target'])
            if unit:
                #self.scene.script_controlled_units.add(unit)
                add_unit_into_checking_list(unit)

                unit.set_external_control({
                    'action': 'attack',
                    'skill': cmd['skill']
                })

        elif cmd['type'] == 'knockback':
            unit = self.find_unit(cmd['target'])
            if unit:
                #self.scene.script_controlled_units.add(unit)
                add_unit_into_checking_list(unit)

                unit.set_external_control({
                    'action': 'knockback',
                    'vx': cmd.get('vx', 0.3),
                    'vz': cmd.get('vz', 0.5)
                })

        elif cmd['type'] == 'wait':
            self.wait_timer = cmd['duration']

        elif cmd['type'] == 'say':
            unit = self.find_unit(cmd['target'])
            if unit:
                self.scene.say(unit, cmd['text'], duration=cmd.get('duration', 90))

    def find_unit(self, name):
        for u in self.scene.get_all_units():
            if getattr(u, 'name', None) == name:
                return u
        return None


import pygame

def get_cjk_font(size=20, prefer='jp'):
    font_path = {
        'jp': '..\\Assets_Drive\\fonts\\NotoSansJP-Regular.ttf',
        'tc': '..\\Assets_Drive\\fonts\\NotoSansTC-Regular.ttf'
    }
    return pygame.font.Font(font_path.get(prefer, 'jp'), size)

class SpeechBubble:
    def __init__(self, target, text, duration=90, direction='up', alpha=200):
        self.target = target  # 綁定角色或物件
        self.text = text
        self.duration = duration
        self.direction = direction
        self.offset = (0, 1.2) if direction == 'up' else (0, -0.5)
        self.alpha = alpha

    def update(self):
        self.duration -= 1

    def is_alive(self):
        return self.duration > 0

    # def draw(self, win, cam_x, cam_y, tile_offset_y, font):
    #     x = self.target.x + self.offset[0]
    #     y = self.target.y + self.offset[1]
    #     screen_x = int(x * TILE_SIZE) - cam_x
    #     screen_y = int((self.target.map_h - y) * TILE_SIZE - cam_y + tile_offset_y)
    #
    #     # 🗨️ 氣泡樣式
    #     padding = 6
    #     lines = self.wrap_text(font, self.text, max_width=160)
    #     bubble_w = max(font.size(line)[0] for line in lines) + padding * 2
    #     bubble_h = len(lines) * font.get_height() + padding * 2
    #
    #     # 🟩 框的位置（顯示在頭上）
    #     bubble_rect = pygame.Rect(screen_x - bubble_w // 2, screen_y - bubble_h - self.target.height*TILE_SIZE, bubble_w, bubble_h)
    #
    #     pygame.draw.rect(win, (255, 255, 255), bubble_rect)
    #     pygame.draw.rect(win, (0, 0, 0), bubble_rect, 2)
    #
    #     # 🔺 尾巴（向下）
    #     tail = [
    #         (bubble_rect.centerx, bubble_rect.bottom),
    #         (bubble_rect.centerx - 6, bubble_rect.bottom + 8),
    #         (bubble_rect.centerx + 6, bubble_rect.bottom + 8)
    #     ]
    #     pygame.draw.polygon(win, (255, 255, 255), tail)
    #     pygame.draw.polygon(win, (0, 0, 0), tail, 2)
    #
    #     # 📝 繪製文字
    #     for i, line in enumerate(lines):
    #         text_surf = font.render(line, True, (0, 0, 0))
    #         win.blit(text_surf, (bubble_rect.left + padding, bubble_rect.top + padding + i * font.get_height()))
    def draw(self, win, cam_x, cam_y, tile_offset_y, font):  # 新增 alpha 參數
        if self.duration < 20:
            alpha = int(self.alpha * (self.duration / 20))  # 最後 20 幀漸漸變透明
        else:
            alpha = self.alpha
        x = self.target.x + self.offset[0]
        y = self.target.y + self.offset[1]
        screen_x = int(x * TILE_SIZE) - cam_x
        screen_y = int((self.target.map_h - y) * TILE_SIZE - cam_y + tile_offset_y)

        padding = 6
        lines = self.wrap_text(font, self.text, max_width=160)
        bubble_w = max(font.size(line)[0] for line in lines) + padding * 2
        bubble_h = len(lines) * font.get_height() + padding * 2

        # 建立一個足以容納氣泡（含尾巴）的臨時 Surface
        # 寬度加上外框，高度預留 10 像素給尾巴
        temp_surf = pygame.Surface((bubble_w + 4, bubble_h + 10), pygame.SRCALPHA)
        temp_surf.fill((0, 0, 0, 0))  # 填充全透明背景

        # 在 temp_surf 上繪製，座標改為從 (0,0) 開始計算的相對座標
        bubble_rect = pygame.Rect(2, 0, bubble_w, bubble_h)

        # 繪製矩形框（傳入包含 Alpha 的 RGBA 顏色）
        pygame.draw.rect(temp_surf, (255, 255, 255, alpha), bubble_rect)
        pygame.draw.rect(temp_surf, (0, 0, 0, alpha), bubble_rect, 2)

        # 🔺 尾巴（座標相對於 temp_surf）
        tail = [
            (bubble_rect.centerx, bubble_rect.bottom),
            (bubble_rect.centerx - 6, bubble_rect.bottom + 8),
            (bubble_rect.centerx + 6, bubble_rect.bottom + 8)
        ]
        pygame.draw.polygon(temp_surf, (255, 255, 255, alpha), tail)
        pygame.draw.polygon(temp_surf, (0, 0, 0, alpha), tail, 2)

        # 📝 繪製文字
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, (0, 0, 0))
            text_surf.set_alpha(alpha)  # 設定文字透明度
            temp_surf.blit(text_surf, (bubble_rect.left + padding, bubble_rect.top + padding + i * font.get_height()))

        # 最後把做好的 temp_surf 貼到 win
        final_x = screen_x - bubble_w // 2
        final_y = screen_y - bubble_h - int(self.target.height * TILE_SIZE)
        win.blit(temp_surf, (final_x, final_y))

    def wrap_text(self, font, text, max_width):
        words = text.split(' ')
        lines = []
        current = ''
        for word in words:
            test = f'{current} {word}' if current else word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
