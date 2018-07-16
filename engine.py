"""
Main game engine for Arkanoid
"""

import random
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
            self.engine.reset(self.engine.vars["high"])
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

        self.scene = display.Scene(["hud", "walls", "ready"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self.sound = audio.play_sound("Ready")

    def update(self):
        self.scene.groups["all"].update()

        if not self.sound.get_busy():
            self.engine.set_state(GameState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class Paddle:
    def __init__(self, sprite, playspace):
        self.sprite = sprite
        self.stuck_ball = None
        self.sound = None

        self.sprite.set_action(display.MouseMove(playspace, [1,0]))

    def stick_ball(self, ball):
        if self.stuck_ball is None:
            self.stuck_ball = ball
            self.stuck_ball.set_action(display.Follow(self.sprite))
            utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.unstick_ball)
            utils.timers.start(3.0, self.unstick_ball)

    def unstick_ball(self, event=None):
        if self.stuck_ball is not None:
            utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.unstick_ball)
            utils.timers.cancel(self.unstick_ball)
            self.hit_ball(self.stuck_ball)
            self.stuck_ball = None

    def hit_ball(self, ball):
        delta = ball.rect.centerx - self.sprite.rect.centerx

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

    def kill(self):
        self.sprite.set_action(display.Animate("explode").then(display.Die()))
        self.sound = audio.play_sound("Death")

    def alive(self):
        return self.sprite.alive() or self.sound.get_busy()

class Capsules:
    def __init__(self, scene):
        self.scene = scene

        for capsule in self.scene.groups["capsules"]:
            capsule.kill()
            self.scene.groups["capsules"].add(capsule)

        self.enable()

    def disable(self):
        self.count = 0

    def enable(self):
        self.count = random.randint(1, 10)

    def kill(self, capsule):
        capsule.set_pos([0,0])
        capsule.set_action(None)
        capsule.kill()
        self.scene.groups["capsules"].add(capsule)

        self.enable()

    def on_brick(self, sprite):
        if self.count > 0:
            self.count -= 1

            if self.count == 0:
                capsule = random.choice(self.scene.groups["capsules"].sprites())
                capsule.set_pos(sprite.get_pos())
                capsule.set_action(display.Move([0,1]).plus(display.Animate(capsule.cfg["animation"])))
                self.scene.groups["paddle"].add(capsule)
                self.scene.groups["all"].add(capsule)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["hud", "walls", "tools"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self.playspace = self.scene.names["bg"].rect
        self.ball = self.scene.names["ball"]
        self.paddle = Paddle(self.scene.names["paddle"], self.playspace)
        self.paddle.stick_ball(self.ball)

        self.capsules = Capsules(self.scene)

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_POINTS, self.on_points)

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)

    def on_points(self, event):
        self.engine.vars["score1"] += event.points
        if self.engine.vars["score1"] > self.engine.vars["high"]:
            self.engine.vars["high"] = self.engine.vars["score1"]

    def update(self):
        self.scene.groups["all"].update()

        # Ball-Paddle collisions
        if pygame.sprite.collide_rect(self.paddle.sprite, self.ball):
            self.paddle.hit_ball(self.ball)

        # Capsules
        sprites = pygame.sprite.spritecollide(self.paddle.sprite, self.scene.groups["paddle"], False)
        for sprite in sprites:
            self.capsules.kill(sprite)

        for sprite in self.scene.groups["paddle"]:
            if sprite.alive() and not sprite.rect.colliderect(self.playspace):
                self.capsules.kill(sprite)

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
                    self.capsules.on_brick(sprite)

                    points = sprite.cfg.get("points", 0)
                    utils.events.generate(utils.EVT_POINTS, points=points)

        # Ball exit detection
        if self.ball.alive() and not self.ball.rect.colliderect(self.playspace):
            self.ball.kill()
            self.paddle.kill()

        if not self.paddle.alive():
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
        self.reset(0)

    def reset(self, high):
        self.vars = Vars({
            "high":high,
            "score1":0,
            "level":1,
            "player":1,
            "lives":3,
            "players":1,
        })

        # Pre-allocate all level scenes
        levels = {}
        for key in utils.config["scenes"]:
            mobj = re.match("level(\\d+)", key)
            if mobj:
                level = int(mobj.group(1))
                levels[level] = key

        self.scenes = {level : display.Scene([key], self.vars) for level, key in levels.items()}

        self.set_state(self.INITIAL_STATE)

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
