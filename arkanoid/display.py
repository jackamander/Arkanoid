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
        screen_size = self.main.get_size()
        world_size = self.screen.get_size()

        x_mult = screen_size[0] // world_size[0]
        y_mult = screen_size[1] // world_size[1]

        x_offset = (screen_size[0] % world_size[0]) // 2
        y_offset = (screen_size[1] % world_size[1]) // 2

        self.main.fill(utils.color(utils.config["bg_color"]))

        scaled = pygame.transform.scale(self.screen,
                                        (world_size[0] * x_mult, world_size[1] * y_mult))

        self.main.blit(scaled, (x_offset, y_offset))

        pygame.display.flip()

    def clear(self):
        "Clear the screen"
        self.screen.fill(utils.color(utils.config["bg_color"]))

    def screen2world(self, screen, relative):
        """Translate coordinates from screen to world."""
        screen_size = self.main.get_size()
        world_size = self.screen.get_size()

        x_mult = screen_size[0] // world_size[0]
        y_mult = screen_size[1] // world_size[1]

        if relative:
            x_offset = 0
            y_offset = 0
        else:
            x_offset = (screen_size[0] % world_size[0]) // 2
            y_offset = (screen_size[1] % world_size[1]) // 2

        world = ((screen[0] - x_offset) / x_mult,
                 (screen[1] - y_offset) / y_mult)

        return world


def grab_mouse():
    "Grab the mouse for this application"
    pygame.mouse.set_visible(0)
    pygame.event.set_grab(1)


def release_mouse():
    "Release the mouse for this application"
    pygame.mouse.set_visible(1)
    pygame.event.set_grab(0)


class Font:
    """Create a font object for rendering text"""

    def __init__(self, name=None):
        self.config = self._load_config(name)
        self.size = self.config["size"]
        self.image = get_image(self.config["image"])

    def _load_config(self, name=None):
        "Load the named font config (default if None)"
        fonts = utils.config["fonts"]

        if name is None:
            defaults = [config for name, config in fonts.items()
                        if config.get("default", False)]
            assert len(defaults) == 1, "Must specify one default font!"
            config = defaults[0]
        else:
            config = fonts[name]

        return config

    def _find_char_offset(self, char):
        "Calculate the offset of the character in the image"
        for row, data in enumerate(self.config["characters"]):
            col = data.find(char)
            if col > -1:
                return [col * self.size[0], row * self.size[1]]

        raise ValueError("Unsupported Character: %s" % char)

    def render(self, text):
        "Create a new surface with the text rendered"
        text_split = text.split('\n')
        rows = len(text_split)
        cols = max(map(len, text_split))

        surf = pygame.Surface(
            [self.size[0] * cols, self.size[1] * rows], pygame.SRCALPHA).convert_alpha()
        for row, line in enumerate(text_split):
            for col, char in enumerate(line):
                dest = [col * self.size[0], row * self.size[1]]
                src = pygame.Rect(self._find_char_offset(char), self.size)
                surf.blit(self.image, dest, src, pygame.BLEND_RGBA_MAX)

        return surf


@functools.lru_cache(maxsize=None)
def get_font(name):
    """Font factory with caching"""
    logging.warning("Font cache miss: %s", name)
    font = Font(name)
    return font


def draw_text(text, font_name=None):
    """Return a surface with the given text"""
    font = get_font(font_name)
    surface = font.render(text)
    return surface


@functools.lru_cache(maxsize=None)
def get_image(name):
    "Fetch an image from cache or disk"
    logging.warning("Image cache miss: %s", name)
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

    return image


def init():
    """Pre-load fonts and images into cache"""
    for name in utils.config["fonts"]:
        get_font(name)

    for name in utils.config["images"]:
        get_image(name)
