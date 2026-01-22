# Component.py
from Skill import *

class Component:
    """所有元件的基底類別"""
    def __init__(self):
        self.owner = None  # 被掛載者（通常是 Character 或 Item）
    def on_attach(self, owner):
        """當元件被加入到 host 上時呼叫"""
        self.owner = owner
    def update(self):
        """每 frame 執行的邏輯"""
        pass
    def override_attack_intent(self, intent: str) -> str | None:
        """
        給元件機會改寫目前的攻擊意圖。
        回傳新意圖字串（例如 'pickup_item'），或 None 表示不修改。
        """
        return None

    def is_within_range(self, box1, box2, max_dist=0.5):
        # 可加入中心點距離的計算
        cx1 = (box1['x1'] + box1['x2']) / 2
        cy1 = (box1['y1'] + box1['y2']) / 2
        cx2 = (box2['x1'] + box2['x2']) / 2
        cy2 = (box2['y1'] + box2['y2']) / 2
        dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
        return dist <= max_dist

class ComponentHost:
    """可掛載 Component 的物件基底（如角色、道具）"""
    def __init__(self):
        self.components = {}
        # 用於給scene註冊物件並查詢
        self.scene = None
        self.side = None
        self.tags = []
        self.type = None
        #<==
        #紀錄是否被拿取的狀態!
        self.held_by = None
        self.thrown_by = None
        #給storyScriptRunner使用
        self.external_control = None
        self.unit_type = None

    #劇情演出用
    def clear_autonomous_behavior(self):
        self.held_by = None
        self.thrown_by = None

    def set_external_control(self, ctrl_dict):
        """設定劇情用的外部控制"""
        self.external_control = ctrl_dict
        if hasattr(self, "set_rigid"):
            self.set_rigid(ctrl_dict.get("duration", 30))  # 若角色支援硬直則設置

    def update_by_external_control(self):
        if not self.external_control:
            return
        ctrl = self.external_control
        act = ctrl.get('action')

        if act == 'move' and hasattr(self, 'x') and hasattr(self, 'y'):
            target_x, target_y = ctrl['to']
            dx = target_x - self.x
            dy = target_y - self.y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < 0.1:
                self.external_control = None
                return
            move_rate = ctrl.get('speed', 0.05)
            self.x += dx / dist * move_rate
            self.y += dy / dist * move_rate
            # if hasattr(self, 'facing') and dx != 0:
            #     self.facing = DirState.RIGHT if dx > 0 else DirState.LEFT
            if hasattr(self, 'state'):
                self.state = MoveState.WALK
        elif act == 'attack' and hasattr(self, 'attack'):
            self.attack(ctrl['skill'])
            self.external_control = None
        elif act == 'knockback' and hasattr(self, 'combat_state'):
            self.combat_state = CombatState.KNOCKBACK
            self.knockback_vel_x = ctrl.get('vx', 0.0)
            self.knockback_vel_z = ctrl.get('vz', 0.0)
            self.external_control = None
        elif act == 'set_z' and hasattr(self, 'z'):
            self.z = ctrl.get('value', 0)
            self.external_control = None
        elif act == 'disappear':
            if hasattr(self, 'scene'):
                self.scene.mark_for_removal(self)
            self.external_control = None

    def add_component(self, name, component: Component):
        """加入一個元件（用 name 做識別鍵）"""
        self.components[name] = component
        component.on_attach(self)
    def get_component(self, name):
        return self.components.get(name)
    def remove_component(self, name):
        if name in self.components:
            del self.components[name]
    def update_components(self):
        components_to_update = list(self.components.values())
        for component in components_to_update:
            component.update()
    def override_attack_intent(self, intent: str) -> str:
        """讓所有元件有機會改寫攻擊意圖"""
        for component in self.components.values():
            #print(f'ComponentHost 的 override_attack_intent')
            new_intent = component.override_attack_intent(intent)
            if new_intent:
                return new_intent
        return intent
    def on_picked_up(self, holder):
        print(f'{self.name} 呼叫 on_pick_up, holder={holder.name}')
        self.held_by = holder
        self.x = holder.x
        self.y = holder.y
        self.jump_z = holder.jump_z
    # def on_thrown(self):
    #     print('aaaaaaaaaaaaaaaaaaaaaaaaaa')
    #     self.held_by = None

    def get_swing_attack_data(self, attacker):
        # fallback 預設：回傳 None，讓開發者知道需要自行實作
        raise NotImplementedError(f"{self.__class__.__name__} 沒有實作 get_swing_attack_data()")
    def get_throw_attack_data(self, attacker):
        # fallback 預設：回傳 None，讓開發者知道需要自行實作
        raise NotImplementedError(f"{self.__class__.__name__} 沒有實作 get_throw_attack_data()")

    def calculate_cx_cy(owner, cam_x, cam_y, tile_offset_y):
        """計算物件『腳底中心』在螢幕上的座標"""
        safe_z = owner.z if owner.z is not None else 0
        #safe_z = owner.z
        terrain_z_offset = safe_z * Z_DRAW_OFFSET
        # cx: 腳底中心 X
        cx = int((owner.x + owner.width / 2) * TILE_SIZE) - cam_x
        # cy: 腳底中心 Y (不扣除 owner.height)
        cy = int((owner.map_h - owner.y) * TILE_SIZE - owner.jump_z * 5 - terrain_z_offset) - cam_y + tile_offset_y
        return cx, cy

