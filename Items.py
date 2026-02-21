#from Component import ComponentHost, HoldFlyLogicMixin
from Entity import Entity
from Config import TILE_SIZE
import pygame
from State_enum import *
from Skill import *
import random

class Item(Entity):
    #Entity def __init__(self, x, y, map_info, width=1.0, height=1.0, weight=0.1):
    def __init__(self, x, y, map_info, **kwargs):
        super().__init__(x, y, map_info, **kwargs)
        self.unit_type = 'item'
        self.name = kwargs.get("name", "item")
        self.x = x
        self.y = y
        self.width = 1.0
        self.height = 1.0
        self.weight = kwargs.get("weight", 0.3)
        self.vz = 0.0
        self.jump_z = 0.0  # 可選：讓 item 可以「拋起」
        self.color = (150, 150, 150)  # 預設灰色
        self.timer = 0
        self.breakthrough = False
        self.attack_state = None
        self.swing_damage = 2
        self.terrain = map_info[0]
        self.map_w = map_info[1]
        self.map_h = map_info[2]
        self.hit_someone = False
        self.attacker_attack_data = None
        self.facing = DirState.RIGHT

    def clear_autonomous_behavior(self):
        self.is_thrown = False
        self.breakthrough = False
        self.attack_state = None
        self.hit_someone = False
        self.attacker_attack_data = None

    def is_pickable(self):
        #檢查是否能持有
        return not self.held_by
    def is_holdable(self):
        #檢查自身條件是否能繼續持有
        return True

    def get_tile_z(self, x, y):
        if 0 <= int(x) < self.map_w and 0 <= int(y) < self.map_h:
            return self.terrain[int(y), int(x)]
        return None
    def draw(self, win, cam_x, cam_y, tile_offset_y):
        terrain_z_offset = self.z * Z_DRAW_OFFSET
        px, py = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        w = int(self.width * TILE_SIZE)
        h = int(self.height * TILE_SIZE)
        pygame.draw.rect(win, self.color, (px, py, w, h))

    def is_pickable(self):
        return not self.held_by
    def update(self):
        self.timer -=1
        if self.external_control:
            self.update_by_external_control()
            return

        if self.held_by:
            self.on_held_location()
            return

        self.z = self.get_tile_z(self.x, self.y)

    # 修改 Item 的 box 獲取方式
    def get_interact_box(self):
        return self.get_physics_box()
    def get_hitbox(self):
        return self.get_physics_box()
    def get_hurtbox(self):
        return self.get_physics_box()

    def get_swing_attack_data(self, attacker):
        return AttackData(
            attack_type=AttackType.SWING,
            duration=32,
            trigger_frame=12,
            recovery=16,
            hitbox_func=item_hitbox,
            damage=lambda _: self.swing_damage if hasattr(self, 'swing_damage') else 7,
            effects=[AttackEffect.SHORT_STUN],
            frame_map=[0] * 12 + [1] * 20,  # 必須與duration等長
            frame_map_ratio = [12, 20]
        )
    def get_throw_attack_data(self, attacker):
        return AttackData(
        attack_type=AttackType.THROW,
        duration=32,
        trigger_frame=16,
        recovery=16,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        damage=lambda _: self.swing_damage if hasattr(self, 'throw_damage') else 7,
        frame_map = [0]*16 + [1]*16,   #必須與duration等長
        frame_map_ratio=[16, 16],
            power = attacker.throw_power if hasattr(attacker, 'throw_power') else 20
    )

    def is_out_of_bounds(self):
        return not (0 <= self.x < self.map_w and 0 <= self.y < self.map_h)

    def on_land_reaction(self, impact_energy=0, is_passive=False):
        """
        當物品落地時觸發。
        這是修復 Bug 的關鍵：落地即失去攻擊判定。
        """
        # 1. 解除投擲狀態
        self.is_thrown = False

        # 2. 清除攻擊數據，防止 SceneManager 繼續進行 Hitbox 檢測
        self.attack_state = None

        # 3. 重置碰撞黑名單 (如果有的話)，避免下次投擲失效
        self.hitting = []

        # 4. 物理靜止
        self.vel_x = 0

        print(f"DEBUG: {self.name} landed safely. Attack state cleared.")


