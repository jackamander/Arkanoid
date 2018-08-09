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
    def __init__(self, engine, data):
        self.engine = engine

    def input(self, event):
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass

class SplashState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["banner", "splash"], engine.vars)

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

        self.splash = self.scene.names["splash"]
        self.splash.set_action(display.MoveLimited([0,-2], (224-48)/2))
        utils.timers.start(10.0, self.engine.set_state, TitleState)

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_click(self, event):
        if event.button == 1:
            self.engine.set_state(TitleState)

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)

    def update(self):
        self.splash.update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class TitleState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["title", "banner"], engine.vars)

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

        display.release_mouse()

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
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

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

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

    def update(self):
        self.scene.groups["all"].update()

        if self.sound is None or not self.sound.get_busy():
            self.engine.reset()
            self.engine.set_state(RoundState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class RoundState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["round", "banner"], engine.vars)

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

        utils.timers.start(2.0, self.engine.set_state, StartState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

def show_lives(state):
    for name, sprite in state.scene.names.items():
        mobj = re.match("life(\\d+)", name)
        if mobj:
            num = int(mobj.group(1))
            if state.engine.vars["lives1" if state.engine.vars["player"] == 1 else "lives2"] <= num:
                sprite.kill()
            else:
                state.scene.groups["all"].add(sprite)

class StartState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["hud", "walls", "ready"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["player"]][engine.vars["level"]])

        if engine.vars["player"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()
        else:
            self.scene.names["1UP"].kill()
            self.scene.names["score1"].kill()

        show_lives(self)

        # This is to fix any stale state from previous lives.  A better solution
        # is to reload the sprite from the config each round.
        doh = self.scene.names.get("doh", None)
        if doh:
            sound = "DohStart"
            doh.set_action(display.DohMgr(self.scene, doh))
        else:
            sound = "Ready"
        self.sound = audio.play_sound(sound)

        utils.timers.start(3.0, self.engine.set_state, GameState)

        display.grab_mouse()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class BreakState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.paddle = data["paddle"]

        self.paddle._break()

    def update(self):
        for name in ["high", "score1", "score2", "break", "paddle"]:
            self.scene.names[name].update()

        if not self.paddle.alive():
            next_level(self.engine)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class DeathState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.paddle = data["paddle"]

        self.paddle.kill()

    def update(self):
        for name in ["high", "score1", "score2", "paddle"]:
            self.scene.names[name].update()

        if not self.paddle.alive():
            self.engine.vars["lives1" if self.engine.vars["player"] == 1 else "lives2"] -= 1

            for _ in range(self.engine.vars["players"]):
                self.engine.vars["player"] = self.engine.vars["player"] % self.engine.vars["players"] + 1

                if self.engine.vars["lives1" if self.engine.vars["player"] == 1 else "lives2"] > 0:
                    self.engine.vars["level"] = self.engine.vars["level1" if self.engine.vars["player"] == 1 else "level2"]
                    self.engine.set_state(RoundState)
                    break
            else:
                self.engine.set_state(GameOverState, {"scene" : self.scene})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class GameOverState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.scene.merge(display.Scene(["gameover"], engine.vars))

        self.sound = audio.play_sound("GameOver")
        utils.timers.start(4.0, self.engine.set_state, TitleState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class ClearState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]

        self.doh = self.scene.names.get("doh", None)
        if self.doh:
            self.sound = audio.play_sound("DohDead")
        else:
            utils.timers.start(2.0, next_level, self.engine)

    def update(self):
        for name in ["high", "score1", "score2"]:
            self.scene.names[name].update()

        if self.doh:
            self.doh.update()

            if not self.sound.get_busy():
                utils.timers.start(1.0, next_level, self.engine)
                self.doh = None

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

        self.handler = self.normal_handler

    def normal_handler(self, event):
        if event == "expand":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_grow")))
            audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
        elif event == "laser":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_to_laser").then(display.Callback(utils.events.register, utils.EVT_MOUSEBUTTONDOWN, self.fire_laser))))
            self.handler = self.laser_handler

    def expanded_handler(self, event):
        if event == "normal":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_shrink")))
            self.handler = self.normal_handler
        elif event == "laser":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_shrink").then(display.Animate("paddle_to_laser").then(display.Callback(utils.events.register, utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)))))
            self.handler = self.laser_handler

    def laser_handler(self, event):
        if event == "expand":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("laser_to_paddle").then(display.Animate("paddle_grow"))))
            audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
            utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)
        elif event == "normal":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("laser_to_paddle")))
            self.handler = self.normal_handler
            utils.events.unregister(utils.EVT_MOUSEBUTTONDOWN, self.fire_laser)

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
        half_width = self.sprite.rect.width / 2
        sharp_thresh = half_width - 3
        mid_thresh = half_width - 8

        if delta < -sharp_thresh:
            vel = [-2,-1]
        elif delta < -mid_thresh:
            vel = [-1.6,-1.6]
        elif delta < 0:
            vel = [-1,-2]
        elif delta <= mid_thresh:
            vel = [1,-2]
        elif delta <= sharp_thresh:
            vel = [1.6,-1.6]
        else:
            vel = [2,-1]

        vel = [i * self.state.ball_speed for i in vel]

        ball.set_action(display.Move(vel))
        audio.play_sound("Low")

    def kill(self):
        self.sprite.set_action(display.Animate("explode").then(display.Die()))
        self.sound = audio.play_sound("Death")

    def _break(self):
        if self.handler == self.normal_handler:
            animation = "paddle_break"
        elif self.handler == self.expanded_handler:
            animation = "paddle_ext_break"
        elif self.handler == self.laser_handler:
            animation = "laser_break"

        self.sprite.set_action(display.Animate(animation).then(display.Die()).plus(display.Move([0.5,0])))
        self.sound = audio.play_sound("Break")

    def alive(self):
        return self.sprite.alive() or (self.sound is not None and self.sound.get_busy())

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

        utils.events.register(utils.EVT_CAPSULE, self.on_brick)

    def available(self):
        return len(self.scene.groups["capsules"].sprites())

    def disable(self):
        self.count = 0

    def enable(self):
        if self.count == 0:
            self.count = random.randint(1, utils.config["max_capsule_count"])

    def block(self, names):
        for name in names:
            self.scene.names[name].kill()
            self.total -= 1

    def unblock(self, names):
        sprites = self.scene.groups["capsules"].sprites()
        for name in names:
            sprite = self.scene.names[name]
            if sprite not in sprites:
                self.scene.groups["capsules"].add(sprite)
                self.total += 1

    def apply(self, capsule):
        effect = capsule.cfg.get("effect", "")
        if effect == "break":
            self.scene.groups["all"].add(self._break)
            self.scene.groups["break"].add(self._break)
            self.block(["capsuleB"])
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
            utils.events.generate(utils.EVT_EXTRA_LIFE)
        elif effect == "slow":
            self.state.ball_speed /= utils.config["ball_speed"]

            for ball in self.state.balls:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i / utils.config["ball_speed"] for i in ball.action.delta]

            self.state.speed_timer()

        if effect == "laser":
            self.state.paddle.handler("laser")
            self.block(["capsuleL"])
            self.unblock(["capsuleE"])
        elif effect == "enlarge":
            self.state.paddle.handler("expand")
            self.block(["capsuleE"])
            self.unblock(["capsuleL"])
        else:
            self.state.paddle.handler("normal")
            self.unblock(["capsuleE", "capsuleL"])

        if effect == "catch":
            self.paddle.catch = True
            self.block(["capsuleC"])
        else:
            self.paddle.catch = False
            self.unblock(["capsuleC"])

        points = capsule.cfg.get("points", 0)
        utils.events.generate(utils.EVT_POINTS, points=points)

    def kill(self, capsule):
        capsule.set_pos([0,0])
        capsule.set_action(None)
        capsule.kill()
        self.scene.groups["capsules"].add(capsule)

        self.enable()

    def on_brick(self, event):
        if self.total == self.available() and self.count > 0:
            self.count -= 1

            if self.count == 0:
                choices = [capsule for capsule in self.scene.groups["capsules"].sprites() for _ in range(capsule.cfg["weight"])]
                capsule = random.choice(choices)
                capsule.set_pos(event.position)
                capsule.set_action(display.Move([0,1]).plus(display.Animate(capsule.cfg["animation"])))
                self.scene.groups["capsules"].remove(capsule)
                self.scene.groups["paddle"].add(capsule)
                self.scene.groups["all"].add(capsule)

