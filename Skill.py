from State_enum import *
import math
from Config import *

#SystemAbility指在實作不依賴hitbox的buff類，有時效、需要與scene互動的技能，例如時停，加速
class SystemAbilityData:
    def __init__(self, name, mp_cost, duration, on_trigger=None, on_update=None, on_expire=None):
        self.name = name
        self.mp_cost = mp_cost
        self.duration = duration
        # 以下為函數指標指標
        self.on_trigger = on_trigger
        self.on_update = on_update
        self.on_expire = on_expire

# --- 時間暫停 (za warudo) ---
def za_warudo_trigger(owner, duration):
    from PhysicsUtils import get_overlap_center
    owner.scene.toggle_highlight_test(owner, alpha=180)
    cx, cy, cz = get_overlap_center(owner.get_hurtbox(), owner.get_hurtbox())
    owner.scene.create_effect(cx, cy, cz, "ring", max_radius=10, width=4)
    if owner.stand:
        owner.scene.toggle_highlight_test(owner.stand, alpha=180)
    if owner.scene.env_manager.freeze_timer <= 0:
        seconds = int(duration / 60)
        owner.super_armor_timer = duration
        owner.say(f'ZA WARUDO!{seconds}秒!')
        owner.scene.env_manager.set_freeze(duration)
        print(f"🔥 {owner.name} 【時之停頓】")

def za_warudo_update(owner):
    if owner.scene.env_manager.freeze_timer in [60, 120, 180]:
        seconds = int(owner.scene.env_manager.freeze_timer / 60)
        for unit in owner.scene.env_manager.highlight_units:
            if unit.is_alive() and unit.name in ['player', 'enemy']:
                unit.say(f"{seconds}..", duration=45)
def za_warudo_expire(owner):
    owner.say("然後時間開始流動")
    owner.scene.env_manager.set_dim(False)
    owner.scene.env_manager.highlight_units.clear()

# --- 超加速 (Haste) ---
def haste_trigger(owner, duration=900):
    owner.scene.toggle_highlight_test(owner, alpha=100)
    owner.double_speed = True
    owner.afterimage_enabled = True
    print(f'owner.afterimage_enabled={owner.afterimage_enabled}')
    owner.say("超加速!!")

def haste_expire(owner):
    if getattr(owner, 'afterimage_enabled', False):
        owner.afterimage_enabled = False
    owner.double_speed = False
    owner.scene.env_manager.highlight_units.clear()
    owner.scene.env_manager.set_dim(False)


# Skill.py

# Skill.py

def trigger_clone_skill(owner, duration):
    """分身術啟動邏輯"""
    from Characters import ClonePlayer  # 延遲導入防止循環引用

    # 計算生成位置：玩家面向的前方 1 單位
    offset_x = 1.0 if owner.facing == DirState.RIGHT else -1.0

    # 建立實體
    clone = ClonePlayer(
        owner.x + offset_x,
        owner.y,
        [owner.terrain, owner.map_w, owner.map_h],
        owner.config_backup,  # 使用本體的貼圖配置備份
        owner
    )

    # 🟢 註冊到場景：設定標籤與陣營
    owner.scene.register_unit(clone, side='player_side', tags=['player_clone'], type='character')

    # 視覺回饋：在生成點產生煙霧或爆氣特效
    owner.scene.create_effect(clone.x, clone.y, clone.z, "brust", alpha=180)
    #owner.say("分身術！")


# --- 數據庫實例 ---
ABILITY_DATA = {
    #狀態類:
    "haste": SystemAbilityData("haste", 1, 600, on_trigger=haste_trigger, on_expire=haste_expire),
    "timestop": SystemAbilityData("timestop", 1, 540, on_trigger=za_warudo_trigger, on_update=za_warudo_update, on_expire=za_warudo_expire),
    #實體類:
    "stand": SystemAbilityData("stand", 1, 900),
    "clone": SystemAbilityData("clone", 1, 900, on_trigger=trigger_clone_skill),
    #演出類:
    "super_move": SystemAbilityData("stand", 3, 0),
}
ABILITY_REPEATABLE = ['clone']

