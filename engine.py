"""
Main game engine for Arkanoid
"""

import pygame

import display
import utils

class Sprite(pygame.sprite.Sprite):
    def __init__(self, cfg):
        pygame.sprite.Sprite.__init__(self)

        name = cfg["filename"]
        size = cfg["size"]
        offsets = cfg["offsets"]
        pos = cfg.get("position", [0,0])

        rects = [pygame.Rect(offset, size) for offset in offsets]

        self.images = [display.get_image(name, rect) for rect in rects]
        self.image = self.images[0]
        self.rect = self.image.get_rect()

        self.set_pos(pos)

    def set_pos(self, pos):
        self.rect.x = pos[0]
        self.rect.y = pos[1]

    def move(self, delta):
        self.rect.x += delta[0]
        self.rect.y += delta[1]

class Engine(object):
    def __init__(self):
        sprites = utils.config["sprites"]
        level = utils.config["levels"]["1"]

        self.playspace = pygame.Rect(*utils.config["playspace"])

        bg1 = Sprite(sprites[level["bg"]])
        self.bg = pygame.sprite.Group(bg1)

        self.paddle = Sprite(sprites["paddle"])

        self.fg = pygame.sprite.Group(self.paddle)
        for row, data in enumerate(level["map"]):
            for col, block in enumerate(data):
                cfg = sprites.get(block, None)
                if cfg:
                    sprite = Sprite(cfg)
                    lft, top = self.playspace.topleft
                    wid, hgt = sprite.rect.size
                    sprite.set_pos([lft + col * wid, top + row * hgt])
                    self.fg.add(sprite)


    def input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.paddle.move([event.rel[0],0])
            self.paddle.rect.clamp_ip(self.playspace)

    def update(self):
        pass

    def draw(self, camera):
        camera.clear("black")
        self.bg.draw(camera.screen)
        self.fg.draw(camera.screen)
