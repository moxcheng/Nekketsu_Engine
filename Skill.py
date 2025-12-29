from State_enum import *
import math
from Config import *
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
            self.character.x += dir_vec*self.data.force_move

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
        return self.character.jump_z > 0 or self.character.jump_z_vel > 0


class SwingAttackState(AttackState):
    def __init__(self, character, unit):
        attack_data = unit.get_swing_attack_data(character)
        if attack_data is None:
            return None
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
        if attack_data is None:
            return None
        super().__init__(character, attack_data)
        self.item = item
        self.thrown = False
        self.holdable = character.get_component("holdable")
        self.name = 'throw'

    def update(self):
        super().update()
        #print(f'ThrowAttackState 的 update {self.character.current_frame}/{self.character.attack_state.data.duration}')
        if not self.thrown and self.frame_index >= self.data.trigger_frame:
            self.thrown = True
            if self.item:
                offset = (self.character.width) + 0.3  # 原本是 ±1，改為角色寬 + 安全距離
                if self.character.facing == DirState.LEFT:
                    offset = -offset
                self.item.x = self.character.x + offset
                self.item.y = self.character.y
                self.item.z = self.character.z
                self.item.jump_z = self.character.jump_z + self.character.height*0.8
                self.item.jump_z_vel = 0.3
                move_rate =  self.character.throw_power
                if hasattr(self.item, 'speed'):
                    move_rate = self.item.speed
                self.item.vel_x = offset * move_rate # 水平飛行速度
                self.item.flying = True  # ✅ 切換 item 的控制狀態
                print(f'{self.item.name} 飛行!')
                self.item.held_by = None   #無人持有
                self.item.thrown_by = self.character
                self.holdable.held_object = None
                #self.character.attack_state = None  # ✅ 結束 attack_state