# === Attack State ===
class AttackState:
    def __init__(self, character, attack_data):
        self.character = character
        self.data = attack_data
        self.timer = attack_data.duration
        self.frame_index = 0
        self.has_hit = []
        #self.force_move = 0
        #self.force_move_y = 0
        self.name = 'basic'
        self.is_fly_attack = False
        self.has_clashed = False

    def update(self):
        #print('AttackState 的 update')
        if self.timer > 0:
            self.timer -= 1
            self.frame_index += 1
        if self.data.can_use(self.character):
            dir_vec = 0
            if self.character.facing == DirState.RIGHT:
                dir_vec = 1
            elif self.character.facing == DirState.LEFT:
                dir_vec = -1

                # --- 修正：計算新座標並檢查邊界 ---
            new_x = self.character.x + dir_vec * self.data.force_move
            # 限制在 [0, MAP_WIDTH - 角色寬度] 之間
            self.character.x = max(0, min(new_x, self.character.map_w - self.character.width))
        # 🟢 屬於特殊遠程招式

        if self.data.attack_type == AttackType.BACKFLIP_SHOT:
            # --- 核心修正：處理滯空物理 ---
            # 假設第 10 幀開始進入滯空射擊
            if 10 <= self.frame_index <= 40:
                self.character.gravity_scale = 0.0  # 關閉重力
                self.character.vz = 0.0  # 🟢 必須將向上速度清零，否則會持續上升
            else:
                self.character.gravity_scale = 1.0  # 恢復重力

            # --- 射擊事件觸發 ---
            if self.frame_index in self.data.contextual_trigger_frames:
                # 直接呼叫 Character 的生成函式
                #print("execute_backflip_shoot")
                #self.character.scene.print_interactiables()
                self.character.execute_backflip_shoot(speed_x = 0.5-self.frame_index/200)
                #self.character.scene.print_interactiables()
                #print("="*50)
        # 2. 🟢 核心重構：處理「情境式/對齊類」傷害
        elif self.data.attack_type in CONTEXTUAL_ATTACK:
            # 從 owner (發動者) 身上抓取我們在 resolve_attack_table 時存好的目標
            target = getattr(self.character, 'interact_target', None)
            if target and target.is_alive():
                # 檢查當前幀是否在 AttackData 定義的觸發清單中
                if self.frame_index in self.data.contextual_trigger_frames:
                    # 直接執行命中邏輯，跳過 Hitbox 掃描
                    target.on_hit(self.character, self.data)

                    # 產生物理回饋與特效
                    if self.character.scene:
                        # 在目標位置產生打擊火花
                        self.character.scene.create_effect(target.x+target.width/2, target.y, target.z, 'hit')
                        # 每次踩踏都來一點小震動增加打擊感
                        self.character.scene.trigger_shake(duration=5, intensity=3)
            if self.frame_index == self.timer -1:
                #結束時清空站存目標
                self.character.interact_target = None

    def is_active(self):
        return self.timer > 0

    def should_trigger_hit(self):
        return self.frame_index >= self.data.trigger_frame

    def get_hitbox(self, x, y, facing, actor=None):
        try:
            return self.data.get_hitbox(x,y,facing,actor)
        except TypeError:
            return self.data.get_hitbox(x, y, facing)


    def can_cancel_to(self, next_attack_type):
        """
        檢查是否可以取消成另一個招式（例如 PUNCH → SLASH）
        """
        if next_attack_type in self.data.cancel_table:
            cancel_start = self.data.cancel_table[next_attack_type]
            return self.frame_index >= cancel_start
        return False

class FlyAttackState(AttackState):
    def __init__(self, character, attack_data):
        super().__init__(character, attack_data)
        self.started = False
        self.is_fly_attack = True

    def is_active(self):
        # ✅ 跳躍中則持續存在
        return self.character.jump_z > 0 or self.character.vz > 0


