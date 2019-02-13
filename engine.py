"""
Main game engine for Arkanoid
"""

import itertools
import logging
import random
import re

import pygame

import audio
import display
import levels
import utils

CollisionSide_None = 0
CollisionSide_Top = 1
CollisionSide_Bottom = 2
CollisionSide_Left = 4
CollisionSide_Right = 8

CollisionSide_Text = {
    CollisionSide_None: "None",
    CollisionSide_Top: "Top",
    CollisionSide_Bottom: "Bottom",
    CollisionSide_Left: "Left",
    CollisionSide_Right: "Right",
}


class State(object):
    def __init__(self, engine, data):
        self.engine = engine
        self.scene = None

    def input(self, event):
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass

    def fix_banner(self):
        if self.engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

    def fix_hud(self):
        if self.engine.vars["player"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()
        else:
            self.scene.names["1UP"].kill()
            self.scene.names["score1"].kill()

        self.fix_lives()

    def fix_lives(self):
        lives = self.engine.get_lives()
        for name, sprite in self.scene.names.items():
            mobj = re.match("life(\\d+)", name)
            if mobj:
                num = int(mobj.group(1))
                if lives <= num:
                    sprite.kill()
                else:
                    self.scene.groups["all"].add(sprite)

    def next_level(self):
        level = self.engine.get_level() + 1
        self.jump_level(level)

    def jump_level(self, level):
        exists = self.engine.set_level(level)
        if exists:
            self.engine.set_state(RoundState)
        else:
            self.engine.set_state(VictoryState)

    def next_player(self):
        if self.engine.switch_player():
            self.engine.set_state(RoundState)
        else:
            self.engine.set_state(TitleState)


class SplashState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["banner", "splash"], engine.vars)

        self.fix_banner()

        self.splash = self.scene.names["splash"]
        self.splash.set_action(display.MoveLimited([0, -2], (224-48)/2))
        utils.timers.start(10.0, self.engine.set_state, TitleState)

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_click(self, event):
        if event.button == 1:
            self.engine.set_state(TitleState)

    def on_keydown(self, event):
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.engine.set_state(TitleState)

    def update(self):
        self.splash.update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class TitleState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["title", "banner"], engine.vars)

        self.fix_banner()

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_MOUSEMOTION, self.on_motion)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

        display.release_mouse()

    def on_var_change(self, event):
        # Update cursor position
        if event.name == "players":
            index = event.value - 1
            cursor = self.scene.names["cursor"]
            pos = cursor.cfg["locations"][index]
            cursor.rect.topleft = pos

    def on_click(self, event):
        if event.button == 1:
            self.engine.set_state(BlinkState)

    def on_motion(self, event):
        locations = self.scene.names["cursor"].cfg["locations"]
        if event.pos[1] < locations[1][1]:
            self.engine.vars["players"] = 1
        else:
            self.engine.vars["players"] = 2

    def on_keydown(self, event):
        if event.key == pygame.K_UP:
            self.engine.vars["players"] = 1
        elif event.key == pygame.K_DOWN:
            self.engine.vars["players"] = 2
        elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.engine.set_state(BlinkState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class BlinkState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["title", "banner"], engine.vars)

        self.fix_banner()

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

        if self.sound is None or not self.sound.get_busy():
            self.engine.reset()
            self.engine.set_state(RoundState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class RoundState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["round", "banner"], engine.vars)

        self.fix_banner()

        utils.timers.start(2.0, self.engine.set_state, StartState)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class StartState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["hud", "walls", "ready"], engine.vars)
        self.scene.merge(
            engine.scenes[engine.vars["player"]][engine.vars["level"]])

        self.fix_hud()

        # This is to fix any stale state from previous lives.  A better solution
        # is to reload the sprite from the config each round.
        doh = self.scene.names.get("doh", None)
        if doh:
            sound = "DohStart"
            doh.set_action(display.DohMgr(self.scene))
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

        for ball in self.scene.groups["balls"]:
            ball.kill()

    def update(self):
        for name in ["high", "score1", "score2", "break", "paddle"]:
            self.scene.names[name].update()

        if not self.paddle.alive():
            self.next_level()

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
            lives = self.engine.get_lives() - 1
            self.engine.set_lives(lives)
            if lives == 0:
                self.engine.set_state(GameOverState, {"scene": self.scene})
            else:
                self.next_player()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class GameOverState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.scene.merge(display.Scene(["gameover"], engine.vars))

        self.sound = audio.play_sound("GameOver")
        utils.timers.start(4.0, self.next_player)

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
            utils.timers.start(2.0, self.next_level)

    def update(self):
        for name in ["high", "score1", "score2"]:
            self.scene.names[name].update()

        if self.doh:
            self.doh.update()

            if not self.sound.get_busy():
                utils.timers.start(1.0, self.next_level)
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

        self.sprite.set_action(display.PaddleMove(playspace))

        self.state.scene.names["laser"].kill()

        self.handler = self.normal_handler

    def normal_handler(self, event):
        if event == "expand":
            self.sprite.set_action(self.sprite.action.plus(
                display.Animate("paddle_grow")))
            audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
        elif event == "laser":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_to_laser").then(
                display.Callback(utils.events.register, utils.EVT_FIRE, self.fire_laser))))
            self.handler = self.laser_handler

    def expanded_handler(self, event):
        if event == "normal":
            self.sprite.set_action(self.sprite.action.plus(
                display.Animate("paddle_shrink")))
            self.handler = self.normal_handler
        elif event == "laser":
            self.sprite.set_action(self.sprite.action.plus(display.Animate("paddle_shrink").then(display.Animate(
                "paddle_to_laser").then(display.Callback(utils.events.register, utils.EVT_FIRE, self.fire_laser)))))
            self.handler = self.laser_handler

    def laser_handler(self, event):
        if event == "expand":
            self.sprite.set_action(self.sprite.action.plus(display.Animate(
                "laser_to_paddle").then(display.Animate("paddle_grow"))))
            audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
            utils.events.unregister(utils.EVT_FIRE, self.fire_laser)
        elif event == "normal":
            self.sprite.set_action(self.sprite.action.plus(
                display.Animate("laser_to_paddle")))
            self.handler = self.normal_handler
            utils.events.unregister(utils.EVT_FIRE, self.fire_laser)

    def fire_laser(self, event):
        sprite = self.state.scene.names["laser"].clone()

        sprite.rect.center = self.sprite.rect.center
        sprite.rect.bottom = self.sprite.rect.top

        sprite.set_action(display.Move([0, -4]))
        self.state.scene.groups["all"].add(sprite)
        self.state.scene.groups["lasers"].add(sprite)

        audio.play_sound("Laser")

    def enable_catch(self):
        self.catch = True

    def disable_catch(self):
        self.catch = False
        self.release_ball(self)

    def catch_ball(self, ball):
        if self.stuck_ball is None:
            self.stuck_ball = ball
            self.stuck_ball.set_action(display.Follow(self.sprite))
            utils.events.register(utils.EVT_FIRE, self.release_ball)
            utils.timers.start(3.0, self.release_ball)

    def release_ball(self, event=None):
        if self.stuck_ball is not None:
            utils.events.unregister(utils.EVT_FIRE, self.release_ball)
            utils.timers.cancel(self.release_ball)
            self.hit_ball(self.stuck_ball)
            self.stuck_ball = None

    def hit(self, ball):
        # Move ball out of contact based on its velocity vector
        collision_move_to_edge(ball, self.sprite)

        if self.catch:
            self.catch_ball(ball)
        elif self.stuck_ball:
            self.release_ball()
        else:
            self.hit_ball(ball)

    def hit_ball(self, ball):
        delta = [ball.rect.centerx - self.sprite.rect.centerx,
                 ball.rect.centery - self.sprite.rect.centery]
        half_width = self.sprite.rect.width / 2
        sharp_thresh = half_width - 3
        mid_thresh = half_width - 8

        if delta[0] < -sharp_thresh:
            if delta[1] > 0:
                vel = [-2, 1]
            else:
                vel = [-2, -1]
        elif delta[0] < -mid_thresh:
            vel = [-1.6, -1.6]
        elif delta[0] < 0:
            vel = [-1, -2]
        elif delta[0] <= mid_thresh:
            vel = [1, -2]
        elif delta[0] <= sharp_thresh:
            vel = [1.6, -1.6]
        else:
            if delta[1] > 0:
                vel = [2, 1]
            else:
                vel = [2, -1]

        vel = [i * self.state.ball_speed for i in vel]

        ball.set_action(display.Move(vel))
        audio.play_sound("Low")

        logging.info("hit_ball d=%s vel=%s", delta, vel)

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

        self.sprite.set_action(display.Animate(animation).then(
            display.Die()).plus(display.Move([0.5, 0])))
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
        logging.info("Capsule disabled")

    def enable(self):
        if self.count == 0:
            self.count = random.randint(1, utils.config["max_capsule_count"])
            logging.info("Capsule in %d", self.count)

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

        logging.info("Apply %s", effect)

        if effect == "catch":
            self.paddle.enable_catch()
            self.block(["capsuleC"])
        else:
            self.paddle.disable_catch()
            self.unblock(["capsuleC"])

        if effect == "break":
            self.scene.groups["all"].add(self._break)
            self.scene.groups["break"].add(self._break)
            self.block(["capsuleB"])
        elif effect == "disrupt":
            ball0 = self.scene.groups["balls"].sprites()[0]
            pos = ball0.rect.topleft
            vel = ball0.action.delta

            signs = [1 if vel[i] > 0 else -1 for i in range(2)]
            vels = [[1, 2], [1.6, 1.6], [2, 1]]
            vels = [[x * signs[0] * self.state.ball_speed,
                     y * signs[1] * self.state.ball_speed]
                    for x, y in vels]

            for name, vel in zip(["ball1", "ball2", "ball3"], vels):
                ball = self.scene.names[name]
                ball.rect.topleft = pos
                ball.set_action(display.Move(vel))
                ball.kill()
                self.scene.groups["balls"].add(ball)
                self.scene.groups["all"].add(ball)

            self.disable()

            logging.info("Vels: %s", vels)
        elif effect == "player":
            utils.events.generate(utils.EVT_EXTRA_LIFE)
        elif effect == "slow":
            self.state.ball_speed /= utils.config["ball_speed_multiplier"]

            for ball in self.scene.groups["balls"]:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i / utils.config["ball_speed_multiplier"]
                                         for i in ball.action.delta]

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

        points = capsule.cfg.get("points", 0)
        utils.events.generate(utils.EVT_POINTS, points=points)

    def kill(self, capsule):
        logging.info("Kill %s", capsule.cfg["effect"])
        capsule.rect.topleft = [0, 0]
        capsule.set_action(None)
        capsule.kill()
        self.scene.groups["capsules"].add(capsule)

        self.enable()

    def spawn(self, capsule, position):
        logging.info("Spawn %s", capsule.cfg["effect"])
        capsule.rect.topleft = position
        capsule.set_action(display.Move([0, 1]).plus(
            display.Animate(capsule.cfg["animation"])))
        self.scene.groups["capsules"].remove(capsule)
        self.scene.groups["paddle"].add(capsule)
        self.scene.groups["all"].add(capsule)

    def on_brick(self, event):
        if self.total == self.available() and self.count > 0:
            self.count -= 1

            if self.count == 0:
                choices = [capsule for capsule in self.scene.groups["capsules"]
                           for _ in range(capsule.cfg["weight"])]
                capsule = random.choice(choices)
                self.spawn(capsule, event.position)


