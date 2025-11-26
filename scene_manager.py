# scene_manager.py
import pygame
from Config import WIDTH, HEIGHT, TILE_SIZE

class SceneManager:
    def __init__(self):
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
        self.darken_enabled = False
        self.darken_alpha = 0
        self.darken_alpha_max = 160
        self.darken_speed = 1

        self.cleared = False
        self.clear_text = ""
        self.clear_font = None  # 由外部設定（main 或 scene_1）
        self.scene_end_countdown = -1

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
        self.darken_enabled = False  # 停止繼續加深
        self.cleared = True
        self.clear_text = message
        self.scene_end_countdown = countdown

    # --- 在每幀繪圖最後呼叫 ---
    def draw_overlay(self, win):
        # 畫面變暗
        if self.darken_enabled and self.scene_end_countdown > 0:
            if self.darken_alpha < self.darken_alpha_max:
                self.darken_alpha = min(
                    self.darken_alpha_max,
                    self.darken_alpha + self.darken_speed
                )
            dark_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark_surface.fill((0, 0, 0, self.darken_alpha))
            win.blit(dark_surface, (0, 0))

        # 通關文字
        if self.cleared and self.clear_font and self.clear_text:
            txt = self.clear_font.render(self.clear_text, True, (255, 255, 0))
            outline = self.clear_font.render(self.clear_text, True, (0, 0, 0))
            x = (WIDTH - txt.get_width()) // 2
            y = (HEIGHT - txt.get_height()) // 2

            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                win.blit(outline, (x + dx, y + dy))
            win.blit(txt, (x, y))

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
        self.script_runner.update()

        for unit in self.interactables:
            #如果劇情模式開啟，且這個單位不在受控名單中 → 跳過更新
            if self.script_runner.active and self.lock_others_during_script:
                if unit not in self.script_controlled_units:
                    continue
            unit.update_components()
            unit.update()
        for text in self.floating_texts:
            text.update()
        self.floating_texts = [t for t in self.floating_texts if t.is_alive()]  # 自動清除結束的
        # 🔸移除所有標記為移除的物件
        for unit in self.to_be_removed:
            self.unregister_unit(unit)
            print(f'scene_manager: 註銷{unit.name}')
        self.to_be_removed.clear()
        # 對話泡泡
        for bubble in self.speech_bubbles:
            bubble.update()
        self.speech_bubbles = [b for b in self.speech_bubbles if b.is_alive()]
        if self.scene_end_countdown > 0:
            self.scene_end_countdown = self.scene_end_countdown -1
        if self.scene_end_countdown == 0:
            print('SceneManager: scene end')

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

    def draw_all(self,win, cam_x, cam_y, tile_offset_y):
        all_drawables = []

        # 包裝所有可繪製物件，加上 type 標記方便後續判斷
        for unit in self.interactables:
            all_drawables.append(("unit", unit))
            #print(f'{unit.name}sY={unit.y}')
        for proj in self.projectiles:
            all_drawables.append(("projectile", proj))

        all_drawables.sort(key=lambda item: getattr(item[1], 'y', 0), reverse=True)
        for item_type, obj in all_drawables:
            if item_type == "text":
                obj.draw(win, cam_x, cam_y, tile_offset_y, font)
            else:
                obj.draw(win, cam_x, cam_y, tile_offset_y)
        for text in self.floating_texts:
            text.draw(win, cam_x, cam_y, tile_offset_y, pygame.font.SysFont(None, 36))  # 顯示傷害文字

        # ✅ 繪製 SpeechBubble
        #font = pygame.font.SysFont(None, 18)
        font = get_cjk_font(20, prefer='tc')  # or 'tc'
        for bubble in self.speech_bubbles:
            bubble.draw(win, cam_x, cam_y, tile_offset_y, font)

        self.draw_overlay(win)

    def add_floating_text(self, x, y, value, map_h, color):
        self.floating_texts.append(FloatingText(x, y, value, map_h, duration=60, color=color))

class FloatingText:
    def __init__(self, x, y, value, map_h, duration=60, color=(255, 0, 0)):
        self.x = x
        self.y = y
        self.value = str(value)
        self.duration = duration
        self.color = color
        self.offset_y = 0  # 漂浮動畫用
        self.map_h = map_h

    def update(self):
        self.duration -= 1
        self.offset_y += 0.3  # 向上漂浮

    def is_alive(self):
        return self.duration > 0

    def draw(self, win, cam_x, cam_y, tile_offset_y, font):
        screen_x = int(self.x * TILE_SIZE) - cam_x
        screen_y = int((self.map_h - self.y) * TILE_SIZE - cam_y + tile_offset_y - self.offset_y)
        label = font.render(self.value, True, self.color)
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
        'jp': 'fonts/NotoSansJP-Regular.ttf',
        'tc': 'fonts/NotoSansTC-Regular.ttf'
    }
    return pygame.font.Font(font_path.get(prefer, 'jp'), size)

class SpeechBubble:
    def __init__(self, target, text, duration=90, direction='up'):
        self.target = target  # 綁定角色或物件
        self.text = text
        self.duration = duration
        self.direction = direction
        self.offset = (0, 1.2) if direction == 'up' else (0, -0.5)

    def update(self):
        self.duration -= 1

    def is_alive(self):
        return self.duration > 0

    def draw(self, win, cam_x, cam_y, tile_offset_y, font):
        x = self.target.x + self.offset[0]
        y = self.target.y + self.offset[1]
        screen_x = int(x * TILE_SIZE) - cam_x
        screen_y = int((self.target.map_h - y) * TILE_SIZE - cam_y + tile_offset_y)

        # 🗨️ 氣泡樣式
        padding = 6
        lines = self.wrap_text(font, self.text, max_width=160)
        bubble_w = max(font.size(line)[0] for line in lines) + padding * 2
        bubble_h = len(lines) * font.get_height() + padding * 2

        # 🟩 框的位置（顯示在頭上）
        bubble_rect = pygame.Rect(screen_x - bubble_w // 2, screen_y - bubble_h - self.target.height*TILE_SIZE, bubble_w, bubble_h)

        pygame.draw.rect(win, (255, 255, 255), bubble_rect)
        pygame.draw.rect(win, (0, 0, 0), bubble_rect, 2)

        # 🔺 尾巴（向下）
        tail = [
            (bubble_rect.centerx, bubble_rect.bottom),
            (bubble_rect.centerx - 6, bubble_rect.bottom + 8),
            (bubble_rect.centerx + 6, bubble_rect.bottom + 8)
        ]
        pygame.draw.polygon(win, (255, 255, 255), tail)
        pygame.draw.polygon(win, (0, 0, 0), tail, 2)

        # 📝 繪製文字
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, (0, 0, 0))
            win.blit(text_surf, (bubble_rect.left + padding, bubble_rect.top + padding + i * font.get_height()))

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
