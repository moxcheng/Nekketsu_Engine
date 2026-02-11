from Component import ComponentHost,HoldFlyLogicMixin
from Config import *
class Entity(ComponentHost, HoldFlyLogicMixin):
    def __init__(self, x, y, map_info, width=1.0, height=1.0, weight=0.1):
        super().__init__()
        # 空間座標
        # 地圖資訊
        self.terrain = map_info[0]
        self.map_w = map_info[1]
        self.map_h = map_info[2]
        # 物理屬性
        self.width = width
        self.height = height
        self.weight = weight

        self.x = max(width/2, min(x, self.map_w-width/2))
        self.y = max(height/2, min(y, self.map_h-height/2))
        self.z = 0.0
        self.jump_z = 0.0


        #加速度
        self.vel_x = 0.0  # 統一整合
        self.vz = 0.0  # 統一整合
        self.hitting = []   #物品碰撞



        # 邏輯狀態
        self.unit_type = None  # 由子類別設定 'character' 或 'item'
        self.side = 'neutral'
        self.held_by = None
        self.thrown_by = None
        self.flying = False
        self.hit_someone = False
        self.attacker_attack_data = None

        # 視覺
        self.current_frame = 0
        self.draw_alpha = 255
        self.cached_pivot = (0, 0)
        self.z = self.get_tile_z(self.x, self.y)
        self.hitting_cache = []

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
    def get_physics_box(self):
        """物件的最基礎物理體積，用於受傷、互動、拼招"""
        return {
            'x1': self.x, 'x2': self.x + self.width,
            'y1': self.y, 'y2': self.y + self.height,
            'z_abs': self.get_abs_z(),
            'z1': self.get_abs_z(),
            'z2': self.get_abs_z() + self.height
        }

    def on_hit(self, attacker, attack_data):
        """保險用空函式：物品被誤打到時不會報錯"""
        pass

    def get_hitbox(self):
        return None  # 預設沒有攻擊判定



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