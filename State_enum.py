from enum import Enum, auto

#Character enumes
class MoveState(Enum):
    STAND = auto()
    WALK = auto()
    RUN = auto()
    STEP = auto()
    JUMP = auto()
    FALL = auto()
    ATTACK = auto()

class CombatState(Enum):
    NORMAL = auto()
    WEAK = auto()
    DOWN = auto()
    KNOCKBACK = auto()
    DEAD = auto()

class DirState(Enum):
    RIGHT = auto()
    LEFT = auto()
    UP = auto()
    DOWN = auto()

#Skill enumes
class AttackType(Enum):
    SLASH=auto()
    PUNCH=auto()
    KICK=auto()
    FLY_KICK=auto()
    BASH=auto()
    SWING=auto()    #揮舞武器
    THROW=auto()    #投擲武器
    THROW_CRASH=auto()  #飛行道具碰撞傷害
    FIREBALL=auto()
    BULLET=auto()
    MAHAHPUNCH=auto()
    METEOFALL=auto()
    SUPER_FINAL=auto()
    BRUST=auto()
    SPECIAL_KICK=auto()
    SPECIAL_PUNCH=auto()
#攻擊特效
class AttackEffect(Enum):
    FORCE_DOWN = auto()        # 強制倒地
    FORCE_WEAK = auto()  # 強制倒地
    SHORT_STUN = auto()              # 暫時無法動作
    IGNORE_INVINCIBLE = auto() # 無視無敵時間
    BURN = auto()
    DROP_MAGIC_POTION = auto()
    AFTER_IMAGE = auto()
    HIT_STOP=auto()
class EffectExpireMode(Enum):
    LANDING = auto()   # 落地消失
    TIMED = auto()     # 定時消失
    ATTACK_END = auto()# 招式結束消失

class SceneState(Enum):
    NORMAL = auto()
    PLAYER_BLOCK = auto()
    NPC_BLOCK = auto()
    SUPER_MOVE = auto()