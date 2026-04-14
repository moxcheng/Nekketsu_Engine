# SoundManager.py
import pygame
from Config import *

# elif type == 'hit':
# elif type == 'hitstop':
# elif type == 'brust':
# elif type == 'guard':
# elif type == 'clash':
# elif type == 'shockwave':
# elif type == 'grounding_impact':
# elif type == 'fireball_hit':
# elif type == 'crashed_rock':

class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.sounds = {
            #"shoot": pygame.mixer.Sound("..//Assets//sfx//laser.wav"),
            "hit": pygame.mixer.Sound("..//Assets_Drive//sfx//hit1.wav"),
            "hitstop": pygame.mixer.Sound("..//Assets_Drive//sfx//hitstop_edited.wav"),
            "brust": pygame.mixer.Sound("..//Assets_Drive//sfx//brust_edited.wav"),
            "guard": pygame.mixer.Sound("..//Assets_Drive//sfx//guard_edited.wav"),
            "clash": pygame.mixer.Sound("..//Assets_Drive//sfx//clash_edited.wav"),
            "shockwave": pygame.mixer.Sound("..//Assets_Drive//sfx//shockwave_edited.wav"),
            "grounding_impact": pygame.mixer.Sound("..//Assets_Drive//sfx//grounding_impact_edited.wav"),
            "fireball_hit": pygame.mixer.Sound("..//Assets_Drive//sfx//fireball_hit_edited.wav"),
            "crashed_rock": pygame.mixer.Sound("..//Assets_Drive//sfx//crashed_rock_edited.wav"),
        }
        self.set_volume(0.5)
        self.bgm_path = "..//Assets_Drive//sfx//"

    def play_bgm(self, bgm_name, loops=-1, fade_ms=1000):
        """
        播放背景音樂。
        若目前已有音樂在播放，會先淡出後再加載新音樂。
        :param bgm_name: 檔案名稱
        :param loops: 循環次數，-1 為無限循環
        :param fade_ms: 淡出與淡入的時間（毫秒）
        """
        full_path = f"{self.bgm_path}{bgm_name}"

        # 1. 檢查是否正在播放音樂
        if pygame.mixer.music.get_busy():
            # 2. 淡出目前音樂 (例如 1000ms = 1秒)
            pygame.mixer.music.fadeout(fade_ms)
            # 由於 fadeout 是阻塞或非同步執行(視版本)，
            # 在某些系統上可能需要短暫延遲或直接加載新歌覆蓋。

        # 3. 加載並播放新音樂
        try:
            pygame.mixer.music.load(full_path)
            # 使用 fade_ms 參數讓新音樂也能平滑淡入
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            print(f"BGM Switched: {bgm_name} (Fade: {fade_ms}ms)")
        except Exception as e:
            print(f"Error loading BGM {bgm_name}: {e}")

    def set_volume(self, volume):
        for s in self.sounds.values():
            s.set_volume(volume)

    def play(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()