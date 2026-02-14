#from Component import ComponentHost, HoldFlyLogicMixin
from Entity import Entity
from Config import TILE_SIZE
import pygame
from State_enum import *
from Skill import *


class Item(Entity):
    #Entity def __init__(self, x, y, map_info, width=1.0, height=1.0, weight=0.1):
    def __init__(self, name, x, y, map_info, weight=0.3):
        super().__init__(x, y, map_info, weight=weight)
        self.unit_type = 'item'
        self.name = name
        self.x = x
        self.y = y
        self.width = 1.0
        self.height = 1.0
        self.weight = weight
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
    # def get_swing_attack_data(self, attacker):
    #     return AttackData(
    #         attack_type=AttackType.SWING,
    #         duration=32,
    #         trigger_frame=12,
    #         recovery=16,
    #         hitbox_func=item_hitbox,
    #         damage=lambda _: self.swing_damage if hasattr(self, 'swing_damage') else 7,
    #         effects=[AttackEffect.SHORT_STUN],
    #         frame_map=[0] * 12 + [1] * 20,  # 必須與duration等長
    #     )
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
        frame_map_ratio=[16, 16]
    )

    def is_out_of_bounds(self):
        return not (0 <= self.x < self.map_w and 0 <= self.y < self.map_h)


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



class Fireball(Item):
    def __init__(self, x, y, map_info, owner=None):
        super().__init__(name='fireball', x=x, y=y, map_info=map_info, weight=0.0)
        self.owner = owner
        self.facing = owner.facing
        self.speed = 0.15  # 自訂速度
        self.timer = 90  # 最多存活幀數
        self.width = 1.0
        self.height = 1.0
        self.vz = 0
        self.throw_damage = 13
        self.swing_damge = 0
        self.raw_image = pygame.image.load("..\\Assets_Drive\\hadouken.png").convert_alpha()
        self.image = self.raw_image

        self.ignore_side = [owner.side]
        if self.facing == DirState.LEFT:
            self.image = pygame.transform.flip(self.raw_image, True, False)
        if self.owner:
            #self.attacker_attack_data = self.owner.attack_state.data
            self.x = self.owner.x + self.owner.width / 2
            self.y = self.owner.y + self.owner.height / 2


    def update(self):
        super().update()
        if self.hit_someone or self.is_out_of_bounds() or self.timer <= 0 or self.x <= self.width/2 or self.x > self.map_w-self.width/2 :
            self.scene.mark_for_removal(self)


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

    def get_hurtbox(self):
        # 🟢 修正：讓火球的物理判定盒在 Z 軸向上與向下延伸
        # 這樣火球即使在胸口高度，也能撞到稍微跳起或倒地的敵人
        box = self.get_physics_box()
        box['z1'] = self.get_abs_z() - 1.0  # 向下延伸
        box['z2'] = self.get_abs_z() + 1.0  # 向上延伸
        box['z_abs'] = self.get_abs_z()
        return box

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

class Bullet(Item):
    def __init__(self, x, y, map_info, owner=None):
        super().__init__(name='子彈', x=x, y=y, map_info=map_info, weight=0.1)
        self.owner = owner
        self.facing = owner.facing
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


    def update(self):
        super().update()
        if self.hit_someone or self.is_out_of_bounds():
            self.scene.mark_for_removal(self)


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

class Coin(Item):
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

    def update(self):
        self.anim_timer += 1
        for unit in self.scene.get_units_by_name('player'):
            if is_box_overlap(self.get_interact_box(), unit.get_hurtbox()):
                print(f'{unit.name} 撿起{self.money}元！')
                unit.money += self.money
                self.scene.add_floating_text(x=unit.x + unit.width / 2,
                        y=unit.y + unit.height,
                        value=f'+{self.money}',
                        map_h=self.map_h,
                        color=(255, 215, 0))
                self.scene.mark_for_removal(self)
                break

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        # win.blit(frame, (px, py))



        # 計算畫面位置
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        # 每 15 frame 換一張，共 4 張動畫
        frame_index = (self.anim_timer // 15) % self.num_frames
        frame = self.frames[frame_index]
        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height

        # 繪製當前幀
        win.blit(frame, (draw_x, draw_y))

class MagicPotion(Item):
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

    def update(self):
        self.anim_timer += 1
        for unit in self.scene.get_units_by_name('player'):
            if is_box_overlap(self.get_interact_box(), unit.get_hurtbox()):
                print(f'{unit.name} 獲得{self.money}點mp！')
                unit.mp += self.mana
                self.scene.add_floating_text(x=unit.x + unit.width / 2,
                        y=unit.y + unit.height,
                        value=f'+{self.mana}',
                        map_h=self.map_h,
                        color=(30, 144, 255))
                self.scene.mark_for_removal(self)
                break

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        # 計算畫面位置
        cx, cy = self.calculate_cx_cy(cam_x, cam_y, tile_offset_y)
        # 每 15 frame 換一張，共 4 張動畫
        frame_index = (self.anim_timer // 15) % self.num_frames
        frame = self.frames[frame_index]
        frame_rect = frame.get_rect()
        draw_x = cx - frame_rect.width // 2
        draw_y = cy - frame_rect.height

        # 繪製當前幀
        win.blit(frame, (draw_x, draw_y))