"""
display.py

Display functionality
"""
import logging
import os

import pygame

import utils

class Camera(object):
    """Screen management."""
    def __init__(self, config):
        self.fonts = {}

        size = config['screen_size']

        flags = 0
        if config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.screen = pygame.display.set_mode(size, flags)

        logging.info("Driver: %s", pygame.display.get_driver())
        logging.info("Display Info:\n    %s", pygame.display.Info())

    def size(self):
        """Return vector of current screen size in pixels"""
        return self.screen.get_size()

    def clear(self, color):
        self.screen.fill(utils.color(color))

    def draw_text(self, text, pos, size=30, color="black", aa=False):
        """Draw some text."""
        font = self.get_font(size)
        surf = font.render(text, aa, utils.color(color))
        self.screen.blit(surf, pos)

    def get_font(self, size):
        if size in self.fonts:
            font = self.fonts[size]
        else:
            font = pygame.font.Font(None, size)
            self.fonts[size] = font
        return font

image_cache = {}

def get_image(name, rect=None):
    fullname = os.path.join("resources", "images", name)

    if fullname in image_cache:
        image = image_cache[fullname]
    else:
        image = pygame.image.load(fullname)
        image = image.convert_alpha()
        image_cache[fullname] = image

    if rect:
        image = image.subsurface(rect)

    return image

