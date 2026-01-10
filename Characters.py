import pygame
from Config import *
#from enum import Enum, auto
from State_enum import *
from Skill import *
from Component import ComponentHost, HoldFlyLogicMixin
from CharactersConfig import *

DEBUG = False

def suspend(info=''):
    print(f"🟡 暫停中，{info}...")
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                waiting = False

        # 避免 CPU 吃滿（加一點等待）
        pygame.time.delay(100)

def is_box_overlap(box1, box2):
    return (
        box1['x1'] <= box2['x2'] and box1['x2'] >= box2['x1'] and
        box1['y1'] <= box2['y2'] and box1['y2'] >= box2['y1'] and
        box1['z1'] <= box2['z2'] and box1['z2'] >= box2['z1']
    )

def get_overlap_center(box1, box2):
    """
    計算兩個碰撞盒交疊區域的中心點 (x, y, z)。
    若無交疊，則回傳各軸的中點平均值（或可視需求回傳 None）。
    """
    # 計算 X 軸交疊區間
    overlap_x1 = max(box1['x1'], box2['x1'])
    overlap_x2 = min(box1['x2'], box2['x2'])
    center_x = (overlap_x1 + overlap_x2) / 2

    # 計算 Y 軸交疊區間
    overlap_y1 = max(box1['y1'], box2['y1'])
    overlap_y2 = min(box1['y2'], box2['y2'])
    center_y = (overlap_y1 + overlap_y2) / 2

    # 計算 Z 軸交疊區間
    overlap_z1 = max(box1['z1'], box2['z1'])
    overlap_z2 = min(box1['z2'], box2['z2'])
    center_z = (overlap_z1 + overlap_z2) / 2

    return center_x, center_y, center_z


KEY_TO_ACTION = {
    pygame.K_z: "z_attack",
    pygame.K_x: "x_attack",
    pygame.K_c: "c_attack"
}

def check_state(self):
    m_state, a_state = None, None
    if self.state:
        m_state=self.state.name
    if self.attack_state:
        a_state = self.attack_state.name
    suspend(f'{self.name}, MoveState={m_state} AttackState={a_state}')

#貼圖管理類別
class SpriteAnimator:
    #def __init__(self, image_path, frame_width=96, frame_height=96, anim_map = basic_anim_map1):
    def __init__(self, image_path, config_dict):
        self.sheet = pygame.image.load(image_path).convert_alpha()
        self.frame_width = config_dict.get("frame_width")
        self.frame_height = config_dict.get("frame_height")
        self.frames = self.slice_sheet()
        # 定義每種狀態的 frame index list
        self.anim_map = config_dict.get("anim_map")

    def slice_sheet(self):
        sheet_w, sheet_h = self.sheet.get_size()
        cols = sheet_w // self.frame_width
        rows = sheet_h // self.frame_height
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * self.frame_width
                y = row * self.frame_height
                frame = self.sheet.subsurface((x, y, self.frame_width, self.frame_height))
                frames.append(frame)
        return frames

    def get_frame(self, state_name, frame_index, flip_x = False, flip_y = False):
        anim = self.anim_map.get(state_name)
        if anim:
            frame = self.frames[anim[frame_index % len(anim)]]
        else:
            frame = self.frames[0]  # fallback to stand
        # 2. 進行翻轉處理
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        return frame

    def get_frame_by_index(self, frame_global_index, flip_x = False, flip_y = False):
        if 0 <= frame_global_index < len(self.frames):
            frame = self.frames[frame_global_index]
        else:
            frame = self.frames[0]
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        return frame
    def get_frame_by_map_index(self, state_name, frame_map_index=0 , flip_x = False, flip_y = False):
        anim = self.anim_map.get(state_name)
        if anim:
            frame =self.frames[anim[frame_map_index]]
        else:
            frame = self.frames[0]  # fallback to stand
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        return frame

def get_component_class(name):
    """根據字串名稱動態獲取 Component 類別"""
    # ⚠️ 這裡假設您的 Component 類別都在 Component.py 中
    from Component import AuraEffectComponent  # 必須在這裡明確導入 Component 類

    # 簡化範例：直接映射字串到類別（實際專案可使用 getattr(sys.modules[__name__], name) 獲取）
    class_map = {
        "AuraEffectComponent": AuraEffectComponent,
        # ... 未來可擴充
    }
    return class_map.get(name)
