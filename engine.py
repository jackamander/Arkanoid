"""
Main game engine for Arkanoid
"""

import re

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

        self.scene = display.Scene(["title", "banner"], engine.vars)

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        # Update cursor position
        if event.name == "players":
            index = event.value - 1
            cursor = self.scene.names["cursor"]
            pos = cursor.cfg["locations"][index]
            cursor.set_pos(pos)

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
        elif event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class BlinkState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["title", "banner"], engine.vars)

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
        self.scene.groups["all"].update()

        if not self.sound.get_busy():
            self.engine.set_state(RoundState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class RoundState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["round", "banner"], engine.vars)

        utils.timers.start(2.0, self.engine.set_state, StartState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

def show_lives(state):
    for name, sprite in state.scene.names.items():
        mobj = re.match("life(\\d+)", name)
        if mobj:
            num = int(mobj.group(1))
            if state.engine.vars["lives"] <= num:
                sprite.kill()

class StartState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["hud", "ready"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self.sound = audio.play_sound("Ready")

    def update(self):
        self.scene.groups["all"].update()

        if not self.sound.get_busy():
            self.engine.set_state(GameState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["hud", "tools"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self.ball = self.scene.names["ball"]

        # Set up the paddle behavior
        self.paddle = self.scene.names["paddle"]

        playspace = self.paddle.rect.copy()
        playspace.left = self.scene.names["left"].rect.right
        playspace.width = self.scene.names["right"].rect.left - playspace.left
        self.paddle.set_action(display.MouseMove(playspace, [1,0]))

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

        self.enable_stuck(self.ball)

    def enable_stuck(self, ball):
        # Stick the ball to the paddle
        ball.set_action(display.Follow(self.paddle))

        # Listen for release
        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, lambda event: self.disable_stuck(ball))

        # Set up the auto release timer
        utils.timers.start(3.0, self.disable_stuck, ball)

    def disable_stuck(self, ball):
        utils.timers.cancel(self.disable_stuck)
        ball.set_action(display.Move([1,-2]))
        audio.play_sound("Low")

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)

    def update(self):
        self.scene.groups["all"].update()

        # Ball-Paddle collisions
        if pygame.sprite.collide_rect(self.paddle, self.ball):
            delta = self.ball.rect.centerx - self.paddle.rect.centerx

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

            self.ball.set_action(display.Move(vel))
            audio.play_sound("Low")

        # Ball collisions
        sprites = pygame.sprite.spritecollide(self.ball, self.scene.groups["ball"], False)
        for sprite in sprites:
            side = collision_side(self.ball, sprite)

            if side == "top":
                self.ball.action.delta[1] = abs(self.ball.action.delta[1])
            elif side == "bottom":
                self.ball.action.delta[1] = -abs(self.ball.action.delta[1])
            elif side == "left":
                self.ball.action.delta[0] = abs(self.ball.action.delta[0])
            elif side == "right":
                self.ball.action.delta[0] = -abs(self.ball.action.delta[0])

            sound = sprite.cfg.get("hit_sound")
            if sound:
                audio.play_sound(sound)

            animation = sprite.cfg.get("hit_animation")
            if animation:
                sprite.set_action(display.Animate(animation))

            hits = sprite.cfg.get("hits")
            if hits:
                hits -= 1
                sprite.cfg["hits"] = hits
                if hits == 0:
                    sprite.kill()

                    points = sprite.cfg.get("points", 0)
                    self.engine.vars["score1"] += points

        # Ball exit detection
        sprites = pygame.sprite.spritecollide(self.ball, self.scene.groups["bg"], False)
        if self.ball.alive() and len(sprites) == 0:
            self.ball.kill()
            self.paddle.set_action(display.Animate("explode").then(display.Die()))
            self.sound = audio.play_sound("Death")

        if not self.paddle.alive() and not self.sound.get_busy():
            self.engine.vars["lives"] -= 1

            if self.engine.vars["lives"] > 0:
                self.engine.set_state(RoundState)
            else:
                self.engine.set_state(TitleState)

        # Level completion detection
        if len(self.scene.groups["bricks"]) == 0:
            self.engine.vars["level"] += 1
            self.engine.set_state(RoundState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

def collision_side(sprite1, sprite2):
    # Expand to include velocity
    s1rect = sprite1.rect.union(sprite1.last)
    s2rect = sprite2.rect.union(sprite2.last)

    wy = (s1rect.width + s2rect.width) * (s1rect.centery - s2rect.centery)
    hx = (s1rect.height + s2rect.height) * (s1rect.centerx - s2rect.centerx)

    if wy > hx:
        if wy > -hx:
            side = "top"
        else:
            side = "right"
    else:
        if wy > -hx:
            side = "left"
        else:
            side = "bottom"

    return side

class Vars:
    def __init__(self, initial={}):
        self.data = initial

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        utils.events.generate(utils.EVT_VAR_CHANGE, name=key, value=value)

class Engine(object):
    
    INITIAL_STATE = TitleState

    def __init__(self):
        self.vars = Vars({
            "high":50000, 
            "score1":0, 
            "level":1, 
            "player":1, 
            "lives":3, 
            "players":1,
        })

        # Pre-allocate all level scenes
        levels = {}
        for key in utils.config["scenes"]:
            mobj = re.match("level(\d+)", key)
            if mobj:
                level = int(mobj.group(1))
                levels[level] = key

        self.scenes = {level : display.Scene([key], self.vars) for level, key in levels.items()}

        self.state = self.INITIAL_STATE(self)

    def set_state(self, state):
        utils.events.clear()
        utils.timers.clear()
        self.state = state(self)

    def input(self, event):
        utils.events.handle(event)
        self.state.input(event)

    def update(self):
        utils.timers.update()
        self.state.update()

    def draw(self, screen):
        self.state.draw(screen)