class DestructibleMixin:
    """
    賦予物件 HP 系統與受擊反應。
    """

    def init_destructible(self, hp=50):
        self.max_hp = hp
        self.health = hp
        self.is_destructible = True
        self.is_destroyed = False

    def on_be_hit(self, attacker):
        from PhysicsUtils import get_overlap_center
        """覆寫 Entity 的預留接受器"""

        if not hasattr(self, 'health') or self.health <= 0:
            return

        # 1. 取得傷害數據
        damage = 1
        if hasattr(attacker, 'attack_state') and attacker.attack_state:
            damage = attacker.attack_state.data.get_damage(attacker)

        self.health -= damage
        print(f'{self.name} 受到 {damage} 傷害 ({self.health}/{self.max_hp})')

        # 2. 受擊視覺與震動
        if self.scene:
            print('aaaaaaaaaaa')
            hit_x, hit_y, hit_z = get_overlap_center(attacker.get_hitbox(), self.get_hurtbox())
            self.scene.create_effect(hit_x, hit_y, hit_z, 'hit')
            self.scene.trigger_shake(5, 3)

        # 3. 毀滅判定
        if self.health <= 0:
            self.on_destroyed()

    def on_destroyed(self):
        """毀滅時的標準程序：掉落物 -> 特效 -> 移除"""
        # 🟢 直接呼叫 Entity 層級的 drop_loot()
        if hasattr(self, 'drop_loot'):
            self.drop_loot()

        if self.scene:
            self.scene.create_effect(self.x + self.width / 2, self.y, self.z, 'dust')
            self.scene.mark_for_removal(self)


class BigRock(DestructibleMixin, Item):
    def __init__(self, x, y, map_info, **kwargs):
        # 大岩石體積較大，設定寬高為 1.5~2.0 單位
        super().__init__(x, y, map_info, name="big_rock", width=kwargs.get("width", 3.0), height=kwargs.get("height", 3.0), weight=kwargs.get("weight", 999), scene=kwargs.get("scene", None))
        self.init_destructible(hp=600)
        self.is_blocking = True  # 阻擋位移
        self.sheet = pygame.image.load("..\\Assets_Drive\\big_rock.png").convert_alpha()
        self.frame_width = 96
        self.frame_height = 192
        self.num_frames = 1
        self.frames = [
            self.sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(self.num_frames)
        ]
        self.combat_state = CombatState.NORMAL
    def is_pickable(self):
        return False
    def on_destroyed(self):
        """碎裂時的特定邏輯"""
        # 1. 觸發特效
        print(f"大石頭 on destroyed! {self.scene}")
        if self.scene:
            # 假設傳入當前中心座標與高度
            self.scene.create_effect(self.x+self.width/2, self.y, self.z, "crashed_rock")

            # 2. 掉出 2 個 Pickable Mid Rock
            for i in range(2):
                drop_x = self.x + random.uniform(-0.5, 0.5)
                drop_y = self.y + random.uniform(-0.5, 0.5)
                vel_x = random.uniform(-0.5, 0.5)
                vz = 0.2  # 向上噴出
                create_dropping_items(self, "mid_rock", x=drop_x, y=drop_y, vel_x=vel_x, vz=vz)
            self.scene.mark_for_removal(self)

    def draw(self, win, cam_x, cam_y, tile_offset_y=0):
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        rect = self.frames[0].get_rect(center=(cx , cy ))

        draw_x = cx - rect.width // 2
        draw_y = cy - rect.height

        win.blit(self.frames[0], rect)
        pygame.draw.rect(win, (255, 0, 0), rect, 1)
        self.draw_hurtbox(win, cam_x, cam_y, tile_offset_y)


