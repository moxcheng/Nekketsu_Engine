from State_enum import *
#定義敵人combo
# 建議在檔案頂部定義招式組全域常數
DEFAULT_COMBOS = [AttackType.PUNCH, AttackType.PUNCH, AttackType.KICK, AttackType.SLASH]
ELITE_COMBOS = [AttackType.SLASH, AttackType.BASH, AttackType.KICK]
FIRE_MAGE_COMBOS = [AttackType.FIREBALL]


STAND_KONOMI_CONFIG={
    "name": "stand_player",
    "image_path": "..//Assets_Drive//konomi_stand_128.png",
    "x_offset": 0.5,
    "y_offset": -0.1,
    "animator_config": {
        "frame_width": 128,
        "frame_height": 128,
        "anim_map": {
            "stand": [[0]],
            "walk":[[8]],
            "punch":[[1],[3],[2]],
            "kick":[[9,10],[6,11]],
            "slash":[[4],[5],[7]]
        }
    },
    "skill_map":{
        AttackType.PUNCH:[AttackType.PUNCH, AttackType.SPECIAL_PUNCH, AttackType.MAHAHPUNCH],
        AttackType.KICK:[AttackType.KICK, AttackType.SPECIAL_KICK, AttackType.FLY_KICK],
        AttackType.SLASH:[AttackType.SLASH,AttackType.PUSH, AttackType.METEOFALL]
    }

}

PLAYER_KONOMI_CONFIG={
    "name": "player",
    "image_path": "..//Assets_Drive//konomi_test_50frame.png",
    "stand_config": STAND_KONOMI_CONFIG,
    "animator_config":{
        "frame_width": 128,
        "frame_height": 128,
        "anim_map": {
            "stand": [[45,46,47,46]],
            "walk": [[1, 2, 3, 4]],
            "run": [[1, 2, 3, 4]],
            "jump": [[5, 6]],  # 須修正與Z軸的關係
            "fall": [[6]],
            "flykick": [[8]],
            "punch": [[9,47], [12], [12]],
            "special_punch": [[18], [19], [9]],
            "kick": [[13, 7], [14]],
            "special_kick": [[24, 25], [26]],
            "bash": [[15, 16], [17]],
            "push": [[20], [21],[22]],
            "upper": [[23]],
            "pose_1": [[27]],
            "on_hit": [[28, 29]],
            "knockback": [[30, 31, 32], [33, 34, 35]],
            "on_fly": [[30]],
            "weak": [[36]],
            "down": [[37]],
            "dead": [[38]],
            "brust": [[40], [39]],
            "slash": [[20], [9], [23]],
            "mahahpunch": [[9], [10], [11], [12], [11], [10], [11], [12], [11], [10], [11], [12], [11], [10], [11],
                           [12]],
            "meteofall": [[44]],
            "ranbu": [[9, 10, 11, 12, 14, 13, 18, 11, 23, 26, 24, 40, 39, 41], [5, 23]],
            "swing": [[9], [11]],
            "throw": [[27], [42,43]],
            "guard":[[41]],
            "down_attack":[[13,48,49]],
            "hold_item":[[27]]
        },
        "anim_map_varient":{
            "punch": [[9,45], [11], [11]],
            "kick":[[20,13],[48]]
        }
    },
    "popup":["landing"],
    "stand":None,
    "attack_table":{'z_attack':{'default': AttackType.PUNCH, 'run': AttackType.BASH, 'highjump_fall': AttackType.METEOFALL, 'down_action':"pickup_item"},
                             'x_attack':{'default': AttackType.KICK, 'jump': AttackType.FLY_KICK, 'run':AttackType.PUSH},
                             'c_attack':{'default': AttackType.SLASH, 'run': AttackType.PUSH},
                             'swing_item':{'default': AttackType.SWING},
                             'throw_item':{'default': AttackType.THROW,'jump':AttackType.THROW}},
    "skill_overrides": {
        AttackType.SPECIAL_PUNCH: {"effect_component_config":{
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_snack.png", # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 150,
                "frame_width": 192,
                "frame_height": 192
            }
        }},
        AttackType.SPECIAL_KICK: {"effect_component_config": {
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_scopion.png",  # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 150,
                "frame_width": 192,
                "frame_height": 192,
                "anim_speed": 12
            }
        }},
        AttackType.PUSH: {"effect_component_config":{
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_tiger2.png",  # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 150,
                "frame_width": 192,
                "frame_height": 192,
                "anim_speed":15
            }
        }},
        AttackType.BASH: {"effect_component_config":{
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_dragon.png",  # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 150,
                "frame_width": 192,
                "frame_height": 192
            }
        },
        "damage": 16}
    },
    "super_ability": {"action":["stand", "haste"], "mp":2},
    "display_name": "一番組組長 多多良 木乃實",
    "neon_color": (0, 255, 255), # 青色霓虹
    "description": "「金色形意拳」",
    "skill_info": " [MP:2] 無窮之鎖˙霸衣",
    "preview_tachie": "..\\Assets_Drive\\konomi_full.png", # 大立繪路徑

}