class SwingAttackState(AttackState):
    def __init__(self, character, unit):
        attack_data = unit.get_swing_attack_data(character)
        super().__init__(character, attack_data)
        self.item = unit
        self.name = 'swing'

    def update(self):
        super().update()
        #print('SwingAttackState 的 update')
        if self.item:
            swing_offset = 0.6 + 0.2 * math.sin(self.frame_index * 0.3)  # 左右擺動
            if self.character.facing == DirState.LEFT:
                swing_offset = -swing_offset

            self.item.x = self.character.x + swing_offset
            self.item.y = self.character.y
            self.item.z = self.character.z
            self.item.jump_z = self.character.jump_z + 0.5

class ThrowAttackState(AttackState):
    def __init__(self, character, item):
        attack_data = item.get_throw_attack_data(character)
        super().__init__(character, attack_data)
        self.item = item
        self.thrown = False
        self.holdable = character.get_component("holdable")
        self.name = 'throw'
        self.attacker_attack_data = None

    def update(self):
        super().update()
        #print(f'ThrowAttackState 的 update {self.character.current_frame}/{self.character.attack_state.data.duration}')
        if not self.thrown and self.frame_index >= self.data.trigger_frame:
            self.thrown = True
            if self.item:
                # 1. 決定基礎投擲力 (根據面向)
                facing_dir = 1 if self.character.facing == DirState.RIGHT else -1
                base_power = self.character.throw_power  # 角色基礎投擲力

                # 2. 決定狀態加成 (跑動中投擲更有力)
                state_multiplier = 1.0
                if self.character.state == MoveState.RUN:
                    state_multiplier = 1.5  # 助跑加成 1.5 倍
                elif self.character.state == MoveState.WALK:
                    state_multiplier = 1.2
                # 3. 慣性繼承：物體速度 = (投擲者當前速度 * 繼承比) + (投擲力 * 加成)
                # 這樣一來，如果你在跳躍中投擲，vz 就會自動包含跳躍的向上動量
                self.item.vel_x = (self.character.vel_x * 0.5) + (facing_dir * base_power * state_multiplier)
                self.item.vz = (self.character.vz * 0.5) + 0.1  # 繼承垂直動量並稍微往上拋


                offset = (self.character.width) + 0.3  # 原本是 ±1，改為角色寬 + 安全距離
                if self.character.facing == DirState.LEFT:
                    offset = -offset
                # 🟢 修正 2：計算目標 X 並確保不超出地圖
                target_x = self.character.x + offset
                self.item.x = max(0, min(target_x, self.item.map_w - self.item.width))
                self.item.y = self.character.y
                self.item.z = self.character.z
                self.item.jump_z = self.character.jump_z + self.character.height*0.8
                #self.item.vz = 0.3
                # move_rate =  self.character.throw_power
                # if hasattr(self.item, 'speed'):
                #     move_rate = self.item.speed
                # self.item.vel_x = offset * move_rate # 水平飛行速度
                self.item.is_thrown = True  # ✅ 切換 item 的控制狀態
                print(f'{self.item.name} 飛行!')
                self.item.held_by = None   #無人持有
                self.item.thrown_by = self.character
                self.holdable.held_object = None
                #self.character.attack_state = None  # ✅ 結束 attack_state


