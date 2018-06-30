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
    def __init__(self):
        self.fonts = {}

        size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.screen = pygame.display.set_mode(size, flags)

        logging.info("Driver: %s", pygame.display.get_driver())
        logging.info("Display Info:\n    %s", pygame.display.Info())

    def size(self):
        """Return vector of current screen size in pixels"""
        return self.screen.get_size()

    def clear(self, color):
        self.screen.fill(utils.color(color))

    def draw_text(self, text, pos):
        config = utils.config["font"]
        filename = config["filename"]
        size = config["size"]
        characters = config["characters"]

        for char in text:
            for row, data in enumerate(characters):
                col = data.find(char)
                if col > -1:
                    offset = (col * size[0], row * size[1])
                    break
            else:
                raise ValueError("Unsupported Character: %s" % char)

            image = get_image(filename, pygame.Rect(offset, size))
            self.screen.blit(image, pos)
            pos = [pos[0] + size[0], pos[1]]

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