# 定義每種狀態的 frame index list
basic_anim_map1 = {
    "stand": [[0]],
    "walk": [[1, 3, 2]],
    "run": [[1, 3, 2]],
    "punch": [[4], [5], [6]],
    "special_punch": [[4], [5], [6]],
    "bash": [[7]],
    "jump": [[8]],
    "fall": [[8]],
    "flykick": [[9]],
    "kick": [[11], [10]],
    "special_kick": [[11], [10]],
    "on_fly": [[12]],
    "slash": [[13], [14], [15]],
    "on_hit": [[16]],
    "weak": [[17]],
    "down": [[18]],
    "dead": [[19]],
    'swing': [[20], [21]],
    'throw': [[22], [23]],
    'meteofall': [[7]],
    'pose_1': [[6]],
    "knockback": [[12], [19]],
    "mahahpunch": [[4], [5], [6], [5], [6], [5], [6], [5], [6], [5], [6], [5], [6], [5], [6], [5]],
    "brust": [[6], [7]],
    "popup":[[24,25,26,27]],
    "guard":[[1]]
}

PLAYER_REN_128_CONFIG={
    "name": "player",
    "image_path": "..//Assets_Drive//yamashiro_128.png",
    "special_move": {"path":"..//Assets_Drive//yamashiro_super_move_128.png","width":128,"height":128},
    "super_move_staging":{
        "pre_pose_background": ["..\\Assets_Drive\\madou\\pre_pose1.png", "..\\Assets_Drive\\madou\\pre_pose2.png","..\\Assets_Drive\\madou\\pre_pose3.png", "..\\Assets_Drive\\madou\\pre_pose4.png",
                            "..\\Assets_Drive\\madou\\pre_pose5.png","..\\Assets_Drive\\madou\\pre_pose6.png", "..\\Assets_Drive\\madou\\pre_pose7.png","..\\Assets_Drive\\madou\\pre_pose8.png",
                            "..\\Assets_Drive\\madou\\pre_pose9.png", "..\\Assets_Drive\\madou\\pre_pose10.png"],
        "portraits": [
            {"path": "..\\Assets_Drive\\madou\\tachie_00.png", "start": 0.7, "end": 0.525, "dir": "L2R", "Offset_y": -50},
            {"path": "..\\Assets_Drive\\madou\\tachie_01.png", "start": 0.525, "end": 0.4, "dir": "R2L", "Offset_y": -15},
            {"path": "..\\Assets_Drive\\madou\\tachie_02.png", "start": 0.4, "end": 0.3, "dir": "L2R", "Offset_y": 15},
            {"path": "..\\Assets_Drive\\madou\\tachie_2.png", "start": 0.3, "end": 0.01, "dir": "R2L", "Offset_y": 0}],
        "effect": "..\\Assets_Drive\\madou\\tachie_5.png",
        "portraits_begin": 0.7,
        "timer": 500},

    "enable_special_move":{
            "pre_pose_background":["..\\Assets_Drive\\madou\\pre_pose1.png", "..\\Assets_Drive\\madou\\pre_pose2.png",
                                 "..\\Assets_Drive\\madou\\pre_pose3.png", "..\\Assets_Drive\\madou\\pre_pose4.png",
                                 "..\\Assets_Drive\\madou\\pre_pose5.png","..\\Assets_Drive\\madou\\pre_pose6.png", "..\\Assets_Drive\\madou\\pre_pose7.png",
                                 "..\\Assets_Drive\\madou\\pre_pose8.png","..\\Assets_Drive\\madou\\pre_pose9.png", "..\\Assets_Drive\\madou\\pre_pose10.png"],
            "portraits":[{"path": "..\\Assets_Drive\\madou\\tachie_00.png", "start": 0.7, "end": 0.525, "dir": "L2R","Offset_y": -50},
                       {"path": "..\\Assets_Drive\\madou\\tachie_01.png", "start": 0.525, "end": 0.4, "dir": "R2L","Offset_y": -15},
                       {"path": "..\\Assets_Drive\\madou\\tachie_02.png", "start": 0.4, "end": 0.3, "dir": "L2R","Offset_y": 15},
                       {"path": "..\\Assets_Drive\\madou\\tachie_2.png", "start": 0.3, "end": 0.01, "dir": "R2L","Offset_y": 0}],
            "effect":"..\\Assets_Drive\\madou\\tachie_5.png",
            "portraits_begin":0.7,
            "timer":500
        },
    "animator_config": {
        "frame_width": 128,
        "frame_height": 128,
        "anim_map":{        "stand": [[29,30,31]],
        "walk": [[1, 3, 2]],
        "run": [[42,43,44]],
        "punch": [[4], [5], [6]],
        "special_punch": [[4], [22], [23]],
        "bash": [[41,40],[7]],
        "jump": [[8]],
        "fall": [[8]],
        "push":[[13],[22],[23]],
        "flykick": [[9]],
        "kick": [[11], [10]],
        "special_kick": [[37,38,27], [39]],
        "on_fly": [[12]],
        "slash": [[13], [14], [15]],
        "on_hit": [[16]],
        "weak": [[17]],
        "down": [[18]],
        "dead": [[19]],
        "hold_item":[[20]],
        'swing': [[20], [32]],
        'throw': [[20], [37,36,36]],
        'meteofall': [[7]],
        'pose_1': [[6]],
        "knockback": [[33,34,35], [18]],
        "mahahpunch": [[4], [5], [6], [5], [6], [5], [6], [5], [6], [5], [6], [5]],
        "brust": [[0], [28]],
        "guard":[[28]],
        "down_attack":[[24,25,26]],
        "meteofall":[[45]]},
        "anim_map_varient":{
            "kick":[[37],[36]]
        }
    },
    "stand":None,
    "attack_table": {
        'z_attack': {'default': AttackType.MAHAHPUNCH, 'run': AttackType.BASH, 'highjump_fall': AttackType.METEOFALL,
                     'down_action': AttackType.DOWN_STOMP},
        'x_attack': {'default': AttackType.KICK, 'jump': AttackType.FLY_KICK, 'run': AttackType.PUSH},
        'c_attack': {'default': AttackType.SLASH, 'run': AttackType.FIREBALL},
        'swing_item': {'default': AttackType.SWING},
        'throw_item': {'default': AttackType.THROW, 'jump': AttackType.THROW}},
    "skill_overrides": {
        AttackType.BASH: {"effect_component_config": {
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_power_fly_256.png",  # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 150,
                "frame_width": 256,
                "frame_height": 256
            }
        },"power": 25},
        AttackType.SPECIAL_KICK: {"effect_component_config": {
            "component_name": "AuraEffectComponent",
            "component_key": "aura_effect",
            "params": {
                "image_path": "..//Assets_Drive//aura_arc_256.png",  # 專屬靈氣圖
                "expire_type": EffectExpireMode.ATTACK_END,
                "alpha": 180,
                "frame_width": 256,
                "frame_height": 256
            }
        }, "power": 40}
    },
    "super_ability": {"action":["super_move"], "mp":1},
    "display_name": "十番組組長 總組長 山城 戀",
    "neon_color": (0, 255, 255),  # 青色霓虹
    "description": "「總括萬物之無限宇宙之全一」",
    "skill_info": " [MP:全] 開幕的炮火",
    "preview_tachie": "..\\Assets_Drive\\ren_full.png",  # 大立繪路徑

}
# 定義每種狀態的 frame index list


