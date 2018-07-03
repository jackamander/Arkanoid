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

    def update(self):
        pass

    def set_pos(self, pos):
        self.rect.x = pos[0]
        self.rect.y = pos[1]

    def move(self, delta):
        self.rect.x += delta[0]
        self.rect.y += delta[1]

class Level(object):
    def __init__(self, key):
        level = utils.config["levels"][key]
        self.playspace = pygame.Rect(*utils.config["playspace"])

        sprites = utils.config["images"]
        bg_key = level["bg"]
        self.bg = pygame.sprite.Group(Sprite(sprites[bg_key]))

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


class State(object):
    def __init__(self, engine):
        self.engine = engine

    def input(self, event):
        return ""

    def update(self):
        pass

    def draw(self, camera):
        pass

class TitleState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        sprites = utils.config["images"]

        arkanoid = Sprite(sprites["arkanoid"])
        taito = Sprite(sprites["taito"])
        copyright = Sprite(sprites["copyright"])
        self.cursor = Sprite(sprites["cursor"])

        self.group = pygame.sprite.Group(arkanoid, taito, copyright, self.cursor)

    def input(self, event):
        if event.type == pygame.MOUSEMOTION:
            pass
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return "blink"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.engine.players = 1
            elif event.key == pygame.K_DOWN:
                self.engine.players = 2
            elif event.key == pygame.K_RETURN:
                return "blink"


    def update(self):
        pass

    def draw(self, camera):
        if self.engine.players == 1:
            self.cursor.set_pos([80, 120])
        else:
            self.cursor.set_pos([80, 136])

        camera.clear("black")
        camera.screen.blit(display.draw_text("1UP"), [32, 8])
        camera.screen.blit(display.draw_text("HIGH SCORE"), [88, 8])
        camera.screen.blit(display.draw_text("00"), [48, 16])
        camera.screen.blit(display.draw_text("50000"), [112, 16])
        camera.screen.blit(display.draw_text("1 PLAYER"), [96, 120])
        camera.screen.blit(display.draw_text("2 PLAYERS"), [96, 136])
        camera.screen.blit(display.draw_text("TAITO CORPORATION 1987"), [48, 192])
        camera.screen.blit(display.draw_text("LICENSED BY"), [84, 200])
        camera.screen.blit(display.draw_text("NINTENDO OF AMERICA INC."), [32, 208])
        self.group.draw(camera.screen)

class BlinkState(TitleState):
    def __init__(self, engine):
        TitleState.__init__(self, engine)

        self.cursor.kill()

        self.timer = 0
        self.blink_rate = utils.config["frame_rate"] / 2

        sound = pygame.mixer.Sound("resources\\sounds\\Intro.wav")
        self.channel = sound.play(maxtime=4500)

    def input(self, event):
        pass

    def update(self):
        self.timer = (self.timer + 1) % (self.blink_rate * 2)

        if not self.channel.get_busy():
            return "level"

    def draw(self, camera):
        TitleState.draw(self, camera)

        if self.engine.players == 1:
            rect = pygame.Rect(96, 120, 72, 8)
        else:
            rect = pygame.Rect(96, 136, 72, 8)

        if self.timer < self.blink_rate:
            camera.screen.fill(utils.color("black"), rect)

class LevelState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

    def draw(self, camera):
        camera.clear("black")



class Engine(object):
    def __init__(self):
        self.high = 0
        self.players = 1
        self.level = Level("1")
        self.state = TitleState(self)

    def set_state(self, next_state):
        if next_state == "blink":
            self.state = BlinkState(self)
        elif next_state == "level":
            self.state = LevelState(self)

    def input(self, event):
        next_state = self.state.input(event)
        self.set_state(next_state)

    def update(self):
        next_state = self.state.update()
        self.set_state(next_state)

    def draw(self, camera):
        self.state.draw(camera)
