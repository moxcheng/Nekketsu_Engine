# PhysicsUtils.py
from Config import *

def get_absolute_z(unit):
    """取得單位的絕對高度 (地形高度 + 跳躍高度)"""
    return (unit.z if unit.z is not None else 0) + (unit.jump_z if hasattr(unit, 'jump_z') else 0)

def is_box_overlap(box1, box2, z_threshold=1.5):
    """
    統一的 AABB 碰撞檢測。
    傳入的 box 應包含 'x1', 'x2', 'y1', 'y2', 'z_abs' (絕對高度)。
    """
    if box1 is None or box2 is None:
        #提供給CONTEXTUAL SKILL使用
        return False
    # X 軸重疊
    x_overlap = box1['x1'] <= box2['x2'] and box1['x2'] >= box2['x1']
    # Y 軸重疊
    y_overlap = box1['y1'] <= box2['y2'] and box1['y2'] >= box2['y1']
    # Z 軸（絕對高度）重疊判斷
    z_dist = abs(box1.get('z_abs', 0) - box2.get('z_abs', 0))
    z_overlap = z_dist <= z_threshold

    return x_overlap and y_overlap and z_overlap


def get_overlap_center(box1, box2):
    """計算 AABB 碰撞盒交疊區域的 3D 中心點 (用於產生特效)"""
    # X, Y 同前
    cx = (max(box1['x1'], box2['x1']) + min(box1['x2'], box2['x2'])) / 2
    cy = (max(box1['y1'], box2['y1']) + min(box1['y2'], box2['y2'])) / 2
    # Z 軸：使用你新標準化的 z1, z2
    cz = (max(box1['z1'], box2['z1']) + min(box1['z2'], box2['z2'])) / 2

    return cx, cy, cz


def update_passive_physics(unit):
    """
    純物理位移計算。回傳此幀發生的物理事件清單。
    """
    events = []

    # --- Z 軸物理 ---
    if unit.vz != 0 or unit.jump_z > 0:
        old_vz = unit.vz
        unit.jump_z += unit.vz
        unit.vz -= GRAVITY * (1.0 + getattr(unit, 'weight', 0.1))

        # 🟢 關鍵修正：只要低於地表，立即強制歸零並回報
        if unit.jump_z <= 0:
            events.append(("LANDING", old_vz))
            unit.jump_z = 0  # 強制對齊地表
            unit.vz = 0  # 徹底切斷垂直動量

    # --- 2. 水平物理 (Momentum & Horizontal Movement) ---
    if unit.vel_x != 0:
        next_x = unit.x + unit.vel_x

        if check_wall_collision(unit, next_x):
            events.append(("WALL_HIT", unit.vel_x))
            # 物理反應：反彈
            unit.vel_x = -unit.vel_x * WALL_BOUNCE_REBOUND
            # 如果撞牆時在空中，給予微量上升力
            if unit.jump_z > 0:
                unit.vz = 0.15
        else:
            unit.x = next_x

        # 摩擦力衰減
        friction = FRICTION_AIR if unit.jump_z > 0 else FRICTION_GROUND
        unit.vel_x *= friction

        if abs(unit.vel_x) < STOP_THRESHOLD:
            unit.vel_x = 0
            events.append(("STOPPED", 0))

    return events

def check_wall_collision(unit, next_x):
    """偵測 next_x 是否撞牆或超出地圖邊界"""
    # 1. 檢查地圖左右邊界
    if next_x < 0 or next_x+unit.width > unit.map_w:
        return True

    # 2. 檢查地形高度差 (牆壁)
    # 取得角色當前高度與前方地塊高度
    if hasattr(unit, "vel_x"):
        vel_x = unit.vel_x
    else:
        vel_x = unit.vel_x
    tx = int(next_x + (0.8 if vel_x > 0 else 0.2))
    ty = int(unit.y + 0.5)

    target_z = unit.get_tile_z(tx, ty)
    if target_z is None:
        return True  # 超出索引視同撞牆
    if target_z is not None:
        # 如果目標地塊比當前位置高出 2 階以上，視為撞牆
        if target_z - unit.z >= 2:
            return True
    return False