NPC_SHUKI_0_CONFIG={
    'name': "shuki0",
    "image_path": "..\\Assets_Drive\\madou\\shuki0_96.png",
    "scale":7/4,
"weight":1.5,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "popup":["anim", 'fade-in'],
    "ai_move_speed": 0.15,
    "attack_cooldown": 40
}
NPC_SHUKI_1_CONFIG={
    'name': "shuki1",
    "image_path": "..\\Assets_Drive\\madou\\shuki1_96.png",
    "scale":5/4,
"weight":1.1,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": DEFAULT_COMBOS,
    "popup":["anim", 'fade-in'],
    "ai_move_speed": 0.2,
    "attack_cooldown": 35
}
NPC_SHUKI_2_CONFIG={
    'name': "shuki2",
    "image_path": "..\\Assets_Drive\\madou\\shuki2_96.png",
    "scale":6/4,
"weight":1.2,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "popup":["anim", 'fade-in'],
    "ai_move_speed": 0.18,
    "attack_cooldown": 40
}
NPC_SHUKI_3_CONFIG={
    'name': "shuki3",
    "image_path": "..\\Assets_Drive\\madou\\shuki3_96.png",
    "scale":1.0,
    "weight":0.8,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": DEFAULT_COMBOS,
    "popup":["anim", 'fade-in'],
    "ai_move_speed": 0.25,
    "attack_cooldown": 40
}
NPC_SHUKI_BOSS_CONFIG={
    'name': "boss",
    "image_path": "..\\Assets_Drive\\madou\\shuki_boss_96.png",
    "scale": 2.0,
"weight":1.5,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "popup":["landing","shake"],
    "ai_move_speed":0.15,
    "attack_cooldown":30,
    "is_blocking":True,
}
NPC_SHUKI_NEW_1_CONFIG={
    'name': "shuki_new1",
    "image_path": "..\\Assets_Drive\\madou\\shuki_new1.png",
    "scale":1.3,
"weight":1.3,
    "animator_config":{
        "frame_width":128,
        "frame_height":128,
        "anim_map":{
            "stand":[[0]],"walk":[[1,2,5,4]],
            "run": [[1, 2, 5,15,16]],
            "punch": [[4,7], [8], [5]],
            "special_punch": [[9], [10], [11]],
            "bash": [[16, 17]],
            "jump": [[12, 13]],
            "fall": [[8]],
            "flykick": [[14]],
            "kick": [[13], [14]],
            "special_kick": [[9,10], [11]],
            "on_fly": [[24]],
            "slash": [[17], [11], [10]],
            "on_hit": [[20]],
            "weak": [[21]],
            "down": [[22]],
            "dead": [[23]],
            'swing': [[18], [19]],
            'throw': [[18], [19]],
            'meteofall': [[14]],
            'pose_1': [[9]],
            "knockback": [[24,25,26], [27,22]],
            "brust": [[4], [9]],
            "popup":[[28,29,30,31]],
            "guard":[[1]]
        }
    },
    "combos": [AttackType.PUNCH, AttackType.PUNCH, AttackType.SPECIAL_PUNCH,AttackType.KICK,AttackType.SPECIAL_KICK, AttackType.SLASH],
    "popup":["anim"],
    "ai_move_speed": 0.25,
    "attack_cooldown": 35
}