# === Attack Data Definition ===
class AttackData:
    # def __init__(self, attack_type, duration, trigger_frame=[0], hitbox_func=None, recovery=5, condition_func=None,
    #              force_move=0, effects=None,knock_back_power=[0.0, 0.0], damage=10,
    #              frame_map = None, cancel_table=None, physical_change=None, effect_component_config: dict = None,
    #              dialogue=None, frame_map_ratio=[1], hit_stop_frames=0, scene_effect = None):
    def __init__(self,attack_type,duration,**kwargs):
        self.attack_type = attack_type
        self.duration = duration
        self.trigger_frame = kwargs.get('trigger_frame', [0])
        self.recovery = kwargs.get('recovery', 5)
        self.hitbox_func = kwargs.get('hitbox_func', None)
        self.condition_func = kwargs.get('condition_func', (lambda actor: True))
        self.force_move = kwargs.get('force_move', 0)    #角色自己的位移
        self.effects = kwargs.get('effects', [])    #被擊中的效果
        self.knock_back_power = kwargs.get('knock_back_power', [0.0,0.0])  #擊飛多遠多高
        self.damage = kwargs.get('damage', 1)
        self.frame_map = kwargs.get('frame_map', [0]*duration)  # 預設全部使用第一張動畫
        #if sum(frame_map_ratio) != self.duration:
        # sun = sum(frame_map_ratio)
        # print(f'frame_map_ratio={frame_map_ratio} sum={sun}, duration={self.duration}')
        self.cancel_table = kwargs.get('cancel_table', {})
        self.physical_change = kwargs.get('physical_change', {})
        self.effect_component_config = kwargs.get('effect_component_config', {})
        self.dialogue = kwargs.get('dialogue',None)
        self.frame_map_ratio=kwargs.get('frame_map_ratio', [1])
        #assert sum(frame_map_ratio) == self.duration, "frame_map 長度({})需與 duration{} 相符".format(sum(frame_map_ratio), duration)
        self.hit_stop_frames = kwargs.get('hit_stop_frames', 0)  # 凍結幀數 (通常 3~8 幀就很強烈)
        self.damage_multiplier = 1.0
        self.contextual_trigger_frames = kwargs.get('contextual_trigger_frames', [1])
        self.guardable = kwargs.get('guardable', True)

        # 🟢 新增動能傳導參數
        # 如果沒給，我們就從 damage 與 knock_back 反推一個預設值，實現平滑過渡
        # 🟢 安全獲取 power：
        # 如果 kwargs 沒給 power，則嘗試從 damage 推導
        # 🟢 新系統：能量傳導參數
        # 如果 kwargs 沒給，則進入「相容模式」自動生成
        if 'power' in kwargs:
            self.power = kwargs['power']
            self.absorption = kwargs.get('absorption', 0.5)
            self.impact_angle = kwargs.get('impact_angle', 0)
        else:
            # 自動反推：Power 應該大於 Damage，剩餘的轉為動能
            # 假設預設吸收率 0.5，則 Power = Damage * 2
            if callable(self.damage):
                self.power = lambda actor: self.damage(actor) * 2.0
            else:
                self.power = self.damage * 2.0

            self.absorption = 0.5  # 預設一半轉傷

            # 根據舊有的 knock_back_power [vx, vz] 計算角度
            import math
            vx, vz = self.knock_back_power
            # 使用 atan2 反推角度 (度數)
            self.impact_angle = math.degrees(math.atan2(vz, abs(vx))) if (vx != 0 or vz != 0) else 0

    def get_sprite_index(self, frame_index):
        return self.frame_map[frame_index]

    def can_use(self, actor):
        return self.condition_func(actor)

    def get_hitbox(self, x, y, facing, actor=None):
        if self.hitbox_func is None:
            return None
        try:
            return self.hitbox_func(x, y, facing, actor)
        except TypeError:
            return self.hitbox_func(x, y, facing)
    def get_damage(self, attacker=None):
        if callable(self.damage):
            return int(self.damage(attacker)*self.damage_multiplier+0.5)
        return int(self.damage*self.damage_multiplier+0.5)



# === Sample hitbox function ===
def front_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 0.6 * (w / 1.5)
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y - 0.2
    y_bottom = y + h * 0.6

    if facing == DirState.RIGHT:
        return {'x1': x + 0.5, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom}
    else:
        return {'x1': x - reach, 'x2': x - 0.5, 'y1': y_top, 'y2': y_bottom}