class HoldableComponent(Component):
    def __init__(self, owner):
        super().__init__()
        self.owner=owner
        self.target_item = None  # 暫存接觸中的 item
        self.held_object = None

    def override_attack_intent(self, intent: str):
        # attack_intent = z/x/c_attack, 對應到招式表
        obj_name = ''
        if self.held_object:
            obj_name = self.held_object.name
        #print(f'HoldableComponent 的 override_attack_intent====={intent}====({obj_name})')
        # 取得持有者當前的輸入狀態
        # 假設 Player.input_intent 會把按鍵狀態存入最後的意圖中，或者直接讀取 owner 的 last_intent

        (u,d,l,r) = self.owner.last_intent.get('dirs', False)

        if self.held_object:
            print(f'手上持有{self.held_object.name}')
            if intent == "z_attack":
                return "swing_item"
            elif intent == "x_attack":
                return "throw_item"
        elif intent == "z_attack" and self.find_nearby_item() and self.owner.jump_z == 0 and d:
            return "pickup_item"
        return intent


    def update(self):
        if self.owner.is_able_hold_item() and self.held_object:
            #持有者無法控制
            print(f'HoldableComponent 的 update 的 無法持有武器')
            if self.held_object:
                self.held_object.held_by = None
            self.held_object = None
        if self.held_object and not self.held_object.is_holdable():
            #物品不給繼續拿著
            print(f'HoldableComponent 的 update 的 放棄拾取 {self.held_object.name}')
            self.held_object.held_by = None
            self.held_object = None
            if hasattr(self, "into_normal_state"):
                self.into_normal_state()


    def handle_action(self, attack_intent):
        print(f'HoldableComponent 的 handle_action : attack_intent = {attack_intent} target_item ={self.target_item}')
        if attack_intent == "pickup_item" and self.target_item:
            self.held_object = self.target_item
            self.target_item = None
            print(f"[INFO] {self.owner.name} 撿起了 {self.held_object.name}")
        elif self.held_object:
            if attack_intent == "swing_item":
                self.held_object.swing_attack(self.owner)
            elif attack_intent == "throw_item":
                self.held_object.throw(self.owner)
                self.held_object = None

    def find_nearest(self, unit_list):
        self_loc = (self.owner.x, self.owner.y)
        min_dist = max(self.owner.map_w, self.owner.map_h)
        tar_item = None
        for unit in unit_list:
            u_dist = (abs(unit.x - self_loc[0])+ abs(unit.y - self_loc[1]))
            if u_dist < min_dist:
                tar_item = unit
                min_dist = u_dist
        return tar_item
    
    def find_nearby_item(self) -> bool:
        """
        檢查 owner 是否接觸到可撿物件。
        搜尋 owner.scene_items 中具有 get_interact_box 的物件，
        且若該物件具有 is_pickable() 方法，也需為 True。
        成功時設定 self.target_item。
        """



        def print_unit_list(unit_list):
            return
        
        unit = self.owner
        result = False
        if not hasattr(unit, "scene_items"):
            print("[DEBUG] owner 未設定 scene_items，無法尋找可撿物品")
            return False
        my_box = unit.get_interact_box()
        if not my_box:
            print("[DEBUG] 無法取得自身的 interact_box")
            return False
        available_units =unit.scene.get_all_units()
        unit_names = [u.name for u in available_units]
        #print(f'')
        nearby_units = []
        for item in available_units:
            if item is self.owner:
                continue  # ✅ 跳過自己（避免自己撿自己）
            # 確保目標物件具有可互動區域
            if not hasattr(item, "get_interact_box"):
                continue
            item_box = item.get_interact_box()
            if item_box is None:
                continue
            # 如果 item 實作 is_pickable 且返回 False，就跳過
            if hasattr(item, "is_pickable") and not item.is_pickable():
                continue
            # 檢查是否碰撞
            if self.is_overlap(my_box, item_box):
                nearby_units.append(item)

        if len(nearby_units) > 0:
            print('{}'.format([u.name for u in nearby_units]))
            #手邊有東西
            item = self.find_nearest(nearby_units)
            self.target_item = item
            result = True

        item_name = ''
        if result:
            item_name = self.target_item.name
        #print(f'HoldableComponent 的 find_nearby_item 可互動物件:{unit_names} 尋找可拾取物件:{result}:{item_name}')
        # 若無任何可撿物件，清空 target
        if result == False:
            self.target_item = None
        return result

    def is_overlap(self, box1, box2) -> bool:
        """簡單 AABB 判斷"""
        return (
            box1['x1'] <= box2['x2'] and box1['x2'] >= box2['x1'] and
            box1['y1'] <= box2['y2'] and box1['y2'] >= box2['y1']
        )

    def try_pickup(self):
        """實際執行撿起行為"""
        #print(f'HoldableComponent 的 try_pickup')
        if self.target_item:
            #如果有找到目標
            self.held_object = self.target_item
            self.held_object.held_by = self.owner  # 🟢 讓 item 知道它被誰拿著
            print(f"[LOG] {self.owner.name} 撿起了 {self.held_object.name}")

            if hasattr(self.owner, "on_picked_up"):
                self.held_object.on_picked_up(self.owner)
            if hasattr(self.owner, "input_buffer") and hasattr(self.owner, "input_buffer_timer"):
                self.owner.input_buffer = None
                self.owner.input_buffer_timer = 0
                self.owner.attack_state = None
                self.owner.set_rigid(8)
                #a=input('stop54321')
            self.target_item = None
        else:
            print(f"[WARN] 嘗試撿取但附近沒有目標物")

