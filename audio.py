"""
Support for audio
"""
import pygame

import utils

def play_sound(name):
    cfg = utils.config["sounds"][name]
    sound = pygame.mixer.Sound(cfg["filename"])
    return sound.play(maxtime = cfg["range"][1])