class MidRock(Item):
    """可被撿起的小石塊原型"""

    def __init__(self, x, y, map_info, **kwargs):
        super().__init__(x, y, map_info, width=kwargs.get("width", 0.8), height=kwargs.get("height", 0.8), weight=kwargs.get("weight", 0.5), scene=kwargs.get("scene", None))
        self.unit_type = 'item'
        self.is_blocking = False  # 小石塊不會阻擋走路
        # 這裡可掛載 HoldableComponent 讓玩家撿起
        self.sheet = pygame.image.load("..\\Assets_Drive\\mid_rock.png").convert_alpha()
        self.frame_width = 64
        self.frame_height = 64
        self.num_frames = 4
        self.throw_damage = 7
        self.swing_damge = 6
        self.breakthrough = False
        self.frames = [
            self.sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(self.num_frames)
        ]
        self.cached_frame = self.frames[0]
    def draw(self, win, cam_x, cam_y, tile_offset_y=0):
        offset_x, offset_y = 0, 0
        if self.held_by:
            offset_x = self.held_by.width * TILE_SIZE * 0.3 * -1.0
            if self.held_by.facing == DirState.LEFT:
                offset_x *=-1.0
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        if self.held_by:
            offset_y -= self.held_by.height*TILE_SIZE*0.3
        selected_image = self.frames[int(self.x*10)%4]
        use_frame = selected_image
        if self.held_by:
            use_frame = self.cached_frame
        else:
            self.cached_frame = selected_image
        rect = use_frame.get_rect(center=(cx+offset_x, cy+offset_y))

        win.blit(use_frame, rect)
        pygame.draw.rect(win, (255, 0, 0), rect, 1)





class Rock(Item):
    def __init__(self, x, y, map_info):
        super().__init__(name="小石頭", x=x, y=y, map_info=map_info, weight=0.3)
        self.width = 1.0
        self.height = 1.0
        self.vz = 0
        self.color = (80, 80, 220)
        self.fly_color = (40, 80, 220)
        self.breakthrough = False
        self.throw_damage = 7
        self.swing_damge = 6

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        offset_x, offset_y = 0, 0
        if self.held_by:
            if self.held_by.facing == DirState.RIGHT:
                offset_x = self.held_by.width*TILE_SIZE*0.6
            elif self.held_by.facing == DirState.LEFT:
                offset_x = 0

        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)

        color = self.color
        if self.is_thrown:
            color = self.fly_color
        pygame.draw.circle(win, color, (cx, cy), int(TILE_SIZE * 0.4))
    def on_be_hit(self, attacker):
        #測試被打時的反應
        print(f'{self.name} 被 {attacker.name} 打到')


class ProjectileItem(Item):
    #飛行道具類，有生命週期
    def __init(self, **kwargs):
        super().__init__(**kwargs)
    def update(self):
        super().update()
        #消滅條件: 撞擊、超出邊界、壽命終了
        if self.hit_someone or self.is_out_of_bounds() or self.timer <= 0 or self.x <= self.width/2 or self.x > self.map_w-self.width/2 or self.jump_z <= 0:
            self.scene.mark_for_removal(self)

