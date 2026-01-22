from Component import ComponentHost,HoldFlyLogicMixin

class Entity(ComponentHost, HoldFlyLogicMixin):
    def __init__(self, x, y, map_info, width=1.0, height=1.0, weight=0.1):
        super().__init__()
        # 空間座標
        self.x = x
        self.y = y
        self.z = 0.0
        self.jump_z = 0.0

        # 物理屬性
        self.width = width
        self.height = height
        self.weight = weight
        #加速度
        self.vel_x = 0.0  # 統一整合
        self.vz = 0.0  # 統一整合

        # 地圖資訊
        self.terrain = map_info[0]
        self.map_w = map_info[1]
        self.map_h = map_info[2]

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
