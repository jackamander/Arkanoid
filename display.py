"""
display.py

Display functionality
"""
import logging
import os

import pygame

import utils

class Window:
    def __init__(self):
        world_size = utils.config['world_size']
        screen_size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.main = pygame.display.set_mode(screen_size, flags)
        self.screen = pygame.Surface(world_size)

        logging.info("Driver: %s", pygame.display.get_driver())
        logging.info("Display Info:\n    %s", pygame.display.Info())

        pygame.display.set_caption(utils.config["title"])

    def flip(self):
        pygame.transform.scale(self.screen, self.main.get_size(), self.main)
        pygame.display.flip()

    def clear(self):
        self.screen.fill(utils.color(utils.config["bg_color"]))

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

_image_cache = {}

def _load_image(fname, rect=None, scaled=[]):
    image = _image_cache.get(fname)
    if image is None:
        image = pygame.image.load(fname)
        image = image.convert_alpha()
        _image_cache[fname] = image

    if rect:
        image = image.subsurface(rect)

    if scaled:
        image = pygame.transform.smoothscale(image, scaled)

    return image

def get_image(name):
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg["size"]
    offset = cfg["offset"]
    scaled = cfg.get("scaled")

    rect = pygame.Rect(offset, size)

    image = _load_image(fname, rect, scaled)

    return image

class MouseMove:
    def __init__(self, engine, region, sensitivity):
        self.rect = region.copy()
        self.delta = [0, 0]
        self.sensitivity = sensitivity

        engine.events.register(pygame.MOUSEMOTION, self.on_mousemove)

    def on_mousemove(self, event):
        self.delta = [self.delta[i] + self.sensitivity[i] * event.rel[i] for i in range(2)]

    def update(self, sprite):
        sprite.move(self.delta)
        sprite.rect.clamp_ip(self.rect)
        self.delta = [0, 0]

class Move:
    def __init__(self, delta):
        self.delta = delta

    def update(self, sprite):
        sprite.move(self.delta)

class Follow:
    def __init__(self, target):
        self.target = target
        self.last = target.get_pos()

    def update(self, sprite):
        pos = self.target.get_pos()
        if pos != self.last:
            delta = [pos[0] - self.last[0], pos[1] - self.last[1]]
            sprite.move(delta)
            self.last = pos

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

class Animate:
    def __init__(self, name):
        cfg = utils.config["animations"][name]
        self.images = [get_image(name) for name in cfg["images"]]
        self.speed = cfg["speed"]
        self.frame = 0
        self.count = 0

    def update(self, sprite):
        if self.frame < len(self.images):
            if self.count == 0:
                sprite.image = self.images[self.frame]

            self.count += 1
            if self.count >= self.speed:
                self.frame += 1
                self.count = 0

class Sprite(pygame.sprite.DirtySprite):
    def __init__(self, image, cfg={}):
        pygame.sprite.DirtySprite.__init__(self)

        self.image = image
        self.rect = image.get_rect()
        self.last = self.rect
        self.dirty = 2
        self.blendmode = 0
        self.source_rect = None
        self.visible = 1
        self.layer = 0

        self.action = None

        self.cfg = cfg

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
        self.last = self.rect.copy()
        if self.action:
            self.action.update(self)

class Scene:
    def __init__(self, name, vars={}):
        sprites = utils.config["scenes"][name]

        self.group = pygame.sprite.LayeredDirty()
        self.names = {}

        for cfg in sprites:
            cfg = cfg.copy()

            if "text" in cfg:
                image = draw_text(cfg.pop("text"))

            if "var" in cfg:
                text = str(vars[cfg.pop("var")])
                image = draw_text(text)

            if "image" in cfg:
                image = get_image(cfg.pop("image"))

            position = cfg.pop("position")

            sprite = Sprite(image, cfg)
            sprite.set_pos(position)

            self.group.add(sprite)

            sprite_name = cfg.get("name")
            if sprite_name:
                self.names[sprite_name] = sprite
