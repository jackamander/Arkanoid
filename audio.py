"""
Support for audio
"""
import logging

import pygame

import utils

_audio_cache = {}

def play_sound(name):
    cfg = utils.config["sounds"][name]
    fname = cfg["filename"]
    _, stop = cfg.get("range", [0, 0])

    sound = _audio_cache.get(fname)
    if sound is None:
        sound = pygame.mixer.Sound(fname)
        _audio_cache[fname] = sound
        logging.warning("Audio cache miss: %s", name)

    channel = sound.play(maxtime = stop)

    if channel is None:
        logging.error("Audio fail: %s", name)

    return channel
