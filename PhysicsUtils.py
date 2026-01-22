# PhysicsUtils.py
from Config import TILE_SIZE

def get_absolute_z(unit):
    """取得單位的絕對高度 (地形高度 + 跳躍高度)"""
    return (unit.z if unit.z is not None else 0) + (unit.jump_z if hasattr(unit, 'jump_z') else 0)

def is_box_overlap(box1, box2, z_threshold=1.5):
    """
    統一的 AABB 碰撞檢測。
    傳入的 box 應包含 'x1', 'x2', 'y1', 'y2', 'z_abs' (絕對高度)。
    """
    # X 軸重疊
    x_overlap = box1['x1'] <= box2['x2'] and box1['x2'] >= box2['x1']
    # Y 軸重疊
    y_overlap = box1['y1'] <= box2['y2'] and box1['y2'] >= box2['y1']
    # Z 軸（絕對高度）重疊判斷
    z_dist = abs(box1.get('z_abs', 0) - box2.get('z_abs', 0))
    z_overlap = z_dist <= z_threshold

    return x_overlap and y_overlap and z_overlap

def get_overlap_center(box1, box2):
    """計算交疊區域中心 (用於產生特效位置)"""
    center_x = (max(box1['x1'], box2['x1']) + min(box1['x2'], box2['x2'])) / 2
    center_y = (max(box1['y1'], box2['y1']) + min(box1['y2'], box2['y2'])) / 2
    center_z = (max(box1.get('z_abs', 0), box2.get('z_abs', 0)) +
                min(box1.get('z_abs', 0), box2.get('z_abs', 0))) / 2
    return center_x, center_y, center_z