class Fireball(ProjectileItem):
    def __init__(self, x, y, map_info, **kwargs):
        super().__init__(map_info=map_info, name='fireball', x=x, y=y, weight=0.0, scene=kwargs.get("scene", None))
        self.owner = kwargs.get("owner", None)
        self.facing = self.owner.facing if self.owner else DirState.RIGHT
        self.speed = 0.15  # 自訂速度
        self.timer = 90  # 最多存活幀數
        self.width = 1.0
        self.height = 1.0
        self.vz = 0
        self.throw_damage = 13
        self.swing_damge = 0
        self.raw_image = pygame.image.load("..\\Assets_Drive\\hadouken.png").convert_alpha()
        self.image = self.raw_image

        self.ignore_side = self.owner.side if self.owner else "player"
        if self.facing == DirState.LEFT:
            self.image = pygame.transform.flip(self.raw_image, True, False)
        if self.owner:
            #self.attacker_attack_data = self.owner.attack_state.data
            self.x = self.owner.x + self.owner.width / 2
            self.y = self.owner.y + self.owner.height / 2


    def draw(self, win, cam_x, cam_y, tile_offset_y=0):
        offset_x, offset_y = 0, 0
        if self.held_by:
            offset_x = self.held_by.width * TILE_SIZE * 0.3 * -1.0
            if self.held_by.facing == DirState.LEFT:
                offset_x *=-1.0
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        if self.held_by:
            offset_y -= self.held_by.height*TILE_SIZE*0.3
        rect = self.image.get_rect(center=(cx+offset_x, cy+offset_y))

        #print('fireball.draw')
        win.blit(self.image, rect)
        pygame.draw.rect(win, (255, 0, 0), rect, 1)

    def get_throw_attack_data(self, attacker):
        return AttackData(
        attack_type=AttackType.THROW,
        duration=32,
        trigger_frame=20,
        recovery=8,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        damage=200,
        frame_map_ratio=[16,16],
        power=200,
        knock_back_power=[1.0,0.0],
    )

class Bullet(ProjectileItem):
    def __init__(self, x, y, map_info, **kwargs):
        super().__init__(name='子彈', x=x, y=y, map_info=map_info, weight=0.1)
        owner = kwargs.get("owner", None)
        self.owner = owner
        self.facing = owner.facing if owner else DirState.RIGHT
        self.speed = 0.5  # 自訂速度
        self.timer = 90  # 最多存活幀數
        self.width = 1.0
        self.height = 1.0
        self.vz = 0
        self.breakthrough = False
        self.throw_damage = 5
        self.swing_damge = 0
        self.raw_image = pygame.image.load("..\\Assets_Drive\\bullet.png").convert_alpha()
        self.image = self.raw_image
        self.ignore_side = [owner.side]
        if self.facing == DirState.LEFT:
            self.image = pygame.transform.flip(self.raw_image, True, False)
        if self.owner:
            #self.attacker_attack_data = self.owner.attack_state.data
            self.x = self.owner.x + self.owner.width / 2
            self.y = self.owner.y + self.owner.height / 2


    def draw(self, win, cam_x, cam_y, tile_offset_y=0):
        offset_x, offset_y = 0, 0
        if self.held_by:
            if self.held_by.facing == DirState.RIGHT:
                offset_x = self.held_by.width*TILE_SIZE*0.6
            elif self.held_by.facing == DirState.LEFT:
                offset_x = 0
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        rect = self.image.get_rect(center=(cx, cy))
        #print('fireball.draw')
        win.blit(self.image, rect)
        pygame.draw.rect(win, (255, 0, 0), rect, 1)

    def get_throw_attack_data(self, attacker):
        return AttackData(
        attack_type=AttackType.THROW,
        duration=48,
        trigger_frame=16,
        recovery=16,
        hitbox_func=item_hitbox,
        effects=[AttackEffect.SHORT_STUN],
        knock_back_power=[0.5,0.1],
        damage=lambda _: self.swing_damage if hasattr(self, 'throw_damage') else 1,
        frame_map = [0]*16 + [1]*32,   #必須與duration等長
        frame_map_ratio = [16,32]
    )

from PhysicsUtils import is_box_overlap

