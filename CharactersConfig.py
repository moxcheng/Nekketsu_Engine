from State_enum import *
#定義敵人combo
# 建議在檔案頂部定義招式組全域常數
DEFAULT_COMBOS = [AttackType.PUNCH, AttackType.PUNCH, AttackType.KICK, AttackType.SLASH]
ELITE_COMBOS = [AttackType.SLASH, AttackType.BASH, AttackType.KICK]
FIRE_MAGE_COMBOS = [AttackType.FIREBALL]

PLAYER_KONOMI_CONFIG={
    "name": "player",
    "image_path": "..//Assets_Drive//konomi_test_42frame.png",
    "special_move": "..//Assets_Drive//yamashiro_super_move_96.png",
    "super_move_staging": {
        "pre_pose_background": ["..\\Assets_Drive\\madou\\pre_pose1.png", "..\\Assets_Drive\\madou\\pre_pose2.png",
                                "..\\Assets_Drive\\madou\\pre_pose3.png", "..\\Assets_Drive\\madou\\pre_pose4.png",
                                "..\\Assets_Drive\\madou\\pre_pose5.png", "..\\Assets_Drive\\madou\\pre_pose6.png",
                                "..\\Assets_Drive\\madou\\pre_pose7.png", "..\\Assets_Drive\\madou\\pre_pose8.png",
                                "..\\Assets_Drive\\madou\\pre_pose9.png", "..\\Assets_Drive\\madou\\pre_pose10.png"],
        "portraits": [
            {"path": "..\\Assets_Drive\\madou\\tachie_00.png", "start": 0.7, "end": 0.525, "dir": "L2R",
             "Offset_y": -50},
            {"path": "..\\Assets_Drive\\madou\\tachie_01.png", "start": 0.525, "end": 0.4, "dir": "R2L",
             "Offset_y": -15},
            {"path": "..\\Assets_Drive\\madou\\tachie_02.png", "start": 0.4, "end": 0.3, "dir": "L2R", "Offset_y": 15},
            {"path": "..\\Assets_Drive\\madou\\tachie_2.png", "start": 0.3, "end": 0.01, "dir": "R2L", "Offset_y": 0}],
        "effect": "..\\Assets_Drive\\madou\\tachie_5.png",
        "portraits_begin": 0.7,
        "timer": 500},
    "animator_config":{
        "frame_width": 128,
        "frame_height": 128,
        "anim_map": {
            "stand": [[0]],
            "walk": [[1, 2, 3, 4]],
            "run": [[1, 2, 3, 4]],
            "jump": [[5, 6]],  # 須修正與Z軸的關係
            "fall": [[6]],
            "flykick": [[8]],
            "punch": [[9], [10, 11], [12]],
            "special_punch": [[18], [19], [9]],
            "kick": [[13, 7], [14]],
            "special_kick": [[24, 25], [26]],
            "bash": [[15, 16], [17]],
            "palm": [[20, 21], [22]],
            "upper": [[23]],
            "pose_1": [[27]],
            "on_hit": [[28, 29]],
            "knockback": [[30, 31, 32], [33, 34, 35]],
            "on_fly": [[30]],
            "weak": [[36]],
            "down": [[37]],
            "dead": [[38]],
            "brust": [[40], [39]],
            "slash": [[20, 10], [21], [23]],
            "mahahpunch": [[9], [10], [11], [12], [11], [10], [11], [12], [11], [10], [11], [12], [11], [10], [11],
                           [12]],
            "meteofall": [[41]],
            "ranbu": [[9, 10, 11, 12, 14, 13, 18, 11, 23, 26, 24, 40, 39, 41], [5, 23]],
            "swing": [[9], [11]],
            "throw": [[27], [22]]
        }
    },
    "popup":["landing"],
    "stand":None
}
PLAYER_REN_CONFIG={
    'name': "player",
    "image_path": "..//Assets_Drive//yamashiro_96.png",
    "special_move": "..//Assets_Drive//yamashiro_super_move_96.png",
    "special_move_staging":{
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
    "frame_width": 96,
    "frame_height": 96,
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
    "brust": [[6], [7]]
}

NPC_SHUKI_0_CONFIG={
    'name': "shuki0",
    "image_path": "..\\Assets_Drive\\madou\\shuki0_96.png",
    "scale":7/4,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "ai_move_speed": 0.15,
    "attack_cooldown": 40
}
NPC_SHUKI_1_CONFIG={
    'name': "shuki1",
    "image_path": "..\\Assets_Drive\\madou\\shuki1_96.png",
    "scale":5/4,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": DEFAULT_COMBOS,
    "ai_move_speed": 0.2,
    "attack_cooldown": 35
}
NPC_SHUKI_2_CONFIG={
    'name': "shuki2",
    "image_path": "..\\Assets_Drive\\madou\\shuki2_96.png",
    "scale":6/4,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "ai_move_speed": 0.18,
    "attack_cooldown": 40
}
NPC_SHUKI_3_CONFIG={
    'name': "shuki3",
    "image_path": "..\\Assets_Drive\\madou\\shuki3_96.png",
    "scale":1.0,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": DEFAULT_COMBOS,
    "ai_move_speed": 0.25,
    "attack_cooldown": 40
}
NPC_SHUKI_BOSS_CONFIG={
    'name': "boss",
    "image_path": "..\\Assets_Drive\\madou\\shuki_boss_96.png",
    "scale": 2.0,
    "animator_config":{
        "frame_width":96,
        "frame_height":96,
        "anim_map":basic_anim_map1
    },
    "combos": ELITE_COMBOS,
    "popup":["landing","shake"],
    "ai_move_speed":0.15,
    "attack_cooldown":30
}