class CharacterBase(ComponentHost, HoldFlyLogicMixin):
    #def __init__(self, x, y, map_info, z=0, popup=None):
    def __init__(self, x, y, map_info, z=0):
        super().__init__()
        self.unit_type = "character"
        self.x = max(0, min(x, map_info[1]-1))
        self.y = max(0, min(y, map_info[2]-1))
        self.jump_z = 0
        self.width = 1.5
        self.height = 2.5

        self.terrain = map_info[0]
        self.map_w = map_info[1]
        self.map_h = map_info[2]
        self.z = self.get_tile_z(x, y)

        self.color = (0,0,0)
        # 受創系統
        self.combat_state = CombatState.NORMAL
        self.combat_timer = 0
        self.hit_count = 0.0
        self.max_hits_before_weak = 3.0
        self.recovery_rate = 0.01
        self.max_hp=100
        self.health = self.max_hp
        self.health_visual = self.max_hp    #UI視覺使用
        self.z = z  # 如有需要強制指定 z 值
        self.summon_sickness=0
        self.hit = False
        self.hit_timer = 0  #受創"持續時間"的timer
        self.on_hit_count = 0 #作為動畫切換用
        self.jump_z_vel = 0
        self.rigid_timer = 0
        self.invincible_timer = 0   #無敵timer
        self.super_armor_timer = 0  #鋼鐵timer
        self.falling_timer = 0
        self.dead_timer = 0 #死亡消失時間
        #擊飛時變數
        self.knockback_vel_x = 0
        self.knockback_vel_z = 0

        
        self.state = MoveState.STAND
        self.last_intent = {'direction': None, 'horizontal': None}
        self.current_frame = 0
        self.facing = DirState.RIGHT
        self.combat_timer_max = 1  # 預設非 0，避免除以 0，會隨狀態切換更新
        #攻擊狀態
        self.attack_state = None

        #基本招式表
        self.attack_table = {'z_attack':{'default': AttackType.PUNCH},
                             'x_attack':{'default': AttackType.KICK},
                             'c_attack':{},
                             'swing_item':{'default': AttackType.SWING},
                             'throw_item':{'default': AttackType.THROW}}

        self.name = 'Base'
        self.attack_intent = None

        self.scene = None

        self.weight = 0.05 # 作為投擲用物件
        self.flying = False
        self.held_by = None
        self.throw_damage = 15   #投擲物件傷害
        self.swing_damage = 10
        self.throw_power = 0.5  #投擲基本力量
        

        self.jump_key_block = False #避免長按連續跳躍
        self.jump_intent_trigger = False
        self.jumpping_flag = False #避免重覆計算跳躍

        #增加動畫支援
        self.animator = None
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 8  # 幀更新頻率
        self.anim_walk_cnt = 0

        self.falling_y_offset = 0   #掉落時調整動畫位置

        self.on_hit_timer = 0
        self.has_stand = False
        self.stand_image = None

        self.side = 'netural'   #為了製造飛行道具
        self.money = 10
        self.mp = 0
        self.drop_mana_rate = 0.5
        self.get_burning = False
        self.burn_frames = []
        self.high_jump = False
        self.popup = None
        self.super_move_config = None


        # 燃燒貼圖初始化
        sheet = pygame.image.load("..\\Assets_Drive\\burn_4frame.png").convert_alpha()
        frame_w = sheet.get_width() // 4
        frame_h = sheet.get_height()
        for i in range(4):
            frame = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
            self.burn_frames.append(frame)
        self.super_move_anim_timer = 0
        self.current_anim_frame = None
        self.currnet_anim_draw_x = None
        self.current_anim_draw_y = None
        self.frame_map_cache = {}
        self.afterimage_list = []  # 儲存快照的 list
        self.afterimage_enabled = False  # 是否開啟殘影
        self.afterimage_timer = 0
        self.cached_pivot = (self.x, self.y)

    def update_afterimages(self):
        # 只有在特定狀態或開啟標記時才記錄
        if self.afterimage_enabled or (
                self.attack_state and AttackEffect.AFTER_IMAGE in self.attack_state.data.effects):
            # 每 2 幀記錄一個快照，避免殘影太密變成一坨
            if self.current_frame % 2 == 0:
                snapshot = {
                    'image': self.current_anim_frame.copy(),  # 必須 copy，否則會隨本體改變
                    'pos': (self.currnet_anim_draw_x, self.current_anim_draw_y),
                    'alpha': 150  # 初始透明度
                }
                self.afterimage_list.append(snapshot)

        # 更新已存在的殘影（減少透明度並移除消失的）
        for img in self.afterimage_list[:]:
            img['alpha'] -= 15  # 每一幀淡出多少
            if img['alpha'] <= 0:
                self.afterimage_list.remove(img)

        # 限制最大殘影數量，避免效能問題
        if len(self.afterimage_list) > 10:
            self.afterimage_list.pop(0)
    def update_burning_flag(self):
        if self.get_burning and not self.is_jump():
            self.get_burning = False

    def clear_autonomous_behavior(self):
        self.flying = False
        self.held_by = None
        self.attack_intent = None
        self.knockback_vel_x = 0
        self.knockback_vel_z = 0
        self.attack_intent = None
        self.hit = False
    
    # def update_anim(self):
    #     self.anim_timer += 1
    #     if self.anim_timer >= self.anim_speed:
    #         self.anim_timer = 0
    #         self.anim_frame += 1
    def generate_frame_index_from_ratio_map(self, frame_map_ratio, anim_map):
        # 2. 根據frame_map_ratio = [8,16,8]與 anim_map的"punch": [[4], [5], [6]] 生成對應frame index
        #   例如: 上述生成結果應該是[4,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,4,4,4,4,4,4,4,4]
        #   換個例子: "punch": [[9], [10, 11], [12, 11]]
        #   則預期生成結果應該是[9,9,9,9,9,9,9,9,
        #   10,10,10,10,10,10,10,10,11,11,11,11,11,11,11,11,
        #   12,12,12,12,11,11,11,11]

        if len(frame_map_ratio) != len(anim_map):
            return None
        result = []
        for one_stage_frame_count, one_stage_map in zip(frame_map_ratio, anim_map):
            step = int(one_stage_frame_count/len(one_stage_map))
            sub_map = []
            for f in one_stage_map:
                sub_map = sub_map + [f]*step
            while len(sub_map) < one_stage_frame_count:
                sub_map.append(one_stage_map[-1])
            result = result + sub_map
        #print(f'{frame_map_ratio}\n{anim_map}\n{result}')
        return result



    def draw(self, win, cam_x, cam_y, tile_offset_y):
        if self.animator:
            cal_func = self.draw_anim
        else:
            cal_func = self.draw_block
        return cal_func(win, cam_x, cam_y, tile_offset_y)

    def draw_debug_info(self, win, px, py):
        # 🧠 顯示於角色上方文字
        font = pygame.font.SysFont("consolas", 14)
        st = ''
        if self.is_falling():
            st = st + 'Fal '
        if self.is_jump():
            st = st + 'Jmp '
        if self.high_jump:
            st = st + 'Hjp'
        if self.is_knockbacking():
            st = st + 'Kbk '
        if self.is_invincible():
            st = st + 'Inv '
        if self.is_locked():
            st = st + 'Lck '
        if self.is_on_hit():
            st = st + 'Hit '

        debug_lines = [
            f"M:{self.state.name} C:{self.combat_state.name}",
            f"Z:{self.z:.1f} Jz:{self.jump_z:.1f}",
            f"Flag:{st} Rt({self.rigid_timer}) Ct({self.combat_timer})"
        ]

        for i, line in enumerate(debug_lines):
            text_surf = font.render(line, True, (255, 255, 0))
            win.blit(text_surf, (px, py - 28 - i * 16))  # 每行往上推一點

    def draw_anim(self, win, cam_x, cam_y, tile_offset_y):

        # 更新動畫 frame（每隔 anim_speed frame 換一次圖）
        self.anim_timer += 1
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.anim_frame += 1

        # 狀態轉換為動畫名
        # print(f'[draw_anim] {self.name} combat_state = {self.combat_state.name} move_state = {self.state.name}', end='\r')
        combat_state_anim_map = {
            CombatState.DEAD: "dead",CombatState.DOWN:"down",CombatState.WEAK:"weak",CombatState.KNOCKBACK:"knockback"
        }
        attack_state_anim_map = {
            AttackType.BASH:"bash",AttackType.SLASH:"slash",AttackType.KICK:"kick",AttackType.FLY_KICK:"flykick",
            AttackType.METEOFALL:"meteofall",AttackType.SWING:"swing",AttackType.THROW:"throw",AttackType.PUNCH:"punch",
            AttackType.MAHAHPUNCH:"mahahpunch", AttackType.SPECIAL_PUNCH:"special_punch", AttackType.SPECIAL_KICK:"special_kick",
            AttackType.BRUST:"brust"
        }
        move_state_anim_map = {MoveState.JUMP:"jump", MoveState.FALL:"fall",MoveState.WALK:"walk",MoveState.RUN:"run"}
        common_anim_material = ['burn']
        #決定anim_frame
        anim_name = 'stand'
        if self.get_burning:
            anim_name = "burn"
        elif self.is_knockbacking():
            anim_name = "knockback"
        elif self.combat_state in combat_state_anim_map:     #判斷戰鬥狀態動畫
            anim_name = combat_state_anim_map[self.combat_state]
        elif self.is_on_hit():
            anim_name = "on_hit"
        elif self.attack_state:
            if hasattr(self.attack_state.data, 'attack_type'):
                if self.attack_state.data.attack_type in attack_state_anim_map:
                    anim_name = attack_state_anim_map[self.attack_state.data.attack_type]
        elif self.state in move_state_anim_map:
            anim_name = move_state_anim_map[self.state]
        else:
            anim_name = "stand"
        # 進行例外處理
        if anim_name == "knockback" and not self.animator.anim_map.get("knockback"):
            anim_name = "on_fly"

        frame_index = 0
        st = ''
        if self.state:
            st = st + f'Mov={self.state.name} '
        if self.attack_state:
            st = st + f'Atk={self.attack_state.name} '
        if self.combat_state:
            st = st + f'Cbt={self.combat_state.name}'
        #print(f'[{self.current_frame}] {st} anim_name {anim_name}')
        #common material anime
        if anim_name in common_anim_material:
            if anim_name == 'burn':
                # 👇 繪製燃燒效果（如果標記為 get_burning）
                burn_idx = (self.current_frame % 16) // 4  # 0~3，每幀持續4 frame
                resize_burn_frames = []
                #
                for f in self.burn_frames:
                    sw = f.get_width()
                    sh = f.get_height()
                    resize_burn_frames.append(pygame.transform.scale(f, (sw * self.width/1.5, sh * self.height/2.5)))
                frame = resize_burn_frames[burn_idx]
        elif len(self.animator.anim_map.get(anim_name)) == 1:
            frames = self.animator.anim_map.get(anim_name)[0]
            #只有一個stage的動畫
            if len(frames) == 1:
                #只有一張圖的動畫
                frame_index = frames[0]
            else:
                #只有一個stage但有多張圖的動畫, 根據某些條件來選擇
                # walk, jump, on_hit
                if anim_name in ['walk','run']:
                    self.anim_walk_cnt += 1
                    frame_period = 8 if anim_name == 'walk' else 4
                    walk_index = int(self.anim_walk_cnt / frame_period) % len(self.animator.anim_map.get('walk')[0])
                    frame_index = frames[walk_index]
                    #print(f'{self.anim_walk_cnt}: {walk_index}')
                elif anim_name == 'jump':
                    if self.jump_z < 0.1:
                        frame_index = frames[0]
                    else:
                        frame_index = frames[1]
                elif anim_name == 'on_hit':
                    if self.on_hit_count %2 == 0:
                        frame_index = frames[1]
                    else:
                        frame_index = frames[0]
        else:
            #多stage frame, 戰鬥動畫要從AttackData的frame_map_ratio與self.anim_map做出對應表
            #戰鬥動畫包括: punch, kick, bash, special_punch, palm, special_kick, slash, mahahpunch, ranbu, swing, throw
            if anim_name in ['punch', 'kick', 'bash', 'special_punch', 'palm','brust',
                             'special_kick', 'slash', 'mahahpunch', 'ranbu', 'swing', 'throw']:
                index_map = self.frame_map_cache.get(anim_name)
                if not index_map:
                    index_map = self.generate_frame_index_from_ratio_map(self.attack_state.data.frame_map_ratio, self.animator.anim_map.get(anim_name))
                    print(f'cache {anim_name}')
                    self.frame_map_cache[anim_name] = index_map.copy()
                use_index = self.attack_state.frame_index if self.attack_state.frame_index < len(index_map) else -1
                frame_index = index_map[use_index]
            elif anim_name in ['knockback']:
                kb_frames = self.animator.anim_map.get('knockback')
                near_ground_bound = 3.0
                if self.jump_z >= near_ground_bound:
                    # 使用frames[1]
                    frames = kb_frames[0]
                    rotation_frame_num = 4*len(frames)
                    # 如果有3張動畫, 每張播放4個frame
                    choose_frame_param = self.current_frame % rotation_frame_num
                    frame_index = frames[int(choose_frame_param/4)]
                else:
                    #靠近地面, 使用kb_frames[1]
                    #越接近地面, 使用後面的張數
                    frames = kb_frames[1]
                    step = near_ground_bound/len(frames)
                    dist_from_start = near_ground_bound-self.jump_z
                    choose_index = min(int(dist_from_start/step), len(frames)-1)
                    frame_index = frames[choose_index]

        # 若角色面向左側，進行左右翻轉
        vertical_flip = False
        if self.facing == DirState.LEFT:
            vertical_flip = True
        if anim_name not in common_anim_material:
            frame = self.animator.get_frame_by_index(frame_index, flip_x = vertical_flip)
            # knockback

        # 新規則<--

        if self.popup and 'landing' in self.popup:
            if self.jump_z > 0 and self.current_frame < self.summon_sickness:
                #調整為跳躍動作
                frames = self.animator.anim_map.get('fall')[0]
                frame = self.animator.get_frame_by_index(frames[0])
            if self.jump_z <= 0 and self.current_frame < self.summon_sickness:
                self.check_ground_contact()
                frames = self.animator.anim_map.get('pose_1')[0]
                frame = self.animator.get_frame_by_index(frames[0])
                if 'shake' in self.popup:
                    self.scene.trigger_shake(20,15)
                    print(f'{self.name}, x y z = {self.x, self.y, self.z}, jump_z = {self.jump_z}')
                self.popup = None
                self.summon_sickness = 0
        elif self.popup is None and self.current_frame < self.summon_sickness:
            # 使用 max(0, 255 - countdown) 的簡潔寫法處理 Alpha
            alpha = min(255, int((self.current_frame / self.summon_sickness) * 255))
            frame.set_alpha(alpha)

        self.current_anim_frame = frame

        # 計算畫面座標
        px = int(self.x * TILE_SIZE) - cam_x
        # py = int((self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        falling_z_offset = 0
        if self.is_falling():
            falling_z_offset = self.falling_y_offset * Z_FALL_OFSSET
        py = int((self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset + falling_z_offset) - cam_y + tile_offset_y
        # print(f'terrain_z_offset={terrain_z_offset:.2f} falling_z_offset={falling_z_offset:.2f} py={py}')

        # 劇情提示（血條與命中特效等）
        self.draw_combat_bar(win, px, py)
        self.draw_hp_bar(win, px, py)

#for swing---
        # 1. 檢測自己是否正在被「揮舞」
        swing_offset_x,swing_offset_y = 0,0
        if self.held_by and self.held_by.attack_state and self.held_by.attack_state.name == 'swing':
            #is_being_swung = True
            print(f'{self.name} 被揮舞!')
            dir = 1
            if self.held_by.facing == DirState.LEFT:
                dir = -1
            swing_offset_x = dir*int(self.held_by.width * TILE_SIZE * 0.6)
            swing_offset_y = self.held_by.height*TILE_SIZE*0.5
#--------


        if DEBUG:
            self.draw_debug_info(win, px, py)
            # DEBUG: 角色腳下的圓形定位點（用於碰撞、踩地感）
        cx = int((self.x + self.width / 2) * TILE_SIZE) - cam_x
#for swing --- 關鍵修正：若正在被揮舞，則不再加上額外的 held_by 偏移，因為 self.x 已在 Skill.py 被更新 ---

        base_cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset + falling_z_offset) - cam_y + tile_offset_y

        # cache住繪圖位置
        self.cached_pivot = (cx, cy)
        pygame.draw.circle(win, (0, 0, 0), (cx, base_cy), 3)
        # DEBUG: 繪製 hitbox
        if DEBUG:
            self.draw_hit_box(win, cam_x, cam_y, tile_offset_y, (255, 0, 0), terrain_z_offset)
        self.draw_hit_box(win, cam_x, cam_y, tile_offset_y, (255, 0, 0), terrain_z_offset)
        # win.blit(frame, (px, py))
        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height

        if self.scene and self.scene.hit_stop_timer > 0:
            import random
            draw_x += random.randint(-2, 2)
            draw_y += random.randint(-2, 2)

        self.update_afterimages()
        # 2. 繪製殘影
        for img in self.afterimage_list:
            # 創建一個帶有 Alpha 值的副本或直接設定 Alpha
            temp_surf = img['image'].copy()
            temp_surf.set_alpha(img['alpha'])
            win.blit(temp_surf, img['pos'])

        if self.has_stand and self.stand_image:
            stand_x = draw_x - 35 if self.facing == DirState.RIGHT else draw_x + 35
            stand_y = draw_y - 20
            stand_img = self.stand_image.copy()  # 複製一份來修改 alpha
            # 設定透明度（0~255），例如 128 為半透明
            stand_img.set_alpha(160)
            # 如果角色向左，替身也要翻轉
            if self.facing == DirState.LEFT:
                stand_img = pygame.transform.flip(stand_img, True, False)
            win.blit(stand_img, (stand_x, stand_y))
        # 根據死亡狀態處理特效：閃爍 + 半透明
        if self.combat_state == CombatState.DEAD:
            if (self.dead_timer // 30) % 2 == 0:  # 每 30 frame 閃一次 (0.5 秒)
                dead_frame = frame.copy()
                dead_frame.set_alpha(128)  # 半透明
                win.blit(dead_frame, (draw_x, draw_y))
        else:
            win.blit(frame, (draw_x+swing_offset_x, draw_y+swing_offset_y))

        self.current_anim_frame = frame
        self.currnet_anim_draw_x = draw_x+swing_offset_x
        self.current_anim_draw_y = draw_y+swing_offset_y
        #win.blit(frame, (draw_x, draw_y))

        aura_comp = self.get_component("aura_effect")
        if aura_comp:
            # 傳入所有繪圖所需參數
            #print(f'{aura_comp} enable')
            aura_comp.draw(win, cam_x, cam_y, tile_offset_y)
        # print(f'{self.name} draw debug {self.current_frame}')
        if DEBUG:
            self.draw_hurtbox(win, cam_x, cam_y, tile_offset_y, terrain_z_offset)
        self.draw_hurtbox(win, cam_x, cam_y, tile_offset_y, terrain_z_offset)
    def draw_silhouette(self, win):
        # 取得玩家當前應該顯示的那一幀 (從 animator 拿)
        # 假設我們已經在原本的 draw 流程算好了 frame
        if not self.animator: return
        if not self.current_anim_frame: return
        temp_frame = self.current_anim_frame.copy()
        temp_frame.set_alpha(120)
        win.blit(temp_frame, (self.currnet_anim_draw_x, self.current_anim_draw_y))
    def draw_block(self, win, cam_x, cam_y, tile_offset_y):
        px = int(self.x * TILE_SIZE) - cam_x
        # py = int((self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        py = int((
                             self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset) - cam_y + tile_offset_y

        # 狀態導向繪製

        if self.combat_state == CombatState.DOWN:
            self.draw_down(win, px, py)
        elif self.combat_state == CombatState.DEAD:
            self.draw_dead(win, px, py)
        elif self.combat_state == CombatState.KNOCKBACK:
            self.draw_knockback(win, px, py)
        elif self.combat_state == CombatState.WEAK:
            self.draw_weak(win, px, py)
        elif self.hit and (self.hit_timer // 4) % 2 == 0:
            # 閃爍效果：每 4 frame 出現一次
            self.draw_stand(win, px, py)
            self.draw_hit(win, px, py)
        else:
            self.draw_stand(win, px, py)

        cx = int((self.x + self.width / 2) * TILE_SIZE) - cam_x
        cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        pygame.draw.circle(win, (0, 0, 0), (cx, cy), 3)

        self.draw_hit_box(win, cam_x, cam_y, tile_offset_y, (255, 0, 0))

        step_info = '-'
        step_dir = self.last_intent.get("direction") or self.step_direction
        if step_dir in [DirState.LEFT, DirState.RIGHT]:
            if self.recently_stepped(step_dir, self.current_frame):
                step_info = f"{step_dir.name}"
        self.draw_combat_bar(win, px, py)
        self.draw_hp_bar(win, px, py)
    def draw_hurtbox(self, win, cam_x, cam_y, tile_offset_y, terrain_z_offset=0):
        # === 顯示 hurtbox ===
        hurtbox = self.get_hurtbox()
        hx1 = int(hurtbox['x1'] * TILE_SIZE) - cam_x
        hy1 = int((self.map_h - hurtbox['y2']) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset) - cam_y + tile_offset_y
        hx2 = int(hurtbox['x2'] * TILE_SIZE) - cam_x
        hy2 = int((self.map_h - hurtbox['y1']) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset) - cam_y + tile_offset_y

        pygame.draw.rect(win, (0, 0, 255), (hx1, hy1, hx2 - hx1, hy2 - hy1), 2)

    def scene_items(self):
        if hasattr(self, 'scene'):
            return self.scene.get_all_interactables()
        return []

    def resolve_attack_table(self):
        attack = None
        if self.attack_intent:
            #z x c attack種類
            #atk_table = self.attack_table[self.attack_intent]
            #1.3d 改為可能接受component修改意圖
            
            real_intent = self.override_attack_intent(self.attack_intent)
            print(f'意圖:{self.attack_intent} -> {real_intent}')
            if real_intent == 'pickup_item' and not self.is_jump():
                self.get_component("holdable").try_pickup()
                return real_intent
            atk_table = self.attack_table.get(real_intent, {})            
            attack = atk_table.get('default', None)
            #if self.z > 0 and 'jump' in atk_table:
            if self.jump_z > 0:
                attack = atk_table.get('jump', None)
                # [新增判斷] 如果是高跳 + 按著 Down 鍵，則使用 highjump 招式
                # 檢查 self.last_intent['down_pressed'] 是否為 True (即按下 Down 鍵)
                is_down_pressed = self.last_intent.get('down_pressed', False)
                if self.high_jump and is_down_pressed:
                    attack=atk_table.get('highjump_fall', None)
            elif self.state==MoveState.RUN and 'run' in atk_table:
                attack = atk_table.get('run', None)
        if attack in [AttackType.PUNCH, AttackType.KICK]:
            enemy_side = 'enemy_side' if self.side == 'player_side' else 'player_side'
            # 定義偵測中心（通常在角色前方一點）
            check_dist = 1.5 if self.facing == DirState.RIGHT else -1.5
            nearby_enemies = self.scene.get_nearby_units_by_side(
                self.x + check_dist, self.y, radius=2.0, side=enemy_side
            )
            # 檢查是否有任何敵人處於 WEAK 狀態
            has_weak_target = any(e.combat_state == CombatState.WEAK for e in nearby_enemies)
            if has_weak_target:
                print(f"[REACTION] 偵測到 Weak 敵人，{self.name} 的 PUNCH 轉變為 SPECIAL_PUNCH！")
                attack = AttackType.SPECIAL_PUNCH if attack == AttackType.PUNCH else AttackType.SPECIAL_KICK

        #處理技能的動量變化
        if attack is not None:
            atk_data = attack_data_dict[attack]
            if atk_data.physical_change is not None:
                for attr_name, value in atk_data.physical_change.items():
                    print(f"[PHYSICS] 角色 {self.name} 套用 {attr_name} = {value}")
                    ori_val = getattr(self, attr_name)
                    new_val = ori_val + value
                    #print(f'before value {ori_val}')
                    setattr(self, attr_name, new_val)
                    #print(f'after value {new_val}')
        return attack


    def get_tile_z(self, x, y):
        if 0 <= int(x) < self.map_w and 0 <= int(y) < self.map_h:
            return self.terrain[int(y), int(x)]
        return None

    def is_jump(self):
        return self.jump_z > 0 or self.jump_z_vel != 0

    def set_rigid(self, duration):
        self.rigid_timer = max(self.rigid_timer, duration)

    def is_locked(self):
        return self.rigid_timer > 0 or self.combat_state == CombatState.DOWN or self.combat_state == CombatState.KNOCKBACK
    def is_on_hit(self):
        return self.on_hit_timer > 0
    def is_invincible(self):
        return self.invincible_timer > 0
    # def is_knockbacking(self):
    #     return abs(self.knockback_vel_x) > 0.0 or self.knockback_vel_z < 0.0
    # Characters.py

    def is_knockbacking(self):
        # 只要狀態是 KNOCKBACK，不論速度正負，都應該鎖定控制
        return self.combat_state == CombatState.KNOCKBACK or abs(self.knockback_vel_x) > 0.1

    def is_falling(self):
        return self.falling_timer > 0
    def is_alive(self):
        return self.health > 0
    def is_able_hold_item(self):
        return self.combat_state == CombatState.WEAK or self.combat_state == CombatState.DOWN

    def is_pickable(self):
        return self.combat_state == CombatState.DOWN and not self.held_by
    def is_holdable(self):
        #檢查自身條件是否能繼續持有
        return self.combat_state == CombatState.DOWN

    def into_weak_state(self):
        self.combat_state = CombatState.WEAK
        self.combat_timer = 90
        self.combat_timer_max = 90
        self.set_rigid(90)
    def into_down_state(self):
        self.combat_state = CombatState.DOWN
        self.invincible_timer = 40
        self.combat_timer = 180
        self.combat_timer_max = 180
        self.hit_count = 0.0
        self.set_rigid(180)
        self.state = MoveState.STAND
    def into_dead_state(self):
        self.combat_state = CombatState.DEAD
        self.invincible_timer = 240
        self.dead_timer = 160
        self.hit_count=100
        print(f'{self.name} 死亡')
    def into_normal_state(self):
        self.combat_state = CombatState.NORMAL
        self.hit = False
        self.hit_timer = 0
        self.hit_count = 0.0
        print(f'{self.name} 回到正常')

    def check_ground_contact(self):
        # 🧠 檢查腳底對應的 tile z 值
        #print(f'{self.name} falling {self.falling_timer}')
        if self.falling_timer > 1:
            return
        tx = int(self.x + self.width / 2)
        ty = int(self.y + self.height * 0.1)
        below_z = self.get_tile_z(tx, ty)
        #如果是空中攻擊, 清除狀態
        if self.attack_state:
            self.attack_state = None
            self.state = MoveState.STAND

        # if below_z is not None:
        #     if self.z >= below_z and self.jump_z <= 0:
                # ✅ 已達地面，停止下落
        print(f'{self.name} 落地')
        self.jump_z = 0
        self.jump_z_vel = 0
        self.knockback_vel_z = 0
        self.knockback_vel_x = 0
        self.z = below_z
        self.state = MoveState.STAND
        self.set_rigid(10)
        self.color = self.default_color
        self.falling_timer = 0
        self.falling_y_offset = 0
    def check_and_trigger_fall(self, dx, dy, move_rate):
        new_x = self.x + dx * move_rate
        new_y = self.y + dy * move_rate

        foot_x = new_x + self.width / 2
        foot_y = new_y + self.height * 0.1
        nx, ny = int(foot_x), int(foot_y)
        target_z = self.get_tile_z(nx, ny)
        if target_z is None:
            return False
        if abs(target_z - self.z) >= 2 and target_z < self.z:
            self.jump_z = 1.5*abs(target_z - self.z)
            self.jump_z_vel = -0.1 #掉落時浮空用判定
            self.vel_xy = (dx * 0.3, dy * 0.3)
            self.falling_timer = abs(target_z - self.z)*15 #根據段差來設置掉落時間, 1z=15frame
            self.falling_y_offset = 0
            return True
        return False

    # Characters.py

    def check_wall_collision(self, next_x):
        """偵測 next_x 是否撞牆或超出地圖邊界"""
        # 1. 檢查地圖左右邊界
        if next_x < 0 or next_x+self.width > self.map_w:
            return True

        # 2. 檢查地形高度差 (牆壁)
        # 取得角色當前高度與前方地塊高度
        tx = int(next_x + (0.8 if self.knockback_vel_x > 0 else 0.2))
        ty = int(self.y + 0.5)

        target_z = self.get_tile_z(tx, ty)
        if target_z is not None:
            # 如果目標地塊比當前位置高出 2 階以上，視為撞牆
            if target_z - self.z >= 2:
                return True

        return False
    def update_physics_only(self):
        if self.knockback_vel_z != 0:
            self.jump_z += self.knockback_vel_z
            self.knockback_vel_z = self.knockback_vel_z - GRAVITY  # 重力加速度
            #print(f'{self.name} knockback with vel_z={self.knockback_vel_z} jump_z={self.jump_z}')

            if self.jump_z <= 0:
                self.jump_z = 0
                self.knockback_vel_z = 0
                #self.check_ground_contact()

        # ✅ 若正在跳躍中，僅更新跳躍高度與落下，不進行碰撞判定
        if self.jump_z != 0 and not self.held_by:
            #排除被拿著的狀態
            self.jump_z += self.jump_z_vel
            self.jump_z_vel -= GRAVITY  # ✅ 注意這裡保持一致，不要重複扣太快

            if self.jump_z <= 0:
                self.jump_z = 0
                self.jump_z_vel = 0
                self.check_ground_contact()
        # ✅ 處理垂直跳躍或擊飛


        # ✅ 處理水平擊退
        if self.super_armor_timer <= 0 and self.combat_state != CombatState.DOWN:
            #鋼體不擊退
            if self.knockback_vel_x != 0:
                self.x += self.knockback_vel_x
                self.knockback_vel_x *= 0.85  # 摩擦力衰減
                #print(f'{self.name} knockback_vel_x={self.knockback_vel_x}')
                if abs(self.knockback_vel_x) < 0.1:
                    self.knockback_vel_x = 0

        # 水平擊退與撞牆偵測
        if self.combat_state == CombatState.KNOCKBACK:
            if self.knockback_vel_x != 0:
                next_x = self.x + self.knockback_vel_x

                if self.check_wall_collision(next_x):
                    # 撞牆反應：
                    print(f"[PHYSICS] {self.name} 撞牆了！, ({self.x}, {self.y})")
                    self.knockback_vel_x = -self.knockback_vel_x * 0.2  # 反彈

                    # 如果還在空中，讓它垂直落下；如果接近地面，直接進入倒地
                    if self.jump_z <= 0.5:
                        self.into_down_state()

                    # 選配：加入撞牆震動
                    if self.scene:
                        self.scene.trigger_shake(10,5)
                else:
                    self.x = next_x
                    self.knockback_vel_x *= 0.85

                    if abs(self.knockback_vel_x) < 0.05:
                        self.knockback_vel_x = 0

    def draw_combat_bar(self, win, px, py):
        if self.combat_state == CombatState.NORMAL:
            return

        # 設定 combat bar 長度與顏色
        width = int(self.width * TILE_SIZE)
        height = 5
        ratio = self.combat_timer / self.combat_timer_max

        if self.combat_state == CombatState.WEAK:
            color = (255, 255, 0)
        elif self.combat_state == CombatState.DOWN:
            color = (150, 0, 0)
        else:
            color = (100, 100, 100)

        # 如果是 down 狀態，改畫在右側橫向縮短，避免重疊倒地姿勢
        if self.combat_state == CombatState.DOWN:
            bar_x = px + width + 4
            bar_y = py + int(self.height * TILE_SIZE * 0.5)
            bar_h = int(self.height * TILE_SIZE * 0.5)
            bar_w = 5
            fill_h = int(bar_h * ratio)
            pygame.draw.rect(win, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(win, color, (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))
        else:
            # 一般狀態畫在角色上方
            bar_x = px
            bar_y = py - 8
            pygame.draw.rect(win, (50, 50, 50), (bar_x, bar_y, width, height))
            pygame.draw.rect(win, color, (bar_x, bar_y, int(width * ratio), height))

    def update_hit_timer(self):
        if self.hit_timer > 0:
            self.hit_timer -= 1
            if self.hit_timer == 0:
                self.hit = False

    def update_combat_state(self):
        #print(f"[DEBUG] {self.name} update_combat_state> hit_count: {self.hit_count}")
        if self.combat_state == CombatState.DEAD:
            return
        if self.combat_state == CombatState.DOWN:
            #self.combat_timer -= 1
            if self.combat_timer <= 0:
                # print(f"{self.__class__.__name__} recovered from {self.combat_state}!")
                # self.combat_state = CombatState.NORMAL
                # self.hit = False
                # self.hit_timer = 0
                # self.hit_count = 0.0
                self.into_normal_state()
                self.invincible_timer = 30
                return True
            return False
        if self.combat_state == CombatState.WEAK:
            #self.combat_timer -= 1
            if self.combat_timer <= 0:
                self.into_normal_state()
                return False
        if self.combat_state == CombatState.KNOCKBACK:
            # 使用較大的閾值判定結束，避免因微小速度導致動畫卡住
            is_vertical_stopped = (self.jump_z <= 0.05 and self.knockback_vel_z <= 0.05)
            is_horizontal_stopped = (abs(self.knockback_vel_x) < 0.05)
            if is_vertical_stopped and is_horizontal_stopped and self.super_armor_timer <= 0:
                self.into_down_state()


        # 若為 normal 狀態，逐步減少 hit count
        if self.hit_count > 0:
            self.hit_count -= self.recovery_rate
            if self.hit_count < 0:
                self.hit_count = 0

        return True

    def get_swing_attack_data(self, attacker):
        duration = 30
        if self.rigid_timer < 30:
            duration = self.rigid_timer
        if duration <= 12:
            return None
        return AttackData(
            attack_type=AttackType.SWING,
            duration=duration,
            trigger_frame=12,
            recovery=16,
            hitbox_func=item_hitbox,
            damage=lambda _: self.throw_damage if hasattr(self, 'swing_damage') else 11,
            knock_back_power=[0.3,0.2],
            effects=[AttackEffect.FORCE_DOWN],
            frame_map = [0] * 12 + [1] * (duration - 12),  # 必須與duration等長
            frame_map_ratio = [12, duration-12]
        )
    def get_throw_attack_data(self, attacker):
        duration = 30
        if self.rigid_timer < 30:
            duration = self.rigid_timer
        if duration <= 16:
            return None
        return AttackData(
            attack_type=AttackType.THROW,
            duration=duration,
            trigger_frame=16,
            recovery=16,
            hitbox_func=item_hitbox,
            effects=[AttackEffect.SHORT_STUN],
            damage=lambda _: self.throw_damage if hasattr(self, 'throw_damage') else 7,
            knock_back_power=[0.6,0.2],
            frame_map = [0] * 16 + [1] * (duration - 16),  # 必須與duration等長
            frame_map_ratio = [16, duration-16]
        )

    def get_knock_direction(self, attacker, attack_data):
        if attacker is None:
            # 無明確來源（如全畫面）→ 用角色自己 facing
            return -1 if self.facing == DirState.RIGHT else 1

        dx = self.x - attacker.x

        # 避免誤差，設定一個最小距離門檻
        if abs(dx) > 1e-3:
            return 1 if dx > 0 else -1

        # 若 dx 幾乎 0，改用 attacker 的 facing 或 direction（若有）
        if hasattr(attacker, "facing"):
            return 1 if attacker.facing == DirState.LEFT else -1
        elif hasattr(attack_data, "direction"):
            return 1 if attack_data.direction == DirState.LEFT else -1

        # fallback
        return -1
    
    def resolve_combat_state_on_hit(self, attack_data):
        #處理虛弱狀態
        effects = attack_data.effects
        if self.super_armor_timer > 0:
            #鋼體時不改變戰鬥狀態
            return
        # if AttackEffect.FORCE_DOWN in effects:
        #     self.into_down_state()
        #force down用knock_back取代
        if AttackEffect.FORCE_WEAK in effects:
            self.into_weak_state()
        else:
            # 普通攻擊後的邏輯
            #print(f'{self.name} CombatState {self.combat_state.name}')
            if self.combat_state == CombatState.NORMAL:
                self.hit_count += 1
                if self.hit_count >= self.max_hits_before_weak:
                    self.into_weak_state()
            elif self.combat_state == CombatState.WEAK:
                #weak中強制所有技能擊倒
                if attack_data.knock_back_power[0] <= 0 and attack_data.knock_back_power[1] <= 0:
                    self.into_down_state()
            elif self.combat_state == CombatState.DOWN:
                #倒地被追加時避免連段到死,給予霸體
                self.super_armor_timer = self.rigid_timer

    def apply_attack_effects(self, attacker, attack_data):
        if self.invincible_timer > 0 or self.super_armor_timer > 0:
            #無敵或鋼體時不接受特殊狀態
            return
        #處理攻擊特效
        effects = attack_data.effects
        # 其他特效依照 enum 加入即可
        # if AttackEffect.FORCE_DOWN in effects:
        #     self.into_down_state()
        if AttackEffect.FORCE_WEAK in effects:
            self.into_weak_state()

        #擊退處理
        if attack_data.knock_back_power[0] > 0 or attack_data.knock_back_power[1] > 0 and not (self.combat_state != CombatState.DOWN and self.health > 0):
            #倒地狀態下不擊退
            #if self.combat_state != CombatState.DOWN or (self.combat_state == CombatState.DOWN and self.health <= 0):
            self.combat_state = CombatState.KNOCKBACK
            #knock_back_power[0]水平 [1]垂直
            if attack_data.knock_back_power[0] != 0:
                direction = self.get_knock_direction(attacker, attack_data)
                self.knockback_vel_x = direction * attack_data.knock_back_power[0]
            if attack_data.knock_back_power[1] != 0:
                self.knockback_vel_z = attack_data.knock_back_power[1]
                self.jump_z = max(0.2, attack_data.knock_back_power[1] * 0.05)

        if AttackEffect.SHORT_STUN in effects:
            self.set_rigid(ON_HIT_SHORT_STUN_TIME)
            self.on_hit_timer = ON_HIT_SHORT_STUN_TIME
        if AttackEffect.BURN in effects:
            #print(f'{self.name} burning!!!!  burning!!!! burning!!!')
            self.get_burning = True

    def take_damage(self, attacker, attack_data):
        #damage = getattr(attack_data, 'damage', 5)
        damage = attack_data.get_damage(attacker)
        #根據敵我進行傷害加成
        self.health -= damage
        # if self.health <= 0 and self.knockback_vel_z <= 0 and self.knockback_vel_x <= 0 and self.jump_z <= 0:
        #     self.health = 0
        #     self.into_dead_state()
        # 顯示傷害數字
        if self.scene:
            font_size = 24
            if damage >= 100:
                font_size = 48
            self.scene.add_floating_text(self.x + self.width / 2, self.y + self.height, f"-{damage}", self.map_h, color=(255, 0, 0), font_size=font_size)
        return f'{self.name} 受到 {damage}, 剩餘HP: {self.health}', damage

    def on_hit(self, attacker, attack_data):
        # 無敵檢查
        st = f'{attacker.name} 的 {attack_data.attack_type.name} 命中 {self.name} '
        if self.jump_z > 0:
            st = st + '(空中)'
        if self.is_invincible() and AttackEffect.IGNORE_INVINCIBLE not in attack_data.effects:
            print(f'{st} (無敵!)')
            return

        # 鋼體檢查
        if self.super_armor_timer > 0:
            print(f'{st} (鋼體!)')

        # 基本命中狀態
        self.hit = True
        self.hit_timer = 20

        if attacker.attack_state:
            #attacker.attack_state.has_hit = True
            attacker.attack_state.has_hit.append(self)


        damage_st, damage = self.take_damage(attacker, attack_data)
        st = st + f' {damage_st}'
        # CombatState 處理
        if self.combat_state != CombatState.DEAD:
            self.resolve_combat_state_on_hit(attack_data)
        # 特效處理
            self.apply_attack_effects(attacker, attack_data)

        if self.attack_state:
            print(f'[on_hit] {self.name} 的 {self.attack_state.data.attack_type.name} 攻擊被中斷')
            self.attack_state = None
            self.state = MoveState.STAND
        #持有物掉落
        if hasattr(self, "held_object"):
            if self.held_object:
                self.held_object.held_by = None
                self.held_object = None
        #print(st)
        self.on_hit_count += 1
        if attacker.get_hitbox():
            hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
            self.scene.create_effect(hit_x, hit_y, hit_z,'hit')

        if attack_data.hit_stop_frames > 0:
            if self.scene:
                self.scene.trigger_hit_stop(attack_data.hit_stop_frames)
                # 選配：配合微小的震動效果更好
                self.scene.trigger_shake(duration=attack_data.hit_stop_frames, intensity=3)
                flip = True if attacker.x < self.x else False
                print(f'{self.name} 發動 hitstop! attacker是{attacker.name}, flip={flip}')
                hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
                self.scene.create_effect(hit_x, hit_y, hit_z, "hitstop", flip)

    def update_common_timer(self):
        self.current_frame += 1
        if self.rigid_timer > 0:
            if self.health < self.max_hp/4:
                self.recovery_rate = 0.04
            elif self.health < self.max_hp/2:
                self.recovery_rate = 0.02
            self.rigid_timer -= 1

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.super_armor_timer > 0:
            self.super_armor_timer -= 1
        if self.falling_timer > 0:
            self.falling_timer -= 1
            self.falling_y_offset += Z_FALL_OFSSET
        if self.on_hit_timer > 0:
            self.on_hit_timer -= 1
        if self.combat_timer > 0:
            #血越少醒的越快
            if self.health > self.max_hp*0.75:
                self.combat_timer -= 1
            elif self.health > self.max_hp*0.5:
                self.combat_timer -= 2
            elif self.health > self.max_hp*0.25:
                self.combat_timer -= 4

        # 每禎遞減攻擊計時器
        #死亡消失
        if self.health <= 0 and self.combat_state != CombatState.DEAD:
            if not self.is_knockbacking() and self.jump_z <= 0:
                self.into_dead_state()

        if self.combat_state == CombatState.DEAD:
            self.dead_timer -=1
            #print(f'{self.name} dead state discount {self.dead_timer}')
            if self.dead_timer <= 0:
                print(f'{self.name} 消失')
                if self.money > 0:
                    loot = self.drop_loot()
                    print('{} 掉落 {} 的 {}'.format(self.name, loot['type'], loot['value']))

                if self.scene:
                    #self.scene.unregister_unit(self)
                    self.scene.mark_for_removal(self)

        if self.attack_state:
            self.attack_state.update()




    def update_common_interactable_unit(self, unit):
        return
    # def update_on_flying(self):
    #
    #     if self.flying:
    #         self.x += self.vel_x
    #         self.jump_z += self.jump_z_vel
    #         self.jump_z_vel -= self.weight  # 模擬重力
    #         below_z = self.get_tile_z(int(self.x), int(self.y))
    #         print(f'{self.name} 飛行中')
    #         if below_z is not None and self.jump_z <= below_z:
    #             self.jump_z = below_z
    #             self.jump_z_vel = 0
    #             self.flying = False  # ✅ 落地後關閉飛行
    #             print(f'{self.name} 落地了')
    #             #<--
        #還沒實作
    def update_common_opponent(self, opponent=None):
        #受創狀態判定
        self.update_combat_state()
        self.update_hit_timer()
        
        #123456
        if self.attack_state:
            #print(f'update_common_opponent: [({self.current_frame}){self.attack_state.timer}] self.attack_state={self.attack_state} ({self.x:.2f}, {self.y:.2f})')
            # self.attack_state.update()
            #attack_state的timer update只能進行一次! 必須在外面
            if self.attack_state and not self.attack_state.is_active():
                #suspend(f'{self.attack_state.data.attack_type.name}收招')
                self.set_rigid(self.attack_state.data.recovery)
                self.attack_state = None
                self.state = MoveState.STAND
                self.mode = MoveState.STAND

        #命中計時器
        if opponent and opponent.attack_state and opponent.attack_state.should_trigger_hit():
            if is_box_overlap(opponent.get_hitbox(), self.get_hurtbox()):
                if self not in opponent.attack_state.has_hit:
                    # hit_x, hit_y, hit_z = get_overlap_center(opponent.get_hitbox(), self.get_hurtbox())


                    if self.held_by is None:
                        #避免打到自己
                        self.on_hit(opponent, opponent.attack_state.data)

        # 若正在攻擊期間
        #
        if self.attack_state:
            if self.is_jump():
                # 空中攻擊時允許 X 軸移動與跳躍物理
                dx = self.last_intent.get('dx')*0.1
                new_x = self.x + dx
                #限制邊界
                self.x = max(0, min(new_x, self.map_w - self.width))
            return False
        else:
            return True

    def draw_hit_box(self, win, cam_x, cam_y, tile_offset_y, color, terrain_z_offset=0):
        #符合條件的才畫
        if self.attack_state and (self.attack_state.should_trigger_hit() or len(self.attack_state.has_hit) > 0):
            hitbox = self.get_hitbox()
            hx = int(hitbox['x1'] * TILE_SIZE) - cam_x
            hy = int((self.map_h - hitbox['y2']) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset) - cam_y + tile_offset_y
            hw = int((hitbox['x2'] - hitbox['x1']) * TILE_SIZE)
            hh = int((hitbox['y2'] - hitbox['y1']) * TILE_SIZE)
            pygame.draw.rect(win, color, (hx, hy, hw, hh), 2)

    def draw_stand(self, win, px, py):
        pygame.draw.rect(win, self.color, (px, py, int(self.width * TILE_SIZE), int(self.height * TILE_SIZE)))

    def draw_weak(self, win, px, py):
        pygame.draw.rect(win, (255, 255, 100), (px, py, int(self.width * TILE_SIZE), int(self.height * TILE_SIZE)))

    def draw_down(self, win, px, py):
        color=(100, 0, 0)
        if self.is_invincible():
            color = (150, 0, 0)
        pygame.draw.ellipse(win, color, (
            px, py + int(self.height * TILE_SIZE * 0.5),
            int(self.width * TILE_SIZE),
            int(self.height * TILE_SIZE * 0.5)
        ))
    def draw_dead(self, win, px, py):
        if (self.dead_timer // 10) % 2 == 0:
            self.draw_down(win, px, py)
        # 額外效果：可以加紅色閃爍、爆炸動畫等

    def draw_knockback(self, win, px, py):
        #suspend('knockback!')
        pygame.draw.rect(win, (255, 180, 0), (px, py, int(self.width * TILE_SIZE), int(self.height * TILE_SIZE)))

    def draw_hit(self, win, px, py):
        """在角色目前姿態上繪製紅色邊框，表示受擊狀態（非實心）"""
        if self.combat_state == CombatState.DOWN:
            # 倒地狀態 → 畫橢圓紅框
            box = pygame.Rect(
                px,
                py + int(self.height * TILE_SIZE * 0.5),
                int(self.width * TILE_SIZE),
                int(self.height * TILE_SIZE * 0.5)
            )
            pygame.draw.ellipse(win, (255, 0, 0), box, width=2)
        else:
            # 正常站立 → 畫矩形紅框
            box = pygame.Rect(
                px,
                py,
                int(self.width * TILE_SIZE),
                int(self.height * TILE_SIZE)
            )
            pygame.draw.rect(win, (255, 0, 0), box, width=2)
    def get_hitbox(self):
        if self.attack_state:
            xy_hitbox =self.attack_state.get_hitbox(self.x+self.width/2, self.y, self.facing, self)
            
            xy_hitbox['z1'] = self.z+self.jump_z
            xy_hitbox['z2'] = self.z+self.jump_z+self.height
            if self.attack_state.is_fly_attack:
                xy_hitbox['z1'] = self.z
            return xy_hitbox
            #return self.attack_state.get_hitbox(self.x+self.width/2, self.y, self.facing)

        return None
    def get_hurtbox(self):
        return {'x1': self.x, 'x2':self.x+self.width, 'y1':self.y, 'y2':self.y+self.height, 'z1':self.z+self.jump_z, 'z2':self.z+self.jump_z+self.height}

    def get_interact_box(self):
        #物件互動使用(非傷害)
        return {
            'x1': self.x - 0.5,
            'x2': self.x + self.width - 0.5,
            'y1': self.y,
            'y2': self.y + self.height*0.5,
            'z1': self.jump_z,
            'z2': self.jump_z+self.height
        }

    def stop_print_info(self):
        st = f'{self.name} ({self.x}, {self.y}, {self.z}) JUMP {self.jump_z}\n'
        st = st + f'move_state [{self.state.name}] combat_state [{self.combat_state.name}] attack_state'

        if self.attack_state:
            st = st + f'[{attack_state.data.attack_type.name}]'
        else:
            st = st + 'None '
        st = st + f'\nFlags: is_knockbacking[{self.is_knockbacking()}] is_falling[{self.is_falling()}] is_locked[{self.is_locked()}] flying[{self.flying}]'
        suspend(st)

    def handle_input(self, intent):
        #所有無法操控狀態
        block_movement = False
        if intent['action'] == 'throw_item':
            self.stop_print_info()
        if self.attack_state:
            #return
            block_movement=True
        if self.combat_state == CombatState.DOWN or self.combat_state == CombatState.DEAD:
            return
        if self.is_knockbacking() or self.is_falling() or self.is_locked():
            return
        if self.flying:
            return



        if not block_movement:
            #攻擊中限制移動
            self.last_intent = intent
            if intent['direction'] in [DirState.LEFT, DirState.RIGHT]:
                self.facing = intent['direction']
            #初始狀態: 站
            self.state = MoveState.STAND
            dx, dy = intent['dx'], intent['dy']
            if intent['jump']:
                print(f'jump param: jump_z {self.jump_z}, jumpping_flag {self.jumpping_flag}')
            if intent['jump'] and self.jump_z == 0 and not self.jumpping_flag:

                if intent['horizontal'] == MoveState.RUN:
                    self.high_jump = True
                self.jump_z_vel = 1.8 if intent['horizontal'] == MoveState.RUN else 1.4
                self.jump_z = 0.1
                self.color = self.jump_color
                self.jumpping_flag = True

            move_rate = 0.4 if intent['horizontal'] == MoveState.RUN else 0.2
            new_x = self.x + dx * move_rate
            new_y = self.y + dy * move_rate
            #掉落檢查
            if self.check_and_trigger_fall(dx, dy, move_rate):
                return

            prev_x, prev_y = self.x, self.y
            foot_x = new_x + self.width / 2
            foot_y = new_y + self.height * 0.1
            nx, ny = int(foot_x), int(foot_y)
            target_z = self.get_tile_z(nx, ny)
            # --- 防呆攔截點 ---
            if target_z is None:
                # 如果目標位置超出地圖，不更新座標 (或是執行擋牆邏輯)
                moved = False
            else:
                if abs(target_z - self.z) <= 1 or (self.jump_z > 0 and self.z + self.jump_z >= target_z):
                    self.x, self.y = new_x, new_y
                    if self.jump_z > 0:
                        self.z = target_z
                    else:
                        self.z = target_z

            moved = (self.x != prev_x or self.y != prev_y)
            if moved and not self.is_falling():
                self.state = intent['horizontal'] if intent['horizontal'] in [MoveState.WALK, MoveState.RUN,
                                                                              MoveState.STEP] else MoveState.WALK

        intent_act =intent.get('action')
        if intent_act == 'pickup_item':
            for comp in self.components.values():
                if hasattr(comp, "handle_action"):
                    comp.handle_action('pickup_item')
                    self.attack_intent = None
        elif intent_act is not None:
            #打出對應招式
            print('{} 出招 {}'.format(self.name, intent['action']))
            self.attack(intent['action'])
            if hasattr(self.attack_state, "data"):
                print(f'[{self.current_frame}]{self.name}打出{self.attack_state.data.attack_type.name}')

            #self.set_rigid(self.attack_state.data.duration / 4) #攻擊硬直
            self.attack_intent = None  # ✅ 清除

    def set_attack_by_skill(self, skill):
        atk_data = attack_data_dict.get(skill)
        if atk_data is not None:
            if atk_data.can_use(self):
                if skill in SWING_ATTACKS:
                    item = self.get_component("holdable").held_object
                    if item:
                        atk_data = item.get_swing_attack_data(self)
                        if atk_data:
                            self.attack_state = SwingAttackState(self, item)  # 會在初始化時載入AttackData.SWING的相關資料
                            self.state = MoveState.ATTACK
                        else:
                            item.held_by = None
                            if hasattr(self, "held_object"):
                                self.held_object = None
                elif skill in THROW_ATTACKS:
                    item = self.get_component("holdable").held_object
                    if item:
                        atk_data = item.get_throw_attack_data(self)
                        if atk_data:
                            self.attack_state = ThrowAttackState(self, item)
                            self.state = MoveState.ATTACK
                        else:
                            item.held_by = None
                            if hasattr(self, "held_object"):
                                self.held_object = None
                elif skill in FLY_ATTACKS:
                    self.attack_state = FlyAttackState(self, atk_data)
                    self.state = MoveState.ATTACK
                elif skill in FLYING_OBJECT_ATTACKS:
                    if skill == AttackType.FIREBALL:
                        object = self.create_flying_object('fireball')
                    elif skill == AttackType.BULLET:
                        object = self.create_flying_object('bullet')
                    else:
                        return
                    self.attack_state = ThrowAttackState(self, object)
                    # 把attack_data備份起來, 這樣在character收招後仍然有有效資料
                    object.attacker_attack_data = self.attack_state.data
                    if self.attack_state is not None:
                        self.state = MoveState.ATTACK
                else:
                    self.attack_state = AttackState(self, atk_data)
                    self.state = MoveState.ATTACK

                if atk_data:
                    self.apply_skill_effect_components(atk_data)

    def draw_hp_bar(self, win, px, py):
        # max_hp = 100
        # bar_width = int(self.width * TILE_SIZE)
        # hp_ratio = self.health / max_hp
        # hp_color = (200, 0, 0)
        # bg_color = (50, 50, 50)
        # bar_height = 4
        # bar_y = py - 14  # 高於角色頭部
        # pygame.draw.rect(win, bg_color, (px, bar_y, bar_width, bar_height))
        # pygame.draw.rect(win, hp_color, (px, bar_y, int(bar_width * hp_ratio), bar_height))
        # 若死亡則不顯示血條
        if self.combat_state == CombatState.DEAD:
            return

        bar_width = int(self.width * TILE_SIZE)
        bar_height = 4
        bar_y = py - 14  # 血條在角色頭上方

        # 🟥 計算比例（最大值避免為 0）
        max_hp = getattr(self, "max_hp", 100)
        max_hp = max(max_hp, 1)  # 防止除以 0
        hp_ratio = self.health / max_hp

        # 🎨 顏色樣式根據角色類型切換
        if hasattr(self, 'name') and self.name == 'player':
            hp_color = (200, 0, 0)  # 玩家 → 紅色
            bg_color = (50, 0, 0)
            border_color = (255, 200, 200)
        else:
            hp_color = (255, 215, 0)  # 敵人
            bg_color = (0, 0, 50)
            border_color = (200, 200, 255)

        # 🖌️ 繪製背景與血量條
        pygame.draw.rect(win, bg_color, (px, bar_y, bar_width, bar_height))
        pygame.draw.rect(win, hp_color, (px, bar_y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(win, border_color, (px, bar_y, bar_width, bar_height), 1)
    def create_flying_object(self, item_to_create='fireball'):
        from Items import Fireball, Bullet
        rebuild_map_info = [self.terrain, self.map_w, self.map_h]
        flying_object = None
        create_func = None
        if item_to_create == 'fireball':
            create_func = Fireball
        elif item_to_create == 'bullet':
            create_func = Bullet
        if create_func:
            flying_object = create_func(self.x, self.y, rebuild_map_info, owner=self)
            self.scene.register_unit(flying_object, side=self.side, tags=['item', 'temp_object'], type='item')
        return flying_object
    def drop_loot(self):
        from Items import Coin, MagicPotion  # 假設你有 Coin 類別
        #加入機率掉落
        import random
        if self.scene:
            prob = random.random()
            if prob > self.drop_mana_rate:
                potion = MagicPotion(self.x, self.y, [self.terrain, self.map_w, self.map_h])
                potion.mana = 1
                self.scene.register_unit(potion, side='netural', tags=['item'], type='item')
                return {'type': 'MagicPotion', 'value': 1}
        #掉落硬幣
            coin = Coin(self.x, self.y, [self.terrain, self.map_w, self.map_h])
            coin.money = self.money
            self.scene.register_unit(coin, side='netural', tags=['item'], type='item')
            return {'type':'money', 'value':coin}
        return None

    def apply_skill_effect_components(self, attack_data):
        config = attack_data.effect_component_config
        if not config:
            return

        comp_name = config.get("component_name")
        comp_key = config.get("component_key")
        params = config.get("params", {})

        if comp_name and comp_key:
            # 1. 動態取得 Component 類別
            ComponentClass = get_component_class(comp_name)

            if ComponentClass:
                # 2. 移除舊元件 (確保沒有重複掛載)
                if self.get_component(comp_key):
                    self.remove_component(comp_key)

                # 3. 實例化並傳入參數
                # **重要**：使用 **params** 字典來初始化元件
                new_component = ComponentClass(**params)

                # 4. 掛載到角色身上
                self.add_component(comp_key, new_component)
                print(f"[{self.name}] 成功掛載特效元件: {comp_name} ({comp_key})")
            else:
                print(f"[WARN] 無法找到特效元件類別: {comp_name}")


class Player(CharacterBase):
    def __init__(self, x, y, map_info, config):
        super().__init__(x, y, map_info)
        self.key_buffer = {dir: None for dir in [DirState.LEFT, DirState.RIGHT]}
        self.step_pending = {dir: -9999 for dir in [DirState.LEFT, DirState.RIGHT]}
        self.color = (255, 100, 100)
        self.jump_color = (0, 220, 0)
        self.fall_color = (0, 140, 0)
        self.default_color = (255, 100, 100)
        self.key_down_frame = {}
        self.last_step_frame = {}
        self.step_active_until_frame = {}
        self.step_direction = None
        self.running_dir = None
        self.name='player'
        self.side = 'player_side'
        self.popup=config.get("popup")
        # self.attack_map = {
        #     "z_attack": lambda: AttackType.BASH if self.state == MoveState.RUN else AttackType.PUNCH,
        #     "x_attack": lambda: AttackType.KICK,
        #     "c_attack": lambda: AttackType.SLASH
        # }
        self.attack_table = {'z_attack':{'default': AttackType.PUNCH, 'run': AttackType.BASH, 'highjump_fall': AttackType.METEOFALL},
                             'x_attack':{'default': AttackType.KICK, 'jump': AttackType.FLY_KICK},
                             'c_attack':{'default': AttackType.SLASH, 'run': AttackType.FIREBALL},
                             'swing_item':{'default': AttackType.SWING},
                             'throw_item':{'default': AttackType.THROW,'jump':AttackType.THROW}}

        self.animator = SpriteAnimator(image_path=config.get("image_path"), config_dict=config.get("animator_config"))  # 載入素材
        if config.get("stand"):
            self.stand_image = pygame.image.load(config.get("stand")).convert_alpha()
        self.super_move_animator = None
        if config.get("special_move"):
            self.super_move_animator = SpriteAnimator(config.get("special_move"), {"frame_width":96, "frame_height":96, "anim_map":None})
        self.super_move_staging = config.get("super_move_staging")
        self.super_move_max_time = 0


        #for dir in ['left', 'right', 'up', 'down']:
        for dir in DirState:
            self.key_down_frame[dir] = None
            self.last_step_frame[dir] = -9999

    def recently_stepped(self, direction, current_frame):
        last_frame = self.last_step_frame.get(direction)
        return last_frame is not None and current_frame - last_frame <= STEP_EFFECT_FRAME

    def input_intent(self, keys):
        #左右key判定
        dir_h = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT])
        dir_v = (keys[pygame.K_UP] - keys[pygame.K_DOWN])
        direction = None
        if dir_h > 0:
            direction = DirState.RIGHT
        elif dir_h < 0:
            direction = DirState.LEFT
        elif dir_v > 0:
            direction = DirState.DOWN
        elif dir_v < 0:
            direction = DirState.UP

        horizontal = MoveState.STAND
        #STEP/WALK/RUN判定
        if direction in [DirState.LEFT, DirState.RIGHT]:
            if self.running_dir == direction:
                horizontal = MoveState.RUN
            elif self.recently_stepped(direction, self.current_frame):
                horizontal = MoveState.RUN
                self.running_dir = direction
            elif self.step_pending.get(direction, -1) >= self.current_frame:
                horizontal = MoveState.STEP
            else:
                horizontal = MoveState.WALK
        else:
            horizontal = MoveState.STAND

        attack_type = None
        if self.attack_intent:
            #attack_intent = z/x/c_attack, 對應到招式表
            attack_type = self.resolve_attack_table()
            self.attack_intent = None

        jump_intent = None
        if self.jump_intent_trigger:
            #print(f'{self.name} jump!')
            jump_intent = True
            self.jump_intent_trigger = False

        down_pressed = keys[pygame.K_DOWN]
        zxc_buttons = [keys[pygame.K_z], keys[pygame.K_x], keys[pygame.K_c]]
        dx = dir_h*0.5
        dy = dir_v * 0.5 if not self.is_jump() or self.is_falling() else dir_v * 0.2,
        if self.x+dx < 0 or self.x+dx+self.width >= self.map_w:
            dx = 0.0

        return {
            'horizontal': horizontal,
            'direction': direction,
            "dx": dx,
            "dy": dir_v * 0.5 if not self.is_jump() or self.is_falling() else dir_v * 0.2,
            'jump': jump_intent,
            'action': attack_type,
            'down_pressed': down_pressed, # <--- 新增
            'button_pressed': zxc_buttons
        }

    def on_key_down(self, key):
        if self.combat_state == CombatState.DOWN or self.combat_state == CombatState.WEAK:
            return  # 倒地或weak無法攻擊
        # 攻擊期間不接受其他輸入:取消攻擊
        # if self.state == MoveState.ATTACK:
        #     return


        if key in KEY_TO_ACTION:
            print(f'{KEY_TO_ACTION[key]} trigger')
            self.attack_intent = KEY_TO_ACTION[key]

        # 左右鍵記錄按下時間
        if key == pygame.K_LEFT:
            self.key_down_frame[DirState.LEFT] = self.current_frame
        elif key == pygame.K_RIGHT:
            self.key_down_frame[DirState.RIGHT] = self.current_frame

        if key == pygame.K_SPACE and not self.jump_key_block:
            self.jump_key_block = True
            self.jump_intent_trigger = True

    def on_key_up(self, key):
        dir_map = {
            pygame.K_LEFT: DirState.LEFT,
            pygame.K_RIGHT: DirState.RIGHT
        }
        direction = dir_map.get(key, None)
        if direction:
            down_frame = self.key_down_frame.get(direction)
            if down_frame is not None:
                hold = self.current_frame - down_frame
                if 1 <= hold <= STEP_PRESS_MAX_FRAME:
                    self.step_pending[direction] = self.current_frame + STEP_STATE_DURATION
                    self.step_direction = direction
                    self.last_step_frame[direction] = self.current_frame
                    self.step_active_until_frame[direction] = self.current_frame + STEP_STATE_DURATION
                if direction == self.running_dir:
                    self.running_dir = None
        if key == pygame.K_SPACE:
            self.jump_key_block = False

    def attack(self, skill):
        if skill == AttackType.BRUST:
            self.attack_state = None
            self.set_attack_by_skill(skill)
            # 設定爆氣後的屬性
            atk_data = attack_data_dict[AttackType.BRUST]
            self.invincible_timer = atk_data.duration
            self.set_rigid(atk_data.duration)
            return

        if self.attack_state:
            if self.attack_state.can_cancel_to(skill):
                print(f"[Cancel] {self.attack_state.data.attack_type.name} → {skill.name}")
                self.attack_state = AttackState(self, attack_data_dict[skill])  # 取消當前招式
            else:
                print(f"[Block] 無法取消 {self.attack_state.data.attack_type.name} → {skill.name}")
                return  # ❌ 無法取消，忽略攻擊
        else:
            #如果是none=沒設定過攻擊
            self.set_attack_by_skill(skill)

        # if self.name == 'player' and self.attack_state is not None and self.attack_state is not ThrowAttackState \
        #         and (data in self.attack_data and self.attack_state.data is not None and self.attack_state.data.attack_type == AttackType.SLASH:
        #     self.scene.say(self, 'Tiger UpperCut!', duration=90)
        if self.name == 'player' and attack_data_dict[skill].dialogue is not None:
            self.scene.say(self, attack_data_dict[skill].dialogue, duration=90)



    def handle_input(self, keys):
        intent = self.input_intent(keys)
        # 1. 偵測爆氣 (Z+X+C)
        try_brust = intent.get("button_pressed")
        # 檢查是否至少按下了兩個攻擊鍵，且目前不是無敵狀態
        if try_brust and sum(try_brust) >= 2 and self.invincible_timer <= 0:
            if self.mp > 0:  # 如果有爆氣資源
                print(f"[BRUST] {self.name} 強制發動爆氣！")
                self.into_normal_state()  # 解除受創狀態
                self.attack(AttackType.BRUST)  # 呼叫攻擊
                self.mp -= 1
                return  # 爆氣是最高優先級，直接結束輸入處理

        # 2. 呼叫父類別處理一般攻擊與移動
        super().handle_input(intent)


    def handle_movement(self):
        # 實作完整的移動邏輯（左右移動、跑步、跳躍、判斷地板等）
        for dir in self.step_pending:
            if self.step_pending[dir] < self.current_frame:
                self.step_pending[dir] = -9999
        if self.is_falling():
            self.jump_z += self.jump_z_vel
            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()

        if self.jump_z != 0:
            self.state = MoveState.JUMP if self.jump_z_vel > 0 else MoveState.FALL
            self.color = self.jump_color if self.jump_z_vel > 0 else self.fall_color
            self.jump_z += self.jump_z_vel
            self.jump_z_vel -= 0.05
            if self.jump_z <= 0:
                self.jump_z = 0
                self.jump_z_vel = 0
                self.color = self.default_color
                self.jumpping_flag = False
                self.high_jump = False
        else:
            self.high_jump = False
            self.jumpping_flag = False
        for dir, end_frame in self.step_pending.items():
            if self.current_frame <= end_frame and self.state == MoveState.STAND:
                self.state = MoveState.STEP


    #這是player的update
    def update(self):
        self.update_common_timer()
        if self.health_visual > self.health:
            self.health_visual -= 0.5
        if self.external_control:
            self.update_by_external_control()
            return

        if self.held_by:
            print(f'{self.name} 被持有 {self.held_by.name}')
        if self.health < 50 and self.health > 0:
            self.has_stand = True
            self.super_armor_timer = 1
            #持續霸體
        if self.held_by:
            self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來
        #處理失控的飛行狀態
        if self.combat_state == CombatState.DEAD:
            print(f'{self.name} 死亡! 遊戲結束')
            return
        # if self.high_jump:
        #     print('Player high jump!')
        enemys = self.scene.get_units_by_side('enemy_side')
        neturals = self.scene.get_units_by_side('netural')
        # attack_timer的update僅限一次!
        for enemy in enemys:
            self.update_common_opponent(enemy)
        for unit in neturals:
            self.update_common_interactable_unit(unit)
        self.update_physics_only()
        self.handle_movement()
        self.update_burning_flag()

    #def enable_super_move(self, pre_pose_background = None, portraits=None, effect=None, timer=350, portraits_begin=0.6):
    def enable_super_move(self):
        #print(f'{self.super_move_staging}')
        if self.super_move_staging is None:
            return
        if self.mp > 0:
            config_dict = self.super_move_staging
            #print(f'enable super move damage {40+self.mp*30}')
            timer = config_dict.get("timer", 350)
            super_move_dict = {"pre_pose_background": config_dict.get("pre_pose_background", None),
                               "portraits": config_dict.get("portraits", None),
                               "effect": config_dict.get("effect", None),
                               "timer": timer,
                               "damage": 40+self.mp*30,
                               "portraits_begin": config_dict.get("portraits_begin", 0.6)}
            self.super_move_max_time = timer
            self.scene.start_super_move(self, super_move_dict)
            self.set_rigid(30)
            self.mp = 0

    def draw_super_move_character(self, win, cam_x, cam_y, tile_offset_y, show_period=0.5):

        # 更新動畫 frame（每隔 anim_speed frame 換一次圖）
        self.super_move_anim_timer += 1
        if self.super_move_anim_timer < self.super_move_max_time*show_period:
            f_idx = int(len(self.super_move_animator.frames)*self.super_move_anim_timer/(self.super_move_max_time*show_period))
            #print(f"draw_super_move_character {self.super_move_anim_timer}, frame_idx {f_idx}")
            frame = self.super_move_animator.get_frame_by_index(f_idx)
        else:
            frame = self.super_move_animator.get_frame_by_index(len(self.super_move_animator.frames)-1)

        # 若角色面向左側，進行左右翻轉
        if self.facing == DirState.LEFT:
            frame = pygame.transform.flip(frame, True, False)

        # 計算畫面座標
        px = int(self.x * TILE_SIZE) - cam_x
        # py = int((self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        falling_z_offset = 0
        if self.is_falling():
            falling_z_offset = self.falling_y_offset * Z_FALL_OFSSET
        py = int((self.map_h - self.y - self.height) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset + falling_z_offset) - cam_y + tile_offset_y

        cx = int((self.x + self.width / 2) * TILE_SIZE) - cam_x
        base_cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5) - cam_y + tile_offset_y
        cy = int((self.map_h - (
                    self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset + falling_z_offset) - cam_y + tile_offset_y

        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height

        win.blit(frame, (draw_x, draw_y))



class Ally(CharacterBase):
    def __init__(self, x, y, z, map_info, config_dict):
        super().__init__(x, y, map_info)
        move_speed = config_dict.get("move_speed", 0.5)
        attack_cooldown_duration = config_dict.get("attack_cooldown",240)
        self.attack_cooldown = 0  # 攻擊冷卻倒數
        self.attack_cooldown_duration = attack_cooldown_duration  # 冷卻時間（可調整）
        self.default_color = (100, 100, 255)
        self.jump_color = (100, 150, 255)
        self.fall_color = (50, 100, 255)
        self.summon_sickness = 150
        self.name = 'ally'
        self.combo_count = 0
        self.combos = [AttackType.BULLET, AttackType.SLASH]
        self.dummy = False
        self.animator = SpriteAnimator(image_path=config_dict.get("image_path"), config_dict=config_dict.get("animator_config"))  # 載入素材
        self.stand_image = None
        self.side = 'player_side'
        self.ai_move_speed = move_speed
        self.popup = config_dict.get("popup")
        self.scale = config_dict.get("scale",1.0)


    # ally的update
    def update(self):
        self.update_common_timer()
        if self.external_control:
            self.update_by_external_control()
            return
        if self.current_frame < self.summon_sickness:
            self.invincible_timer =2

        # 關閉AI
        # return

        self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來

        if self.combat_state == CombatState.DEAD:
            return
        enemys = self.scene.get_units_by_side('enemy_side')
        #neturals = self.scene.get_units_by_side('netural')
        enemy_target = None
        min_dist = 10000
        for enemy in enemys:
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < min_dist:
                enemy_target = enemy
                min_dist = dist
            if not self.update_common_opponent(enemy):
                # 不能動作的狀態
                return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if enemy_target:
            intent = self.decide_intent(enemy_target)
            self.handle_input(intent)
        self.update_physics_only()
        self.handle_movement()
        self.update_burning_flag()


    def decide_intent(self, target):
        intent = {
            'direction': self.facing,
            'horizontal': MoveState.STAND,
            'dx': 0,
            'dy': 0,
            'jump': False,
            'action': None
        }
        if self.dummy:
            return intent

        if self.attack_state or not self.is_alive():
            return intent

        # 分開邏輯模組處理
        ai_jump_logic(self, target, intent)
        ai_attack_logic(self, target, intent, act='support')
        ai_move_logic(self, target, intent, far_speed = self.ai_move_speed, near_speed = self.ai_move_speed*0.6)
        return intent

    def attack(self, skill):
        # 123456
        if self.state == MoveState.ATTACK:
            return
        if self.attack_state:
            return
        else:
            # 如果是none=沒設定過攻擊
            self.set_attack_by_skill(skill)

    def handle_movement(self):
        # 實作完整的移動邏輯（左右移動、跑步、跳躍、判斷地板等）
        if self.is_falling():
            self.jump_z += self.jump_z_vel
            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()
        if self.jump_z != 0 and not self.held_by:
            self.state = MoveState.JUMP if self.jump_z_vel > 0 else MoveState.FALL
            self.color = self.jump_color if self.jump_z_vel > 0 else self.fall_color
            self.jump_z += self.jump_z_vel
            self.jump_z_vel -= 0.05
            if self.jump_z <= 0:
                self.jump_z = 0
                self.jump_z_vel = 0
                self.color = self.default_color

def ai_move_logic(unit, target, intent, far_speed = 0.5, near_speed=0.3):
    if unit.attack_state or unit.is_locked() or unit.state == MoveState.ATTACK:
        #攻擊時不移動
        return
    dx = target.x - unit.x
    dy = target.y - unit.y
    dist = (dx ** 2 + dy ** 2) ** 0.5

    if dist > 10.0:
        move_speed = 1  # approach fast
    elif dist > 4.0:
        move_speed = 0.5  # approach slow
    elif dist > 2.0:
        move_speed = far_speed
    elif dist > 1.0:
        move_speed = near_speed
    else:
        move_speed = 0.0  # keep distance

    move_dx = 0.5 if dx > 0.2 else -0.5 if dx < -0.2 else 0
    move_dy = 0.5 if dy > 0.2 else -0.5 if dy < -0.2 else 0
    intent['dx'] = move_dx * move_speed
    intent['dy'] = move_dy * move_speed

    if intent['dx'] > 0:
        intent['direction'] = DirState.RIGHT
        intent['horizontal'] = MoveState.RUN if move_speed > 0.3 else MoveState.WALK
    elif intent['dx'] < 0:
        intent['direction'] = DirState.LEFT
        intent['horizontal'] = MoveState.RUN if move_speed > 0.3 else MoveState.WALK

def ai_jump_logic(unit, target, intent):
    dx = target.x - unit.x
    dy = target.y - unit.y
    dz = abs((target.z) - (unit.z))

    tile_x = int(unit.x + (0.4 if dx > 0 else -0.4))
    tile_y = int(unit.y + (0.4 if dy > 0 else -0.4))
    next_tile_z = unit.get_tile_z(tile_x, tile_y)

    if unit.jump_z == 0 and next_tile_z is not None:
        dz_to_next_tile = next_tile_z - unit.z
        if dz >= 2 and dz_to_next_tile >= 2:
            intent['jump'] = True
            intent['dx'] = dx
            intent['dy'] = dy
            intent['direction'] = DirState.RIGHT if dx > 0 else DirState.LEFT
            intent['horizontal'] = MoveState.STAND
            print(f'{unit.name} 試圖跳躍!')

def ai_attack_logic(unit, target, intent, act='support'):
    dx = target.x - unit.x
    dy = target.y - unit.y
    dz = abs((target.z) - (unit.z))
    dist = (dx ** 2 + dy ** 2) ** 0.5
    if act == 'support':
        if dy < 0.5 and dz < 1.5 and unit.attack_cooldown <= 0:
            if dist > 1:
                intent['action'] = AttackType.BULLET
            else:
                intent['action'] = AttackType.SLASH
            unit.attack_cooldown = unit.attack_cooldown_duration
            unit.facing = DirState.LEFT if dx < 0 else DirState.RIGHT
            unit.attack_cooldown = unit.attack_cooldown_duration
    else:
        if hasattr(unit, "scale"):
            attack_range = 3*unit.scale
        else:
            attack_range = 3
        if dist <= attack_range and dz < 1.0:
            if unit.attack_cooldown <= 0:
                intent['action'] = unit.combos[int(unit.combo_count) % len(unit.combos)]
                unit.combo_count += 1
                unit.attack_cooldown = unit.attack_cooldown_duration
                unit.facing = DirState.LEFT if dx < 0 else DirState.RIGHT

from CharactersConfig import *
class Enemy(CharacterBase):
    #def __init__(self, x, y, z, map_info, config_dict,scale=1.0, combos=DEFAULT_COMBOS, name='enemy', ai_move_speed = 0.2, attack_cooldown = 45, popup=None):
    def __init__(self, x, y, z, map_info, config_dict):
        super().__init__(x, y, map_info)
        # 1) 放大碰撞尺寸
        scale = config_dict.get("scale", 1.0)
        ai_move_speed = config_dict.get("ai_move_speed", 0.2)
        attack_cooldown = config_dict.get("attack_cooldown", 45)
        self.width = self.width * scale
        self.height = self.height * scale
        self.attack_cooldown = 0  # 攻擊冷卻倒數
        self.attack_cooldown_duration = attack_cooldown  # 冷卻時間（可調整）
        self.default_color=(100,100,255)
        self.jump_color=(100,150,255)
        self.fall_color=(50, 100, 255)
        self.summon_sickness = 150
        self.name=config_dict.get("name", "default")
        self.combo_count = 0
        self.combos = config_dict.get("combos", DEFAULT_COMBOS)
        self.dummy = False
        self.animator = SpriteAnimator(image_path=config_dict.get("image_path"), config_dict=config_dict.get("animator_config"))  # 載入素材
        self.stand_image = pygame.image.load("..\\Assets_Drive\\star_p.png").convert_alpha()
        self.side = 'enemy_side'
        self.money = 10 #loot
        self.ai_move_speed = ai_move_speed
        self.popup=config_dict.get("popup")
        if self.popup and "landing" in self.popup:
            self.jump_z = 20
            self.jump_z_vel = -0.2

        # 4) 調整動畫貼圖大小
        #    如果 Enemy 原本有 self.animator 並且 animator.frames 是一組 pygame.Surface
        if scale != 1.0:
            if hasattr(self, "animator") and self.animator and hasattr(self.animator, "frames"):
                scaled_frames = []
                for f in self.animator.frames:
                    sw = f.get_width()
                    sh = f.get_height()
                    scaled_frames.append(pygame.transform.scale(f, (sw * scale, sh * scale)))
                self.animator.frames = scaled_frames

                # 如果 animator 有 frame_width/height 屬性就同步更新
                if hasattr(self.animator, "frame_width"):
                    self.animator.frame_width *= scale
                if hasattr(self.animator, "frame_height"):
                    self.animator.frame_height *= scale


    #enemy的update
    def update(self):

        self.update_common_timer()
        if self.external_control:
            self.update_by_external_control()
            return
        if self.current_frame < self.summon_sickness:
            self.invincible_timer=2
            #開場發呆
        #關閉AI
        #return
        #替身測試
        # if self.health < 50:
        #     self.has_stand = True
        
        self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來

        if self.combat_state == CombatState.DEAD:
            return
        players = self.scene.get_units_by_side('player_side')
        neturals = self.scene.get_units_by_side('netural')
        for player in players:
            if not self.update_common_opponent(player):
                #不能動作的狀態
                return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        intent = self.decide_intent(players[0])
        if self.current_frame >= self.summon_sickness:
            self.handle_input(intent)
        self.update_physics_only()
        self.handle_movement()
        self.update_burning_flag()



    def decide_intent(self, target):
        intent = {
            'direction': self.facing,
            'horizontal': MoveState.STAND,
            'dx': 0,
            'dy': 0,
            'jump': False,
            'action': None
        }
        if self.dummy:
            return intent

        if self.attack_state or not self.is_alive():
            return intent

        # 分開邏輯模組處理
        ai_jump_logic(self, target, intent)
        ai_attack_logic(self, target, intent, act='Enemy')
        ai_move_logic(self, target, intent, far_speed=self.ai_move_speed, near_speed=self.ai_move_speed*0.6)



        return intent

    def attack(self, skill):
        # 123456
        if self.state == MoveState.ATTACK:
            return
        if self.attack_state:
            return
        else:
            #如果是none=沒設定過攻擊
            self.set_attack_by_skill(skill)


    def handle_movement(self):
        # 實作完整的移動邏輯（左右移動、跑步、跳躍、判斷地板等）
        if self.is_falling():
            self.jump_z += self.jump_z_vel
            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()
        if self.jump_z != 0 and not self.held_by:
            self.state = MoveState.JUMP if self.jump_z_vel > 0 else MoveState.FALL
            self.color = self.jump_color if self.jump_z_vel > 0 else self.fall_color
            self.jump_z += self.jump_z_vel
            self.jump_z_vel -= 0.05
            if self.jump_z <= 0:
                self.jump_z = 0
                self.jump_z_vel = 0
                self.color = self.default_color

class BigEnemy(Enemy):
    def __init__(self, x, y, z, map_info, material, big_ratio=2.0):
        super().__init__(x, y, z, map_info, material)

        # 1) 放大碰撞尺寸
        self.width = self.width * big_ratio
        self.height = self.height * big_ratio

        # 2) 視覺區別 (顏色或其他旗標)
        self.default_color = (200, 80, 20)
        self.jump_color = (220, 140, 40)
        self.fall_color = (180, 80, 30)

        # 3) 能力值強化
        #   - 血量大幅提升
        #   - money 掉更多
        base_max_hp = getattr(self, "max_hp", 100)
        self.max_hp = base_max_hp * 3
        self.health = self.max_hp

        base_money = getattr(self, "money", 10)
        self.money = base_money * 5

        # 攻擊冷卻更長，顯得笨重但危險
        self.attack_cooldown_duration = max(
            15,
            int(self.attack_cooldown_duration * 1.8)
        )
        self.attack_cooldown = 0

        # 召喚後僵直時間（或開場不動秒數）可以調整
        self.summon_sickness = 10

        # 4) 調整動畫貼圖大小
        #    如果 Enemy 原本有 self.animator 並且 animator.frames 是一組 pygame.Surface
        if hasattr(self, "animator") and self.animator and hasattr(self.animator, "frames"):
            scaled_frames = []
            for f in self.animator.frames:
                sw = f.get_width()
                sh = f.get_height()
                scaled_frames.append(pygame.transform.scale(f, (sw * big_ratio, sh * big_ratio)))
            self.animator.frames = scaled_frames

            # 如果 animator 有 frame_width/height 屬性就同步更新
            if hasattr(self.animator, "frame_width"):
                self.animator.frame_width *= big_ratio
            if hasattr(self.animator, "frame_height"):
                self.animator.frame_height *= big_ratio

        # 5) 改招式組合（可依你遊戲平衡調）
        self.combos = [AttackType.SLASH, AttackType.BASH, AttackType.KICK]

        # 6) metadata / 辨識
        self.name = 'big_enemy'
        self.side = 'enemy_side'


