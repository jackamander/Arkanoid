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

def clear_screen(screen):
    screen.fill(utils.color(utils.config["bg_color"]))

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
    image = _load_image(filename)
    pos = 0
    for char in text:
        col, row = _find_char_offset(char, characters)

        offset = (col * size[0], row * size[1])

        surf.blit(image, [pos, 0], pygame.Rect(offset, size))

        pos += size[0]

    return surf

image_cache = {}

def _load_image(fname, rect=None):
    if fname in image_cache:
        image = image_cache[fname]
    else:
        image = pygame.image.load(fname)
        image = image.convert_alpha()
        image_cache[fname] = image

    if rect:
        image = image.subsurface(rect)

    return image

def get_image(name):
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg.get("size")
    offsets = cfg.get("offsets")

    if size and offsets:
        rect = pygame.Rect(offsets[0], size)
    else:
        rect = None

    image = _load_image(fname, rect)

    return image

class Blink:
    def __init__(self, rate):
        # Convert rate from seconds to frames per half cycle
        fps = utils.config["frame_rate"]
        self.rate = int(rate * fps) / 2
        self.frames = 0

    def update(self, sprite):
        self.frames += 1

        if self.frames == self.rate:
            sprite.visible ^= 1
            self.frames = 0

class Sprite(pygame.sprite.DirtySprite):
    def __init__(self, image):
        pygame.sprite.DirtySprite.__init__(self)

        self.image = image
        self.rect = image.get_rect()
        self.dirty = 2
        self.blendmode = 0
        self.source_rect = None
        self.visible = 1
        self.layer = 0

        self.action = None

    def get_pos(self):
        return self.rect.topleft

    def set_pos(self, pos):
        self.rect.x = pos[0]
        self.rect.y = pos[1]

    def move(self, delta):
        self.rect.x += delta[0]
        self.rect.y += delta[1]

    def set_action(self, action=None):
        self.action = action

    def update(self):
        if self.action:
            self.action.update(self)

def render_scene(name, vars={}):
    cfg = utils.config["scenes"][name]

    surf = pygame.Surface(utils.config["screen_size"])

    surf.fill(utils.color(utils.config["bg_color"]))

    group = pygame.sprite.LayeredDirty()

    names = {}

    for name, type_, key, pos in cfg["sprites"]:
        if type_ == "text":
            image = draw_text(key)
        elif type_ == "var":
            text = str(vars[key])
            image = draw_text(text)
        elif type_ == "image":
            image = get_image(key)

        sprite = Sprite(image)
        sprite.set_pos(pos)
        group.add(sprite)

        if name:
            names[name] = sprite

    return group, names, cfg["data"]


