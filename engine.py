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
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass

class TitleState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene("title", engine.vars)

    def input(self, event):
        if event.type == pygame.MOUSEMOTION:
            pass
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.engine.set_state(BlinkState)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.engine.vars["players"] = 1
            elif event.key == pygame.K_DOWN:
                self.engine.vars["players"] = 2
            elif event.key == pygame.K_RETURN:
                self.engine.set_state(BlinkState)

        # Update cursor position
        index = self.engine.vars["players"] - 1
        pos = self.scene.data[index]
        self.scene.names["cursor"].set_pos(pos)

    def draw(self, screen):
        display.clear_screen(screen)
        self.scene.group.draw(screen)

class BlinkState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene("title", engine.vars)

        self.sound = audio.play_sound("Intro")

        # Blink the chosen option
        if engine.vars["players"] == 1:
            key = "p1"
        else:
            key = "p2"
        self.scene.names[key].set_action(display.Blink(1.0))

        # Get rid of the cursor
        self.scene.names["cursor"].kill()

    def update(self):
        self.scene.group.update()

        if not self.sound.get_busy():
            self.engine.set_state(RoundState)

    def draw(self, screen):
        display.clear_screen(screen)
        self.scene.group.draw(screen)

class RoundState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene("round", engine.vars)

        self.counter = 0
        self.limit = 2 * utils.config["frame_rate"]

    def update(self):
        self.counter += 1

        if self.counter > self.limit:
            self.engine.set_state(StartState)

    def draw(self, screen):
        display.clear_screen(screen)
        self.scene.group.draw(screen)

class StartState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        level_key ="level%d" % engine.vars["level"]
        self.scenes = {scene : display.Scene(scene, engine.vars) for scene in ["hud", level_key, "ready"]}

        # Lives
        for life in range(engine.vars["lives"], 7):
            key = "life%d" % life
            self.scenes["hud"].names[key].kill()

        self.sound = audio.play_sound("Ready")

    def update(self):
        for scene in self.scenes.values():
            scene.group.update()

        if not self.sound.get_busy():
            self.engine.set_state(GameState)

    def draw(self, screen):
        display.clear_screen(screen)
        for scene in self.scenes.values():
            scene.group.draw(screen)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        level_key ="level%d" % engine.vars["level"]
        self.scenes = {scene : display.Scene(scene, engine.vars) for scene in ["hud", level_key, "tools"]}

        # Lives
        for life in range(engine.vars["lives"], 7):
            key = "life%d" % life
            self.scenes["hud"].names[key].kill()

        self.playspace = pygame.Rect(*utils.config["playspace"])

        self.balls = [self.scenes["tools"].names["ball"]]
        self.paddle = self.scenes["tools"].names["paddle"]

        self.balls[0].set_action(display.Follow(self.paddle))

    def input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.paddle.move([event.rel[0],0])
            self.paddle.rect.clamp_ip(self.playspace)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.balls[0].set_action(display.Move([1,-2]))

    def update(self):
        for scene in self.scenes.values():
            scene.group.update()

        ball = self.balls[0]
        if ball.rect.left < self.playspace.left or ball.rect.right > self.playspace.right:
            ball.action.delta[0] *= -1
        if ball.rect.top < self.playspace.top:
            ball.action.delta[1] *= -1
        if ball.rect.top > self.playspace.bottom:
            ball.kill()

    def draw(self, screen):
        display.clear_screen(screen)
        for scene in self.scenes.values():
            scene.group.draw(screen)

class Engine(object):
    def __init__(self):
        self.vars = {"high":0, "score1":0, "level":1, "player":1, "lives":3, "players":1}
        self.state = TitleState(self)

    def set_state(self, state):
        self.state = state(self)

    def input(self, event):
        self.state.input(event)

    def update(self):
        self.state.update()

    def draw(self, screen):
        self.state.draw(screen)