def on_fly_z(selfunit):
    hit_someone = False
    # 1. 拋物線重力感：減低下降速度 (weight 影響下墜快慢)
    selfunit.vz -= selfunit.weight * FLY_GRAVITY_MULT  # 降低重力常數讓拋物線更明顯
    selfunit.jump_z += selfunit.vz

    for unit in selfunit.scene.get_units_with_type('character'):
        if not unit.is_alive() or unit in ([selfunit, selfunit.thrown_by] + selfunit.hitting):
            continue
        if hasattr(selfunit, 'ignore_side') and unit.side in selfunit.ignore_side:
            continue

        if selfunit.check_collision(unit):
            hit_someone = True
            selfunit.hitting.append(unit)

            # --- 🟢 核心修正：撞到人且自己快沒血時，強制準備落地 ---
            # 不要在這裡呼叫物理，而是設定標記，讓下一幀或本幀結束時自然落地
            if hasattr(selfunit, 'health') and selfunit.health <= 0:
                selfunit.vel_x *= 0.1
                selfunit.vz = -0.1
                selfunit.flying = False

            # --- 核心改動：動量損耗與物理反饋 ---
            # 2. 根據重量比計算動量損失 (模擬大撞小/小撞大)
            # 假設 self.weight 是 0.1, unit 預設也是 0.1 (可透過 getattr 抓取)
            target_weight = getattr(unit, 'weight', 0.1)
            momentum_loss = min(UNIT_IMPACT_MOMENTUM_LOSS_MAX, target_weight / (self.weight + 0.01) * 0.5)

            # 減損 X 軸速度
            impact_vel = selfunit.vel_x
            selfunit.vel_x *= (1.0 - momentum_loss)

            # 3. 擊中後的微幅彈起 (增加打擊的震動感)
            selfunit.vz = abs(impact_vel) * UNIT_IMPACT_UP_VZ_FACTOR

            # 觸發受擊
            atk_data = selfunit.attacker_attack_data  # 優先使用物件自帶的備份數據
            if not atk_data and selfunit.thrown_by:
                # 如果自帶數據為空，才去嘗試找投擲者的當前狀態，並增加安全門檻
                if hasattr(selfunit.thrown_by, 'attack_state') and selfunit.thrown_by.attack_state:
                    atk_data = selfunit.thrown_by.attack_state.data
            if atk_data:
                unit.on_hit(selfunit.thrown_by, atk_data)

            # 🟢 新增：飛行者(self)也要受傷
            if selfunit.unit_type == 'character':
                # 傷害值可以根據當前速度 vel_x 決定，越快越痛
                impact_damage = int(abs(impact_vel) * 20)
                # 建立一個虛擬的攻擊數據，代表「撞擊傷害」
                collision_atk = AttackData(AttackType.THROW_CRASH, 1, 0, None, damage=impact_damage)
                selfunit.on_hit(unit, collision_atk)  # 這裡 unit 變成攻擊來源

            # 4. 判斷是否停止飛行 (動量過低時才落地)
            is_breakthrough = getattr(self, 'breakthrough', False)
            if not is_breakthrough and abs(selfunit.vel_x) < 0.05:
                selfunit.down_to_ground()
                return hit_someone

    # --- 5. 觸地彈跳邏輯 (取代直接 down_to_ground) ---
    if selfunit.jump_z <= 0:
        impact_vz = abs(selfunit.vz)

        # 執行傷害計算
        if selfunit.unit_type == 'character' and impact_vz > 0.3:
            fall_damage = int((impact_vz - 0.3) * 20)
            if fall_damage > 0:
                fall_atk = AttackData(AttackType.THROW_CRASH, 1, 0, None, damage=fall_damage)
                selfunit.on_hit(None, fall_atk)

        # 🟢 修正：如果已經死亡，不准彈起，直接強制落地
        if hasattr(selfunit, 'health') and selfunit.health <= 0:
            selfunit.down_to_ground()  # 強制設定 self.flying = False 並重置速度
            return hit_someone

        # 只有活著的人才執行彈跳
        if impact_vz > BOUNCE_THRESHOLD_VZ:
            selfunit.vz = -selfunit.vz * GROUND_BOUNCE_REBOUND
            selfunit.vel_x *= FRICTION_GROUND
        else:
            selfunit.down_to_ground()
    return hit_someone

def update_hold_fly_position(self):
    hit_someone = False
    if self.held_by:
        self.on_held_location()
    elif self.flying:
        #可能是item或character, 只有character需要反彈
        next_x = self.x + self.vel_x

        # 🟢 修正點: 增加速度檢查門檻
        # 如果速度已經低於停止閾值，且偵測到碰撞，直接停止飛行
        if abs(self.vel_x) < STOP_THRESHOLD:
            if self.check_wall_collision(next_x):
                self.vel_x = 0
                self.flying = False  # 停止飛行狀態，避免下一幀繼續判定
                return hit_someone

        # 🟢 修正點 1: 確保所有飛行物(含Item)都執行撞牆偵測
        if self.check_wall_collision(next_x):
            # 🟢 修正點 2: 座標回退 (防止滲透牆壁)
            # 將物件推離牆壁一點點，確保它下一幀不會再卡在同一個判定區
            # 假設向右撞，就往左推；向左撞，就往右推
            push_back = 0.05 if self.vel_x > 0 else -0.05
            self.x -= push_back

            # 🟢 修正點：如果撞牆後已經沒血了，強制停止飛行並進入落地反應
            if hasattr(self, 'health') and self.health <= 0:
                self.vel_x = 0
                self.flying = False
                self.vz = -0.1
                self.z=0
                if hasattr(self, 'check_ground_contact'):
                    self.check_ground_contact()
                return hit_someone

            if self.unit_type == 'character':
                # 🟢 修正後的撞牆傷害：加入 0.2 的速度門檻
                impact_speed = abs(self.vel_x)
                if impact_speed > 0.2:
                    # 只有超過門檻的部分才計算傷害，倍率調低至 15
                    wall_damage = int((impact_speed - 0.2) * 15)
                    if wall_damage > 0:
                        wall_atk = AttackData(AttackType.THROW_CRASH, 1, 0, None, damage=wall_damage)
                        self.on_hit(None, wall_atk)  # 傳 None 表示環境傷害
            self.vel_x = -self.vel_x * WALL_BOUNCE_REBOUND
            # 只有當反彈力道還夠時，才給予垂直彈跳 vz
            if abs(self.vel_x) > STOP_THRESHOLD:
                self.vz = WALL_BOUNCE_REBOUND
            else:
                self.vel_x = 0
                self.flying = False  # 力道太小，直接落地/停下

            print(f'[PHYSICS] {self.name} 撞牆反彈! 新速度: {self.vel_x:.2f}')
            if self.scene and self.weight > 0.1:
                self.scene.trigger_shake(10, 5)

            # 為了避免連續觸發，此幀不執行位移更新
            return hit_someone

        # 正常位移更新
        self.x += self.vel_x
        hit_someone = self.on_fly_z()
    return hit_someone