# === Attack Data Definition ===
class AttackData:
    def __init__(self, attack_type, duration, trigger_frame, hitbox_func, recovery=5, condition_func=None,
                 force_move=0, effects=None,knock_back_distance=0.0,knock_up_height=0.0, damage=10,
                 frame_map = None, cancel_table=None, physical_change=None, effect_component_config: dict = None, dialogue=None):

        self.attack_type = attack_type
        self.duration = duration
        self.trigger_frame = trigger_frame
        self.recovery = recovery
        self.hitbox_func = hitbox_func
        self.condition_func = condition_func or (lambda actor: True)
        self.force_move = force_move    #角色自己的位移
        self.effects = effects or []    #被擊中的效果
        self.knock_back_distance = knock_back_distance  #擊飛距離
        self.knock_up_height = knock_up_height  #擊飛高度
        self.damage = damage
        self.frame_map = frame_map or [0] * duration  # 預設全部使用第一張動畫
        assert frame_map is None or len(frame_map) == self.duration, "frame_map 長度需與 duration 相符"
        self.cancel_table = cancel_table or {}
        self.physical_change = physical_change or {}
        self.effect_component_config = effect_component_config or {}
        self.dialogue = dialogue

    def get_sprite_index(self, frame_index):
        return self.frame_map[frame_index]

    def can_use(self, actor):
        return self.condition_func(actor)

    def get_hitbox(self, x, y, facing, actor=None):
        try:
            return self.hitbox_func(x, y, facing, actor)
        except TypeError:
            return self.hitbox_func(x, y, facing)
    def get_damage(self, attacker=None):
        if callable(self.damage):
            return self.damage(attacker)
        return self.damage



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
    y_top = y+h*0.6
    y_bottom = y + h * 0.8

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
attack_data_dict = {
    AttackType.SLASH: AttackData(
        attack_type=AttackType.SLASH,
        duration=60,
        trigger_frame=30,
        recovery=15,
        hitbox_func=front_hitbox_func,
        condition_func=lambda actor: actor.state != MoveState.JUMP and actor.state != MoveState.FALL,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.BURN],
        knock_up_height = 5.0,
        knock_back_distance=1.0,
        damage = 20,
        frame_map = [0]*15 + [1]*10 + [2]*35   #必須與duration等長
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
        cancel_table = {AttackType.SLASH: 12, AttackType.PUNCH: 8, AttackType.KICK: 8}
    ),
    AttackType.MAHAHPUNCH: AttackData(
        attack_type=AttackType.MAHAHPUNCH,
        duration=64,
        trigger_frame=8,
        recovery=2,
        hitbox_func = punch_hitbox_func,
        condition_func=lambda actor: True,
        effects=[AttackEffect.SHORT_STUN],
        knock_up_height=0.5,
        knock_back_distance=2.0,
        damage = 7,
        frame_map = [0]*4 + [2]*4 + [1]*4+ [2]*4 + [1]*4+ [2]*4 + [1]*4+ [2]*4+ [1]*4+ [2]*4+ [1]*4+ [2]*4+ [1]*4+ [2]*4+ [1]*4+ [2]*4,
        effect_component_config={
            # 必須使用 Component 類別的字串名稱，以便動態載入
            "component_name": "AuraEffectComponent",
            # 這是您在 ComponentHost 中使用的 key，用於移除
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//hyakuretsu.png",
                "expire_type":EffectExpireMode.ATTACK_END,
                "alpha":128,
                "anim_speed":4
            }
        },
        dialogue = '啊達達達達達'
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
        cancel_table = {AttackType.SLASH: 24, AttackType.KICK: 18}
    ),
    AttackType.FLY_KICK: AttackData(
        attack_type=AttackType.FLY_KICK,
        duration=999,# ✅ 實際上會被 is_active() 覆蓋
        trigger_frame=8,
        recovery=15,
        hitbox_func=kick_hitbox_func,
        condition_func=lambda actor: actor.jump_z > 0,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_distance=1.0,
        damage=8
    ),
    AttackType.METEOFALL: AttackData(
        attack_type=AttackType.METEOFALL,
        duration=999,
        trigger_frame=8,
        recovery=15,
        hitbox_func=down_hitbox_func,
        condition_func=lambda actor: actor.state != MoveState.JUMP and actor.state != MoveState.FALL,
        effects=[AttackEffect.SHORT_STUN, AttackEffect.BURN],
        knock_up_height=1.5,
        knock_back_distance=2.0,
        damage=20,
        physical_change={'jump_z_vel':GRAVITY*-2},
        effect_component_config={
            # 必須使用 Component 類別的字串名稱，以便動態載入
            "component_name": "AuraEffectComponent",
            # 這是您在 ComponentHost 中使用的 key，用於移除
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_96.png",
                "expire_type":EffectExpireMode.LANDING
            }
        },
        dialogue="流星下墜!"
    ),
    AttackType.BASH: AttackData(
        attack_type=AttackType.BASH,
        duration=30,
        trigger_frame=3,
        recovery=10,
        hitbox_func=front_hitbox_func,
        condition_func=lambda actor: True,
        force_move=0.2,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_distance=2.0,
        damage = 5
    ),
    AttackType.SWING: AttackData(
        attack_type=AttackType.SWING,
        duration=32,
        trigger_frame=12,
        recovery=16,
        hitbox_func=punch_hitbox_func,
        effects=[AttackEffect.SHORT_STUN],
        damage = 10,
        frame_map = [0]*12 + [1]*20,   #必須與duration等長
    ),
    AttackType.THROW: AttackData(
        attack_type=AttackType.THROW,
        duration=32,
        trigger_frame=16,
        recovery=16,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        damage = 15,
        frame_map = [0]*16 + [1]*16,   #必須與duration等長
    ),
    AttackType.THROW_CRASH: AttackData(
        attack_type=AttackType.THROW,
        duration=2,
        trigger_frame=1,
        recovery=0,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_distance=1.0,
        damage=lambda attacker: getattr(attacker, "throw_damage", 2)  # 如果無此屬性就預設 2
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
    ),
    AttackType.SUPER_FINAL:AttackData(
        attack_type=AttackType.SUPER_FINAL,
        effects=[AttackEffect.SHORT_STUN],
        duration=20,
        trigger_frame=0,
        recovery=16,
        hitbox_func=item_hitbox,
        damage=0,
        knock_up_height=1.5,
        knock_back_distance=1.0,
        frame_map=[0] * 20
    )
}