"""
Main game engine for Arkanoid
"""

import gc
import itertools
import logging
import re

import pygame

import audio
import collision
import display
import entities
import levels
import systems
import utils


class State(object):
    """Base class for game engine states"""
    # pylint: disable=unused-argument,unnecessary-pass

    def __init__(self, engine, data):
        self.engine = engine
        self.scene = None

    def stop(self):
        """Stop handler"""
        pass

    def input(self, event):
        """Process input event"""
        pass

    def update(self):
        """Update the state for the next frame"""
        pass

    def draw(self, screen):
        """Draw the state to the screen"""
        pass

    def fix_banner(self):
        """Fix the banner sprites for the number of players"""
        if self.engine.vars["players"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()

    def fix_hud(self):
        """Fix the HUD sprites for the current player"""
        if self.engine.vars["player"] == 1:
            self.scene.names["2UP"].kill()
            self.scene.names["score2"].kill()
        else:
            self.scene.names["1UP"].kill()
            self.scene.names["score1"].kill()

        self.fix_lives()

    def fix_lives(self):
        """Update the life sprites"""
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
        """Bump to next level"""
        level = self.engine.get_level() + 1
        self.jump_level(level)

    def jump_level(self, level):
        """Jump to given level"""
        exists = self.engine.set_level(level)
        if exists:
            self.engine.set_state(RoundState, {})
        else:
            self.engine.set_state(VictoryState, {})

    def next_player(self):
        """Switch to next player"""
        if self.engine.switch_player():
            self.engine.set_state(RoundState, {})
        else:
            self.engine.set_state(TitleState, {})


class SplashState(State):
    """Game splash screen"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["banner", "splash"])

        self.fix_banner()

        self.splash = self.scene.names["splash"]
        utils.timers.start(10.0, self.engine.set_state, TitleState, {})

        utils.events.register(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.Event.KEYDOWN, self.on_keydown)

    def stop(self):
        utils.events.unregister(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.unregister(utils.Event.KEYDOWN, self.on_keydown)
        utils.timers.cancel(self.engine.set_state)

    def on_click(self, event):
        """Skip to title menu when clicked"""
        if event.button == 1:
            self.engine.set_state(TitleState, {})

    def on_keydown(self, event):
        """Skip to title menu when key is pressed"""
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.engine.set_state(TitleState, {})

    def update(self):
        self.splash.update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class TitleState(State):
    """Title menu"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["title", "banner"])

        self.fix_banner()

        utils.events.register(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.Event.MOUSEMOTION, self.on_motion)
        utils.events.register(utils.Event.KEYDOWN, self.on_keydown)
        utils.events.register(utils.Event.VAR_CHANGE, self.on_var_change)

        display.release_mouse()

        # Disable garbage
        items = gc.collect()
        logging.info("Garbage collection (%d items)", items)
        gc.enable()

    def stop(self):
        utils.events.unregister(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.unregister(utils.Event.MOUSEMOTION, self.on_motion)
        utils.events.unregister(utils.Event.KEYDOWN, self.on_keydown)
        utils.events.unregister(utils.Event.VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        """Update cursor position if number of players changed"""
        if event.name == "players":
            index = event.value - 1
            cursor = self.scene.names["cursor"]
            pos = cursor.cfg["locations"][index]
            cursor.rect.topleft = pos

    def on_click(self, event):
        """Start game on mouse click"""
        if event.button == 1:
            self.engine.set_state(BlinkState, {})

    def on_motion(self, event):
        """Track mouse to select players"""
        locations = self.scene.names["cursor"].cfg["locations"]
        if event.pos[1] < locations[1][1]:
            self.engine.vars["players"] = 1
        else:
            self.engine.vars["players"] = 2

    def on_keydown(self, event):
        """Track key presses to select players or start game"""
        if event.key == pygame.K_UP:
            self.engine.vars["players"] = 1
        elif event.key == pygame.K_DOWN:
            self.engine.vars["players"] = 2
        elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.engine.set_state(BlinkState, {})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class BlinkState(State):
    """Blink after player count was chosen"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["title", "banner"])

        self.fix_banner()

        self.sound = audio.play_sound("Intro")

        # Blink the chosen option
        if engine.vars["players"] == 1:
            key = "p1"
        else:
            key = "p2"
        self.scene.names[key].set_action(entities.Blink(1.0))

        # Get rid of the cursor
        self.scene.names["cursor"].kill()

    def update(self):
        self.scene.groups["all"].update()

        if self.sound is None or not self.sound.get_busy():
            self.engine.reset()
            self.engine.set_state(RoundState, {})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class RoundState(State):
    """Show current round"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["round", "banner"])

        self.fix_banner()

        utils.timers.start(2.0, self.engine.set_state, StartState, {})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class StartState(State):
    """Start a level"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["hud", "walls", "ready"])
        self.scene.merge(
            engine.scenes[engine.vars["player"]][engine.vars["level"]])

        self.fix_hud()

        # This is to fix any stale state from previous lives.  A better solution
        # is to reload the sprite from the config each round.
        doh = self.scene.names.get("doh", None)
        if doh:
            sound = "DohStart"
            doh.set_action(entities.DohMgr(self.scene))
        else:
            sound = "Ready"
        self.sound = audio.play_sound(sound)

        utils.timers.start(3.0, self.engine.set_state, GameState, {})

        display.grab_mouse()
        gc.disable()    # Disable GC during gameplay

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class BreakState(State):
    """Perform a break to next level"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.paddle = data["paddle"]

        self.paddle.break_()

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
    """Paddle death"""

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
    """Game over!"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = data["scene"]
        self.scene.merge(entities.Scene(["gameover"]))

        self.sound = audio.play_sound("GameOver")
        utils.timers.start(4.0, self.next_player)

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class ClearState(State):
    """Level has been cleared"""

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


class GameState(State):
    """Play the game"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["hud", "walls", "tools"])
        self.scene.merge(
            engine.scenes[engine.vars["player"]][engine.vars["level"]])

        self.fix_hud()

        self.playspace = self.scene.names["bg"].rect
        self.scene.names["ball2"].kill()
        self.scene.names["ball3"].kill()

        self.ball_speed = 1.0

        self.paddle = systems.Paddle(self.scene.names["paddle"],
                                     self.playspace,
                                     self)
        self.paddle.catch_ball(self.scene.names["ball1"])

        self.capsules = systems.Capsules(self, self.paddle)

        utils.events.register(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.Event.MOUSEMOTION, self.on_motion)
        utils.events.register(utils.Event.KEYDOWN, self.on_keydown)
        utils.events.register(utils.Event.POINTS, self.on_points)
        utils.events.register(utils.Event.EXTRA_LIFE, self.on_extra_life)

        self.speed_timer()

        doh = self.scene.names.get("doh", None)
        if doh:
            doh.set_action(entities.DohMgr(self.scene))

        for name in ["inlet_left", "inlet_right"]:
            inlet = self.scene.names[name]
            inlet.set_action(entities.InletMgr(self.scene))

        self.scene.names["alien"].kill()

        self.threshold = self.next_life_threshold()

    def stop(self):
        self.capsules.stop()
        utils.events.unregister(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.unregister(utils.Event.MOUSEMOTION, self.on_motion)
        utils.events.unregister(utils.Event.KEYDOWN, self.on_keydown)
        utils.events.unregister(utils.Event.POINTS, self.on_points)
        utils.events.unregister(utils.Event.EXTRA_LIFE, self.on_extra_life)
        utils.timers.cancel(self.on_timer)

    def next_life_threshold(self):
        """Calculate next score threshold for a free life"""
        score = self.engine.get_score()
        for threshold in itertools.chain([20000], itertools.count(60000, 60000)):
            if score < threshold:
                logging.info("Next threshold:%d", threshold)
                return threshold

    def speed_timer(self):
        """Start the ball speed timer"""
        logging.info("Ball speed: %.1f", self.ball_speed)
        utils.timers.start(10.0, self.on_timer)

    def on_timer(self):
        """Increase ball speed and start the timer again"""
        new_speed = self.ball_speed * utils.config["ball_speed_multiplier"]
        if new_speed <= utils.config["max_ball_speed"]:
            self.ball_speed = new_speed

            for ball in self.scene.groups["balls"]:
                if isinstance(ball.action, entities.Move):
                    ball.action.delta = [i * utils.config["ball_speed_multiplier"]
                                         for i in ball.action.delta]

        self.speed_timer()

    def on_click(self, event):
        """Generate a fire event on a mouse click"""
        if event.button == 1:
            utils.events.generate(utils.Event.FIRE)

    def on_motion(self, event):
        """Generate a paddle move event on mouse motion"""
        delta = utils.config["mouse_speed"] * event.rel[0]
        utils.events.generate(utils.Event.PADDLEMOVE, delta=delta)

    def on_keydown(self, event):
        """Generate a fire event on key presses"""
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            utils.events.generate(utils.Event.FIRE)

    def on_points(self, event):
        """Respond to points events"""
        score = self.engine.get_score() + event.points
        self.engine.set_score(score)

        # Check for extra lives
        if score >= self.threshold:
            utils.events.generate(utils.Event.EXTRA_LIFE)
            self.threshold = self.next_life_threshold()

    def on_extra_life(self, _event):
        """Respond to extra life events"""
        lives = self.engine.get_lives() + 1
        self.engine.set_lives(lives)
        audio.play_sound("Life")
        self.fix_lives()

    def keyboard_input(self):
        """Scan for key state and fire move events if needed"""
        keys = pygame.key.get_pressed()

        # Calculate the direction the paddle should move
        direction = 0
        if keys[pygame.K_LEFT]:
            direction -= 1
        if keys[pygame.K_RIGHT]:
            direction += 1

        # Send the motion event
        delta = utils.config["kb_speed"] * direction
        utils.events.generate(utils.Event.PADDLEMOVE, delta=delta)

    def update(self):
        self.keyboard_input()

        self.scene.groups["all"].update()

        # Paddle collisions
        for group in [self.scene.groups["balls"], self.scene.groups["paddle"]]:
            hitters = pygame.sprite.spritecollide(self.paddle.sprite,
                                                  group,
                                                  False)
            for sprite in hitters:
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
        projectiles = self.scene.groups["balls"].sprites()
        projectiles += self.scene.groups["lasers"].sprites()
        for projectile in projectiles:
            # Hit the closest object and slide along the collsion edge.  Repeat a few more times
            # in case the slide hits other objects
            for attempt in range(3):
                hitters = pygame.sprite.spritecollide(projectile,
                                                      self.scene.groups["ball"],
                                                      False)

                if hitters:
                    closest = collision.find_closest(projectile, hitters)

                    logging.info("collision %d", attempt)
                    logging.info("proj %s", projectile.rect)
                    for sprite in hitters:
                        logging.info("targ %s", sprite.rect)

                    projectile.hit(self.scene)
                    closest.hit(self.scene)

                    # Bounce the balls
                    if projectile.alive() and isinstance(projectile.action, entities.Move):
                        side = collision.collision_side(projectile, closest)
                        delta = projectile.action.delta
                        if side == collision.Side.BOTTOM:
                            delta[1] = abs(delta[1])
                            projectile.rect.top = closest.rect.bottom
                        elif side == collision.Side.TOP:
                            delta[1] = -abs(delta[1])
                            projectile.rect.bottom = closest.rect.top
                        elif side == collision.Side.RIGHT:
                            delta[0] = abs(delta[0])
                            projectile.rect.left = closest.rect.right
                        elif side == collision.Side.LEFT:
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
        balls = self.scene.groups["balls"].sprites()
        if len(balls) == 1:
            self.capsules.enable()

        # Check for death
        if not balls:
            self.engine.set_state(DeathState,
                                  {"scene": self.scene, "paddle": self.paddle})

        # Level completion detection
        remaining = sum([brick.cfg.get("hits", 0)
                         for brick in self.scene.groups["bricks"].sprites()])
        if remaining == 0:
            self.paddle.stop()
            self.engine.set_state(ClearState, {"scene": self.scene})

        # Break support
        for sprite in self.scene.groups["break"]:
            if self.paddle.sprite.rect.right >= sprite.rect.left:
                utils.events.generate(utils.Event.POINTS, points=10000)
                self.engine.set_state(BreakState,
                                      {"scene": self.scene, "paddle": self.paddle})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class VictoryState(State):
    """Won the game"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["victory", "banner"])

        self.fix_banner()

        self.sound = audio.play_sound("Victory")

        self.victory = self.scene.names["victory"]

        display.grab_mouse()

        utils.events.register(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.register(utils.Event.KEYDOWN, self.on_keydown)

    def stop(self):
        utils.events.unregister(utils.Event.MOUSEBUTTONDOWN, self.on_click)
        utils.events.unregister(utils.Event.KEYDOWN, self.on_keydown)

    def on_click(self, event):
        """Abort victory song on click"""
        if event.button == 1:
            self.sound.stop()

    def on_keydown(self, event):
        """Abort victory song on key press"""
        if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
            self.sound.stop()

    def update(self):
        self.victory.update()
        if not self.sound.get_busy():
            self.engine.set_state(FinalState, {})

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class FinalState(State):
    """Final screen after victory"""

    def __init__(self, engine, data):
        State.__init__(self, engine, data)

        self.scene = entities.Scene(["final", "banner"])

        self.fix_banner()

        self.doh = self.scene.names["doh"]

        utils.timers.start(3.0, self.animate)

    def animate(self):
        """Animate little Doh"""
        self.doh.set_action(
            entities.Animate("final_doh").then(
                entities.PlaySound("High").then(
                    entities.Callback(utils.timers.start, 3.0, self.done))))

    def done(self):
        """Switch to next player"""
        self.engine.set_lives(0)
        self.next_player()

    def update(self):
        self.doh.update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class Vars:
    """Track game variables"""

    def __init__(self, initial):
        self.data = initial
        utils.events.register(utils.Event.VAR_REQUEST, self.on_request)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        utils.events.generate(utils.Event.VAR_CHANGE, name=key, value=value)

    def on_request(self, event):
        """Respond to variable request."""
        utils.events.generate(utils.Event.VAR_CHANGE,
                              name=event.name, value=self.data[event.name])


class Engine(object):
    """Game engine"""

    INITIAL_STATE = SplashState

    def __init__(self):
        self.state = None
        self.vars = Vars({
            "high": 0,
            "players": 1,
        })

        # Load the level scene configurations into the global config structure
        self.level_data = levels.create_scene_configs(utils.config["levels"])
        self.level_data.update(utils.config["levels_custom"])
        utils.config["scenes"].update(self.level_data)

        self.reset()

        self.set_state(self.INITIAL_STATE, {})

    def reset(self):
        """Reset the engine"""
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
            self.scenes[player] = {levels.parse_num(key): entities.Scene([key])
                                   for key in self.level_data}

    def set_lives(self, lives):
        """Set the lives for the current player"""
        player = self.vars["player"]
        key = "lives1" if player == 1 else "lives2"
        self.vars[key] = lives

        logging.info("P%d Lives %d", player, lives)

    def get_lives(self):
        """Get the lives for the current player"""
        key = "lives1" if self.vars["player"] == 1 else "lives2"
        return self.vars[key]

    def set_score(self, score):
        """Set the score for the current player"""
        player = self.vars["player"]
        key = "score1" if player == 1 else "score2"
        self.vars[key] = score

        if score > self.vars["high"]:
            self.vars["high"] = score
            logging.info("P%d Score %d (h)", player, score)
        else:
            logging.info("P%d Score %d", player, score)

    def get_score(self):
        """Get the score for the current player"""
        key = "score1" if self.vars["player"] == 1 else "score2"
        return self.vars[key]

    def set_level(self, level):
        """Set the level for the current player"""
        player = self.vars["player"]
        key = "level1" if player == 1 else "level2"
        self.vars[key] = level
        self.vars["level"] = level
        logging.info("P%d Level %d", player, level)
        return level in self.scenes[player]

    def get_level(self):
        """Get the level for the current player"""
        key = "level1" if self.vars["player"] == 1 else "level2"
        return self.vars[key]

    def switch_player(self):
        """Switch to the next player (may be same player)"""
        for _ in range(self.vars["players"]):
            self.vars["player"] = self.vars["player"] % self.vars["players"] + 1

            if self.get_lives() > 0:
                self.set_level(self.get_level())
                return True

        return False

    def set_state(self, state, data):
        """Set engine state"""
        logging.info("State: %s", state.__name__)
        if self.state:
            self.state.stop()
        self.state = state(self, data)

    def input(self, event):
        """Process input event"""
        utils.events.handle(event)
        self.state.input(event)

    def update(self):
        """Update engine for the next frame"""
        utils.timers.update()
        self.state.update()

    def draw(self, screen):
        """Render engine to screen"""
        self.state.draw(screen)


EngineClass = Engine


def main_loop():
    """Arkanoid main loop"""

    utils.init()                    # Lazy initialization to give time to set up logging

    pygame.init()

    window = display.Window()

    eng = EngineClass()

    clock = pygame.time.Clock()
    frame_timer = utils.Delta()
    utilization_timer = utils.Delta()

    while True:
        utilization_timer.get()

        # Event pump
        for event in pygame.event.get():
            logging.debug("Event: %s", pygame.event.event_name(event.type))

            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

            eng.input(event)

        # Integration
        eng.update()

        # Render
        window.clear()
        eng.draw(window.screen)

        fps = int(clock.get_fps())
        window.screen.blit(display.draw_text(str(fps), "white"), (0, 0))

        utime = utilization_timer.get()

        # Frame sync
        clock.tick(utils.config["frame_rate"])
        window.flip()

        # FPS logging
        ftime = frame_timer.get()
        utilization = utime / ftime * 100
        if ftime > 2.0 / utils.config["frame_rate"] or utilization > 50:
            logfunc = logging.warning
        else:
            logfunc = logging.debug
        logfunc("%d FPS %.3fs (%d%%)", fps, ftime, utilization)
