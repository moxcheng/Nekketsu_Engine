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
            "hit": pygame.mixer.Sound("..//Assets_Drive//sfx//hit_soft.wav"),
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

    def play_bgm(self, bgm_name, loops=-1, fade_ms=500, volume=0.5):
        """
        播放背景音樂。
        :param volume: 獨立設定此 BGM 的音量 (0.0 到 1.0)
        """
        full_path = f"{self.bgm_path}{bgm_name}"

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)

        try:
            pygame.mixer.music.load(full_path)
            # 💡 關鍵：只設定音樂通道的音量，不影響 self.sounds
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            print(f"BGM Switched: {bgm_name} (Vol: {volume})")
        except Exception as e:
            print(f"Error loading BGM {bgm_name}: {e}")

    def set_volume(self, volume):
        for s in self.sounds.values():
            s.set_volume(volume)

    def play(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()