def next_level(engine):
    key = "level1" if engine.vars["player"] == 1 else "level2"
    engine.vars["level"] += 1
    engine.vars[key] += 1
    if engine.vars["level"] <= engine.last_level:
        engine.set_state(RoundState)
    else:
        engine.set_state(VictoryState)

def jump_level(engine, level):
    key = "level1" if engine.vars["player"] == 1 else "level2"
    engine.vars["level"] = level
    engine.vars[key] = level
    if engine.vars["level"] <= engine.last_level:
        engine.set_state(RoundState)
    else:
        engine.set_state(VictoryState)

class GameState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["hud", "walls", "tools"], engine.vars)
        self.scene.merge(engine.scenes[engine.vars["player"]][engine.vars["level"]])

        if engine.vars["player"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()
        else:
            self.scene.names["1UP"].kill()
            self.scene.names["score1"].kill()

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
        utils.events.register(utils.EVT_EXTRA_LIFE, self.on_extra_life)

        self.speed_timer()

        doh = self.scene.names.get("doh", None)
        if doh:
            doh.set_action(display.DohMgr(self.scene, doh))

        for name in ["inlet_left", "inlet_right"]:
            inlet = self.scene.names[name]
            inlet.set_action(display.InletMgr(self.scene, inlet))

        self.scene.names["alien"].kill()

    def speed_timer(self):
        utils.timers.start(10.0, self.on_timer)

    def on_timer(self):
        if self.ball_speed < 4:
            self.ball_speed *= utils.config["ball_speed"]

            for ball in self.balls:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i * utils.config["ball_speed"] for i in ball.action.delta]

        self.speed_timer()

    def on_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.engine.set_state(StartState)
        elif event.key == pygame.K_PERIOD:
            next_level(self.engine)
        elif event.key == pygame.K_q:
            jump_level(self.engine, 36)

    def on_points(self, event):
        key = "score1" if self.engine.vars["player"] == 1 else "score2"

        # Accumulate the points
        before = self.engine.vars[key]
        after = before + event.points
        self.engine.vars[key] = after

        # Update the high score
        if after > self.engine.vars["high"]:
            self.engine.vars["high"] = after

        # Check for extra lives
        for threshold in [20000] + range(60000, after+1, 60000):
            if before < threshold and after >= threshold:
                utils.events.generate(utils.EVT_EXTRA_LIFE)

    def on_extra_life(self, event):
        self.engine.vars["lives1" if self.engine.vars["player"] == 1 else "lives2"] += 1
        audio.play_sound("Life")
        show_lives(self)

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
                self.engine.set_state(BreakState, {"scene" : self.scene, "paddle" : self.paddle})

        # Capsules
        sprites = pygame.sprite.spritecollide(self.paddle.sprite, self.scene.groups["paddle"], False)
        for sprite in sprites:

            sprite.hit(self.scene)

            if sprite.cfg.get("effect"):
                self.capsules.kill(sprite)
                self.capsules.apply(sprite)

            if sprite.cfg.get("kill_paddle", False):
                self.engine.set_state(DeathState, {"scene" : self.scene, "paddle" : self.paddle})

        for sprite in self.scene.groups["paddle"]:
            if sprite.alive() and sprite.rect.top > self.playspace.bottom:
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

                sprite.hit(self.scene)

        # Ball exit detection
        for ball in list(self.balls):
            if ball.alive() and ball.rect.top > self.playspace.bottom:
                ball.kill()
                self.balls.remove(ball)

                if len(self.balls) == 1:
                    self.capsules.enable()

        # Check for death
        if len(self.balls) == 0:
            self.engine.set_state(DeathState, {"scene" : self.scene, "paddle" : self.paddle})

        # Level completion detection
        remaining = sum([brick.cfg.get("hits", 0) for brick in self.scene.groups["bricks"].sprites()])
        if remaining == 0:
            self.engine.set_state(ClearState, {"scene" : self.scene})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

