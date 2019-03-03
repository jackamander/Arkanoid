"""
Support for audio
"""

import functools
import logging

import pygame

import utils

# Increase the frequency and lower the buffer size to reduce audio lag
pygame.mixer.pre_init(frequency=44100, buffer=512)


def init():
    """Pre-load audio files into cache"""
    for name in utils.config["sounds"]:
        get_sound(name)


@functools.lru_cache(maxsize=None)
def get_sound(name):
    "Load and configure a sound"
    logging.warning("Sound cache miss: %s", name)
    cfg = utils.config["sounds"][name]

    fname = cfg["filename"]             # Filename is mandatory
    volume = cfg.get("volume", 1.0)     # Volume is optional

    sound = pygame.mixer.Sound(fname)
    sound.set_volume(volume)

    return sound


def stop():
    """Stop all sounds"""
    pygame.mixer.stop()


def play_sound(name):
    """Play the given sound"""
    sound = get_sound(name)

    sound.stop()            # Stop any previous instance of this sound
    channel = sound.play()

    if channel is None:
        logging.error("Audio fail: %s", name)

    return channel
