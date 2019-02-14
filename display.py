"""
display.py

Display functionality
"""

import functools
import logging
import os

import pygame

import utils

os.environ['SDL_VIDEODRIVER'] = 'directx'


def set_cursor(cursor_strings, hotspot=(0, 0), scale=1):
    "Set cursor for pygame window"
    # Scale the strings larger if requested
    cursor_strings = ["".join([ch * scale for ch in line])
                      for line in cursor_strings for _ in range(scale)]
    size = [len(cursor_strings[0]), len(cursor_strings)]
    xormask, andmask = pygame.cursors.compile(cursor_strings)
    pygame.mouse.set_cursor(size, hotspot, xormask, andmask)


class Window:
    "Manage the pygame screen"

    def __init__(self):
        world_size = utils.config['world_size']
        screen_size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.main = pygame.display.set_mode(screen_size, flags)
        self.screen = pygame.Surface(world_size)

        logging.warning("Driver: %s", pygame.display.get_driver())
        logging.warning("Display Info:\n    %s", str(pygame.display.Info()))

        pygame.display.set_caption(utils.config["title"])

        # Load a white cursor
        set_cursor(pygame.cursors.thickarrow_strings)

    def flip(self):
        "Flip the screen buffer"
        pygame.transform.scale(self.screen, self.main.get_size(), self.main)
        pygame.display.flip()

    def clear(self):
        "Clear the screen"
        self.screen.fill(utils.color(utils.config["bg_color"]))


def grab_mouse():
    "Grab the mouse for this application"
    pygame.mouse.set_visible(0)
    pygame.event.set_grab(1)


def release_mouse():
    "Release the mouse for this application"
    pygame.mouse.set_visible(1)
    pygame.event.set_grab(0)


def _find_char_offset(char, characters):
    for row, data in enumerate(characters):
        col = data.find(char)
        if col > -1:
            return [col, row]

    raise ValueError("Unsupported Character: %s" % char)


def draw_text(text, font):
    "Return a surface with the given text"
    config = utils.config["fonts"][font]
    name = config["image"]
    size = config["size"]
    characters = config["characters"]

    text_split = text.split('\n')
    rows = len(text_split)
    cols = max(map(len, text_split))

    surf = pygame.Surface([size[0] * cols, size[1] * rows],
                          pygame.SRCALPHA).convert_alpha()
    image = get_image(name)
    for row, line in enumerate(text_split):
        for col, char in enumerate(line):
            offset = _find_char_offset(char, characters)
            offset = [offset[i] * size[i] for i in range(2)]

            surf.blit(image, [col * size[0], row * size[1]],
                      pygame.Rect(offset, size), pygame.BLEND_RGBA_MAX)

    return surf


@functools.lru_cache(maxsize=None)
def get_image(name):
    "Fetch an image from cache or disk"
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg.get("size", None)
    offset = cfg.get("offset", None)
    scaled = cfg.get("scaled", None)

    image = pygame.image.load(fname)
    image = image.convert_alpha()

    if size and offset:
        rect = pygame.Rect(offset, size)
        image = image.subsurface(rect)

    if scaled:
        image = pygame.transform.smoothscale(image, scaled)

    logging.warning("Image cache miss: %s", name)

    return image
