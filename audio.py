"""
Support for audio
"""
import logging

import pygame

import utils

# Increase the frequency and lower the buffer size to reduce audio lag
pygame.mixer.pre_init(frequency=44100, buffer=512)


def sound_factory(name):
    "Load and configure a sound"
    cfg = utils.config["sounds"][name]

    fname = cfg["filename"]             # Filename is mandatory
    volume = cfg.get("volume", 1.0)     # Volume is optional

    sound = pygame.mixer.Sound(fname)
    sound.set_volume(volume)

    return sound

_audio_cache = utils.Cache(sound_factory)

def play_sound(name):
    sound = _audio_cache.get(name)

    sound.stop()            # Stop any previous instance of this sound
    channel = sound.play()

    if channel is None:
        logging.error("Audio fail: %s", name)

    return channel
