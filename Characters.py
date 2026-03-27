import pygame
from Config import *
#from enum import Enum, auto
from State_enum import *
from Skill import *
#from Component import ComponentHost, HoldFlyLogicMixin, StandComponent
from Component import StandComponent
from Entity import Entity
from CharactersConfig import *
import random
import math
import copy
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

from PhysicsUtils import is_box_overlap, get_overlap_center

KEY_TO_ACTION = {
    pygame.K_z: "z_attack",
    pygame.K_x: "x_attack",
    pygame.K_c: "c_attack"
}
from Config import WIDTH, HEIGHT


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
        self.anim_map_varient = config_dict.get("anim_map_varient", {})

    def slice_sheet(self):
        sheet_w, sheet_h = self.sheet.get_size()
        print(f'slice_sheet>{sheet_w}({self.frame_width}) {sheet_h}')
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
class CharacterBase(Entity):
    #Entity的初始化def __init__(self, x, y, map_info, width=1.0, height=1.0, weight=0.1):
    def __init__(self, x, y, map_info, width=1.5, height=2.5, weight = 1.0):
        super().__init__(x=x, y=y, map_info=map_info, width=width, height=height, weight=weight)
        self.unit_type = "character"

        self.color = (0,0,0)
        # 受創系統
        self.combat_state = CombatState.NORMAL
        self.combat_timer = 0
        self.hit_count = 0.0
        self.max_hits_before_weak = 12.0
        self.recovery_rate = 0.01
        self.max_hp=100
        self.health = self.max_hp
        self.health_visual = self.max_hp    #UI視覺使用
        #self.z = z  # 如有需要強制指定 z 值
        self.summon_sickness=0
        self.hit = False
        self.hit_timer = 0  #受創"持續時間"的timer
        self.on_hit_count = 0 #作為動畫切換用
        self.vz = 0
        self.rigid_timer = 0
        self.invincible_timer = 0   #無敵timer
        self.super_armor_timer = 0  #鋼鐵timer
        self.falling_timer = 0
        self.dead_timer = 0 #死亡消失時間
        #擊飛時變數
        self.vel_x = 0
        self.vz = 0

        
        self.state = MoveState.STAND
        #self.last_intent = {'direction': None, 'horizontal': None}
        self.last_intent = None
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

        self.weight = weight # 作為投擲用物件
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
        #輸入緩衝
        self.input_buffer = None  # 存儲指令字串，例如 'z_attack', 'jump'
        self.input_buffer_timer = 0  # 緩衝剩餘幀數
        self.BUFFER_MAX_FRAMES = 6  # 緩衝窗口大小
        self.is_mashing = False
        self.death_knockback = False
        self.skill_overrides = {}  # 預設為空

        # AI行為控制
        self.morale = 1.0  # 士氣：1.0 是正常，低於 0.3 會恐慌
        self.aggressiveness = 0.8  # 攻擊性：影響進攻距離的判斷
        self.personality = random.choice(['brave', 'coward', 'cautious'])
        self.ai_target_cache = None
        self.ai_recalc_timer = 0
        self.draw_alpha=255
        self.breakthrough=False
        self.attacker_attack_data=None
        self.interact_target = None #用來儲存倒地攻擊的互動對象
        self.strength = 10.0
        self.unable_to_grab_item = None

        self.attack_cooldown = 0  # 攻擊冷卻倒數


    def take_contextual_attack(self, attacker_attack_state):
        atk_data = attacker_attack_state.data
        #這邊要根據contextual_trigger_frames定時觸發傷害

    def is_holding(self):
        comp = self.components.get('holdable', None)
        if comp:
            return comp.held_object
        return None
    def try_use_ability(self, ability_key):
        from Skill import ABILITY_DATA
        from Component import AbilityComponent, StandComponent
        data = ABILITY_DATA.get(ability_key)
        comp_key = f"ability_{ability_key}"
        #優先攔截function類
        if ability_key == 'super_move':
            if not hasattr(self, "enable_super_move") or self.scene.super_move_timer > 0:
                return False
            self.enable_super_move()
        else:
        # 1. 檢查是否已經在該技能狀態中 (避免重複註冊)
            if self.get_component(comp_key) and ability_key not in ABILITY_REPEATABLE:
                print(f"[LOG] {self.name}的{data.name} 正在冷卻或持續中，無法重複使用")
                return False
            if ability_key in ['stand'] and self.stand_config:
                self.add_component(comp_key, StandComponent(self.stand_config, data.duration))
            else:
                self.add_component(comp_key, AbilityComponent(data))
        self.mp -= data.mp_cost
        return True
    def trigger_guard_success(self, attacker, attack_data):
        """
        熱血物語式格擋成功：將攻擊前搖轉化為防禦。
        """
        # 1. 播放格擋特效
        if self.scene:
            # 計算命中位置 (利用現有的碰撞檢測函數)
            hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
            self.scene.create_effect(hit_x, hit_y, hit_z, 'guard')  # 需在 SceneManager 實作此類別
            self.scene.trigger_hit_stop(5)  # 短暫的命中凍結增加力道感
            self.scene.trigger_shake(duration=10, intensity=3)

        # 2. 狀態轉換：中斷攻擊，進入格擋
        self.attack_state = None
        self.state = MoveState.GUARD  # 確保 State_enum 有定義 GUARD
        # 3. 物理反饋：小退一步 (向後推)
        knock_dir = -1 if self.facing == DirState.RIGHT else 1
        self.x = min(self.map_w-self.width/2, max(self.width/2, (self.x+knock_dir * 1.5))) # 直接位移或設定一個極短的 vel_x

        # 4. 設定短硬直 (格擋硬直)
        # 這裡的硬直要比受傷短，讓玩家有機會快速反擊
        self.set_rigid(ON_GUARD_STUN_TIME)
        self.on_hit_timer = ON_GUARD_STUN_TIME
        # 5. 傷害減免 (選擇性)
        # 即使格擋成功，也可以考慮扣除極少量生命值或 MP
        # self.health -= 1
        print(f"[GUARD] {self.name} 成功招架了 {attacker.name} 的攻擊！")
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
        self.is_thrown = False
        self.held_by = None
        self.attack_intent = None
        self.vel_x = 0
        self.vz = 0
        self.attack_intent = None
        self.hit = False

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


        # if self.health <= 0:
        #     print(f'===========\n{self.name}的HP小於0，繪製動畫')
        # 狀態轉換為動畫名
        # print(f'[draw_anim] {self.name} combat_state = {self.combat_state.name} move_state = {self.state.name}', end='\r')
        combat_state_anim_map = {
            CombatState.DEAD: "dead",CombatState.DOWN:"down",CombatState.WEAK:"weak",CombatState.KNOCKBACK:"knockback"
        }
        attack_state_anim_map = {
            AttackType.BASH:"bash",AttackType.SLASH:"slash",AttackType.KICK:"kick",AttackType.FLY_KICK:"flykick",
            AttackType.METEOFALL:"meteofall",AttackType.SWING:"swing",AttackType.THROW:"throw",AttackType.PUNCH:"punch",
            AttackType.MAHAHPUNCH:"mahahpunch", AttackType.SPECIAL_PUNCH:"special_punch", AttackType.SPECIAL_KICK:"special_kick",
            AttackType.BRUST:"brust",AttackType.PUSH:"push",AttackType.DOWN_STOMP:"down_attack",AttackType.SPEAR:"spear",
            AttackType.SPECIAL_SPEAR:"special_spear",AttackType.MAHAHSPEAR:"mahahspear",AttackType.BACKFLIP_SHOT:"backflip_shot"
        }
        move_state_anim_map = {MoveState.JUMP:"jump", MoveState.FALL:"fall",MoveState.WALK:"walk",MoveState.RUN:"run", MoveState.GUARD:"guard"}
        common_anim_material = ['burn']
        #決定anim_frame
        anim_name = 'stand'
        if self.get_burning:
            anim_name = "burn"
        # elif self.is_knockbacking():
        #     anim_name = "knockback"
        elif self.combat_state in combat_state_anim_map:     #判斷戰鬥狀態動畫
            anim_name = combat_state_anim_map[self.combat_state]
        elif self.state == MoveState.GUARD:
            #防禦動畫的優先度高於攻擊
            anim_name = "guard"
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
        #print(f'{self.name} anim_name {anim_name}')

        if anim_name == 'stand' and self.is_holding():
            anim_name = 'hold_item'

        base_frames = self.animator.anim_map.get(anim_name)
        # 使用 getattr 安全取得可能不存在的變體字典
        var_map = getattr(self.animator, 'anim_map_varient', {})
        var_frames = var_map.get(anim_name, None)

        anim_stage_frames = base_frames
        # 判定是否處於戰鬥招式中 (排除 stand, walk 等基礎狀態)
        choosed = 0
        if self.attack_state and var_frames:
            # 🟢 修正：向右位移 4 位 (相當於除以 16) 再取奇偶
            offset_index_value =id(self.attack_state) >> 4
            if offset_index_value % 2 == 0:
                anim_stage_frames = var_frames
                choosed = 2
            else:
                anim_stage_frames = base_frames
                choosed = 1
        # if self.name=="player" and var_frames:
        #     print(f'[{choosed}]frame_compares:{base_frames}/{var_frames}, {offset_index_value}')

        if anim_stage_frames is None:
            #print(f'[draw_anim]{self.name} has no {anim_name} frame, change to stand')
            anim_name = 'stand'
            anim_stage_frames = self.animator.anim_map.get(anim_name)

        # if self.name=='player':
        #     print(f'[{self.current_frame}], anim_name={anim_name}')

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
        elif len(anim_stage_frames) == 1:
            frames = anim_stage_frames[0]
            #只有一個stage的動畫
            if len(frames) == 1:
                #只有一張圖的動畫
                frame_index = frames[0]
            else:
                #只有一個stage但有多張圖的動畫, 根據某些條件來選擇
                # walk, jump, on_hit
                if anim_name in ['walk','run']:
                    #self.anim_walk_cnt += 1
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
                elif anim_name == 'stand':
                    #多個stand的設定
                    stand_cycle = len(frames)*16 #一個張圖維持16 frame
                    stand_index = int((self.current_frame%stand_cycle)/16)
                    frame_index = frames[stand_index]
                elif anim_name == 'down_attack':
                    frame_period = 6
                    down_attack_index = int(self.attack_state.frame_index / frame_period) % len(self.animator.anim_map.get('down_attack')[0])
                    frame_index = frames[down_attack_index]
        else:
            #多stage frame, 戰鬥動畫要從AttackData的frame_map_ratio與self.anim_map做出對應表
            #戰鬥動畫包括: punch, kick, bash, special_punch, palm, special_kick, slash, mahahpunch, ranbu, swing, throw
            if anim_name in ['punch', 'kick', 'bash', 'special_punch', 'palm','brust','push',
                             'special_kick', 'slash', 'mahahpunch', 'ranbu', 'swing', 'throw', 'meteofall',
                             'spear','special_spear','mahahspear','backflip_shot']:
                index_map = self.generate_frame_index_from_ratio_map(self.attack_state.data.frame_map_ratio, anim_stage_frames)
                use_index = self.attack_state.frame_index if self.attack_state.frame_index < len(index_map) else -1
                frame_index = index_map[use_index]
            elif anim_name in ['knockback']:
                kb_frames = self.animator.anim_map.get('knockback')
                near_ground_bound = 3.0
                if (self.jump_z >= near_ground_bound or self.is_knockbacking()) and self.health > 0:
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
                    choose_index = max(0, min(int(dist_from_start/step), len(frames)-1))
                    #print(f'choose_index {choose_index}')
                    frame_index = frames[choose_index]

        # 若角色面向左側，進行左右翻轉
        vertical_flip = False
        if self.facing == DirState.LEFT:
            vertical_flip = True
        if anim_name not in common_anim_material:
            frame = self.animator.get_frame_by_index(frame_index, flip_x = vertical_flip)

        # 新規則<--

        if self.popup:
            if 'landing' in self.popup:
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
            if self.popup and 'anim' in self.popup and self.current_frame < self.summon_sickness:
                frames = self.animator.anim_map.get('popup')[0]
                popup_frame_cnt = len(frames)
                frame_idx = min(int(popup_frame_cnt * self.current_frame / self.summon_sickness),
                                popup_frame_cnt - 1)
                frame = self.animator.get_frame_by_index(frames[frame_idx])
            if self.popup and 'fade-in' in self.popup and self.current_frame < self.summon_sickness:
            #if self.current_frame < self.summon_sickness:
                # 使用 max(0, 255 - countdown) 的簡潔寫法處理 Alpha
                alpha_value = min(255, int((self.current_frame / self.summon_sickness) * 255))
                frame.set_alpha(alpha_value)


        self.current_anim_frame = frame
        if self.draw_alpha != 255:
            frame.set_alpha(self.draw_alpha)
        # 計算畫面座標
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        falling_z_offset = 0
        if self.is_falling():
            falling_z_offset = self.falling_y_offset * Z_FALL_OFSSET
        px, py = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)

        # 劇情提示（血條與命中特效等）
        self.draw_combat_bar(win, px, py)
        self.draw_hp_bar(win, px, py)

