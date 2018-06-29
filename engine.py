"""
Main game engine for Arkanoid
"""

import pygame

import display
import utils

class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = display.get_image('vaus.png', pygame.Rect(0, 0, 32, 8))
        self.rect = self.image.get_rect()

    def set_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

class Engine(object):
    def __init__(self, config):
        self.paddle = Paddle()
        self.allsprites = pygame.sprite.RenderPlain(self.paddle)

    def input(self, event):
        return True

    def update(self):
        pass

    def draw(self, camera):
        camera.clear("blue")
        self.allsprites.draw(camera.screen)