class GameState(State):
    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = display.Scene(["hud", "walls", "tools"], engine.vars)
        self.scene.merge(
            engine.scenes[engine.vars["player"]][engine.vars["level"]])

        self.fix_hud()

        self.playspace = self.scene.names["bg"].rect
        self.scene.names["ball2"].kill()
        self.scene.names["ball3"].kill()

        self.ball_speed = 1.0

        self.paddle = Paddle(self.scene.names["paddle"], self.playspace, self)
        self.paddle.catch_ball(self.scene.names["ball1"])

        self.capsules = Capsules(self, self.paddle)

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_MOUSEMOTION, self.on_motion)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)
        utils.events.register(utils.EVT_POINTS, self.on_points)
        utils.events.register(utils.EVT_EXTRA_LIFE, self.on_extra_life)

        self.speed_timer()

        doh = self.scene.names.get("doh", None)
        if doh:
            doh.set_action(display.DohMgr(self.scene))

        for name in ["inlet_left", "inlet_right"]:
            inlet = self.scene.names[name]
            inlet.set_action(display.InletMgr(self.scene))

        self.scene.names["alien"].kill()

        self.threshold = self.next_life_threshold()

    def next_life_threshold(self):
        score = self.engine.get_score()
        for threshold in itertools.chain([20000], itertools.count(60000, 60000)):
            if score < threshold:
                logging.info("Next threshold:%d", threshold)
                return threshold

    def speed_timer(self):
        logging.info("Ball speed: %.1f", self.ball_speed)
        utils.timers.start(10.0, self.on_timer)

    def on_timer(self):
        new_speed = self.ball_speed * utils.config["ball_speed_multiplier"]
        if new_speed <= utils.config["max_ball_speed"]:
            self.ball_speed = new_speed

            for ball in self.scene.groups["balls"]:
                if isinstance(ball.action, display.Move):
                    ball.action.delta = [i * utils.config["ball_speed_multiplier"]
                                         for i in ball.action.delta]

        self.speed_timer()

    def on_click(self, event):
        if event.button == 1:
            utils.events.generate(utils.EVT_FIRE)

    def on_motion(self, event):
        delta = utils.config["mouse_speed"] * event.rel[0]
        utils.events.generate(utils.EVT_PADDLEMOVE, delta=delta)

    def on_keydown(self, event):
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            utils.events.generate(utils.EVT_FIRE)

    def on_points(self, event):
        # Accumulate the points
        score = self.engine.get_score() + event.points
        self.engine.set_score(score)

        # Check for extra lives
        if score >= self.threshold:
            utils.events.generate(utils.EVT_EXTRA_LIFE)
            self.threshold = self.next_life_threshold()

    def on_extra_life(self, event):
        lives = self.engine.get_lives() + 1
        self.engine.set_lives(lives)
        audio.play_sound("Life")
        self.fix_lives()

    def keyboard_input(self):
        # Scan the keyboard state
        keys = pygame.key.get_pressed()

        # Calculate the direction the paddle should move
        direction = 0
        if keys[pygame.K_LEFT]:
            direction -= 1
        if keys[pygame.K_RIGHT]:
            direction += 1

        # Send the motion event
        delta = utils.config["kb_speed"] * direction
        utils.events.generate(utils.EVT_PADDLEMOVE, delta=delta)

    def update(self):
        self.keyboard_input()

        self.scene.groups["all"].update()

        # Paddle collisions
        for group in [self.scene.groups["balls"], self.scene.groups["paddle"]]:
            sprites = pygame.sprite.spritecollide(self.paddle.sprite,
                                                  group,
                                                  False)
            for sprite in sprites:
                sprite.hit(self.scene)

                if sprite.cfg.get("effect"):
                    self.capsules.kill(sprite)
                    self.capsules.apply(sprite)

                if sprite.cfg.get("kill_paddle", False):
                    # Drain all the lives and die!
                    self.engine.set_lives(1)
                    self.engine.set_state(DeathState,
                                          {"scene": self.scene, "paddle": self.paddle})

                if sprite.cfg.get("paddle_bounce", False):
                    self.paddle.hit(sprite)

        # Projectile collisions
        for projectile in self.scene.groups["balls"].sprites() + self.scene.groups["lasers"].sprites():
            # Hit the closest object and slide along the collsion edge.  Repeat a few more times
            # in case the slide hits other objects
            for attempt in range(3):
                sprites = pygame.sprite.spritecollide(projectile,
                                                      self.scene.groups["ball"],
                                                      False)

                if len(sprites) > 0:
                    closest = find_closest(projectile, sprites)

                    logging.info("collision %d", attempt)
                    logging.info("proj %s", projectile.rect)
                    for sprite in sprites:
                        logging.info("targ %s", sprite.rect)

                    projectile.hit(self.scene)
                    closest.hit(self.scene)

                    # Bounce the balls
                    if projectile.alive() and isinstance(projectile.action, display.Move):
                        side = collision_side(projectile, closest)
                        delta = projectile.action.delta
                        if side == CollisionSide_Bottom:
                            delta[1] = abs(delta[1])
                            projectile.rect.top = closest.rect.bottom
                        elif side == CollisionSide_Top:
                            delta[1] = -abs(delta[1])
                            projectile.rect.bottom = closest.rect.top
                        elif side == CollisionSide_Right:
                            delta[0] = abs(delta[0])
                            projectile.rect.left = closest.rect.right
                        elif side == CollisionSide_Left:
                            delta[0] = -abs(delta[0])
                            projectile.rect.right = closest.rect.left
                else:
                    break

        # Destroy anything that wanders off the playspace
        for group in [self.scene.groups["paddle"], self.scene.groups["balls"]]:
            for sprite in group:
                if sprite.alive() and sprite.rect.top >= self.playspace.bottom:
                    if sprite.cfg.get("effect"):
                        self.capsules.kill(sprite)
                    else:
                        sprite.kill()

        # Re-enable capsules when ball count drops to 1
        if len(self.scene.groups["balls"].sprites()) == 1:
            self.capsules.enable()

        # Check for death
        if len(self.scene.groups["balls"].sprites()) == 0:
            self.engine.set_state(DeathState,
                                  {"scene": self.scene, "paddle": self.paddle})

        # Level completion detection
        remaining = sum([brick.cfg.get("hits", 0)
                         for brick in self.scene.groups["bricks"].sprites()])
        if remaining == 0:
            self.engine.set_state(ClearState, {"scene": self.scene})

        # Break support
        for sprite in self.scene.groups["break"]:
            if self.paddle.sprite.rect.right >= sprite.rect.left:
                utils.events.generate(utils.EVT_POINTS, points=10000)
                self.engine.set_state(BreakState,
                                      {"scene": self.scene, "paddle": self.paddle})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