Z_TORRENCE = 10.0
class HoldFlyLogicMixin:
    #被拾取/被投擲共通邏輯

    def check_wall_collision(self, next_x):
        """偵測 next_x 是否撞牆或超出地圖邊界"""
        # 1. 檢查地圖左右邊界
        if next_x < 0 or next_x+self.width > self.map_w:
            return True

        # 2. 檢查地形高度差 (牆壁)
        # 取得角色當前高度與前方地塊高度
        if hasattr(self, "knockback_vel_x"):
            vel_x = self.knockback_vel_x
        else:
            vel_x = self.vel_x
        tx = int(next_x + (0.8 if vel_x > 0 else 0.2))
        ty = int(self.y + 0.5)

        target_z = self.get_tile_z(tx, ty)
        if target_z is None:
            return True  # 超出索引視同撞牆
        if target_z is not None:
            # 如果目標地塊比當前位置高出 2 階以上，視為撞牆
            if target_z - self.z >= 2:
                return True

        return False

    def update_hold_fly_position(self):
        hit_someone = False
        if self.held_by:
            self.on_held_location()
        elif self.flying:
            #可能是item或character, 只有character需要反彈
            next_x = self.x + self.vel_x
            #print(f'{self.name} {self.x}->{next_x} ({self.map_w}) ({self.width})')
            # 🟢 修正點 1: 確保所有飛行物(含Item)都執行撞牆偵測
            if self.check_wall_collision(next_x):
                # 🟢 修正點 2: 真正的反彈 (速度取負值) 並加入動量損耗
                # 修正您原本 0.2*vel_x 導致持續向牆內擠壓的問題
                self.vel_x = -self.vel_x * 0.1  # 反向彈回 40% 速度

                # 🟢 修正點 3: 撞牆時給予微小的向上彈力，防止直接滑落
                self.vz = 0.3

                print(f'[PHYSICS] {self.name} 撞牆反彈! 新速度: {self.vel_x:.2f}')
                if self.scene and self.weight > 0.1:
                    self.scene.trigger_shake(10, 5)

                # 為了避免連續觸發，此幀不執行位移更新
                return hit_someone

            # 正常位移更新
            self.x += self.vel_x
            hit_someone = self.on_fly_z()
            # if self.check_wall_collision(next_x):
            #
            # if hasattr(self, "check_wall_collision"):
            #     wall_collied = self.check_wall_collision(self.x+self.vel_x)
            # if wall_collied:
            #     #撞牆反彈
            #     self.vel_x = 0.2*self.vel_x
            #     print('飛行撞牆反彈')
            #     if self.scene and self.weight > 0.1:
            #         self.scene.trigger_shake(10, 5)
            # self.x += self.vel_x
            # #print(f'{self.name}: x({self.x:.2f})+ {self.vel_x}')
            # hit_someone = self.on_fly_z()
        return hit_someone
    def on_held_location(self):
        # 若被持有，位置跟隨持有者（偏移值可以視覺調整）
        # print('Rock 的 update')
        self.x = self.held_by.x + 0.2
        self.y = self.held_by.y
        self.z = self.held_by.z
        self.jump_z = self.held_by.jump_z + self.held_by.height  # 顯得浮起來
        self.vz = 0
        self.flying = False  # 🟢 強制退出拋出狀態
        self.hitting = []
        #print(f'{self.name} (x={self.x}, y={self.y}, z={self.z}, jump_z={self.jump_z}, jump_z_vel = {self.jump_z_vel}')
        #print('on_held_location')

    def on_fly_z(self):
        hit_someone = False
        # 1. 拋物線重力感：減低下降速度 (weight 影響下墜快慢)
        self.vz -= self.weight * 0.5  # 降低重力常數讓拋物線更明顯
        self.jump_z += self.vz

        for unit in self.scene.get_units_with_type('character'):
            if not unit.is_alive() or unit in ([self, self.thrown_by] + self.hitting):
                continue
            if hasattr(self, 'ignore_side') and unit.side in self.ignore_side:
                continue

            if self.check_collision(unit):
                hit_someone = True
                self.hitting.append(unit)

                # --- 核心改動：動量損耗與物理反饋 ---
                # 2. 根據重量比計算動量損失 (模擬大撞小/小撞大)
                # 假設 self.weight 是 0.1, unit 預設也是 0.1 (可透過 getattr 抓取)
                target_weight = getattr(unit, 'weight', 0.1)
                momentum_loss = min(0.8, target_weight / (self.weight + 0.01) * 0.5)

                # 減損 X 軸速度
                impact_vel = self.vel_x
                self.vel_x *= (1.0 - momentum_loss)

                # 3. 擊中後的微幅彈起 (增加打擊的震動感)
                self.vz = abs(impact_vel) * 0.2

                # 觸發受擊
                atk_data = self.attacker_attack_data  # 優先使用物件自帶的備份數據
                if not atk_data and self.thrown_by:
                    # 如果自帶數據為空，才去嘗試找投擲者的當前狀態，並增加安全門檻
                    if hasattr(self.thrown_by, 'attack_state') and self.thrown_by.attack_state:
                        atk_data = self.thrown_by.attack_state.data
                if atk_data:
                    unit.on_hit(self.thrown_by, atk_data)

                # 4. 判斷是否停止飛行 (動量過低時才落地)
                is_breakthrough = getattr(self, 'breakthrough', False)
                if not is_breakthrough and abs(self.vel_x) < 0.05:
                    self.down_to_ground()
                    return hit_someone

        # --- 5. 觸地彈跳邏輯 (取代直接 down_to_ground) ---
        if self.jump_z <= 0:
            self.jump_z = 0
            if abs(self.vz) > 0.1:  # 如果掉落速度夠快，就彈起來
                self.vz = -self.vz * 0.4  # 彈起高度衰減
                self.vel_x *= 0.6  # 地面摩擦力
            else:
                self.down_to_ground()

        return hit_someone
    def down_to_ground(self):
        self.jump_z = 0
        self.vz = 0
        self.flying = False
        self.jump_z_vel = 0
        print(f"[LOG] {self.name} 落地了")
    def check_collision(self, target):
        my_box = self.get_interact_box()
        their_box = target.get_hurtbox()
        if (my_box['x1'] <= their_box['x2'] and my_box['x2'] >= their_box['x1'] and
                my_box['y1'] <= their_box['y2'] and my_box['y2'] >= their_box['y1']):
            # do z judgement
            if my_box['z1'] <= their_box['z2']+Z_TORRENCE and my_box['z2']+Z_TORRENCE >= their_box['z1']:
                print(f'{self.name} 碰撞 {target.name}')
                return True
            else:
                print('z miss! {}-{} V.S. {}-{} '.format(my_box['z1'],my_box['z2'],their_box['z1'],their_box['z2']))
        return False
    def on_hit_unit(self, target):
        print(f"[HIT] {self.name} 命中了 {target.name}")
        #觸發敵我雙方的命中行為


