"""
Main game engine for Arkanoid
"""

import random
import re

import pygame

import audio
import display
import utils

CollisionSide_None = 0
CollisionSide_Top = 1
CollisionSide_Bottom = 2
CollisionSide_Left = 4
CollisionSide_Right = 8

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
            else:
                state.scene.groups["all"].add(sprite)

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

class BreakState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["hud", "walls", "break"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self._break = self.scene.names["break"]
        self._break.set_action(display.Animate(self._break.cfg["animation"]))

        self.paddle_shrink = self.scene.names["paddle_shrink"]
        self.paddle_shrink.set_action(display.Animate(self.paddle_shrink.cfg["animation"]).then(display.Die()).plus(display.Move([0.5,0])))

        self.sound = audio.play_sound("Break")

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(BreakState)

    def update(self):
        self.scene.groups["all"].update()

        if not self.sound.get_busy():
            next_level(self.engine)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class Paddle:
    def __init__(self, sprite, playspace, state):
        self.state = state
        self.sprite = sprite
        self.stuck_ball = None
        self.sound = None
        self.catch = False

        self.sprite.set_action(display.MouseMove(playspace, [1,0]))

        self.state.scene.names["laser"].kill()

    def expand(self):
        self.sprite.set_image(display.get_image("paddle_ext"))
        utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)
        audio.play_sound("Enlarge")

    def normal(self):
        self.sprite.set_image(display.get_image("paddle"))
        utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)

    def laser(self):
        self.sprite.set_image(display.get_image("paddle_laser"))
        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)

    def fire_laser(self, event):
        sprite = self.state.scene.names["laser"].clone()

        sprite.rect.center = self.sprite.rect.center
        sprite.rect.bottom = self.sprite.rect.top

        sprite.set_action(display.Move([0,-4]))
        self.state.scene.groups["all"].add(sprite)
        self.state.scene.groups["lasers"].add(sprite)

        audio.play_sound("Laser")

    def catch_ball(self, ball):
        if self.stuck_ball is None:
            self.stuck_ball = ball
            self.stuck_ball.set_action(display.Follow(self.sprite))
            utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.release_ball)
            utils.timers.start(3.0, self.release_ball)

    def release_ball(self, event=None):
        if self.stuck_ball is not None:
            utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.release_ball)
            utils.timers.cancel(self.release_ball)
            self.hit_ball(self.stuck_ball)
            self.stuck_ball = None

    def hit(self, ball):
        if self.catch:
            self.catch_ball(ball)
        elif self.stuck_ball:
            self.release_ball()
        else:
            self.hit_ball(ball)

    def hit_ball(self, ball):
        delta = ball.rect.centerx - self.sprite.rect.centerx

        if delta < -13:
            vel = [-2,-1]
        elif delta < -8:
            vel = [-1.6,-1.6]
        elif delta < 0:
            vel = [-1,-2]
        elif delta < 8:
            vel = [1,-2]
        elif delta < 13:
            vel = [1.6,-1.6]
        else:
            vel = [2,-1]

        vel = [i * self.state.ball_speed for i in vel]

        ball.set_action(display.Move(vel))
        audio.play_sound("Low")

    def kill(self):
        self.sprite.set_action(display.Animate("explode").then(display.Die()))
        self.sound = audio.play_sound("Death")

    def alive(self):
        return self.sprite.alive() or self.sound.get_busy()