def find_closest(projectile, sprites):
    # Sort by distance from projectile
    def keyfunc(sprite): return rect_distance(projectile.last.center,
                                              sprite.last)
    closest = min(sprites, key=keyfunc)
    return closest


def rect_distance(point, rect):
    dx = 0
    if point[0] < rect.left:
        dx = rect.left - point[0]
    elif rect.right - 1 < point[0]:
        dx = point[0] - (rect.right - 1)

    dy = 0
    if point[1] < rect.top:
        dy = rect.top - point[1]
    elif rect.bottom - 1 < point[1]:
        dy = point[1] - (rect.bottom - 1)

    return dx**2 + dy**2


def collision_move_to_edge(sprite1, sprite2):
    "sprite1 is projectile, sprite2 is the other.  Move sprite1 to be out of contact based on velocity"

    # Velocity1 alone keeps the ball path cleaner, but can be wonky when the paddle is moving fast
    # Relative velocity improves the overall response, but jerks the ball path around under fast motion
    v1_x = sprite1.rect.centerx - sprite1.last.centerx
    v1_y = sprite1.rect.centery - sprite1.last.centery

    v2_x = sprite2.rect.centerx - sprite2.last.centerx
    v2_y = sprite2.rect.centery - sprite2.last.centery

    v_x = v1_x - v2_x
    v_y = v1_y - v2_y

    # Find the overlapping distances
    if v_x >= 0:
        overlap_x = sprite1.rect.right - sprite2.rect.left
    else:
        overlap_x = sprite1.rect.left - sprite2.rect.right

    if v_y >= 0:
        overlap_y = sprite1.rect.bottom - sprite2.rect.top
    else:
        overlap_y = sprite1.rect.top - sprite2.rect.bottom

    # Hack to account for 0 - just assume they're very small
    if v_x == 0:
        v_x = 0.00001

    if v_y == 0:
        v_y = 0.00001

    # Calculate the time to each edge, and rewind position by the minimum of the two
    time_x = overlap_x / float(v_x)
    time_y = overlap_y / float(v_y)
    if time_x < time_y:
        dx = -v_x * time_x
        dy = -v_y * time_x
    else:
        dx = -v_x * time_y
        dy = -v_y * time_y

    logging.info("Move: (%d, %d)", dx, dy)

    sprite1.rect.move_ip(int(dx), int(dy))