def collision_side(sprite1, sprite2):
    # Code adapted from https://hopefultoad.blogspot.com/2017/09/code-example-for-2d-aabb-collision.html

    cornerSlopeRise = 0
    cornerSlopeRun = 0

    velocityRise = sprite1.rect.top - sprite1.last.top
    velocityRun = sprite1.rect.left - sprite1.last.left

    velocityRise2 = sprite2.rect.top - sprite2.last.top
    velocityRun2 = sprite2.rect.left - sprite2.last.left

    # Adjust for sprite2's velocity
    velocityRise -= velocityRise2
    velocityRun -= velocityRun2
    sprite1_prev = sprite1.last.move(velocityRun2, velocityRise2)

    # Stores what sides might have been collided with
    potentialCollisionSide = CollisionSide_None

    if sprite1_prev.right <= sprite2.rect.left:
        # Did not collide with right side might have collided with left side
        potentialCollisionSide |= CollisionSide_Left

        cornerSlopeRun = sprite2.rect.left - sprite1_prev.right

        if sprite1_prev.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potentialCollisionSide |= CollisionSide_Top
            cornerSlopeRise = sprite2.rect.top - sprite1_prev.bottom
        elif sprite1_prev.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potentialCollisionSide |= CollisionSide_Bottom
            cornerSlopeRise = sprite2.rect.bottom - sprite1_prev.top
        else:
            # Did not collide with top side or bottom side or right side
            return CollisionSide_Left
    elif sprite1_prev.left >= sprite2.rect.right:
        # Did not collide with left side might have collided with right side
        potentialCollisionSide |= CollisionSide_Right

        cornerSlopeRun = sprite1_prev.left - sprite2.rect.right

        if sprite1_prev.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potentialCollisionSide |= CollisionSide_Top
            cornerSlopeRise = sprite1_prev.bottom - sprite2.rect.top
        elif sprite1_prev.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potentialCollisionSide |= CollisionSide_Bottom
            cornerSlopeRise = sprite1_prev.top - sprite2.rect.bottom
        else:
            # Did not collide with top side or bottom side or left side
            return CollisionSide_Right
    else:
        # Did not collide with either left or right side
        # must be top side, bottom side, or none
        if sprite1_prev.bottom <= sprite2.rect.top:
            return CollisionSide_Top
        elif sprite1_prev.top >= sprite2.rect.bottom:
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
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["victory", "banner"], engine.vars)

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

        self.sound = audio.play_sound("Victory")

        self.victory = self.scene.names["victory"]
        self.victory.set_action(display.MoveLimited([0,-2], (224-48)/2))

        display.grab_mouse()

    def update(self):
        self.victory.update()
        if not self.sound.get_busy():
            self.engine.set_state(FinalState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)