#for swing---
        # 1. 檢測自己是否正在被「揮舞」
        swing_offset_x,swing_offset_y = 0,0
        if self.held_by:
            #swing_offset_y =  -self.held_by.height*TILE_SIZE*0.8
            swing_offset_y = -self.held_by.height * 0.95
        if self.held_by and self.held_by.attack_state and self.held_by.attack_state.name == 'swing':
            #is_being_swung = True

            dir = 1
            if self.held_by.facing == DirState.LEFT:
                dir = -1
            # swing_offset_x = dir*int(self.held_by.width * TILE_SIZE * 0.6)
            # swing_offset_y += self.held_by.height*TILE_SIZE*0.4
            swing_offset_x = dir * self.held_by.height * 0.6*TILE_SIZE
            swing_offset_y += self.held_by.width*0.4*TILE_SIZE
            print(f'{self.name} 被揮舞 {swing_offset_x}, {swing_offset_y}!')
#--------


        if DEBUG:
            self.draw_debug_info(win, px, py)
            # DEBUG: 角色腳下的圓形定位點（用於碰撞、踩地感）
        base_cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * TILE_SIZE) - cam_y + tile_offset_y
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)

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

        #顫抖特效區
        if self.scene and self.scene.hit_stop_timer > 0:
            #import random
            draw_x += random.randint(-2, 2)
            draw_y += random.randint(-2, 2)

            # --- 抖動回饋整合 ---
        if self.is_mashing:
            # 產生 -2 到 2 像素的隨機偏移
            #import random
            draw_x += random.randint(-2, 2)
            draw_y += random.randint(-2, 2)

        # --- 1. 時停壓迫感：根據累積動量產生震動 ---
        if self.scene and self.scene.env_manager.freeze_timer > 0 and self not in self.scene.env_manager.highlight_units:
            # 計算目前的動量總和
            momentum = (abs(self.vel_x) + abs(self.vz)) * 0.6  # 係數可調
            #print(f'{self.name} momentum {momentum}')
            intensity = int(min(6, momentum))  # 最大震動幅度限制在 12 像素
            if intensity > 0:
                #import random
                draw_x += random.randint(-intensity, intensity)
                draw_y += random.randint(-intensity, intensity)

        # if self.name=='player':
        #     print(f'{self.name}的afterimage_enabled={self.afterimage_enabled}')
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
            if swing_offset_x != 0.0 or swing_offset_y != 0.0:
                print(f"draw_offset swing={swing_offset_x},{swing_offset_y}")
            win.blit(frame, (draw_x+swing_offset_x, draw_y+swing_offset_y))

        self.current_anim_frame = frame
        self.currnet_anim_draw_x = draw_x+swing_offset_x
        self.current_anim_draw_y = draw_y+swing_offset_y
        #win.blit(frame, (draw_x, draw_y))

        # 新增：讓所有組件（包括 AuraEffect 或 StatusAura）進行繪製
        for component in self.components.values():
            if hasattr(component, "draw"):
                component.draw(win, cam_x, cam_y, tile_offset_y)

        # aura_comp = self.get_component("aura_effect")
        # if aura_comp:
        #     # 傳入所有繪圖所需參數
        #     #print(f'{aura_comp} enable')
        #     aura_comp.draw(win, cam_x, cam_y, tile_offset_y)
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
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        px, py = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)

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

        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        pygame.draw.circle(win, (0, 0, 0), (cx, cy), 3)

        self.draw_hit_box(win, cam_x, cam_y, tile_offset_y, (255, 0, 0))

        step_info = '-'
        step_dir = self.last_intent.get("direction") or self.step_direction
        if step_dir in [DirState.LEFT, DirState.RIGHT]:
            if self.recently_stepped(step_dir, self.current_frame):
                step_info = f"{step_dir.name}"
        self.draw_combat_bar(win, px, py)
        self.draw_hp_bar(win, px, py)

    def scene_items(self):
        if hasattr(self, 'scene'):
            return self.scene.get_all_interactables()
        return []

    def resolve_attack_table(self):
        def only_item_nearby(units):
            for u in units:
                if u.type != 'item':
                    return False
            return True
        def get_nearest_target(character, units):
            max_dist = 1000000.0
            target = None
            for u in units:
                if u.type != 'item':
                    x_u = u.x+u.width/2
                    y_u = u.y+u.height/2
                    x_c = character.x+character.width/2
                    y_c = character.y+character.height/2
                    dist = (x_u-x_c)**2+(y_u-y_c)**2
                    if target is None:
                        target = u
                    if dist < max_dist:
                        max_dist = dist
                        target = u
            return target


        attack = None
        if self.attack_intent:
            (u, d, l, r) = self.last_intent.get('dirs', False)
            real_intent = self.attack_intent
            comp = self.components.get("holdable")
            if real_intent == 'z_attack':
                if comp.held_object:
                    real_intent = 'swing_item'
                elif d:
                    something_nearby, avail_items = comp.find_nearby_item()
                    if something_nearby:
                        if self.unable_to_grab_item == False:
                            real_intent = "pickup_item"
                        else:
                            real_intent = "z_attack"
                        z_table = self.attack_table.get("z_attack", None)
                        if z_table:
                            real_intent = z_table.get("down_action", real_intent)
                        if real_intent in CONTEXTUAL_ATTACK:
                            if only_item_nearby(avail_items):
                                #real_intent = "pickup_item"
                                # 只有"沒有敵人可已做down_attack，只有物品"時，退化為pickup_item
                                if self.unable_to_grab_item == False:
                                    real_intent = "pickup_item"
                                else:
                                    real_intent = "z_attack"
                            else:
                                #從avail_items抓出最近的那個敵人
                                self.interact_target = get_nearest_target(self, avail_items)


            elif real_intent == 'x_attack':
                if comp.held_object:
                    real_intent = 'throw_item'


            #jump_flag = self.is_jump()
            #print(f'意圖:{self.attack_intent} -> {real_intent} (jz:{self.jump_z}, is_jump {jump_flag})')
            if real_intent in ['pickup_item']+CONTEXTUAL_ATTACK and not self.is_jump():
                return real_intent
            elif real_intent not in ['swing_item', 'throw_item']:
                # rollback回去
                real_intent = self.attack_intent

            atk_table = self.attack_table.get(real_intent, {})            
            attack = atk_table.get('default', None)
            print(f'attack1 {attack}')
            #if self.z > 0 and 'jump' in atk_table:
            if self.jump_z > 0:
                attack = atk_table.get('jump', None)
                # [新增判斷] 如果是高跳 + 按著 Down 鍵，則使用 highjump 招式
                # 檢查 self.last_intent['down_pressed'] 是否為 True (即按下 Down 鍵)
                u,d,l,r = self.last_intent.get('dirs', False)
                if self.high_jump and d:
                    attack=atk_table.get('highjump_fall', None)
            elif self.state==MoveState.RUN and 'run' in atk_table:
                attack = atk_table.get('run', None)
                print(f'>>> run attack = {attack}<<<<')
            print(f'attack2 {attack}')
        if attack in [AttackType.PUNCH, AttackType.KICK, AttackType.SPEAR]:
            enemy_side = 'enemy_side' if self.side == 'player_side' else 'player_side'
            # 定義偵測中心（通常在角色前方一點）
            check_dist = 1.5 if self.facing == DirState.RIGHT else -1.5
            nearby_enemies = self.scene.get_nearby_units_by_side(
                self.x + check_dist, self.y, radius=2.0, side=enemy_side
            )
            # 檢查是否有任何敵人處於 WEAK 狀態
            has_weak_target = any(e.combat_state == CombatState.WEAK for e in nearby_enemies)
            if has_weak_target:
                atk_table = self.attack_table.get(real_intent, None)
                # z_table = self.attack_table.get("z_attack", None)
                if atk_table:
                    attack = atk_table.get("special", attack)
                print(f"[REACTION] 偵測到 Weak 敵人，{self.name} 的 {real_intent} 使用 {attack}!")
                # attack = AttackType.SPECIAL_PUNCH if attack == AttackType.PUNCH else AttackType.SPECIAL_KICK




        # #處理技能的動量變化
        # if attack is not None:
        #     atk_data = attack_data_dict[attack]
        #     if atk_data.physical_change is not None:
        #         for attr_name, value in atk_data.physical_change.items():
        #             print(f"[PHYSICS] 角色 {self.name} 套用 {attr_name} = {value}")
        #             ori_val = getattr(self, attr_name)
        #             new_val = ori_val + value
        #             #print(f'before value {ori_val}')
        #             setattr(self, attr_name, new_val)
        #             #print(f'after value {new_val}')
        return attack


    def get_tile_z(self, x, y):
        if 0 <= int(x) < self.map_w and 0 <= int(y) < self.map_h:
            return self.terrain[int(y), int(x)]
        return None

    def is_jump(self):
        return self.jump_z > 0 or self.vz != 0

    def set_rigid(self, duration):
        self.rigid_timer = max(self.rigid_timer, duration)

    def is_locked(self):
        return self.rigid_timer > 0 or self.combat_state in [CombatState.DOWN, CombatState.KNOCKBACK]
    def is_on_hit(self):
        return self.on_hit_timer > 0
    def is_invincible(self):
        return self.invincible_timer > 0
    def is_super_armor(self):
        return self.super_armor_timer > 0
    # Characters.py

    def is_knockbacking(self):
        # 只要狀態是 KNOCKBACK，不論速度正負，都應該鎖定控制
        return self.combat_state == CombatState.KNOCKBACK or abs(self.vel_x) > 0.1

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

    def apply_combat_state_impact(self, state):
        # 🟢 漂亮攔截：時停中且我被凍結，先存入緩衝區，不改變動畫格
        if self.scene and self.scene.env_manager.freeze_timer > 0:
            if self not in self.scene.env_manager.highlight_units:
                self.pending_combat_state = state
                return
        self._exec_state_change(state)

    def _exec_state_change(self, state):
        if state == CombatState.KNOCKBACK:
            self.combat_state = CombatState.KNOCKBACK
        elif state == CombatState.WEAK:
            self.combat_state = CombatState.WEAK
            self.combat_timer = 90
            self.combat_timer_max = 90
            self.set_rigid(90)
        elif state == CombatState.DOWN:
            self.combat_state = CombatState.DOWN
            self.invincible_timer = 40
            knockout_time = 120 + int(100 * (1 - self.health / self.max_hp))
            # 血越少越快醒
            self.combat_timer = knockout_time
            self.combat_timer_max = knockout_time
            self.vel_x = 0.0
            self.vz = 0.0
            self.hit_count = 0.0
            self.set_rigid(knockout_time)
            self.state = MoveState.STAND
        elif state == CombatState.DEAD:
            self.combat_state = CombatState.DEAD
            self.invincible_timer = 240
            self.dead_timer = 160
            self.hit_count = 100
            # 🟢 核心修正：死亡是所有「飛行/持有」狀態的終點
            self.is_thrown = False
            self.held_by = None
            self.vz = 0
            self.vel_x = 0
            # 確保座標直接對齊地板，防止懸空死亡
            tx, ty = int(self.x + self.width / 2), int(self.y + self.height * 0.1)
            self.z = self.get_tile_z(tx, ty) or self.z
            self.jump_z = 0
        elif state == CombatState.NORMAL:
            self.combat_state = CombatState.NORMAL
            self.hit = False
            self.hit_timer = 0
            self.hit_count = 0.0
            self.rigid_timer = 0
            self.combat_timer = 0
            self.vel_x = 0.0
            self.is_mashing = False
            # 清除快取意圖
            self.clean_input_buffer()
            print(f'{self.name} 回到正常')

    def into_knockback_state(self, vel_x=0.0, vz = 0.0):
        self.vel_x += vel_x
        self.vz += vz
        self.apply_combat_state_impact(CombatState.KNOCKBACK)
    def into_weak_state(self):
        self.apply_combat_state_impact(CombatState.WEAK)
    def into_down_state(self):
        self.apply_combat_state_impact(CombatState.DOWN)
    def into_dead_state(self):
        self.apply_combat_state_impact(CombatState.DEAD)
    def into_normal_state(self):
        self.apply_combat_state_impact(CombatState.NORMAL)

    def clean_input_buffer(self):
        self.input_buffer = None
        self.input_buffer_timer = 0

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
        self.vz = 0
        self.vz = 0
        self.vel_x = 0
        self.z = below_z
        self.state = MoveState.STAND
        self.set_rigid(10)
        self.color = self.default_color
        self.falling_timer = 0
        self.falling_y_offset = 0

    def on_land_reaction(self, impact_energy=0, is_passive=False):
        """
        角色專屬的落地反應。
        因為 Entity.check_ground_contact 已經處理了物理，
        這裡只處理『人物狀態變更』。
        """
        # 🟢 修正後的門檻邏輯
        # 主動跳躍：門檻極高 (例如 150)，除非從懸崖跳下否則不扣血
        # 被動摔落：門檻低 (例如 30)，體現重摔感
        current_threshold = 18 if is_passive else 50
        print(f'{self.name} on_land_reaction: TH {current_threshold}, energy {impact_energy}, passive {is_passive}')

        # 建立一個虛擬的落地傷害 AttackData
        if is_passive:
            from Skill import AttackData, AttackType
            fall_atk = AttackData(
                attack_type=AttackType.FALL_DAMAGE,
                duration=1,
                power=impact_energy,
                absorption=1.0,  # 落地傷害由身體全額吸收，不產生位移
                impact_angle=0
            )
            # 讓自己受到落地傷害，attacker 為 None 表示環境傷害
            self.on_hit(None, fall_atk)
            if impact_energy > current_threshold:  # 使用 Config 中的門檻
                if self.scene:
                    self.scene.trigger_shake(duration=15, intensity=5)
                    # 根據能量決定是否產生落地煙塵特效
                    self.scene.create_effect(self.x+self.width/2, self.y+self.width/2, self.z, 'grounding_impact')

        if self.attack_state:
            self.attack_state = None

        from State_enum import MoveState
        self.state = MoveState.STAND
        self.set_rigid(10)  # 物品呼叫這個不會崩潰，因為 Entity 裡有空實作

        if hasattr(self, "default_color"):
            self.color = self.default_color
        self.falling_timer = 0
        self.falling_y_offset = 0
        print(f"[CHARACTER] {self.name} 落地並重置狀態")
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
            self.vz = -0.1 #掉落時浮空用判定
            self.vel_xy = (dx * 0.3, dy * 0.3)
            self.falling_timer = abs(target_z - self.z)*15 #根據段差來設置掉落時間, 1z=15frame
            self.falling_y_offset = 0
            return True
        return False


    def say(self, txt, duration=90):
        #def say(self, unit, text, duration=90, direction='up'):
        if self.scene:
            self.scene.say(self, txt, duration=duration)


    def draw_combat_bar(self, win, px, py):
        if self.combat_state == CombatState.NORMAL:
            return

        # 設定 combat bar 長度與顏色
        width = int(self.width * TILE_SIZE)
        height = 5
        ratio = self.combat_timer / self.combat_timer_max

        # 這裡計算角色在螢幕上的實際高度
        char_visual_height = int(self.height * TILE_SIZE)

        if self.combat_state == CombatState.WEAK:
            color = (255, 255, 0)
        elif self.combat_state == CombatState.DOWN:
            color = (150, 0, 0)
        else:
            color = (100, 100, 100)

        # 如果是 down 狀態，改畫在右側橫向縮短，避免重疊倒地姿勢
        if self.combat_state == CombatState.DOWN:
            bar_x = px + width + 4
            bar_y = py - int(char_visual_height * 0.5)
            bar_h = int(char_visual_height * 0.5)
            bar_w = 5
            fill_h = int(bar_h * ratio)
            pygame.draw.rect(win, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(win, color, (bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))
        else:
            # 一般狀態（如 WEAK）畫在頭頂
            bar_x = px - width // 2  # 因為 px 是中心，所以要減去半寬
            bar_y = py - char_visual_height - 10  # 腳底 - 身高 - 偏移 = 頭頂上方
            pygame.draw.rect(win, (50, 50, 50), (bar_x, bar_y, width, height))
            pygame.draw.rect(win, (255, 255, 0), (bar_x, bar_y, int(width * ratio), height))

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
            is_vertical_stopped = (self.jump_z <= 0.05 and self.vz <= 0.05)
            is_horizontal_stopped = (abs(self.vel_x) < 0.05)
            if is_vertical_stopped and is_horizontal_stopped and self.super_armor_timer <= 0:
                self.into_down_state()


        # 若為 normal 狀態，逐步減少 hit count
        if self.hit_count > 0:
            self.hit_count -= self.recovery_rate
            if self.hit_count < 0:
                self.hit_count = 0

        return True

    def get_swing_attack_data(self, attacker):
        duration = 32
        if self.rigid_timer < 32:
            #return None
            duration = self.rigid_timer
        if duration <= 12:
            return None
        return AttackData(
            attack_type=AttackType.SWING,
            duration=duration,
            trigger_frame=12,
            recovery=16,
            hitbox_func=swing_hitbox_func,
            damage=lambda _: self.swing_damage if hasattr(self, 'swing_damage') else 11,
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
            trigger_frame=1,
            recovery=16,
            hitbox_func=item_hitbox,
            effects=[AttackEffect.SHORT_STUN],
            damage=lambda _: self.throw_damage if hasattr(self, 'throw_damage') else 7,
            knock_back_power=[0.6,0.2],
            frame_map = [0] * 1 + [1] * (duration - 1),  # 必須與duration等長
            frame_map_ratio = [1, duration-1]
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
        if AttackEffect.FORCE_WEAK in effects and self.combat_state not in [CombatState.WEAK, CombatState.DOWN, CombatState.DEAD]:
            self.into_weak_state()
        else:
            # 普通攻擊後的邏輯
            #print(f'{self.name} CombatState {self.combat_state.name}')
            if self.combat_state == CombatState.NORMAL:
                self.hit_count += attack_data.get_damage()
                if self.hit_count >= self.max_hits_before_weak:
                    self.into_weak_state()
            elif self.combat_state == CombatState.WEAK:
                #weak中強制所有技能擊倒
                if attack_data.knock_back_power[0] <= 0 and attack_data.knock_back_power[1] <= 0 and self.scene.env_manager.freeze_timer <= 0:
                    self.into_down_state()
            elif self.combat_state == CombatState.DOWN:
                #倒地被追加時避免連段到死,給予霸體
                self.super_armor_timer = self.rigid_timer

    def apply_attack_effects(self, attacker, attack_data):
        if self.is_invincible() or self.is_super_armor():
            #無敵或鋼體時不接受特殊狀態
            return
        #處理攻擊特效
        effects = attack_data.effects
        # 其他特效依照 enum 加入即可
        # if AttackEffect.FORCE_DOWN in effects:
        #     self.into_down_state()
        if AttackEffect.FORCE_WEAK in effects and self.combat_state not in [CombatState.WEAK, CombatState.DOWN, CombatState.KNOCKBACK, CombatState.DEAD]:
            self.into_weak_state()

        #擊退處理
        #physics_scale = 0.2
        min_knockback_threshold = (getattr(self, 'weight', 1.0))*0.4
        power_x, power_z = attack_data.knock_back_power
        # power_x*= physics_scale
        # power_z*= physics_scale
        #print(f'{self.name} 受到 {attack_data.attack_type}攻擊! min_kb={min_knockback_threshold}, power = ({power_x:.3f}, {power_z:.3f}) {(self.combat_state != CombatState.DOWN and self.health > 0)}')
        #if (power_x > min_knockback_threshold or abs(power_z) > min_knockback_threshold) and not (self.combat_state != CombatState.DOWN and self.health > 0):
        if (power_x > min_knockback_threshold or abs(power_z) > min_knockback_threshold) and not (self.combat_state == CombatState.DOWN and self.health > 0):
            #倒地狀態下不擊退
            self.into_knockback_state()
            resistance = 1.0 + (getattr(self, 'weight', 0.15) * 5)
            #knock_back_power[0]水平 [1]垂直
            if power_x > 0:
                direction = self.get_knock_direction(attacker, attack_data)
                added_vx = (direction * power_x) / resistance
                current_speed_ratio = abs(self.vel_x) / MAX_REASONABLE_VEL
                scaling_factor = max(0.2, 1.0 - current_speed_ratio)  # 最少保留 20% 的衝擊力
                self.vel_x += added_vx * scaling_factor
            if power_z > 0:
                added_vz = power_z / resistance
                # vz 同理，防止向上飛到看不見
                current_vz_ratio = abs(self.vz) / MAX_REASONABLE_VEL
                scaling_factor_z = max(0.2, 1.0 - current_vz_ratio)
                self.vz += added_vz * scaling_factor_z
                # 🔴 重要修正：不要 += jump_z
                # jump_z 代表位置，累加會導致「瞬間傳送」
                # 只要確保第一擊讓他在空中即可 (0.1~0.2)
                if self.jump_z == 0:
                    self.jump_z = 0.2
            else:
                self.vz += power_z/resistance

        if AttackEffect.SHORT_STUN in effects:
            self.set_rigid(ON_HIT_SHORT_STUN_TIME)
            self.on_hit_timer = ON_HIT_SHORT_STUN_TIME
        if AttackEffect.BURN in effects:
            #print(f'{self.name} burning!!!!  burning!!!! burning!!!')
            self.get_burning = True

    def take_damage(self, attacker, attack_data, manual_damage=None):
        #damage = getattr(attack_data, 'damage', 5)
        if attacker:
            damage = attack_data.get_damage(attacker)
            print(f'{self.name}受到{attacker.name}的{attack_data.attack_type.name} {damage}點傷害')
        else:
            damage = attack_data.damage
        # 優先使用動能計算出的傷害
        damage = manual_damage if manual_damage is not None else attack_data.get_damage(attacker)
        #根據敵我進行傷害加成
        self.health -= damage
        # 顯示傷害數字
        if self.scene:
            font_size = 24
            if damage >= 100:
                font_size = 48
            self.scene.add_floating_text(self.x + self.width / 2, self.y + self.height, f"-{damage}", self.map_h, color=(255, 0, 0), font_size=font_size)
        return f'{self.name} 受到 {damage}, 剩餘HP: {self.health}', damage

    def _on_hit(self, attacker, attack_data):
        # 無敵檢查
        if attacker:
            attack_name = attacker.name
        else:
            attack_name = "環境物件"
        st = f'{attack_name} 的 {attack_data.attack_type.name} 命中 {self.name} '

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

        if attacker and attacker.attack_state:
            #attacker.attack_state.has_hit = True
            attacker.attack_state.has_hit.append(self)

        #格擋判定
        can_guard = (self.attack_state and not self.is_invincible()
                     and not self.is_super_armor() and self.facing != attacker.facing
                     and self.attack_state.data.guardable)
        if can_guard:
            if not self.attack_state.should_trigger_hit() and self.attack_state.frame_index < ON_GUARD_MAX_WINDOW:
                #前搖狀態中才能格擋
                basic_guard_rate = 1.0 if self.name == 'player' else self.morale
                bonus_rate = 0.2 if self.personality == 'cautious' else 0.0
                if random.random() < (basic_guard_rate + bonus_rate):
                    self.trigger_guard_success(attacker, attack_data)
                    print(f'{self.name} 成功招架')
                    return

        damage_st, damage = self.take_damage(attacker, attack_data)
        #士氣系統調整
        morale_decay = (damage/self.max_hp)
        if self.personality == 'brave':
            morale_decay /= 2
        elif self.personality == 'coward':
            morale_decay *= 1.3
        self.morale -= morale_decay

        # --- 舊系統計算 (維持現狀) ---
        old_damage = attack_data.damage
        old_vx, old_vz = attack_data.knock_back_power
        # --- 🟢 新動能傳導系統計算 (影子計算) ---
        # 這是修正 TypeError 的核心：判斷是否為公式
        if callable(attack_data.power):
            raw_power = attack_data.power(attacker)
        else:
            raw_power = attack_data.power
        # 1. 能量拆分
        kinetic_damage = raw_power * attack_data.absorption
        residual_energy = raw_power * (1 - attack_data.absorption)
        # 2. 考慮質量的物理阻力 (假設 self.weight 在 Entity 定義)
        # 阻力公式可依手感調整：a = F/m
        resistance = 1.0 + (self.weight * 5.0)
        impulse = residual_energy / resistance
        # 3. 角度分解 (將角度轉為弧度)

        rad = math.radians(attack_data.impact_angle)
        # 這裡的 direction 是根據攻擊者位置判斷 (1 或 -1)
        dir_x = 1 if (attacker and attacker.x < self.x) else -1
        new_vx = impulse * math.cos(rad) * dir_x
        new_vz = impulse * math.sin(rad)
        # 4. Debug 觀察 (清醒腦袋的關鍵：比對數據)
        if True:
            print(f"--- Kinetic Check: {attack_data.attack_type.name} ---")
            print(f"Dmg:{old_damage}->{int(kinetic_damage)}(Pow{raw_power}), V:[{old_vx}, {old_vz}]->[{new_vx:.2f}, {new_vz:.2f}]")

        # --- 暫時執行舊系統，確保遊戲不崩潰 ---
        # self.take_damage(attacker, attack_data)
        # self.into_knockback_state(old_vx, old_vz)

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
        if attacker and attacker.get_hitbox():
            hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
            self.scene.create_effect(hit_x, hit_y, hit_z,'hit')

        if attack_data.hit_stop_frames > 0:
            if self.scene:
                self.scene.trigger_hit_stop(attack_data.hit_stop_frames)
                # 選配：配合微小的震動效果更好
                self.scene.trigger_shake(duration=attack_data.hit_stop_frames, intensity=3)
                flip = True if attacker and attacker.x < self.x else False
                if attacker:
                    print(f'{self.name} 發動 hitstop! attacker是{attacker.name}, flip={flip}')
                hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
                self.scene.create_effect(hit_x, hit_y, hit_z, "hitstop", flip=flip)

    def on_hit(self, *args):
        return self.on_hit_by_power(*args)
        #return self._on_hit(*args)

    def on_hit_by_power(self, attacker, attack_data):
        # --- 1. 基礎防護檢查 (無敵與鋼體) ---
        if attacker:
            attack_name = attacker.name
        else:
            attack_name = "環境物件"

        # 無敵檢查
        if self.is_invincible() and AttackEffect.IGNORE_INVINCIBLE not in attack_data.effects:
            return

        # 鋼體日誌 (鋼體不跳過傷害，但通常會配合減少受擊硬直，這裡先保留邏輯)
        if self.super_armor_timer > 0:
            print(f"[{self.name}] 鋼體作用中，無視受擊硬直")

        # --- 2. 🟢 格擋系統 (Guard) 整合 ---
        # 判斷條件：有攻擊狀態、非無敵/鋼體、且面向與攻擊者相反
        can_guard = (self.unit_type not in ['item'] and
                     self.attack_state and not self.is_invincible()
                     and self.super_armor_timer <= 0 and attacker
                     and self.facing != attacker.facing
                     and self.attack_state.data.guardable)

        if can_guard:
            # 前搖狀態中 (frame_index 較小) 才能觸發格擋
            if not self.attack_state.should_trigger_hit() and self.attack_state.frame_index < ON_GUARD_MAX_WINDOW:
                basic_guard_rate = 1.0 if self.name == 'player' else getattr(self, 'morale', 0.5)
                bonus_rate = 0.2 if getattr(self, 'personality', '') == 'cautious' else 0.0

                if random.random() < (basic_guard_rate + bonus_rate):
                    self.trigger_guard_success(attacker, attack_data)
                    print(f'{self.name} 成功招架了來自 {attack_name} 的攻擊')
                    return  # 🔴 格擋成功，直接攔截，不計算後續傷害與動能

        # --- 3. 命中基本狀態設定 ---
        self.hit = True
        self.hit_timer = 20
        if attacker and attacker.attack_state:
            attacker.attack_state.has_hit.append(self)

        # --- 4. 🟢 動能傳導核心結算 ---
        # 取得 Power (支援 callable 公式)
        if callable(attack_data.power):
            raw_power = attack_data.power(attacker)
        else:
            raw_power = attack_data.power

        # A. 傷害結算 (做功 x 吸收率)
        final_damage = int(raw_power * attack_data.absorption)
        _, damage = self.take_damage(attacker, attack_data, manual_damage=final_damage)

        # B. 士氣系統調整 (根據傷害比例扣除)
        morale_decay = (damage / max(1, self.max_hp))
        pers = getattr(self, 'personality', 'normal')
        if pers == 'brave':
            morale_decay /= 2
        elif pers == 'coward':
            morale_decay *= 1.3
        if hasattr(self, 'morale'):
            self.morale -= morale_decay

        # C. 位移結算 (殘餘能量 / 阻力)
        residual_energy = raw_power * (1 - attack_data.absorption)

        # 🟢 修正：引入「啟動門檻」與「動量轉換率」
        # 只有當殘餘能量超過 (重量 * 係數) 時才產生擊飛，解決低重力下的飄移問題
        KB_THRESHOLD = self.weight * 5.0
        KINETIC_CONVERSION_RATE = 0.1  # 100 Power 產生 10 單位速度

        new_vx, new_vz = 0, 0

        if residual_energy > KB_THRESHOLD:
            resistance = max(0.2, self.weight)
            impulse = (residual_energy * KINETIC_CONVERSION_RATE) / resistance

            # 角度分解

            rad = math.radians(attack_data.impact_angle)
            dir_x = self.get_knock_direction(attacker, attack_data)

            new_vx = impulse * math.cos(rad) * dir_x
            new_vz = impulse * math.sin(rad)

            print(
                f'{attack_data.attack_type}: Pwr:{raw_power} -> Dmg:{final_damage} Imp:{impulse:.2f} V:({new_vx:.2f},{new_vz:.2f})')

        # --- 5. 狀態套用與物理緩衝 ---
        if self.combat_state != CombatState.DEAD:
            self.resolve_combat_state_on_hit(attack_data)
            # 如果有動量產出，套用效果 (例如擊飛動畫)
            self.apply_attack_effects(attacker, attack_data)
            # 注意：此處應確保 apply_attack_effects 會處理 new_vx/new_vz 或呼叫 into_knockback

        # --- 6. 清理與持物掉落 ---
        if self.attack_state:
            # 鋼體不中斷攻擊狀態
            if self.super_armor_timer <= 0:
                self.attack_state = None
                self.state = MoveState.STAND

        # 處理持有物掉落
        if hasattr(self, "held_object") and self.held_object:
            self.held_object.held_by = None
            self.held_object = None

        self.on_hit_count += 1

        # --- 7. 特效與 HitStop ---
        if attacker and attacker.get_hitbox():
            hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
            self.scene.create_effect(hit_x, hit_y, hit_z, 'hit')

            if attack_data.hit_stop_frames > 0:
                self.scene.trigger_hit_stop(attack_data.hit_stop_frames)
                self.scene.trigger_shake(duration=attack_data.hit_stop_frames, intensity=3)

                # 視覺化 Hitstop
                flip = True if attacker.x < self.x else False
                self.scene.create_effect(hit_x, hit_y, hit_z, "hitstop", flip=flip)
    # def on_hit_by_power(self, attacker, attack_data):
    #     # --- 1. 基礎防護檢查 ---
    #     if self.is_invincible() and AttackEffect.IGNORE_INVINCIBLE not in attack_data.effects:
    #         return
    #     if self.super_armor_timer > 0:
    #         pass  # 鋼體僅不跳動畫，傷害照吃
    #
    #     self.hit = True
    #     self.hit_timer = 20
    #     if attacker and attacker.attack_state:
    #         attacker.attack_state.has_hit.append(self)
    #
    #     # --- 2. 🟢 動能傳導核心結算 ---
    #     # 取得 Power (支援 callable 公式)
    #     if callable(attack_data.power):
    #         raw_power = attack_data.power(attacker)
    #     else:
    #         raw_power = attack_data.power
    #
    #     # A. 傷害結算 (做功 x 吸收率)
    #     final_damage = int(raw_power * attack_data.absorption)
    #     _, damage = self.take_damage(attacker, attack_data, manual_damage=final_damage)
    #
    #     # B. 位移結算 (殘餘能量 / 體重)
    #     residual_energy = raw_power * (1 - attack_data.absorption)
    #     # 🟢 修正 1：引入一個「動量轉換率」常數 (例如 0.2 ~ 0.3)
    #     # 這樣 100 Power 的招式才不會產生 100 速度
    #     KINETIC_CONVERSION_RATE = 0.1
    #
    #     # 🟢 修正 2：加強重量的影響力 (平方或加乘)
    #     resistance = max(0.2, self.weight)
    #     impulse = (residual_energy * KINETIC_CONVERSION_RATE) / resistance
    #
    #     # C. 角度分解
    #     import math
    #     rad = math.radians(attack_data.impact_angle)
    #     dir_x = self.get_knock_direction(attacker, attack_data)
    #
    #     new_vx = impulse * math.cos(rad) * dir_x
    #     new_vz = impulse * math.sin(rad)
    #
    #     print(f'{attack_data.attack_type}: {attack_data.damage}->{final_damage:.3f} impulse{impulse:.3f} ({new_vx:.3f},{new_vz:.3f})')
    #
    #     # --- 3. 狀態套用與物理緩衝 ---
    #     if self.combat_state != CombatState.DEAD:
    #         self.resolve_combat_state_on_hit(attack_data)
    #         # 這裡套用重構後的狀態鎖
    #         #self.into_knockback_state(new_vx, new_vz)
    #         self.apply_attack_effects(attacker, attack_data)
    #
    #
    #     # --- 4. 清理與特效 ---
    #     if self.attack_state:
    #         self.attack_state = None
    #         self.state = MoveState.STAND
    #     self.on_hit_count += 1
    #
    #     # 產生打擊火花與 HitStop
    #     if attacker and attacker.get_hitbox():
    #         hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
    #         self.scene.create_effect(hit_x, hit_y, hit_z, 'hit')
    #         if attack_data.hit_stop_frames > 0:
    #             self.scene.trigger_hit_stop(attack_data.hit_stop_frames)
    def update(self):
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
            self.combat_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # 每禎遞減攻擊計時器
        #死亡消失
        if self.health <= 0 and self.combat_state not in [CombatState.KNOCKBACK] and self.death_knockback == False and self.vel_x <= 0 and abs(self.vz) <= 0:
            #只有本身沒有被動位移者會強加一個小的擊退
            if self.facing == DirState.LEFT:
                vel_x = 0.1
            else:
                vel_x = -0.1
            vz = 0.1
            self.jump_z = 0.1
            #self.combat_state = CombatState.KNOCKBACK
            self.into_knockback_state(vel_x, vz)
            self.death_knockback = True

        # if self.health <= 0 and self.combat_state not in [CombatState.DEAD]:
        #     if not self.is_knockbacking() and self.jump_z <= 0:
        #         self.into_dead_state()
        if self.health <= 0:
            if not self.is_knockbacking() and self.jump_z <= 0:
                if self.combat_state != CombatState.DEAD and self.scene.env_manager.freeze_timer <= 0:
                    #時停中也不改變狀態
                    self.into_dead_state()
            else:
                # 如果還在飛，強制維持 KNOCKBACK 狀態以播放旋轉動畫
                #self.combat_state = CombatState.KNOCKBACK
                self.into_knockback_state()

        if self.combat_state == CombatState.DEAD:
            self.dead_timer -=1
            #print(f'{self.name} dead state discount {self.dead_timer}')
            if self.dead_timer <= 0:
                print(f'{self.name} 消失')
                if self.money > 0:
                    loot = self.drop_loot()
                    if loot:
                        print('{} 掉落 {} 的 {}'.format(self.name, loot['type'], loot['value']))

                if self.scene:
                    #self.scene.unregister_unit(self)
                    self.scene.mark_for_removal(self)

        if self.attack_state:
            self.attack_state.update()

        if (self.is_super_armor() or self.is_invincible()) and not self.get_component("status_aura"):
            from Component import StatusAuraComponent
            self.add_component("status_aura", StatusAuraComponent())
        # 更新動畫 frame（每隔 anim_speed frame 換一次圖）
        self.anim_timer += 1
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.anim_frame += 1
        if self.state in [MoveState.WALK, MoveState.RUN]:
            self.anim_walk_cnt += 1

        # 🟢 新增：如果被玩家抓起來（例如作為投擲道具）
        if self.held_by:
            self.on_held_location()  # 執行座標同步
            return  # 被抓取時，跳過 AI 與自主移動邏輯
        # 🟢 重要：如果已經落地且速度歸零，但 flying 還是 True，強行修正
        if self.jump_z <= 0 and abs(self.vel_x) < 0.05 and self.is_thrown:
            self.is_thrown = False





    def update_common_interactable_unit(self, unit):
        return
        #還沒實作
    # def update_common_opponent(self, opponent=None):
    #     #受創狀態判定
    #     self.update_combat_state()
    #     self.update_hit_timer()
    #
    #     #123456
    #     if self.attack_state:
    #         #print(f'update_common_opponent: [({self.current_frame}){self.attack_state.timer}] self.attack_state={self.attack_state} ({self.x:.2f}, {self.y:.2f})')
    #         # self.attack_state.update()
    #         #attack_state的timer update只能進行一次! 必須在外面
    #         if self.attack_state and not self.attack_state.is_active():
    #             #suspend(f'{self.attack_state.data.attack_type.name}收招')
    #             self.set_rigid(self.attack_state.data.recovery)
    #             self.attack_state = None
    #             self.state = MoveState.STAND
    #             self.mode = MoveState.STAND
    #
    #     #命中計時器
    #     if opponent and opponent.attack_state and opponent.attack_state.should_trigger_hit():
    #         if is_box_overlap(opponent.get_hitbox(), self.get_hurtbox()):
    #             if self not in opponent.attack_state.has_hit:
    #                 # hit_x, hit_y, hit_z = get_overlap_center(opponent.get_hitbox(), self.get_hurtbox())
    #                 if self.held_by is None:
    #                     #避免打到自己
    #                     self.on_hit(opponent, opponent.attack_state.data)
    #
    #     # 若正在攻擊期間
    #     #
    #     if self.attack_state:
    #         if self.is_jump():
    #             # 空中攻擊時允許 X 軸移動與跳躍物理
    #             dx = self.last_intent.get('dx')*0.1
    #             new_x = self.x + dx
    #             #限制邊界
    #             self.x = max(0, min(new_x, self.map_w - self.width))
    #         return False
    #     else:
    #         return True
    # Characters.py

    def update_common_opponent(self, opponent=None):
        """
        重構後的保險版本：
        不再主動偵測 opponent 的 hitbox，
        只負責處理『自身』的戰鬥狀態更新與收招邏輯。
        """
        # 1. 更新受創計時與 combat 狀態 (這必須保留，否則不會醒來)
        self.update_combat_state()
        self.update_hit_timer()

        # 2. 處理攻擊結束後的收招 (這必須保留，否則會卡在攻擊動作)
        if self.attack_state:
            if not self.attack_state.is_active():
                # 攻擊結束，進入收招硬直
                self.set_rigid(self.attack_state.data.recovery)
                self.attack_state = None
                self.state = MoveState.STAND
                self.mode = MoveState.STAND

        # ---------------------------------------------------------
        # 🔴 原本這裡有一大段 is_box_overlap 的代碼，現在可以放心地註解掉或刪除
        # 因為 SceneManager.resolve_all_collisions 已經幫我們做完了。
        # ---------------------------------------------------------

        # 3. 處理攻擊期間的特殊物理 (這必須保留，影響手感)
        if self.attack_state:
            if self.is_jump():
                # 空中攻擊時允許微量 X 軸移動 (10% 慣性)
                dx = self.last_intent.get('dx', 0) * 0.1
                new_x = self.x + dx
                self.x = max(0, min(new_x, self.map_w - self.width))
            return False  # 告訴外部：我正在忙 (攻擊中)

        return True  # 告訴外部：我可以自由行動
    def draw_hit_box(self, win, cam_x, cam_y, tile_offset_y, color, terrain_z_offset=0):
        #符合條件的才畫
        if self.attack_state and (self.attack_state.should_trigger_hit() or len(self.attack_state.has_hit) > 0):
            hitbox = self.get_hitbox()
            if not hitbox:
                return
            hx = int(hitbox['x1'] * TILE_SIZE) - cam_x
            hy = int((self.map_h - hitbox['y2']) * TILE_SIZE - self.jump_z * TILE_SIZE - terrain_z_offset) - cam_y + tile_offset_y
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
        if self.attack_state and self.attack_state.data.attack_type not in CONTEXTUAL_ATTACK:
            xy_hitbox =self.attack_state.get_hitbox(self.x+self.width/2, self.y, self.facing, self)
            #print(f'self.z={self.z}, self.jump_z={self.jump_z}')
            xy_hitbox['z1'] = self.z+self.jump_z
            xy_hitbox['z2'] = self.z+self.jump_z+self.height
            xy_hitbox['z_abs'] = self.z+self.jump_z
            if self.attack_state.is_fly_attack:
                # 取得當前絕對高度
                abs_z = self.get_abs_z()
                # 讓判定範圍從腳底下方 1.0 單位到頭頂
                # 這樣只有當你跳得夠低、或是敵人在你下方合理距離時才會中
                xy_hitbox['z1'] = abs_z - 1.0
                xy_hitbox['z2'] = abs_z + self.height
                xy_hitbox['z_abs'] = abs_z  # 物理引擎改回讀取目前的實際高度
                #print(f'{self.name}: xy_hitbox_z=[{abs_z-1.0}, {abs_z+self.height}], z_abs={abs_z}')
            return xy_hitbox
            #return self.attack_state.get_hitbox(self.x+self.width/2, self.y, self.facing)

        return None
    def get_hurtbox(self):
        return self.get_physics_box()

    def get_interact_box(self):
        #物件互動使用(非傷害)
        return self.get_physics_box()

    def stop_print_info(self):
        st = f'{self.name} ({self.x}, {self.y}, {self.z}) JUMP {self.jump_z}\n'
        st = st + f'move_state [{self.state.name}] combat_state [{self.combat_state.name}] attack_state'

        if self.attack_state:
            st = st + f'[{attack_state.data.attack_type.name}]'
        else:
            st = st + 'None '
        st = st + f'\nFlags: is_knockbacking[{self.is_knockbacking()}] is_falling[{self.is_falling()}] is_locked[{self.is_locked()}] is_thrown[{self.is_thrown}]'
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
        if self.is_thrown:
            return



        if not block_movement:
            #攻擊中限制移動
            self.last_intent = intent
            if intent['direction'] in [DirState.LEFT, DirState.RIGHT]:
                self.facing = intent['direction']
            #初始狀態: 站
            self.state = MoveState.STAND
            dx, dy = intent['dx'], intent['dy']
            # if intent['jump']:
            #     print(f'jump param: jump_z {self.jump_z}, jumpping_flag {self.jumpping_flag}')
            if intent['jump'] and self.jump_z == 0 and not self.jumpping_flag:

                if intent['horizontal'] == MoveState.RUN:
                    self.high_jump = True
                # 🟢 修正：跳躍力從 1.4/1.8 提升至 8.0/10.0 左右
                self.vz = 0.4 if intent['horizontal'] == MoveState.RUN else 0.3
                self.jump_z = 0.2  # 起跳高度也稍微拉高一點，避免瞬間 LANDING
                self.jumpping_flag = True

            move_rate = 0.4 if intent['horizontal'] == MoveState.RUN else 0.2
            new_x = self.x + dx * move_rate
            new_y = self.y + dy * move_rate
            #掉落檢查
            if self.check_and_trigger_fall(dx, dy, move_rate):
                return
            # 🟢 修正 1：強制限制 new_y 範圍，避免索引越界
            new_y = max(0, min(new_y, self.map_h - self.height * 0.1 - 0.1))
            new_x = max(0, min(new_x, self.map_w - self.width))

            prev_x, prev_y = self.x, self.y
            foot_x = new_x + self.width / 2
            foot_y = new_y + self.height * 0.1
            nx, ny = int(foot_x), int(foot_y)
            target_z = self.get_tile_z(nx, ny)
            # --- 防呆攔截點 ---
            if target_z is not None:
                # 這裡也要確保 z 軸差距判定後才更新
                if abs(target_z - self.z) <= 1 or (self.jump_z > 0 and self.z + self.jump_z >= target_z):
                    # 2. 新增: is_blocking物件阻擋檢查
                    if self.scene:
                        others = self.scene.get_all_units()
                        for other in others:
                            if other != self and getattr(other, 'is_blocking', False) and other.side!=self.side and other.combat_state not in [CombatState.DOWN, CombatState.DEAD, CombatState.KNOCKBACK]:
                                # 判斷兩者在物理空間（包含 Z 軸高度）是否重疊
                                #print(f"{other.name} 我能撞人")
                                if is_box_overlap(self.get_feet_box(), other.get_feet_box()):
                                    #print('撞到了撞到了撞到了撞到了撞到了撞到了撞到了')
                                    # 分別檢查 X 與 Y 軸，是否正在「惡化」重疊情況
                                    current_dist_x = abs(self.x - other.x)
                                    new_dist_x = abs(new_x - other.x)
                                    current_dist_y = abs(self.y - other.y)
                                    new_dist_y = abs(new_y - other.y)
                                    # 如果新的 X 座標讓距離變短，則鎖定 X 軸
                                    if new_dist_x < current_dist_x:
                                        new_x = self.x-dx * move_rate
                                    # 如果新的 Y 座標讓距離變短，則鎖定 Y 軸
                                    if new_dist_y < current_dist_y:
                                        new_y = self.y-dy*move_rate
                    new_x = max(self.width/2, min(self.map_w-self.width/2, new_x))
                    new_y = max(self.width / 2, min(self.map_h - self.width / 2, new_y))

                    self.x, self.y = new_x, new_y  # 現在 new_y 已經安全了
                    self.z = self.get_tile_z(self.x, self.y)


            # if target_z is None:
            #     # 如果目標位置超出地圖，不更新座標 (或是執行擋牆邏輯)
            #     moved = False
            # else:
            #     if abs(target_z - self.z) <= 1 or (self.jump_z > 0 and self.z + self.jump_z >= target_z):
            #         self.x, self.y = new_x, new_y
            #         if self.jump_z > 0:
            #             self.z = target_z
            #         else:
            #             self.z = target_z

            moved = (self.x != prev_x or self.y != prev_y)
            if moved and not self.is_falling():
                self.state = intent['horizontal'] if intent['horizontal'] in [MoveState.WALK, MoveState.RUN,
                                                                              MoveState.STEP] else MoveState.WALK

#定義了AttackType.DOWN_STOMP, 但還沒實作down_attack功能
        intent_act = intent.get('action')
        if intent_act == 'pickup_item':
            # 這裡必須確保有呼叫 try_pickup，而不是只傳給 attack()
            hold_comp = self.get_component("holdable")
            if hold_comp:
                hold_comp.try_pickup()  # 這才會正確執行 held_by 連結與座標對齊
            self.attack_intent = None
            self.clean_input_buffer()
        #elif intent_act == 'down_attack':
        elif intent_act is not None:
            print('{} 出招 {}'.format(self.name, intent['action']))
            self.attack(intent_act)
            self.attack_intent = None
        # if intent_act == 'pickup_item':
        #     for comp in self.components.values():
        #         if hasattr(comp, "handle_action"):
        #             comp.handle_action('pickup_item')
        #             self.attack_intent = None
        #             self.clean_input_buffer()
        # elif intent_act is not None:
        #     #打出對應招式
        #     print('{} 出招 {}'.format(self.name, intent['action']))
        #     self.attack(intent['action'])
        #     if hasattr(self.attack_state, "data"):
        #         print(f'[{self.current_frame}]{self.name}打出{self.attack_state.data.attack_type.name}')
        #     self.attack_intent = None  # ✅ 清除

    def set_attack_by_skill(self, skill):
        # 1. 取得原始模板數據
        base_data = attack_data_dict.get(skill)
        if not base_data or not base_data.can_use(self):
            return

        # 2. 數據合併：建立一個本次攻擊專用的 atk_data
        # 我們不修改全域字典，而是建立一個屬性完全相同的複製品
        import copy
        atk_data = copy.copy(base_data)
        # 3. 套用角色/技能特定覆蓋 (例如：靈氣圖、特效配置)
        custom_override = self.skill_overrides.get(skill)
        if custom_override:
            # 將 custom_override 字典中的內容，直接更新到 atk_data 的屬性中
            for key, value in custom_override.items():
                if hasattr(atk_data, key):
                    setattr(atk_data, key, value)

        # 4. 套用組件/道具動態修正 (例如：裝備增加 20% 傷害)
        # 這裡實作您擔心的擴充性：遍歷所有組件來修改這個臨時的 atk_data
        for comp in self.components.values():
            if hasattr(comp, "modify_attack_data"):
                ori_damage = atk_data.get_damage()
                comp.modify_attack_data(atk_data)
                new_damage = atk_data.get_damage()
                print(f'modified {atk_data.attack_type.name}: damage {ori_damage}->{new_damage}')

        if atk_data is not None:
            if atk_data.can_use(self):
                custom_config = self.skill_overrides.get(skill)
                # 🟢 關鍵：在真正建立 AttackState 並切換 state 後執行
                success = False

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
                # --- 修正：套用特效組件邏輯 ---
                if atk_data and atk_data.effect_component_config:
                    self.apply_skill_effect_components(atk_data)
                if atk_data and atk_data.physical_change is not None:
                    for attr_name, value in atk_data.physical_change.items():
                        print(f"[set_attack_by_skill] 角色 {self.name} 套用 {attr_name} = {value}")
                        ori_val = getattr(self, attr_name)
                        if attr_name == 'vel_x' and self.facing == DirState.LEFT:
                            value = -1.0*value
                        new_val = ori_val + value
                        setattr(self, attr_name, new_val)


    def draw_hp_bar(self, win, px, py):
        # 若死亡則不顯示血條
        if self.combat_state == CombatState.DEAD:
            return

        bar_width = int(self.width * TILE_SIZE)
        bar_height = 4
        # --- 關鍵修正：py 是腳底，要減去身高 ---
        char_visual_height = int(self.height * TILE_SIZE)
        bar_y = py - char_visual_height - 18  # 放在比 combat bar 更高一點的地方
        # 🟥 計算比例（最大值避免為 0）
        max_hp = max(getattr(self, "max_hp", 100), 1)
        hp_ratio = self.health / max_hp

        # 修正繪製 X 座標，px 是中心點
        draw_x = px - bar_width // 2
        pygame.draw.rect(win, (50, 0, 0), (draw_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(win, (200, 0, 0), (draw_x, bar_y, int(bar_width * hp_ratio), bar_height))
        pygame.draw.rect(win, (255, 200, 200), (draw_x, bar_y, bar_width, bar_height), 1)

    def create_flying_object(self, item_to_create='fireball'):
        from Items import Fireball, Bullet, Feather
        rebuild_map_info = [self.terrain, self.map_w, self.map_h]
        flying_object = None
        create_func = None
        if item_to_create == 'fireball':
            create_func = Fireball
        elif item_to_create == 'bullet':
            create_func = Bullet
        elif item_to_create == 'feather':
            create_func = Feather
        if create_func:
            flying_object = create_func(self.x, self.y, rebuild_map_info, owner=self)
            flying_object.scene = self.scene
            flying_object.jump_z = self.jump_z
            if item_to_create == 'fireball':
                flying_object.on_picked_up(self)
            self.scene.register_unit(flying_object, side=self.side, tags=['item', 'temp_object'], type='item')
        return flying_object
    def drop_loot(self):
        from Items import create_dropping_items  # 假設你有 Coin 類別
        #加入機率掉落
        import random
        if self.scene:
            prob = random.random()
            if prob > self.drop_mana_rate:
                create_dropping_items(self, 'potion', value =1)
                return {'type': 'MagicPotion', 'value': 1}
        #掉落硬幣
            gold = random.randint(5, 15)
            create_dropping_items(self, 'coin', value=gold)
            return {'type':'money', 'value':gold}
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
    def queue_command(self, cmd):
        """將指令塞入緩衝，這會在 handle_input 中被呼叫"""
        self.input_buffer = cmd
        self.input_buffer_timer = self.BUFFER_MAX_FRAMES

    def execute_command(self, cmd):
        if cmd == 'pickup_item' and not self.is_jump():
            self.get_component("holdable").try_pickup()
            self.clean_input_buffer()
            print('execute_command - pickup_item')
            self.attack_intent = None
            return
        """真正執行招式的入口，此時才判定人物狀態"""
        # 1. 處理移動/特殊指令
        if cmd == 'jump':
            if not self.is_jump:
                self.jump()
            return
        elif cmd == 'brust':
            self.attack(AttackType.BRUST)
            return

        # 🟢 修正：處理 down_attack 指令
        if cmd in CONTEXTUAL_ATTACK:
            #例如AttackType.DOWN_STOMP
            target = self.interaction_target
            if target:
                # 1. 自動對齊：讓玩家與敵人重疊（或稍微偏移）
                self.x = target.x
                self.y = target.y
                # 面向目標
                self.facing = DirState.LEFT if self.x > target.x else DirState.RIGHT

                # 2. 強制延長敵人的倒地時間，避免踩一半敵人站起來
                # 至少要讓敵人的倒地剩餘時間大於我的攻擊持續時間
                skill_duration = cmd.data.duration
                if target.combat_timer < skill_duration:  # 假設定義過
                    target.combat_timer = skill_duration  # 給予一個緩衝時間
                    if target.rigid_timer < skill_duration:
                        target.set_rigid(skill_duration)

                # 3. 正式發動攻擊
                self.attack(cmd)
                self.clean_input_buffer()
            return
        # 2. 處理攻擊指令：對齊你原有的 resolve_attack_table 邏輯
        # cmd 可能為 'z_attack', 'x_attack', 'c_attack'
        if cmd in self.attack_table:
            # 這裡呼叫你原有的函式來判斷目前是 default / run / high_jump
            # 確保緩衝出來的拳，會根據「執行那一刻」的速度或狀態來決定招式
            self.attack_intent = cmd
            print(f'cmd={cmd}')
            skill_data = self.resolve_attack_table()
            if skill_data and skill_data not in ['pickup_item']:
                self.attack(skill_data)


    def try_consume_buffer(self):
        """檢查當前狀態是否可以執行緩衝中的指令"""
        if not self.input_buffer: return False

        # 狀態判斷 A: 正常行動 (招式結束或 IDLE)
        #print(f'try_consume_buffer={self.input_buffer}')
        can_act = self.attack_state is None and self.combat_state == CombatState.NORMAL and not self.is_locked()
        # 狀態判斷 B: 受身系統 (在擊飛狀態快落地時按跳)
        is_tech_roll = (self.combat_state in [CombatState.KNOCKBACK, CombatState.DOWN] and
                        self.jump_z > 0.1 and self.input_buffer == 'jump')
        if can_act:
            cmd = self.input_buffer
            self.clean_input_buffer()
            self.execute_command(cmd)
            return True
        elif is_tech_roll:
            print(f"✨ {self.name} 受身成功！")
            self.into_normal_state()
            self.vz = 0.1  # 🚀 關鍵：給予向上的瞬時速度，造成「翻身跳」的效果
            #改由方向鍵控制方向
            self.vel_x = 0.3 if self.last_intent['direction'] == DirState.RIGHT else -0.3  # 稍微後跳拉開距離
            self.invincible_timer = 20
            return True
        return False

    def distance_to_target(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        return (dx ** 2 + dy ** 2) ** 0.5

    def ai_move_logic(self, target, intent, far_speed=0.5, near_speed=0.3):
        if self.attack_state or self.is_locked() or self.state == MoveState.ATTACK:
            return

        # 初始化必要的 AI 變數
        if not hasattr(self, 'ai_target_cache'): self.ai_target_cache = None
        if not hasattr(self, 'ai_recalc_timer'): self.ai_recalc_timer = 0

        p_dx = target.x - self.x
        p_dy = target.y - self.y
        dist_to_player = (p_dx ** 2 + p_dy ** 2) ** 0.5
        morale_factor = 1.0 if self.morale > 0.5 else 0.6

        # 始終看向玩家
        if abs(p_dx) > 0.01:
            intent['direction'] = DirState.RIGHT if p_dx > 0 else DirState.LEFT

        if self.side != 'player_side':
            has_token = self in self.scene.token_holders
        else:
            has_token = True
        self.ai_recalc_timer = max(0, self.ai_recalc_timer - 1)

        # 決定移動目標點
        if has_token:
            # 1. 有 Token：目的地指向 Player
            target_x, target_y = target.x, target.y
            #move_speed = far_speed * morale_factor
            move_speed = far_speed

            if dist_to_player < (self.width+target.width)/2: move_speed = 0  # 抵達出招距離
        else:
            # 2. 沒 Token：執行繞背路徑邏輯
            # 判斷是否需要重新計算目標 (冷卻結束 或 距離玩家過遠)
            need_recalc = (self.ai_recalc_timer <= 0) or (dist_to_player > 8.0) or self.last_intent is None

            if need_recalc:
                # 計算新目標點：環繞半徑 4.0 ~ 6.0
                orbit_radius = 4.5 if self.personality == 'brave' else 6.0
                # 50% 機率計算玩家背後，50% 玩家側面
                angle_offset = random.uniform(math.pi * 0.6,
                                              math.pi * 1.4) if random.random() < 0.5 else random.uniform(0.3, 1.2)
                base_angle = math.atan2(p_dy, p_dx)
                final_angle = base_angle + angle_offset

                self.ai_target_cache = (
                    target.x + math.cos(final_angle) * orbit_radius,
                    target.y + math.sin(final_angle) * orbit_radius
                )
                self.ai_recalc_timer = random.randint(240, 360)  # 1~2秒重新計算一次

            target_x, target_y = self.ai_target_cache
            move_speed = far_speed * 0.7 * morale_factor


        # 執行位移計算：向量一體化 (解決分開 dx/dy 的生硬感)
        mv_dx = target_x - self.x
        mv_dy = target_y - self.y
        move_dist = (mv_dx ** 2 + mv_dy ** 2) ** 0.5

        if move_dist > 0.1 and move_speed > 0:
            # 斜向移動直接線性插值
            norm_x = mv_dx / move_dist
            norm_y = mv_dy / move_dist

            # 🟢 新增：前方地形檢查 (段差偵測)
            check_x = self.x + norm_x * 0.5
            check_y = self.y + norm_y * 0.5
            front_z = self.get_tile_z(int(check_x), int(check_y))

            if front_z is not None:
                z_diff = front_z - self.z
                # 如果前方太高，且目標確實在那邊，觸發跳躍意圖
                if z_diff >= 1.0 and self.jump_z == 0:
                    intent['jump'] = True
                    # 給予額外的前衝力
                    move_speed *= 1.5

            # 如果沒 Token，疊加一個垂直於目標的微小向量來實現「弧形移動」感
            if not has_token:
                side_x, side_y = -norm_y, norm_x  # 取得法向量
                norm_x += side_x * 0.3
                norm_y += side_y * 0.3
                # 重新正規化
                new_dist = (norm_x ** 2 + norm_y ** 2) ** 0.5
                norm_x, norm_y = norm_x / new_dist, norm_y / new_dist

            intent['dx'] = norm_x * move_speed
            intent['dy'] = norm_y * move_speed
            intent['horizontal'] = MoveState.RUN if move_speed > 0.3 else MoveState.WALK
        else:
            intent['dx'], intent['dy'] = 0, 0
            intent['horizontal'] = MoveState.STAND

    def ai_attack_logic(self, target, intent, act='support'):
        attack_chance = self.aggressiveness
        if self.morale < 0.3:
            attack_chance *= 0.5
        dx = target.x - self.x
        dy = target.y - self.y
        dz = abs((target.z) - (self.z))
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if act == 'support':
            if dy < 0.5 and dz < 1.5 and unit.attack_cooldown <= 0:
                if dist > 1:
                    intent['action'] = AttackType.BULLET
                else:
                    intent['action'] = AttackType.SLASH
                self.attack_cooldown = self.attack_cooldown_duration
                self.facing = DirState.LEFT if dx < 0 else DirState.RIGHT
                self.attack_cooldown = self.attack_cooldown_duration
        else:
            if random.random() < attack_chance:
                if hasattr(self, "scale"):
                    attack_range = 2.5 * self.scale
                else:
                    attack_range = 2.5
                if dist <= attack_range and dz < 1.0:
                    #print(f'<<<<<dist = {dist}>>>>>>')
                    if self.attack_cooldown <= 0:
                        intent['action'] = self.combos[int(self.combo_count) % len(self.combos)]
                        self.combo_count += 1
                        self.attack_cooldown = self.attack_cooldown_duration
                        # unit.facing = DirState.LEFT if dx < 0 else DirState.RIGHT

    def ai_mental_logic(self, target):
        emotional_change = 0.05
        if self.personality:
            if self.personality == 'brave':
                # unit.morale = min(1.0, unit.morale + emotional_change*(unit.max_hp - unit.health)/unit.max_hp)
                self.aggressive = min(1.0, 0.5 + emotional_change * (self.max_hp - self.health) / self.max_hp)
                # 勇敢者血越少越進取
            elif self.personality == 'coward':
                self.aggresive = max(0.2, 0.5 - (self.max_hp - self.health) / self.max_hp)
                # 膽小者血越少越消極
            elif self.personality == 'cautious':
                self.aggresive = min(0.7, max(0.3, self.morale))

    # Characters.py

    def execute_backflip_shoot(self, speed_x=0.5):
        """由 AttackState 在特定影格調用"""
        # 1. 呼叫現有的飛行道具工廠
        feather = self.create_flying_object('feather')

        if feather:
            # 2. 設定子彈初速 (俯衝彈道)
            #print(f'backflip_shot_z = {bullet.z}')
            feather.vel_x = speed_x if self.facing == DirState.RIGHT else -speed_x
            feather.vz = 0.0

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
        self.skill_overrides = config.get("skill_overrides", {})
        self.config_backup = copy.copy(config)
        # self.attack_map = {
        #     "z_attack": lambda: AttackType.BASH if self.state == MoveState.RUN else AttackType.PUNCH,
        #     "x_attack": lambda: AttackType.KICK,
        #     "c_attack": lambda: AttackType.SLASH
        # }
        print('PLAYER config attack_table={}'.format(config.get("attack_table")))
        self.attack_table = config.get("attack_table") or {'z_attack':{'default': AttackType.PUNCH, 'run': AttackType.BASH, 'highjump_fall': AttackType.METEOFALL},
                             'x_attack':{'default': AttackType.KICK, 'jump': AttackType.FLY_KICK},
                             'c_attack':{'default': AttackType.SLASH, 'run': AttackType.FIREBALL},
                             'swing_item':{'default': AttackType.SWING},
                             'throw_item':{'default': AttackType.THROW,'jump':AttackType.THROW}}
        print('PLAYER config attack_table={}'.format(self.attack_table))

        self.animator = SpriteAnimator(image_path=config.get("image_path"), config_dict=config.get("animator_config"))  # 載入素材
        if config.get("stand"):
            self.stand_image = pygame.image.load(config.get("stand")).convert_alpha()
        self.super_move_animator = None
        if config.get("special_move"):
            super_move_anim = config.get("special_move")
            super_move_anim_path = super_move_anim.get('path', None)
            super_move_anim_frame_w = super_move_anim.get('width', None)
            super_move_anim_frame_h = super_move_anim.get('height', None)
            self.super_move_animator = SpriteAnimator(super_move_anim_path,
                                                      {"frame_width":super_move_anim_frame_w,
                                                       "frame_height":super_move_anim_frame_h, "anim_map":None})
        self.super_move_staging = config.get("super_move_staging")
        self.super_move_max_time = 0
        self.last_dir_input = [0,0,0,0]
        self.stand_config = config.get("stand_config", None)
        self.super_ability = config.get("super_ability", None)
        self.strength = config.get("strength", 10.0)
        self.unable_to_grab_item = config.get("unable_to_grab_item", False)


        #for dir in ['left', 'right', 'up', 'down']:
        for dir in DirState:
            self.key_down_frame[dir] = None
            self.last_step_frame[dir] = -9999

    def activate_stand(self):
        # 避免重複掛載
        if self.stand_config is None:
            return
        if self.get_component("ability_stand"):
            return
        self.add_component("ability_stand", StandComponent(self.stand_config, duration=900))
        # 之後在 update_components() 就會自動執行 StandComponent.update

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
            if attack_type in ['pickup_item']:
                self.clean_input_buffer()
                self.attack_intent = None

        jump_intent = None
        if self.jump_intent_trigger:
            #print(f'{self.name} jump!')
            jump_intent = True
            self.jump_intent_trigger = False

        zxc_buttons = [keys[pygame.K_z], keys[pygame.K_x], keys[pygame.K_c]]
        dx = dir_h*0.5
        #dy = dir_v * 0.5 if not self.is_jump() or self.is_falling() else dir_v * 0.2,
        if self.x+dx < 0 or self.x+dx+self.width >= self.map_w:
            dx = 0.0

        #按鍵快照
        up_pressed = keys[pygame.K_UP]
        down_pressed = keys[pygame.K_DOWN]
        left_pressed = keys[pygame.K_LEFT]
        right_pressed = keys[pygame.K_RIGHT]
        # 組合鍵快照 (Z, X, C)
        z_pressed = keys[pygame.K_z]
        x_pressed = keys[pygame.K_x]
        c_pressed = keys[pygame.K_c]
        return {
            'horizontal': horizontal,
            'direction': direction,
            "dx": dx,
            "dy": dir_v * 0.5 if not self.is_jump() or self.is_falling() else dir_v * 0.2,
            'jump': jump_intent,
            'action': attack_type,
            'buttons': (z_pressed, x_pressed, c_pressed),  # 方便解構
            'dirs': (up_pressed, down_pressed, left_pressed, right_pressed),  # 新增方向快照
            #'down_pressed': down_pressed, # <--- 新增
            'button_pressed': zxc_buttons
        }

    def on_key_down(self, key):
        if self.combat_state == CombatState.DOWN or self.combat_state == CombatState.WEAK:
            return  # 倒地或weak無法攻擊
        # 攻擊期間不接受其他輸入:取消攻擊
        # if self.state == MoveState.ATTACK:
        #     return
        # 將入隊邏輯移到這裡，這只會在按下的一瞬間觸發一次
        if key == pygame.K_z:
            self.queue_command('z_attack')
        elif key == pygame.K_x:
            self.queue_command('x_attack')
        elif key == pygame.K_c:
            self.queue_command('c_attack')
        elif key == pygame.K_SPACE and not self.is_jump():
            self.queue_command('jump')

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
            #self.set_rigid(atk_data.duration)
            self.rigid_timer = 0
            self.into_normal_state()
            if self.mp > 0:
                self.mp -= 1
            else:
                self.health -= min(20, self.health-1)
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
            if skill not in ['pickup_item']:
                self.set_attack_by_skill(skill)
                print(f'player set_attackc_by_skill {skill}')
                if skill in CONTEXTUAL_ATTACK and self.interact_target:
                    self.interact_target.take_contextual_attack(self.attack_state)


        if self.name == 'player' and attack_data_dict[skill].dialogue is not None:
            self.scene.say(self, attack_data_dict[skill].dialogue, duration=90)



    def handle_input(self, input_source):
        # --- 1. 檢查輸入鎖定 (防止連發) ---
        if getattr(self, 'input_lock_timer', 0) > 0:
            self.input_lock_timer -= 1
            # 在鎖定期間，我們仍需更新移動意圖，但不允許觸發新攻擊
            intent = self.input_intent(input_source) if not isinstance(input_source, dict) else input_source
            super().handle_input(intent)
            return


        is_ai = isinstance(input_source, dict)

        if is_ai:
            # AI 模式：從傳入的字典直接讀取布林值
            z = input_source.get('z', False)
            x = input_source.get('x', False)
            c = input_source.get('c', False)
            jump = input_source.get('jump', False)
            # 方向鍵模擬
            u, d, l, r = input_source.get('dirs', (False, False, False, False))
        else:
            # 玩家模式：讀取 pygame 按鍵物件
            z, x, c = input_source[pygame.K_z], input_source[pygame.K_x], input_source[pygame.K_c]
            jump = input_source[pygame.K_SPACE]
            u, d, l, r = input_source[pygame.K_UP], input_source[pygame.K_DOWN], input_source[pygame.K_LEFT], \
            input_source[pygame.K_RIGHT]

        # --- 後續邏輯統一使用變數 z, x, c, jump ---

        # # 1. 偵測按鍵
        # z = keys[pygame.K_z]
        # x = keys[pygame.K_x]
        # c = keys[pygame.K_c]
        # jump = keys[pygame.K_SPACE]
        # u = keys[pygame.K_UP]
        # d = keys[pygame.K_DOWN]
        # l = keys[pygame.K_LEFT]
        # r = keys[pygame.K_RIGHT]

        # 2. 優先判定 BRUST (組合鍵優先權最高，不進緩衝直接發動)
        if u and x and z:
            if self.super_ability:
                acts = self.super_ability.get("action", [])
                mp_cost = self.super_ability.get("mp", 11)
                print(f"mp:{self.mp} cost:{mp_cost}")
                serihu = self.super_ability.get('serihu', None)
                if serihu:
                    self.say(serihu)
                if self.mp >= mp_cost:
                    success = True
                    self.input_lock_timer = 15  # 鎖定 15 幀 (約 0.25秒)
                    for act in acts:
                        success = success & self.try_use_ability(act)
                    # if success:
                    #     self.mp -= mp_cost
                else:
                    self.say("mp不足...")
                return
        elif (z + x + c) >= 2:
            if self.attack_state is None:  # 只有非攻擊時能主動爆氣
                self.execute_command('brust')
                self.input_lock_timer = 15  # 鎖定 15 幀 (約 0.25秒)
                return  # 發動組合鍵後，不進行後續單鍵緩衝

        # 3. 單鍵緩衝判定 (若在硬直中按鍵，會被 queue 起來)
        if jump:
            self.queue_command('jump')


        # 生成移動意圖 (若是 AI，直接使用傳入的 intent)
        if is_ai:
            intent = input_source
        else:
            intent = self.input_intent(input_source)

        # 4. 嘗試消耗緩衝 (如果剛好是 IDLE 狀態，這一幀就會執行)
        did_action = self.try_consume_buffer()

        super().handle_input(intent)

        # 5. 處理移動意圖 (移動不緩衝，因為移動是持續性的)
        #intent = self.input_intent(keys)

        # 偵測方向是否有變化
        input_changed = []
        current_dir_input = [u, d, l, r]
        for lst, cur in zip(current_dir_input, self.last_dir_input):
            input_changed.append(1 if lst != cur else 0)
        dir_changed = False
        if (input_changed[0] > 0 and input_changed[1] > 0) or (input_changed[2] > 0 and input_changed[3] > 0):
            dir_changed = True

        self.last_dir_input = current_dir_input

        # 偵測是否有任何攻擊鍵按下 (z, x, c)
        any_button_pressed = any(intent.get('button_pressed', [False] * 3))

        if self.combat_state == CombatState.DOWN:
            #print(f"dir_changed={dir_changed}, any_button_pressed={any_button_pressed}")
            recovery_bonus = 0
            if dir_changed: recovery_bonus += 5  # 搖晃搖桿獎勵
            if any_button_pressed: recovery_bonus += 2  # 狂按按鈕獎勵
            self.is_mashing = True if recovery_bonus > 0 else False

            # 套用加速
            self.combat_timer -= recovery_bonus
            self.rigid_timer -= recovery_bonus

        # 2. 呼叫父類別處理一般攻擊與移動

        super().handle_input(intent)


    def handle_movement(self):
        # 實作完整的移動邏輯（左右移動、跑步、跳躍、判斷地板等）
        for dir in self.step_pending:
            if self.step_pending[dir] < self.current_frame:
                self.step_pending[dir] = -9999
        if self.is_falling():
            #self.jump_z += self.vz
            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()

        if self.jump_z != 0:
            self.state = MoveState.JUMP if self.vz > 0 else MoveState.FALL
            self.color = self.jump_color if self.vz > 0 else self.fall_color
            if self.jump_z <= 0:
                self.jump_z = 0
                self.vz = 0
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
        # 1. 處理緩衝計時
        if self.input_buffer_timer > 0:
            self.input_buffer_timer -= 1
            if self.input_buffer_timer == 0:
                self.input_buffer = None
        # 2. 原有的狀態更新 (update_combat_state, etc.)
        super().update()
        if self.health_visual > self.health:
            self.health_visual -= 0.5
        if self.external_control:
            self.update_by_external_control()
            return

        if self.held_by:
            print(f'{self.name} 被持有 {self.held_by.name}')
        if self.health < 50 and self.health > 0:
            if not self.has_stand:
                self.mp += 3
            self.has_stand = True
            self.super_armor_timer = 1
            #持續霸體
        # if self.held_by:
        #     self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來
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
        #self.update_physics_only()
        self.handle_movement()
        self.update_burning_flag()

    #def enable_super_move(self, pre_pose_background = None, portraits=None, effect=None, timer=350, portraits_begin=0.6):
    def enable_super_move(self):
        if self.super_move_staging is None:
            return
        config_dict = self.super_move_staging
        timer = config_dict.get("timer", 350)
        super_move_dict = {"pre_pose_background": config_dict.get("pre_pose_background", None),
                           "portraits": config_dict.get("portraits", None),
                           "effect": config_dict.get("effect", None),
                           "timer": timer,
                           "damage": 50+self.mp*30,
                           "portraits_begin": config_dict.get("portraits_begin", 0.6)}
        self.super_move_max_time = timer
        self.scene.start_super_move(self, super_move_dict)
        self.set_rigid(30)

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
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        falling_z_offset = 0
        if self.is_falling():
            falling_z_offset = self.falling_y_offset * Z_FALL_OFSSET

        # cx = int((self.x + self.width / 2) * TILE_SIZE) - cam_x
        # cy = int((self.map_h - (self.y + self.height * 0.1)) * TILE_SIZE - self.jump_z * 5 - terrain_z_offset + falling_z_offset) - cam_y + tile_offset_y
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height

        win.blit(frame, (draw_x, draw_y))



class Ally(CharacterBase):
    def __init__(self, x, y, z, map_info, config_dict):
        super().__init__(x, y, map_info)
        move_speed = config_dict.get("move_speed", 0.5)
        attack_cooldown_duration = config_dict.get("attack_cooldown",240)
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
        super().update()
        if self.external_control:
            self.update_by_external_control()
            return
        if self.current_frame < self.summon_sickness:
            self.invincible_timer =2

        # 關閉AI
        # return

        #self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來

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


        if enemy_target:
            intent = self.decide_intent(enemy_target)
            self.handle_input(intent)
        #self.update_physics_only()
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
        self.ai_mental_logic(target)
        intent['direction'] = self.facing
        self.ai_attack_logic(target, intent, act='support')
        self.ai_move_logic(target, intent, far_speed = self.ai_move_speed, near_speed = self.ai_move_speed*0.6)
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
            #self.jump_z += self.vz
            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()
        if self.jump_z != 0 and not self.held_by:
            self.state = MoveState.JUMP if self.vz > 0 else MoveState.FALL
            self.color = self.jump_color if self.vz > 0 else self.fall_color
            if self.jump_z <= 0:
                self.jump_z = 0
                self.vz = 0
                self.color = self.default_color

class StandEntity(Ally):
    def __init__(self, owner, config_dict):
        super().__init__(owner.x, owner.y, owner.z, [owner.terrain, owner.map_w, owner.map_h], config_dict)
        self.owner = owner
        self.type="stand"
        self.invincible_timer = 999999
        self.dummy = True  # 確保不執行 AI
        # 替身不參與受擊，判定由主人承擔
        self.health = 1
    def update(self):
        # 僅執行視覺與動畫計時器的基本更新
        self.current_frame += 1
        if self.attack_state:
            self.attack_state.update()
        elif self.state in [MoveState.WALK, MoveState.RUN]:
            self.state = MoveState.WALK
        else:
            self.state=MoveState.STAND
        #不與其他單位互動
    def draw(self, win, cam_x, cam_y, tile_offset_y):
        # 使用特殊濾鏡（例如 BLEND_RGB_ADD）增強靈體感
        # 此處呼叫 simplified_draw 或直接在 draw 中設定 alpha

        comp = self.owner.get_component("ability_stand")
        alpha_remain = 255
        if comp and hasattr(comp, "duration"):
            # 取得螢幕位置
            cx, cy = self.cached_pivot
            bar_w = 40
            bar_h = 4
            draw_x = cx - bar_w // 2
            draw_y = cy + 10  # 放在腳下

            # 計算比例 (假設初始 duration 為 900)
            # 如果想要動態，可以在 StandComponent 紀錄一個 initial_duration
            ratio = max(0, comp.duration / comp.max_duration)
            self.draw_alpha = int(255*ratio)

            # 繪製背景與進度
            pygame.draw.rect(win, (50, 50, 50), (draw_x, draw_y, bar_w, bar_h))
            pygame.draw.rect(win, (200, 100, 255), (draw_x, draw_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(win, (255, 255, 255), (draw_x, draw_y, bar_w, bar_h), 1)
        super().draw(win, cam_x, cam_y, tile_offset_y)

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
        self.summon_sickness = 60
        self.name=config_dict.get("name", "default")
        self.combo_count = 0
        self.combos = config_dict.get("combos", DEFAULT_COMBOS)
        self.dummy = False
        self.animator = SpriteAnimator(image_path=config_dict.get("image_path"), config_dict=config_dict.get("animator_config"))  # 載入素材
        self.stand_image = pygame.image.load("..\\Assets_Drive\\star_p.png").convert_alpha()
        self.side = 'enemy_side'
        self.money = 10 #loot
        self.ai_move_speed = ai_move_speed
        self.popup = config_dict.get("popup")
        self.is_blocking = config_dict.get("is_blocking", False)
        if self.popup and "landing" in self.popup:
            self.jump_z = 5
            self.vz = -0.2

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

        super().update()
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
        
        #self.update_hold_fly_position()  # 從HoldFlyLogicMixin而來

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

        # --- 進攻權杖管理 ---
        scene = self.scene
        # 1. 如果正在攻擊，重置權杖計時器
        if self.attack_state:
            scene.refresh_token(self)

        # 2. 如果沒有權杖，且士氣高昂/性格勇敢，嘗試申請
        has_token = self in scene.token_holders
        if not has_token and (self.morale > 0.4 or self.personality == 'brave'):
            players = self.scene.get_units_by_side('player_side')
            if players and abs(players[0].x - self.x) < 8:  # 靠近玩家才申請
                scene.request_token(self)
        intent = None
        if (self.current_frame + id(self))%3 == 0:
            intent = self.decide_intent(players[0])
        elif self.last_intent:
            #如果攻擊過一次就不再繼續攻擊
            if self.last_intent.get('action') is not None:
                self.last_intent['action'] = None
            intent = self.last_intent

        if self.current_frame >= self.summon_sickness and intent:
            self.handle_input(intent)
        #self.update_physics_only()
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
        self.ai_mental_logic(target)
        self.ai_mental_logic(target)
        self.ai_attack_logic(target, intent, act='Enemy')
        self.ai_move_logic(target, intent, far_speed=self.ai_move_speed, near_speed=self.ai_move_speed*0.6)

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
            #self.jump_z += self.vz

            self.x += self.vel_xy[0] * 0.2
            self.y += self.vel_xy[1] * 0.2
            self.color = self.fall_color
            self.check_ground_contact()
        if self.jump_z != 0 and not self.held_by:
            self.state = MoveState.JUMP if self.vz > 0 else MoveState.FALL
            self.color = self.jump_color if self.vz > 0 else self.fall_color
            if self.jump_z <= 0:
                self.jump_z = 0
                self.vz = 0
                self.color = self.default_color

# class BigEnemy(Enemy):
#     def __init__(self, x, y, z, map_info, material, big_ratio=2.0):
#         super().__init__(x, y, z, map_info, material)
#
#         # 1) 放大碰撞尺寸
#         self.width = self.width * big_ratio
#         self.height = self.height * big_ratio
#
#         # 2) 視覺區別 (顏色或其他旗標)
#         self.default_color = (200, 80, 20)
#         self.jump_color = (220, 140, 40)
#         self.fall_color = (180, 80, 30)
#
#         # 3) 能力值強化
#         #   - 血量大幅提升
#         #   - money 掉更多
#         base_max_hp = getattr(self, "max_hp", 100)
#         self.max_hp = base_max_hp * 3
#         self.health = self.max_hp
#
#         base_money = getattr(self, "money", 10)
#         self.money = base_money * 5
#
#         # 攻擊冷卻更長，顯得笨重但危險
#         self.attack_cooldown_duration = max(
#             15,
#             int(self.attack_cooldown_duration * 1.8)
#         )
#         self.attack_cooldown = 0
#
#         # 召喚後僵直時間（或開場不動秒數）可以調整
#         self.summon_sickness = 10
#
#         # 4) 調整動畫貼圖大小
#         #    如果 Enemy 原本有 self.animator 並且 animator.frames 是一組 pygame.Surface
#         if hasattr(self, "animator") and self.animator and hasattr(self.animator, "frames"):
#             scaled_frames = []
#             for f in self.animator.frames:
#                 sw = f.get_width()
#                 sh = f.get_height()
#                 scaled_frames.append(pygame.transform.scale(f, (sw * big_ratio, sh * big_ratio)))
#             self.animator.frames = scaled_frames
#
#             # 如果 animator 有 frame_width/height 屬性就同步更新
#             if hasattr(self.animator, "frame_width"):
#                 self.animator.frame_width *= big_ratio
#             if hasattr(self.animator, "frame_height"):
#                 self.animator.frame_height *= big_ratio
#
#         # 5) 改招式組合（可依你遊戲平衡調）
#         self.combos = [AttackType.SLASH, AttackType.BASH, AttackType.KICK]
#
#         # 6) metadata / 辨識
#         self.name = 'big_enemy'
#         self.side = 'enemy_side'


# Characters.py
# Characters.py

# Characters.py

class ClonePlayer(Player):
    def __init__(self, x, y, map_info, config, owner, duration=600):
        super().__init__(x, y, map_info, config)
        self.owner = owner
        self.side = 'player_side'  # 盟友陣營
        #self.unit_type = 'Character'
        self.name='clone'
        self.is_ai_controlled = True

        # 🟢 設定分身的戰鬥性格與 Combo
        self.combos = config.get("combos", [AttackType.PUNCH, AttackType.PUNCH, AttackType.SPECIAL_PUNCH, AttackType.KICK, AttackType.KICK, AttackType.SPECIAL_KICK, AttackType.MAHAHPUNCH, AttackType.SLASH, AttackType.BASH])
        self.combo_count = 0
        self.attack_cooldown = 90
        self.attack_cooldown_duration = 30  # 分身出招較快
        self.aggressiveness = 0.9  # 極具攻擊性
        self.morale = 1.0
        self.lifetime = duration

    # Characters.py -> 修正 ClonePlayer.update

    def update(self):
        # 1. 生命週期處理
        self.lifetime -= 1
        if self.lifetime <= 0 or self.health <= 0:
            self.scene.mark_for_removal(self)
            return

        # 2. 🟢 關鍵修正：執行收招與碰撞檢查
        # 分身必須模擬與敵人的互動，才能讓 attack_state 倒數到 0
        enemies = self.scene.get_units_by_side('enemy_side')
        for enemy in enemies:
            # 這個函式會處理 attack_state 的結束與回到 STAND 狀態
            self.update_common_opponent(enemy)

        # 3. 自主 AI 思考 (僅在非攻擊、非受擊時執行)
        if self.combat_state == CombatState.NORMAL and not self.attack_state:
            if enemies:
                target = min(enemies, key=lambda e: self.distance_to_target(e))
                intent = {
                    'direction': self.facing, 'horizontal': MoveState.STAND,
                    'dx': 0, 'dy': 0, 'jump': False, 'action': None,
                    'z': False, 'x': False, 'c': False,
                    'dirs': (False, False, False, False)
                }
                self.ai_attack_logic(target, intent, act='Enemy')
                self.ai_move_logic(target, intent, far_speed=0.4, near_speed=0.2)
                self.handle_input(intent)

        # 4. 🟢 物理位移更新
        # 這裡呼叫 Player.update 會處理跳躍物理與 anim_timer
        super().update()