def collision_side(sprite1, sprite2):
    result = collision_side_worker(sprite1, sprite2)
    logging.info("collision curr %s %s", sprite1.rect, sprite2.rect)
    logging.info("collision prev %s %s", sprite1.last, sprite2.last)
    logging.info("collision side %s", CollisionSide_Text[result])
    return result


def collision_side_worker(sprite1, sprite2):
    # Code adapted from https://hopefultoad.blogspot.com/2017/09/code-example-for-2d-aabb-collision.html

    cornerSlopeRise = 0
    cornerSlopeRun = 0

    velocityRise = sprite1.rect.centery - sprite1.last.centery
    velocityRun = sprite1.rect.centerx - sprite1.last.centerx

    velocityRise2 = sprite2.rect.centery - sprite2.last.centery
    velocityRun2 = sprite2.rect.centerx - sprite2.last.centerx

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
                                               velocityRise,
                                               velocityRun,
                                               cornerSlopeRise,
                                               cornerSlopeRun)


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

        self.fix_banner()

        self.sound = audio.play_sound("Victory")

        self.victory = self.scene.names["victory"]
        self.victory.set_action(display.MoveLimited([0, -2], (224-48)/2))

        display.grab_mouse()

        utils.events.register(utils.EVT_MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_click(self, event):
        if event.button == 1:
            self.sound.stop()

    def on_keydown(self, event):
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.sound.stop()

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

        self.fix_banner()

        self.doh = self.scene.names["doh"]

        utils.timers.start(3.0, self.animate)

    def animate(self):
        self.doh.set_action(
            display.Animate(self.doh.cfg["animation"]).then(
                display.PlaySound("High").then(
                    display.Callback(utils.timers.start, 3.0, self.done))))

    def done(self):
        self.engine.set_lives(0)
        self.next_player()

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
            "high": 0,
            "players": 1,
        })

        # Load the level scene configurations into the global config structure
        self.level_data = levels.create_scene_configs(utils.config["levels"])
        self.level_data.update(utils.config["levels_custom"])
        utils.config["scenes"].update(self.level_data)

        self.reset()

        self.set_state(self.INITIAL_STATE)

    def reset(self):
        logging.warning("Engine Reset")

        self.vars["score1"] = 0
        self.vars["score2"] = 0
        self.vars["level"] = 1
        self.vars["level1"] = 1
        self.vars["level2"] = 1
        self.vars["player"] = 1
        self.vars["lives1"] = 3
        self.vars["lives2"] = 3

        # Create independent scenes for all levels for each player to track progress
        self.scenes = {}
        for player in range(1, self.vars["players"]+1):
            self.scenes[player] = {levels.parse_num(key): display.Scene([key], self.vars)
                                   for key in self.level_data}

    def set_lives(self, lives):
        player = self.vars["player"]
        key = "lives1" if player == 1 else "lives2"
        self.vars[key] = lives

        logging.info("P%d Lives %d", player, lives)

    def get_lives(self):
        key = "lives1" if self.vars["player"] == 1 else "lives2"
        return self.vars[key]

    def set_score(self, score):
        player = self.vars["player"]
        key = "score1" if player == 1 else "score2"
        self.vars[key] = score

        if score > self.vars["high"]:
            self.vars["high"] = score
            logging.info("P%d Score %d (h)", player, score)
        else:
            logging.info("P%d Score %d", player, score)

    def get_score(self):
        key = "score1" if self.vars["player"] == 1 else "score2"
        return self.vars[key]

    def set_level(self, level):
        player = self.vars["player"]
        key = "level1" if player == 1 else "level2"
        self.vars[key] = level
        self.vars["level"] = level
        logging.info("P%d Level %d", player, level)
        return level in self.scenes[player]

    def get_level(self):
        key = "level1" if self.vars["player"] == 1 else "level2"
        return self.vars[key]

    def switch_player(self):
        for _ in range(self.vars["players"]):
            self.vars["player"] = self.vars["player"] % self.vars["players"] + 1

            if self.get_lives() > 0:
                self.set_level(self.get_level())
                return True

        return False

    def set_state(self, state, data={}):
        logging.info("State: %s", state.__name__)
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
