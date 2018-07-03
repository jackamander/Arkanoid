"""
display.py

Display functionality
"""
import logging
import os

import pygame

import utils

def init_screen():
    size = utils.config['screen_size']

    flags = 0
    if utils.config['full_screen']:
        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

    screen = pygame.display.set_mode(size, flags)

    logging.info("Driver: %s", pygame.display.get_driver())
    logging.info("Display Info:\n    %s", pygame.display.Info())

    pygame.display.set_caption(utils.config["title"])

    return screen

def _find_char_offset(char, characters):
    for row, data in enumerate(characters):
        col = data.find(char)
        if col > -1:
            return [col, row]

    raise ValueError("Unsupported Character: %s" % char)

def draw_text(text):
    config = utils.config["font"]
    filename = config["filename"]
    size = config["size"]
    characters = config["characters"]

    surf = pygame.Surface([size[0]*len(text), size[1]])
    pos = 0
    for char in text:
        col, row = _find_char_offset(char, characters)

        offset = (col * size[0], row * size[1])

        image = get_image(filename, pygame.Rect(offset, size))
        surf.blit(image, [pos, 0])
        pos += size[0]

    return surf

image_cache = {}

def get_image(fname, rect=None):
    if fname in image_cache:
        image = image_cache[fname]
    else:
        image = pygame.image.load(fname)
        image = image.convert_alpha()
        image_cache[fname] = image

    if rect:
        image = image.subsurface(rect)

    return image
