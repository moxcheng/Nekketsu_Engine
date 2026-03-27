from Component import ComponentHost,HoldFlyLogicMixin
from Config import *
import pygame
class Entity(ComponentHost, HoldFlyLogicMixin):
    def __init__(self, x, y, map_info, **kwargs):
        super().__init__()
        # 空間座標
        # 地圖資訊

        self.terrain = map_info[0]
        self.map_w = map_info[1]
        self.map_h = map_info[2]
        # 物理屬性
        width = kwargs.get("width", 1.0)
        height = kwargs.get("height", 1.0)
        weight = kwargs.get("weight", 1.0)
        self.scene = kwargs.get("scene", None)
        self.width = width
        self.height = height
        self.weight = weight

        # 🟢 修正：增加 0.1 的安全邊距 (Safe Margin)，防止 int() 轉換後的邊界溢出
        margin = 0.1
        self.x = max(margin, min(x, self.map_w - width - margin))
        self.y = max(margin, min(y, self.map_h - margin))

        self.z = 0.0
        self.jump_z = 0.0


        #加速度
        self.vel_x = 0.0  # 統一整合
        self.vz = 0.0  # 統一整合
        self.hitting = []   #物品碰撞
        #重力縮放
        self.gravity_scale = 1.0



        # 邏輯狀態
        self.unit_type = None  # 由子類別設定 'character' 或 'item'
        self.side = 'neutral'
        self.held_by = None
        self.thrown_by = None
        self.is_thrown = False
        self.hit_someone = False
        self.attacker_attack_data = None

        # 視覺
        self.current_frame = 0
        self.draw_alpha = 255
        self.cached_pivot = (0, 0)
        self.z = self.get_tile_z(self.x, self.y)
        self.hitting_cache = []
        self.is_blocking = False  # 🟢 預設不阻擋
        self.is_destructible = False  # 預設不可破壞

    def get_tile_z(self, x, y):
        """通用高度獲取，增加邊界夾緊保護"""
        # 將座標夾緊在有效索引範圍內
        safe_x = max(0, min(int(x), self.map_w - 1))
        safe_y = max(0, min(int(y), self.map_h - 1))

        try:
            return self.terrain[safe_y, safe_x]
        except (IndexError, TypeError):
            return 0.0  # 萬一真的出錯，回傳最低高度

    def get_abs_z(self):
        """計算絕對高度，用於 PhysicsUtils"""
        return (self.z or 0) + self.jump_z

    # Entity.py
    def get_physics_box(self, specified_x=None, specified_y=None):
        """物件的最基礎物理體積，用於受傷、互動、拼招"""
        base_x, base_y = specified_x, specified_y
        if specified_x is None:
            base_x = self.x
        if specified_y is None:
            base_y = self.y
        return {
            'x1': base_x, 'x2': base_x + self.width,
            'y1': base_y, 'y2': base_y + self.width,
            'z_abs': self.get_abs_z(),
            'z1': self.get_abs_z(),
            'z2': self.get_abs_z() + self.height
        }

    def on_hit(self, attacker, attack_data):
        """保險用空函式：物品被誤打到時不會報錯"""
        pass

    def get_hitbox(self):
        return None  # 預設沒有攻擊判定

    def drop_loot(self):
        return None
    # Entity.py
    def get_feet_box(self, nx=None, ny=None):
        """用於位移阻擋的微小判定區"""
        curr_x = nx if nx is not None else self.x
        curr_y = ny if ny is not None else self.y

        # 這裡只取腳底中心 20% 的寬度，以及極薄的深度
        padding_x = self.width*0.2
        padding_y = self.width*0.1

        return {
            'x1': curr_x + padding_x,
            'x2': curr_x + self.width - padding_x,
            'y1': curr_y - padding_y,
            'y2': curr_y + padding_y,
            'z1': self.get_abs_z(),
            'z2': self.get_abs_z() + 0.5
        }

    def check_ground_contact(self):
        """
        Entity 層級的基礎落地：只處理物理，不處理狀態。
        """
        tx = int(self.x + self.width / 2)
        ty = int(self.y + self.height * 0.1)
        below_z = self.get_tile_z(tx, ty)

        self.jump_z = 0
        self.vz = 0
        self.vel_x = 0
        if below_z is not None:
            self.z = below_z

        # 🟢 呼叫一個 Hook 讓子類別擴充行為 (例如 Character 的硬直)
        self.on_land_reaction()

    def on_land_reaction(self, impact_energy=0, is_passive=False):
        """落地反應：Entity 預設不做事，Character 會在此處清除攻擊狀態與設硬直"""
        pass

    def set_rigid(self, duration):
        """安全空函式：防止 SceneManager 呼叫 Item.set_rigid 時崩潰"""
        pass

    def on_be_hit(self, attacker):
        """安全空函式：當 SceneManager 判定物品被打到時呼叫"""
        pass
    def update(self):
        pass
    def draw_hurtbox(self, win, cam_x, cam_y, tile_offset_y, terrain_z_offset=0):
        # === 顯示 hurtbox ===
        hurtbox = self.get_hurtbox()
        hx1 = int(hurtbox['x1'] * TILE_SIZE) - cam_x
        hy1 = int((self.map_h - hurtbox['y2']) * TILE_SIZE - self.jump_z * TILE_SIZE - terrain_z_offset) - cam_y + tile_offset_y
        hx2 = int(hurtbox['x2'] * TILE_SIZE) - cam_x
        hy2 = int((self.map_h - hurtbox['y1']) * TILE_SIZE - self.jump_z * TILE_SIZE - terrain_z_offset) - cam_y + tile_offset_y

        pygame.draw.rect(win, (0, 0, 255), (hx1, hy1, hx2 - hx1, hy2 - hy1), 2)