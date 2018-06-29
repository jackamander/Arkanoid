"""
Main game engine for Arkanoid
"""

import pygame

import display
import utils



class Sprite(pygame.sprite.Sprite):
    def __init__(self, config):
        pygame.sprite.Sprite.__init__(self)

        name = config["filename"]
        size = config["size"]
        offsets = config["offsets"]
        pos = config.get("position", [0,0])

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
    def __init__(self, config):
        sprites = config["sprites"]

        self.playspace = pygame.Rect(*config["playspace"])

        bg1 = Sprite(sprites["bg1"])
        self.bg = pygame.sprite.Group(bg1)

        self.vaus = Sprite(sprites["vaus"])

        self.fg = pygame.sprite.Group(self.vaus)
        for row, data in enumerate(config["levels"]["1"]):
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
            self.vaus.move([event.rel[0],0])
            self.vaus.rect.clamp_ip(self.playspace)

    def update(self):
        pass

    def draw(self, camera):
        camera.clear("black")
        self.bg.draw(camera.screen)
        self.fg.draw(camera.screen)
