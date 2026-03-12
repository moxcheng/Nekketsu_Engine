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
    # # Z 軸（絕對高度）重疊判斷
    # z_dist = abs(box1.get('z_abs', 0) - box2.get('z_abs', 0))
    # z_overlap = z_dist <= z_threshold
    # 🟢 修正：區間重疊判定 (Interval Overlap)
    # 比起中心點 z_abs 的距離，判斷 [z1, z2] 兩個區間是否有交集更精確
    # 公式：max(z1_a, z1_b) <= min(z2_a, z2_b)
    z1_a, z2_a = box1['z1'], box1['z2']
    z1_b, z2_b = box2['z1'], box2['z2']

    # 如果有傳入自定義門檻（如 victim.height），則擴張判定區間
    if z_threshold is not None:
        # 將攻擊方的判定區間向下延伸，確保能打到地面的目標
        z1_a -= z_threshold * 0.5

    z_overlap = max(z1_a, z1_b) <= min(z2_a, z2_b)
    x11, x12 = box1['x1'], box1['x2']
    x21, x22 = box2['x1'], box2['x2']
    #print(f'is_box_overlap: x = {x_overlap}, ({x11:.2f},{x12:.2f}), ({x21:.2f},{x22:.2f})')

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

    is_flying_projectile = getattr(unit, 'is_thrown', False) and getattr(unit, 'weight', 0.1) == 0
    # --- Z 軸物理 ---
    if unit.vz != 0.0 or unit.jump_z > 0.0:
        old_vz = unit.vz
        unit.jump_z += unit.vz


        # if -0.1 < unit.vz < 0.1:
        #     current_gravity = GRAVITY * 0.5

        if not is_flying_projectile:
            current_gravity = GRAVITY
            #current_gravity = 0.25*GRAVITY if -0.15 < unit.vz < 0 else GRAVITY
            print(f'[{unit.current_frame}] vz={unit.vz}, gravity={current_gravity}, jump_z={unit.jump_z}')
            #增加最高點璇停
            unit.vz -= current_gravity
        else:
            #不受重力影響
            unit.vz = 0

        # 🟢 關鍵修正：只要低於地表，立即強制歸零並回報
        if unit.jump_z <= 0:
            impact_energy = (unit.z + abs(old_vz) * 2) * getattr(unit, 'weight', 1.0) * 10.0
            events.append(("LANDING", impact_energy))
            unit.jump_z = 0  # 強制對齊地表
            unit.vz = 0  # 徹底切斷垂直動量
            unit.check_ground_contact()

    # --- 2. 水平物理 (Momentum & Horizontal Movement) ---
    if unit.vel_x != 0:
        next_x = unit.x + unit.vel_x

        if check_wall_collision(unit, next_x) and not is_flying_projectile:
            events.append(("WALL_HIT", unit.vel_x))
            # 物理反應：反彈
            unit.vel_x = -unit.vel_x * WALL_BOUNCE_REBOUND
            # 如果撞牆時在空中，給予微量上升力
            if unit.jump_z > 0:
                unit.vz = 0.15
        else:
            unit.x = next_x

        # 摩擦力衰減
        if not is_flying_projectile:
            #飛行道具不受摩擦力
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