from Config import TILE_SIZE, Z_DRAW_OFFSET


import pygame
class AuraEffectComponent(Component):
    """
    用於在角色周圍繪製半透明、持續性的靈氣特效。
    特效持續到角色落地為止。
    """

    def __init__(self, image_path, frame_width=96, frame_height=96, expire_type=None, expire_value=None,alpha=128, anim_speed=3):
        super().__init__()
        # 1. 載入原始圖檔
        self.sheet = pygame.image.load(image_path).convert_alpha()
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.alpha = alpha

        # 2. 自動切片
        self.frames = self.slice_sheet()

        # 3. 動態狀態
        self.anim_timer = 0
        self.anim_speed = anim_speed  # 控制動畫播放快慢
        self.current_frame_idx = 0
        self.expire_type = expire_type or EffectExpireMode.LANDING
        self.expire_value = expire_value or 0

    def slice_sheet(self):
        """參考 SpriteAnimator 的切片邏輯"""
        sheet_w, sheet_h = self.sheet.get_size()
        cols = sheet_w // self.frame_width
        rows = sheet_h // self.frame_height
        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * self.frame_width
                y = row * self.frame_height
                frame = self.sheet.subsurface((x, y, self.frame_width, self.frame_height)).copy()
                frame.set_alpha(self.alpha)
                frames.append(frame)
        return frames

    def on_attach(self, owner):
        super().on_attach(owner)
        # 首次掛載時，確保圖片尺寸與角色匹配
        if owner.width and owner.height and owner.animator:
            # 假設靈氣圖片與角色動畫幀尺寸一致
            char_w = owner.animator.frame_width
            char_h = owner.animator.frame_height
            self.image = pygame.transform.scale(self.frames[0], (char_w, char_h))
        else:
            self.image = self.raw_image  # 使用原始尺寸

    def update(self):
        # 檢查落地條件，並移除自身
        if self.expire_type == EffectExpireMode.LANDING:
            if not self.owner or self.owner.jump_z <= 0:
                if self.owner and self.owner.state != self.owner.state.JUMP:
                    # 角色已落地且不是在跳躍狀態
                    self.owner.remove_component("aura_effect")
                    return
        elif self.expire_type == EffectExpireMode.TIMED and self.anim_timer >= self.expire_value:
            self.owner.remove_component("aura_effect")
            return
        elif self.expire_type == EffectExpireMode.ATTACK_END:
            if self.owner.attack_state is None:
                self.owner.remove_component("aura_effect")
                return

        self.anim_timer += 1
        # [可選] 實作靈氣的微小動畫或閃爍效果
        if self.anim_timer % self.anim_speed == 0:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        """處理特效的繪製，在 Character.draw_anim 內部被呼叫"""
        #print('enable auraeffect component draw')
        owner = self.owner
        if not owner: return

        # 取得當前動畫幀
        raw_frame = self.frames[self.current_frame_idx]
        # 假設原始素材是面向右邊，則面向左邊時需翻轉
        draw_image = raw_frame
        if owner.facing == DirState.LEFT:
            draw_image = pygame.transform.flip(raw_frame, True, False)

        cx, cy = self.owner.cached_pivot
        # 向上偏移半個身高，對準腰部
        center_y = cy - (self.owner.height * TILE_SIZE // 2)
        rect = draw_image.get_rect()
        draw_x = cx - rect.width // 2
        #draw_y = center_y - rect.height // 2
        # draw_y = center_y - rect.height*3//4
        # 對準角色正中心 (腰部)
        char_center_y = cy - (self.owner.height * TILE_SIZE // 2)
        # 讓靈氣素材的中心點對準角色中心
        draw_y = char_center_y - rect.height // 2
        win.blit(draw_image, (draw_x, draw_y))

class StatusAuraComponent(Component):
    """
    專門顯示霸體(黃)或無敵(白)狀態的特效組件
    """
    def __init__(self):
        super().__init__()
        self.timer = 0

    def update(self):
        self.timer += 1
        # 如果角色既沒有霸體也沒有無敵，就自我移除
        # 如果兩者皆為 False，則從角色身上移除此組件
        if not (self.owner.is_invincible() or self.owner.is_super_armor()):
            self.owner.remove_component("status_aura")

    def draw(self, win, cam_x, cam_y, tile_offset_y):
        if not self.owner: return
        if self.owner.combat_state in [CombatState.DOWN, CombatState.DEAD]: return
        if self.owner.current_frame <= self.owner.summon_sickness: return

        # 1. 決定基礎顏色 (使用 0.0 ~ 1.0 的浮點數來計算亮度)
        # 讓亮度在 0.2 ~ 0.8 之間震盪
        brightness = 0.1 + 0.1 * math.sin(self.timer * 0.4)

        # 2. 根據亮度縮放 RGB 數值
        if getattr(self.owner, "is_invincible", False):
            base_color = (255, 255, 255)  # 白色
        elif getattr(self.owner, "is_super_armor", False):
            base_color = (255, 255, 0)  # 黃色
        else:
            return

        # 關鍵：將 RGB 乘以亮度
        current_color = (
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness)
        )

        if hasattr(self.owner, "animator") and self.owner.current_anim_frame:
            frame = self.owner.current_anim_frame

            # 使用 pygame.mask 獲取形狀
            char_mask = pygame.mask.from_surface(frame)

            # 3. 填滿縮放後的顏色 (此處 alpha 設為 255 或不設，因為加法模式主要看 RGB)
            fill_surf = char_mask.to_surface(setcolor=current_color, unsetcolor=(0, 0, 0, 0))

            # 取得位置
            cx, cy = self.owner.cached_pivot
            draw_x = cx - frame.get_width() // 2
            draw_y = cy - frame.get_height()

            # if self.owner.facing == DirState.LEFT:
            #     fill_surf = pygame.transform.flip(fill_surf, True, False)

            # 4. 使用 BLEND_RGB_ADD (不處理 Alpha 的加法，效能較好且效果正確)
            win.blit(fill_surf, (draw_x, draw_y), special_flags=pygame.BLEND_RGB_ADD)


# Component.py

class StandComponent(Component):
    def __init__(self, stand_config, duration=900):
        super().__init__()
        self.config = stand_config
        self.stand = None
        self.active_timer = 0
        self.x_offset = stand_config.get("x_offset", 0.3)
        self.y_offset = stand_config.get("y_offset", -0.1)
        self.skill_map = stand_config.get("skill_map", None)
        self.max_duration = duration
        self.duration=duration

    def on_attach(self, owner):
        from Characters import StandEntity
        super().on_attach(owner)
        # 建立連結但不一定立刻顯示
        self.stand = StandEntity(owner, self.config)
        owner.scene.register_unit(self.stand, side="stand", type='stand')
        #"stand"side 不會與其他單位互動
        owner.stand = self.stand  # 讓 Player 類別直接持有引用

    def update(self):
        # 同步位置與面向
        # 1. 處理生命週期：時間到則註銷
        self.duration -= 1
        if self.duration <= 0 or not self.owner.is_alive():
            self.cleanup()
            return

        # 2. 同步視覺位置 (Slave 模式)
        self.sync_visuals()

    def sync_visuals(self):
        # 簡單的跟隨邏輯，確保替身在主人背後浮動
        owner, stand = self.owner, self.stand
        target_x = owner.x - (self.x_offset if owner.facing == DirState.RIGHT else -1*self.x_offset)
        stand.x = target_x
        stand.y = owner.y + self.y_offset
        stand.jump_z = owner.jump_z + math.sin(owner.current_frame * 0.1) * 0.3
        stand.facing = owner.facing
        # 動作同步修正
        if owner.attack_state:
            # 如果主人在攻擊，同步或映射招式
            if self.skill_map:
                for mapped_skill, owner_skills in self.skill_map.items():
                    if owner.attack_state.data.attack_type in owner_skills:
                        if not stand.attack_state:
                            stand.set_attack_by_skill(mapped_skill)
        else:
            # 如果主人停止攻擊，替身也必須立刻停止
            stand.attack_state = None
            if owner.state in [MoveState.WALK, MoveState.JUMP, MoveState.RUN]:
                stand.state = MoveState.WALK
            else:
                stand.state = MoveState.STAND

    def cleanup(self):
        """銷毀替身並從主人身上移除引用"""
        if self.stand and self.owner.scene:
            self.owner.scene.mark_for_removal(self.stand)  # 通知場景回收
        self.owner.stand = None  # 清除主人的 slave 指向
        self.owner.remove_component("stand_logic")  # 移除此組件自身

    def modify_attack_data(self, atk_data):
        """核心：當替身在場時，修改玩家的攻擊屬性"""
        # 1. 擴大判定範圍 (視覺上替身手比玩家長)
        atk_data.range_multiplier = 1.8
        # 2. 增加傷害或特定效果
        atk_data.damage_multiplier = 1.5
        # 3. 如果需要，加入不可格擋效果
        # atk_data.effects.append(AttackEffect.UNGUARDABLE)
        self.stand.set_attack_by_skill(atk_data)

        # 4. 指令推播：讓替身播放動作 (多對一映射)