class FinalState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["final", "banner"], engine.vars)

        if engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

        self.doh = self.scene.names["doh"]

        utils.timers.start(3.0, self.animate)

    def animate(self):
        self.doh.set_action(display.Animate(self.doh.cfg["animation"]).then(display.PlaySound("High").then(display.Callback(self.done))))

    def done(self):
        utils.timers.start(3.0, self.engine.set_state, TitleState)

    def update(self):
        self.doh.update()

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

    INITIAL_STATE = SplashState

    def __init__(self):
        self.vars = Vars({
            "high":0,
            "score1":0,
            "score2":0,
            "level":1,
            "level1":1,
            "level2":1,
            "player":1,
            "lives1":3,
            "lives2":3,
            "players":1,
        })

        self.reset()

    def reset(self):
        self.vars["score1"] = 0
        self.vars["score2"] = 0
        self.vars["level"] = 1
        self.vars["level1"] = 1
        self.vars["level2"] = 1
        self.vars["player"] = 1
        self.vars["lives1"] = 3
        self.vars["lives2"] = 3

        # Pre-allocate all level scenes
        levels = {}
        for key in utils.config["scenes"]:
            mobj = re.match("level(\\d+)", key)
            if mobj:
                level = int(mobj.group(1))
                levels[level] = key

        self.last_level = max(levels.keys())

        self.scenes = {}
        for player in range(1, self.vars["players"]+1):
            self.scenes[player] = {level : display.Scene([key], self.vars) for level, key in levels.items()}

        self.set_state(self.INITIAL_STATE)

    def set_state(self, state, data={}):
        utils.events.clear()
        utils.timers.clear()
        self.state = state(self, data)

    def input(self, event):
        utils.events.handle(event)
        self.state.input(event)

    def update(self):
        utils.timers.update()
        self.state.update()

    def draw(self, screen):
        self.state.draw(screen)