class Capsules:
    def __init__(self, state, paddle):
        self.state = state
        self.scene = state.scene
        self.paddle = paddle

        for capsule in self.scene.groups["capsules"]:
            capsule.kill()
            self.scene.groups["capsules"].add(capsule)

        self.total = self.available()

        self.disable()
        self.enable()

        self._break = self.scene.names["break"]
        self._break.set_action(display.Animate(self._break.cfg["animation"]))
        self._break.kill()
        self.scene.names["paddle_shrink"].kill()

    def available(self):
        return len(self.scene.groups["capsules"].sprites())

    def disable(self):
        self.count = 0

    def enable(self):
        if self.count == 0:
            self.count = random.randint(1, 10)

    def apply(self, capsule):
        effect = capsule.cfg.get("effect", "")
        if effect == "break":
            self.scene.groups["all"].add(self._break)
            self.scene.groups["break"].add(self._break)
        elif effect == "disrupt":
            pos = self.state.balls[0].rect.topleft
            last = self.state.balls[0].last.topleft

            signs = [1 if pos[i] - last[i] >= 0 else -1 for i in range(2)]
            vels = [[1,2], [1.6,1.6], [2,1]]
            vels = [[x * signs[0] * self.state.ball_speed, y * signs[1] * self.state.ball_speed] for x,y in vels]

            self.state.balls = [self.scene.names[name] for name in ["ball1", "ball2", "ball3"]]

            for sprite, vel in zip(self.state.balls, vels):
                sprite.set_pos(pos)

                sprite.kill()
                self.scene.groups["all"].add(sprite)
                sprite.set_action(display.Move(vel))

            self.disable()
        elif effect == "player":
            self.state.engine.vars["lives"] += 1
            audio.play_sound("Life")
            show_lives(self.state)
        elif effect == "slow":
            self.state.ball_speed /= utils.config["ball_speed"]

            for ball in self.state.balls:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i / utils.config["ball_speed"] for i in ball.action.delta]

        if effect == "laser":
            self.state.paddle.laser()
        elif effect == "enlarge":
            self.state.paddle.expand()
        else:
            self.state.paddle.normal()

        if effect == "catch":
            self.paddle.catch = True
        else:
            self.paddle.catch = False

        points = capsule.cfg.get("points", 0)
        utils.events.generate(utils.EVT_POINTS, points=points)

    def kill(self, capsule):
        capsule.set_pos([0,0])
        capsule.set_action(None)
        capsule.kill()
        self.scene.groups["capsules"].add(capsule)

        self.enable()

    def on_brick(self, sprite):
        if self.total == self.available() and self.count > 0:
            self.count -= 1

            if self.count == 0:
                choices = [capsule for capsule in self.scene.groups["capsules"].sprites() for _ in range(capsule.cfg["weight"])]
                capsule = random.choice(choices)
                capsule.set_pos(sprite.get_pos())
                capsule.set_action(display.Move([0,1]).plus(display.Animate(capsule.cfg["animation"])))
                self.scene.groups["capsules"].remove(capsule)
                self.scene.groups["paddle"].add(capsule)
                self.scene.groups["all"].add(capsule)

def next_level(engine):
    engine.vars["level"] += 1
    if engine.vars["level"] <= engine.last_level:
        engine.set_state(RoundState)
    else:
        engine.set_state(VictoryState)

class GameState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["hud", "walls", "tools", "break"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["level"]])

        show_lives(self)

        self.playspace = self.scene.names["bg"].rect
        self.balls = [self.scene.names["ball1"]]
        self.scene.names["ball2"].kill()
        self.scene.names["ball3"].kill()

        self.ball_speed = 1

        self.paddle = Paddle(self.scene.names["paddle"], self.playspace, self)
        self.paddle.catch_ball(self.balls[0])

        self.capsules = Capsules(self, self.paddle)

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_POINTS, self.on_points)

        utils.timers.start(10.0, self.on_timer)

    def on_timer(self):
        if self.ball_speed < 4:
            self.ball_speed *= utils.config["ball_speed"]

            for ball in self.balls:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i * utils.config["ball_speed"] for i in ball.action.delta]

        utils.timers.start(10.0, self.on_timer)

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
        for ball in self.balls:
            if pygame.sprite.collide_rect(self.paddle.sprite, ball):
                self.paddle.hit(ball)

        # Break support
        for sprite in self.scene.groups["break"]:
            if self.paddle.sprite.rect.right + 1 >= sprite.rect.left:
                utils.events.generate(utils.EVT_POINTS, points=10000)
                self.engine.set_state(BreakState)

        # Capsules
        sprites = pygame.sprite.spritecollide(self.paddle.sprite, self.scene.groups["paddle"], False)
        for sprite in sprites:
            self.capsules.kill(sprite)
            self.capsules.apply(sprite)

        for sprite in self.scene.groups["paddle"]:
            if sprite.alive() and not sprite.rect.colliderect(self.playspace):
                self.capsules.kill(sprite)

        # Ball and laser collisions
        for ball in self.balls + self.scene.groups["lasers"].sprites():
            sprites = pygame.sprite.spritecollide(ball, self.scene.groups["ball"], False)
            for sprite in sprites:
                hits = ball.cfg.get("hits")
                if hits:
                    hits -= 1
                    ball.cfg["hits"] = hits
                    if hits == 0:
                        ball.kill()
                else:
                    if isinstance(ball.action, display.Move):
                        side = collision_side(ball, sprite)

                        if side == CollisionSide_Bottom:
                            ball.action.delta[1] = abs(ball.action.delta[1])
                        elif side == CollisionSide_Top:
                            ball.action.delta[1] = -abs(ball.action.delta[1])
                        elif side == CollisionSide_Right:
                            ball.action.delta[0] = abs(ball.action.delta[0])
                        elif side == CollisionSide_Left:
                            ball.action.delta[0] = -abs(ball.action.delta[0])

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
        for ball in list(self.balls):
            if ball.alive() and not ball.rect.colliderect(self.playspace):
                ball.kill()
                self.balls.remove(ball)

                if len(self.balls) == 1:
                    self.capsules.enable()

                if len(self.balls) == 0:
                    self.paddle.kill()

        if not self.paddle.alive():
            self.engine.vars["lives"] -= 1

            if self.engine.vars["lives"] > 0:
                self.engine.set_state(RoundState)
            else:
                self.engine.set_state(TitleState)

        # Level completion detection
        if len(self.scene.groups["bricks"]) == 0:
            next_level(self.engine)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

