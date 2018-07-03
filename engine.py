"""
Main game engine for Arkanoid
"""

import pygame

import display
import utils

class Sound:
    def __init__(self, name):
        cfg = utils.config["sounds"][name]
        sound = pygame.mixer.Sound(cfg["filename"])
        self.channel = sound.play(maxtime = cfg["range"][1])

    def is_done(self):
        return not self.channel.get_busy()


class Sprite(pygame.sprite.Sprite):
    def __init__(self, name):
        pygame.sprite.Sprite.__init__(self)

        cfg = utils.config["images"][name]
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

        bg_key = level["bg"]
        self.bg = pygame.sprite.Group(Sprite(bg_key))

        self.paddle = Sprite("paddle")

        self.fg = pygame.sprite.Group(self.paddle)
        for row, data in enumerate(level["map"]):
            for col, block in enumerate(data):
                if block != " ":
                    sprite = Sprite(block)
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

def render_scene(name, vars):
    cfg = utils.config["scenes"][name]

    surf = pygame.Surface(utils.config["screen_size"])

    surf.fill(utils.color(cfg["bg"]))

    for type_, key, pos in cfg["sprites"]:
        if type_ == "text":
            image = display.draw_text(key)
            surf.blit(image, pos)
        elif type_ == "var":
            text = str(vars[key])
            image = display.draw_text(text)
            surf.blit(image, pos)
        elif type_ == "image":
            sprite = Sprite(key)
            surf.blit(sprite.image, pos)

    return surf

class TitleState(State):
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
        surf = render_scene("title", {"p1score":0, "hiscore":0})
        camera.screen.blit(surf, [0,0])

class BlinkState(TitleState):
    def __init__(self, engine):
        TitleState.__init__(self, engine)

        self.timer = 0
        self.blink_rate = utils.config["frame_rate"] / 2

        self.sound = Sound("Intro")

    def input(self, event):
        pass

    def update(self):
        self.timer = (self.timer + 1) % (self.blink_rate * 2)

        if self.sound.is_done():
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
        camera.screen.blit(display.draw_text("ROUND %2d" % self.engine.level), [96, 108])

class Engine(object):
    def __init__(self):
        self.high = 0
        self.players = 1
        self.level = 1
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
