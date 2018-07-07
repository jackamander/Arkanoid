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

        self.engine.events.register(pygame.MOUSEBUTTONDOWN, self.on_click)
        self.engine.events.register(pygame.KEYDOWN, self.on_keydown)

    def input(self, event):
        # Update cursor position
        index = self.engine.vars["players"] - 1
        pos = self.scene.data[index]
        self.scene.names["cursor"].set_pos(pos)

    def on_click(self, event):
        if event.button == 1:
            self.engine.set_state(BlinkState)

    def on_keydown(self, event):
        if event.key == pygame.K_UP:
            self.engine.vars["players"] = 1
        elif event.key == pygame.K_DOWN:
            self.engine.vars["players"] = 2
        elif event.key == pygame.K_RETURN:
            self.engine.set_state(BlinkState)

    def draw(self, screen):
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
        self.scene.group.draw(screen)

class RoundState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene("round", engine.vars)

        self.engine.timer.start(2.0, self.engine.set_state, StartState)

    def draw(self, screen):
        self.scene.group.draw(screen)

class StartState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        level_key ="level%d" % engine.vars["level"]
        self.scenes = {scene : display.Scene(scene, engine.vars) for scene in ["hud", level_key, "ready", "walls"]}

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
        for scene in self.scenes.values():
            scene.group.draw(screen)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        level_key ="level%d" % engine.vars["level"]
        self.scenes = {scene : display.Scene(scene, engine.vars) for scene in ["hud", level_key, "tools", "walls"]}

        # Lives
        for life in range(engine.vars["lives"], 7):
            key = "life%d" % life
            self.scenes["hud"].names[key].kill()

        self.playspace = pygame.Rect(*utils.config["playspace"])

        self.ball = self.scenes["tools"].names["ball"]
        self.paddle = self.scenes["tools"].names["paddle"]

        self.engine.events.register(pygame.MOUSEMOTION, self.on_mousemove)
        self.engine.events.register(pygame.KEYDOWN, self.on_keydown)

        self.enable_stuck(self.ball)

    def enable_stuck(self, ball):
        # Stick the ball to the paddle
        ball.set_action(display.Follow(self.paddle))

        # Listen for release
        self.engine.events.register(pygame.MOUSEBUTTONDOWN, lambda event: self.disable_stuck(ball))

        # Set up the auto release timer
        self.engine.timer.start(3.0, self.disable_stuck, ball)

    def disable_stuck(self, ball):
        self.engine.timer.cancel(self.disable_stuck)
        ball.set_action(display.Move([1,-2]))
        audio.play_sound("Low")

    def on_mousemove(self, event):
        self.paddle.move([event.rel[0],0])
        self.paddle.rect.clamp_ip(self.playspace)

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)

    def update(self):
        for scene in self.scenes.values():
            scene.group.update()

        # Ball-Wall collisions
        # Don't just flip the velocity sign - the ball can get stuck in the wall!
        ball = self.ball
        if ball.rect.left < self.playspace.left:
            ball.action.delta[0] = abs(ball.action.delta[0])
        elif ball.rect.right > self.playspace.right:
            ball.action.delta[0] = -abs(ball.action.delta[0])

        if ball.rect.top < self.playspace.top:
            ball.action.delta[1] = abs(ball.action.delta[1])
        elif ball.rect.top > self.playspace.bottom:
            ball.kill()

        # Ball-Paddle collisions
        if pygame.sprite.collide_rect(self.paddle, ball):
            delta = ball.rect.centerx - self.paddle.rect.centerx

            if delta < -13:
                vel = [-2,-1]
            elif delta < -8:
                vel = [-2,-2]
            elif delta < 0:
                vel = [-1,-2]
            elif delta < 8:
                vel = [1,-2]
            elif delta < 13:
                vel = [2,-2]
            else:
                vel = [2,-1]

            ball.set_action(display.Move(vel))
            audio.play_sound("Low")

        # Ball-Wall collisions
        sprites = pygame.sprite.spritecollide(ball, self.scenes["walls"].group, False)
        for sprite in sprites:
            side = utils.collision_side(ball, sprite)

            if side == "top":
                ball.action.delta[1] = abs(ball.action.delta[1])
            elif side == "bottom":
                ball.action.delta[1] = -abs(ball.action.delta[1])
            elif side == "left":
                ball.action.delta[0] = abs(ball.action.delta[0])
            elif side == "right":
                ball.action.delta[0] = -abs(ball.action.delta[0])
            print sprite.name, side,

        if len(sprites):
            print

        # Ball-Brick collisions
        sprites = pygame.sprite.spritecollide(ball, self.scenes["level1"].group, False)
        for sprite in sprites:
            side = utils.collision_side(ball, sprite)

            if side == "top":
                ball.action.delta[1] = abs(ball.action.delta[1])
            elif side == "bottom":
                ball.action.delta[1] = -abs(ball.action.delta[1])
            elif side == "left":
                ball.action.delta[0] = abs(ball.action.delta[0])
            elif side == "right":
                ball.action.delta[0] = -abs(ball.action.delta[0])

            audio.play_sound("Med")

            sprite.kill()

    def draw(self, screen):
        for scene in self.scenes.values():
            scene.group.draw(screen)

class DebugState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scenes = {scene : display.Scene(scene, engine.vars) for scene in ["debug"]}

        self.ball = self.scenes["debug"].names["ball"]
        self.brick = self.scenes["debug"].names["brick"]

        self.engine.events.register(pygame.KEYDOWN, self.on_keydown)

    def on_keydown(self, event):
        delta = [0,0]

        if event.key == pygame.K_UP:
            delta = [0,-1]
        elif event.key == pygame.K_DOWN:
            delta = [0,1]
        elif event.key == pygame.K_LEFT:
            delta = [-1,0]
        elif event.key == pygame.K_RIGHT:
            delta = [1,0]

        self.scenes["debug"].names["ball"].move(delta)

        if pygame.sprite.collide_rect(self.ball, self.brick):
            side = utils.collision_side(self.ball, self.brick)
            print side
        else:
            print

    def update(self):
        for scene in self.scenes.values():
            scene.group.update()

    def draw(self, screen):
        for scene in self.scenes.values():
            scene.group.draw(screen)

class Engine(object):
    def __init__(self):
        self.vars = {"high":0, "score1":0, "level":1, "player":1, "lives":3, "players":1}
        self.events = utils.Events()
        self.timer = utils.Timer()

        self.state = TitleState(self)

    def set_state(self, state):
        self.events.clear()
        self.timer.clear()
        self.state = state(self)

    def input(self, event):
        self.events.input(event)
        self.state.input(event)

    def update(self):
        self.timer.update()
        self.state.update()

    def draw(self, screen):
        self.state.draw(screen)