def collision_side(sprite1, sprite2):
    # Code adapted from https://hopefultoad.blogspot.com/2017/09/code-example-for-2d-aabb-collision.html

    cornerSlopeRise = 0
    cornerSlopeRun = 0

    velocityRise = sprite1.rect.top - sprite1.last.top
    velocityRun = sprite1.rect.left - sprite1.last.left

    # Stores what sides might have been collided with
    potentialCollisionSide = CollisionSide_None

    if sprite1.last.right <= sprite2.rect.left:
        # Did not collide with right side might have collided with left side
        potentialCollisionSide |= CollisionSide_Left

        cornerSlopeRun = sprite2.rect.left - sprite1.last.right

        if sprite1.last.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potentialCollisionSide |= CollisionSide_Top
            cornerSlopeRise = sprite2.rect.top - sprite1.last.bottom
        elif sprite1.last.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potentialCollisionSide |= CollisionSide_Bottom
            cornerSlopeRise = sprite2.rect.bottom - sprite1.last.top
        else:
            # Did not collide with top side or bottom side or right side
            return CollisionSide_Left
    elif sprite1.last.left >= sprite2.rect.right:
        # Did not collide with left side might have collided with right side
        potentialCollisionSide |= CollisionSide_Right

        cornerSlopeRun = sprite1.last.left - sprite2.rect.right

        if sprite1.last.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potentialCollisionSide |= CollisionSide_Top
            cornerSlopeRise = sprite1.last.bottom - sprite2.rect.top
        elif sprite1.last.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potentialCollisionSide |= CollisionSide_Bottom
            cornerSlopeRise = sprite1.last.top - sprite2.rect.bottom
        else:
            # Did not collide with top side or bottom side or left side
            return CollisionSide_Right
    else:
        # Did not collide with either left or right side
        # must be top side, bottom side, or none
        if sprite1.last.bottom <= sprite2.rect.top:
            return CollisionSide_Top
        elif sprite1.last.top >= sprite2.rect.bottom:
            return CollisionSide_Bottom
        else:
            # Previous hitbox of moving object was already colliding with stationary object
            return CollisionSide_None

    # Corner case might have collided with more than one side
    # Compare slopes to see which side was collided with
    return GetCollisionSideFromSlopeComparison(potentialCollisionSide,
        velocityRise, velocityRun, cornerSlopeRise, cornerSlopeRun)

def GetCollisionSideFromSlopeComparison(potentialSides, velocityRise, velocityRun, nearestCornerRise, nearestCornerRun):
    if velocityRun == 0:
        velocityRun = 0.001

    if nearestCornerRun == 0:
        nearestCornerRun = 0.001

    velocitySlope = velocityRise / velocityRun
    nearestCornerSlope = nearestCornerRise / nearestCornerRun

    if (potentialSides & CollisionSide_Top) == CollisionSide_Top:
        if (potentialSides & CollisionSide_Left) == CollisionSide_Left:
            if velocitySlope < nearestCornerSlope:
                return CollisionSide_Top
            else:
                return CollisionSide_Left
        elif (potentialSides & CollisionSide_Right) == CollisionSide_Right:
            if velocitySlope > nearestCornerSlope:
                return CollisionSide_Top
            else:
                return CollisionSide_Right
    elif (potentialSides & CollisionSide_Bottom) == CollisionSide_Bottom:
        if (potentialSides & CollisionSide_Left) == CollisionSide_Left:
            if velocitySlope > nearestCornerSlope:
                return CollisionSide_Bottom
            else:
                return CollisionSide_Left
        elif (potentialSides & CollisionSide_Right) == CollisionSide_Right:
            if velocitySlope < nearestCornerSlope:
                return CollisionSide_Bottom
            else:
                return CollisionSide_Right
    return CollisionSide_None

class VictoryState(State):
    def __init__(self, engine):
        State.__init__(self, engine)

        self.scene = display.Scene(["victory", "banner"], engine.vars)

        utils.timers.start(5.0, self.engine.set_state, TitleState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

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

        self.last_level = max(levels.keys())

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
