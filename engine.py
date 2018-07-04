"""
Main game engine for Arkanoid
"""

import pygame

import audio
import display
import utils

class State(object):
    def __init__(self, engine):
        self.engine = engine

    def input(self, event):
        return ""

    def update(self):
        pass

    def draw(self, screen):
        pass

class TitleState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.group, self.names, self.data = display.render_scene("title", engine.vars)

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

    def draw(self, screen):
        display.clear_screen(screen)

        # Update cursor position
        index = self.engine.players - 1
        pos = self.data[index]
        self.names["cursor"].set_pos(pos)

        self.group.draw(screen)

class BlinkState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.group, self.names, self.data = display.render_scene("title", engine.vars)

        self.sound = audio.play_sound("Intro")

        # Blink the chosen option
        key = {1 : "p1", 2 : "p2"}[engine.players]
        self.names[key].set_action(display.Blink(1.0))

        # Get rid of the cursor
        self.names["cursor"].kill()

    def update(self):
        self.group.update()

        if not self.sound.get_busy():
            return "round"

    def draw(self, screen):
        display.clear_screen(screen)
        self.group.draw(screen)

class RoundState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.group, self.names, self.data = display.render_scene("round", engine.vars)

        self.counter = 0

    def update(self):
        self.counter += 1

        if self.counter > 2 * utils.config["frame_rate"]:
            return "game"

    def draw(self, screen):
        display.clear_screen(screen)
        self.group.draw(screen)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.playspace = pygame.Rect(*utils.config["playspace"])

        key = str(engine.vars["level"])
        cfg = utils.config["levels"][key]

        bg_key = cfg["bg"]
        bg_image = display.get_image(bg_key)
        bg_sprite = display.Sprite(bg_image)
        self.bg = pygame.sprite.Group(bg_sprite)

        paddle_image = display.get_image("paddle")
        self.paddle = display.Sprite(paddle_image)

        self.fg = pygame.sprite.Group(self.paddle)

        for row, data in enumerate(cfg["map"]):
            for col, block in enumerate(data):
                if block != " ":
                    image = display.get_image(block)
                    sprite = display.Sprite(image)
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

    def draw(self, screen):
        screen.fill(utils.color(utils.config["bg_color"]))
        self.bg.draw(screen)
        self.fg.draw(screen)

class Engine(object):
    def __init__(self):
        self.vars = {"high":0, "score1":0, "level":1}
        self.players = 1
        self.state = TitleState(self)

    def set_state(self, next_state):
        if next_state == "blink":
            self.state = BlinkState(self)
        elif next_state == "round":
            self.state = RoundState(self)
        elif next_state == "game":
            self.state = GameState(self)

    def input(self, event):
        next_state = self.state.input(event)
        self.set_state(next_state)

    def update(self):
        next_state = self.state.update()
        self.set_state(next_state)

    def draw(self, screen):
        self.state.draw(screen)
