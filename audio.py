"""
Support for audio
"""
import pygame

import utils

def play_sound(name):
    cfg = utils.config["sounds"][name]
    fname = cfg["filename"]
    _, stop = cfg.get("range", [0, 0])

    sound = pygame.mixer.Sound(fname)

    return sound.play(maxtime = stop)