def front_hitbox_func2(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 0.6 * w
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y+h*0.5
    y_bottom = y_top + h*0.4

    if facing == DirState.RIGHT:
        return {'x1': x + 0.5, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom}
    else:
        return {'x1': x - reach, 'x2': x - 0.5, 'y1': y_top, 'y2': y_bottom}

def swing_hitbox_func(x, y, facing, actor=None):

    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
        item_w = getattr(actor.get_component("holdable").held_object, "width", 1.5)
        item_h = getattr(actor.get_component("holdable").held_object, "heihgt", 1.5)
    else:
        w = 1.5
        h = 2.5
        item_w, item_h = 1.5, 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + (item_w+item_h)/2
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y + h*0.5
    y_bottom = y_top + (item_w+item_h)/2

    if facing == DirState.RIGHT:
        return {'x1': x + 0.5, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom}
    else:
        return {'x1': x - reach, 'x2': x - 0.5, 'y1': y_top, 'y2': y_bottom}
def two_side_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 0.8 * w
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y - 0.2
    y_bottom = y + h * 0.6
    return {'x1': x -reach, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom}

def down_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    return {'x1':x-w/2, 'x2':x+w/2, 'y1':y-h/2, 'y2':y+h/2}


def punch_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 0.6 * (w / 1.5)
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y+h*0.4
    y_bottom = y + h * 0.6
    if facing == DirState.RIGHT:
        return {'x1': x + 0.2, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom }
    else:
        return {'x1': x - reach, 'x2': x - 0.2, 'y1': y_top, 'y2': y_bottom }

def spear_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 1.6 * (w / 1.5)
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y+h*0.4
    y_bottom = y + h * 0.6
    if facing == DirState.RIGHT:
        return {'x1': x + 0.2, 'x2': x + reach, 'y1': y_top, 'y2': y_bottom }
    else:
        return {'x1': x - reach, 'x2': x - 0.2, 'y1': y_top, 'y2': y_bottom }

def kick_hitbox_func(x, y, facing, actor=None):
    if actor is not None:
        w = getattr(actor, "width", 1.5)
        h = getattr(actor, "height", 2.5)
    else:
        w = 1.5
        h = 2.5
    # 2. 計算攻擊觸及距離（reach）
    #    舉例：讓 reach 跟寬度成比例
    reach = 0.9 + 0.6 * (w / 1.5)
    # 3. 垂直覆蓋範圍也用角色高度來估
    y_top = y+h*0.1
    y_bottom = y_top + h * 0.7

    if facing == DirState.RIGHT:
        return {'x1': x + 0.2, 'x2': x + reach, 'y1': y_top , 'y2': y_bottom}
    else:
        return {'x1': x - reach, 'x2': x - 0.2, 'y1': y_top , 'y2': y_bottom}

def item_hitbox(x, y, facing):
    # 可依 item 參數決定範圍，或讓角色在攻擊前動態設置
    if facing == DirState.RIGHT:
        return {'x1': x + 0.5, 'x2': x + 1.2, 'y1': y - 0.2, 'y2': y + 1.5}
    else:
        return {'x1': x - 1.2, 'x2': x - 0.5, 'y1': y - 0.2, 'y2': y + 1.5}


# def throw_damage(self):
#     return self.item_damage
# === Attack Data Dictionary ===
FLY_ATTACKS = [AttackType.FLY_KICK, AttackType.METEOFALL]
SWING_ATTACKS = [AttackType.SWING]
THROW_ATTACKS = [AttackType.THROW]
#FIREBALL_ATTACKS = [AttackType.FIREBALL]
FLYING_OBJECT_ATTACKS = [AttackType.FIREBALL, AttackType.BULLET]
CONTEXTUAL_ATTACK =[AttackType.DOWN_STOMP, AttackType.DOWN_HAMMER, AttackType.BACKFLIP_SHOT]
attack_data_dict = {
    AttackType.SLASH: AttackData(
        attack_type=AttackType.SLASH,
        duration=60,
        trigger_frame=30,
        recovery=15,
        hitbox_func=front_hitbox_func,
        condition_func=lambda actor: actor.state != MoveState.JUMP and actor.state != MoveState.FALL,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_power=[0.5,3.0],
        damage = 20,
        #frame_map = [0]*15 + [1]*10 + [2]*35,   #必須與duration等長
        frame_map_ratio = [15,10,35], #必須與duration等長
        hit_stop_frames=5
    ),
    AttackType.PUSH: AttackData(
        attack_type=AttackType.PUSH,
        duration=60,
        trigger_frame=30,
        recovery=15,
        hitbox_func=front_hitbox_func2,
        condition_func=lambda actor: actor.state != MoveState.JUMP and actor.state != MoveState.FALL,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE],
        knock_back_power=[2.0, 0.5],
        damage=20,
        # frame_map = [0]*15 + [1]*10 + [2]*35,   #必須與duration等長
        frame_map_ratio=[15, 10, 35],  # 必須與duration等長
        hit_stop_frames=5,
        power=40, absorption=0.9, angle=0
    ),
    AttackType.PUNCH: AttackData(
        attack_type=AttackType.PUNCH,
        duration=32,
        trigger_frame=8,
        recovery=2,
        hitbox_func = punch_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN],
        damage = 5,
        frame_map = [0]*8 + [2]*16 + [1]*8,   #必須與duration等長
        cancel_table = {AttackType.SLASH: 12, AttackType.PUNCH: 8, AttackType.KICK: 8},
        frame_map_ratio = [8,16,8],
    ),
    AttackType.SPEAR: AttackData(
        attack_type=AttackType.SPEAR,
        duration=32,
        trigger_frame=8,
        recovery=2,
        hitbox_func=spear_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN],
        damage=10,
        power=30,
        frame_map=[0] * 8 + [2] * 16 + [1] * 8,  # 必須與duration等長
        cancel_table={AttackType.SLASH: 12, AttackType.SPEAR: 12},
        frame_map_ratio=[8, 16, 8],
    ),
    AttackType.SPECIAL_PUNCH: AttackData(
        attack_type=AttackType.SPECIAL_PUNCH,
        duration=32,
        trigger_frame=8,
        recovery=2,
        hitbox_func=punch_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE],
        damage=8,
        frame_map=[0] * 8 + [2] * 16 + [1] * 8,  # 必須與duration等長
        frame_map_ratio=[8, 16, 8],
        knock_back_power=[1.0,0.1],
        hit_stop_frames=5
    ),
    AttackType.SPECIAL_SPEAR: AttackData(
        attack_type=AttackType.SPECIAL_SPEAR,
        duration=32,
        trigger_frame=8,
        recovery=2,
        hitbox_func=spear_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE],
        damage=8,
        frame_map=[0] * 8 + [2] * 16 + [1] * 8,  # 必須與duration等長
        frame_map_ratio=[8, 16, 8],
        knock_back_power=[1.0, 0.1],
        hit_stop_frames=5
    ),
    AttackType.MAHAHPUNCH: AttackData(
        attack_type=AttackType.MAHAHPUNCH,
        duration=48,
        trigger_frame=8,
        recovery=2,
        hitbox_func = punch_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE, AttackEffect.FORCE_WEAK],
        #knock_back_power=[1.5,0.0],
        damage = 10,
        frame_map = [0]*4 + [2]*4 + [1]*4+ [2]*4 + [1]*4+ [2]*4 + [1]*4+ [2]*4+ [1]*4+ [2]*4+ [1]*4+ [2]*4,
        effect_component_config={
            # 必須使用 Component 類別的字串名稱，以便動態載入
            "component_name": "AuraEffectComponent",
            # 這是您在 ComponentHost 中使用的 key，用於移除
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//hyakuretsu.png",
                "expire_type":EffectExpireMode.ATTACK_END,
                "alpha":180,
                "anim_speed":4
            },
            "frame_width":128,
            "frame_height":128
        },
        frame_map_ratio = [4]*12,
        hit_stop_frames=5
    ),
    AttackType.MAHAHSPEAR: AttackData(
        attack_type=AttackType.MAHAHSPEAR,
        duration=48,
        trigger_frame=8,
        recovery=2,
        hitbox_func=spear_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE, AttackEffect.FORCE_WEAK],
        # knock_back_power=[1.5,0.0],
        damage=15,
        # frame_map=[0] * 4 + [2] * 4 + [1] * 4 + [2] * 4 + [1] * 4 + [2] * 4 + [1] * 4 + [2] * 4 + [1] * 4 + [2] * 4 + [
        #     1] * 4 + [2] * 4,
        frame_map_ratio=[4] * 12,
        hit_stop_frames=5
    ),
    AttackType.KICK: AttackData(
        attack_type=AttackType.KICK,
        duration=36,
        trigger_frame=12,
        recovery=5,
        hitbox_func=kick_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN],
        damage = 7,
        frame_map = [1]*12 + [0]*24,
        cancel_table = {AttackType.SLASH: 24, AttackType.KICK: 18},
        frame_map_ratio = [12,24],
    ),
    AttackType.SPECIAL_KICK: AttackData(
        attack_type=AttackType.SPECIAL_KICK,
        duration=36,
        trigger_frame=12,
        recovery=5,
        hitbox_func=kick_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.AFTER_IMAGE],
        damage=8,
        frame_map=[1] * 12 + [0] * 24,
        frame_map_ratio=[12, 24],
        knock_back_power=[1.0,0.1],
        hit_stop_frames=5
    ),
    AttackType.FLY_KICK: AttackData(
        attack_type=AttackType.FLY_KICK,
        duration=999,# ✅ 實際上會被 is_active() 覆蓋
        trigger_frame=2,
        recovery=15,
        hitbox_func=kick_hitbox_func,
        condition_func=lambda actor: actor.jump_z > 0,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_power=[0.2,-1.0],
        damage=12,
        frame_map_ratio = [999],
        hit_stop_frames=5
    ),
    AttackType.METEOFALL: AttackData(
        attack_type=AttackType.METEOFALL,
        duration=999,
        trigger_frame=8,
        recovery=15,
        hitbox_func=down_hitbox_func,
        condition_func=lambda actor: actor.state != MoveState.JUMP and actor.state != MoveState.FALL,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.BURN, AttackEffect.AFTER_IMAGE],
        knock_back_power=[0.5,-1.5],
        damage=35,
        physical_change={'vz':GRAVITY*-2},
        effect_component_config={
            # 必須使用 Component 類別的字串名稱，以便動態載入
            "component_name": "AuraEffectComponent",
            # 這是您在 ComponentHost 中使用的 key，用於移除
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_4frame_256.png",
                "expire_type":EffectExpireMode.LANDING,
                "frame_width": 256,
                "frame_height": 256
            },
        },
        dialogue="飛翔白麗!",
        frame_map_ratio = [999],
        hit_stop_frames=5
    ),
    AttackType.BASH: AttackData(
        attack_type=AttackType.BASH,
        duration=30,
        trigger_frame=3,
        recovery=10,
        hitbox_func=front_hitbox_func,
        condition_func=lambda actor: True,
        force_move=0.3,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_power=[0.7,0.05],
        damage = 5,
        frame_map_ratio = [10,20]
    ),

    AttackType.SWING: AttackData(
        attack_type=AttackType.SWING,
        duration=32,
        trigger_frame=12,
        recovery=16,
        hitbox_func=swing_hitbox_func,
        effects=[AttackEffect.SHORT_STUN],
        damage = 10,
        frame_map = [0]*12 + [1]*20,   #必須與duration等長
        frame_map_ratio = [12,20]
    ),
    AttackType.THROW: AttackData(
        attack_type=AttackType.THROW,
        duration=32,
        trigger_frame=1,
        recovery=16,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        damage = 15,
        frame_map = [0]*1 + [1]*31,   #必須與duration等長
        frame_map_ratio = [1,31]
    ),
    AttackType.THROW_CRASH: AttackData(
        attack_type=AttackType.THROW,
        duration=1,
        trigger_frame=1,
        recovery=0,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        damage=lambda attacker: getattr(attacker, "throw_damage", 2),  # 如果無此屬性就預設 2
        frame_map_ratio = [1]
    ),
    AttackType.FIREBALL: AttackData(
        attack_type=AttackType.FIREBALL,
        effects=[AttackEffect.SHORT_STUN],
        duration=32,
        trigger_frame=16,
        recovery=16,
        hitbox_func=item_hitbox,
        damage = 0,
        frame_map = [0]*16 + [1]*16,   #必須與duration等長
        frame_map_ratio = [16,16]
    ),
    AttackType.BULLET: AttackData(
        attack_type=AttackType.BULLET,
        effects=[AttackEffect.SHORT_STUN],
        duration=32,
        trigger_frame=16,
        recovery=16,
        hitbox_func=item_hitbox,
        damage=0,
        frame_map=[0] * 16 + [1] * 16,  # 必須與duration等長
        frame_map_ratio = [16,16]
    ),
    AttackType.SUPER_FINAL:AttackData(
        attack_type=AttackType.SUPER_FINAL,
        effects=[AttackEffect.SHORT_STUN],
        duration=20,
        trigger_frame=0,
        recovery=16,
        hitbox_func=item_hitbox,
        damage=0,
        knock_back_power=[3.0,1.5],
        frame_map=[0] * 20,
        frame_map_ratio = [20],
        guardable=False
    ),
    AttackType.BRUST: AttackData(
        attack_type=AttackType.BRUST,
        effects=[AttackEffect.SHORT_STUN],
        duration=45,
        trigger_frame=15,
        recovery=2,
        hitbox_func=two_side_hitbox_func,
        damage=10,
        knock_back_power=[1.0,1.5],
        frame_map=[0] * 15 + [1]* 30,
        frame_map_ratio=[15, 30],
        effect_component_config={
            # 必須使用 Component 類別的字串名稱，以便動態載入
            "component_name": "AuraEffectComponent",
            # 這是您在 ComponentHost 中使用的 key，用於移除
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//brust_256.png",
                "expire_type": EffectExpireMode.ATTACK_END,
                "frame_width": 256,
                "frame_height": 256,
                "anim_speed": 12
            },
        },
        hit_stop_frames=5
    ),
    AttackType.DOWN_STOMP: AttackData(
        attack_type=AttackType.DOWN_STOMP,
        effects=[],
        duration = 45,
        trigger_frame = 0,
        contextual_trigger_frames=[10,20,30],
        recovery=1,
        hitbox_func=None,
        damage=8,
        knock_back_power=[0.0, -3.0],
        frame_map_ratio=[5]*9
    ),
    AttackType.DOWN_HAMMER: AttackData(
        attack_type=AttackType.DOWN_HAMMER,
        effects=[],
        duration=40,
        trigger_frame=0,
        contextual_trigger_frames=[10],
        recovery=1,
        hitbox_func=None,
        damage=18,
        knock_back_power=[0.0, -3.0],
        frame_map_ratio=[10,30],
    ),
    AttackType.BACKFLIP_SHOT: AttackData(
        attack_type=AttackType.BACKFLIP_SHOT,
        duration=90,
        trigger_frame=0,  # 🟢 支援三連射
        contextual_trigger_frames = [20, 30, 40],
        recovery=10,
        hitbox_func=None,  # 角色本體沒有判定，判定在飛行道具上
        #condition_func=lambda actor: actor.jump_z == 0, # 限制地面發動
        # 🟢 核心物理：向上躍起 + 向後推力 (假設重量 1.0)
        physical_change={
            'vz': 0.45,
            'vel_x': -0.3 # 向後噴射
        },
        effects=[AttackEffect.AFTER_IMAGE], # 加上殘影視覺效果
        frame_map_ratio=[20, 30, 40],
        hit_stop_frames=0
    ),
    AttackType.FEATHER_BOMB: AttackData(
        attack_type=AttackType.FEATHER_BOMB,
        effects=[AttackEffect.SHORT_STUN],
        duration=2,
        trigger_frame=1,
        recovery=0,
        hitbox_func=item_hitbox,
        damage=10,
        frame_map_ratio = [2]
    )
}