class ConsumableItem(Item):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def on_touched_me(self, picked_by):
        print(f'{self.name}被撿起')
        return
    def update(self):
        self.anim_timer += 1
        for unit in self.scene.get_units_by_name('player'):
            if is_box_overlap(self.get_interact_box(), unit.get_hurtbox()):
                self.on_touched_me(picked_by=unit)
                self.scene.mark_for_removal(self)
                break

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        # 計算畫面位置
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        # 每 15 frame 換一張
        frame_index = (self.anim_timer // 15) % self.num_frames
        frame = self.frames[frame_index]
        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height
        # 繪製當前幀
        win.blit(frame, (draw_x, draw_y))

class Coin(ConsumableItem):
    def __init__(self, x, y, map_info):
        #        super().__init__(name='子彈', x=x, y=y, map_info=map_info, weight=0.0)
        super().__init__(name='coin', x=x, y=y, map_info=map_info)
        #self.name = 'coin'
        self.sheet = pygame.image.load("..\\Assets_Drive\\Coin_4frame.png").convert_alpha()
        self.frame_width = 96
        self.frame_height = 96
        self.num_frames = 4
        self.frames = [
            self.sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(self.num_frames)
        ]

        self.width = 1.0
        self.height = 1.0
        self.timer = 600
        self.money = 0
        self.z = self.get_tile_z(x, y)
        self.anim_timer = 0

    def on_touched_me(self, picked_by):
        print(f'{picked_by.name} 撿起{self.money}元！')
        picked_by.money += self.money
        self.scene.add_floating_text(x=picked_by.x + picked_by.width / 2,
                                     y=picked_by.y + picked_by.height,
                                     value=f'+{self.money}',
                                     map_h=self.map_h,
                                     color=(255, 215, 0))

class MagicPotion(ConsumableItem):
    def __init__(self, x, y, map_info):
        #        super().__init__(name='子彈', x=x, y=y, map_info=map_info, weight=0.0)
        super().__init__(name='coin', x=x, y=y, map_info=map_info)
        #self.name = 'coin'
        self.sheet = pygame.image.load("..\\Assets_Drive\\Potion_4frame.png").convert_alpha()
        self.frame_width = 96
        self.frame_height = 96
        self.num_frames = 4
        self.frames = [
            self.sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            for i in range(self.num_frames)
        ]

        self.width = 1
        self.height = 1
        self.timer = 600
        self.mana = 1
        self.money=0
        self.z = self.get_tile_z(x, y)
        self.anim_timer = 0
    def on_touched_me(self, picked_by):
        unit = picked_by
        print(f'{unit.name} 獲得{self.mana}MP ！')
        unit.mp += self.mana
        self.scene.add_floating_text(x=unit.x + unit.width / 2,
                                     y=unit.y + unit.height,
                                     value=f'+{self.mana}',
                                     map_h=self.map_h,
                                     color=(30, 144, 255))


def create_dropping_items(drop_by, item_name, **kwargs):
    value = kwargs.get('value', 0)
    if item_name == 'coin':
        coin = Coin(drop_by.x, drop_by.y, [drop_by.terrain, drop_by.map_w, drop_by.map_h])
        coin.money = value
        drop_by.scene.register_unit(coin, side='netural', tags=['item'], type='item')
    elif item_name == 'potion':
        potion = MagicPotion(drop_by.x, drop_by.y, [drop_by.terrain, drop_by.map_w, drop_by.map_h])
        potion.mana = value
        drop_by.scene.register_unit(potion, side='netural', tags=['item'], type='item')
    elif item_name == 'rock':
        rock = Rock(drop_by.x, drop_by.y, [drop_by.terrain, drop_by.map_w, drop_by.map_h])
        drop_by.scene.register_unit(rock, side='netural', tags=['item'], type='item')
    elif item_name == 'mid_rock':
        rock = MidRock(drop_by.x, drop_by.y, [drop_by.terrain, drop_by.map_w, drop_by.map_h], scene=drop_by.scene)
        rock.x = kwargs.get("x", drop_by.x)
        rock.y = kwargs.get("y", drop_by.y)
        rock.vel_x = kwargs.get("vel_x", 0.0)
        rock.vz = kwargs.get("vz", 0.0)
        drop_by.scene.register_unit(rock, side='netural', tags=['item'], type='item')
