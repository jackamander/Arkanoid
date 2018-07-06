"""
Support for audio
"""
import pygame

import utils

_audio_cache = {}

def play_sound(name):
    cfg = utils.config["sounds"][name]
    fname = cfg["filename"]
    start, stop = cfg.get("range", [0, 0])

    sound = _audio_cache.get(fname)
    if sound is None:
        sound = pygame.mixer.Sound(fname)
        _audio_cache[fname] = sound

    return sound.play(maxtime = stop)

