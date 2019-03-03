"""
Critical game systems
"""
import logging

import audio
import collision
import entities
import utils


class Paddle:
    """Manage paddle behavior"""

    def __init__(self, sprite, playspace, state):
        self.state = state
        self.sprite = sprite
        self.stuck_ball = None
        self.sound = None
        self.catch = False

        self.sprite.set_action(entities.PaddleMove(playspace))

        self.state.scene.names["laser"].kill()

        self.handler = self.normal_handler

    def stop(self):
        """Deregister the paddle"""
        if self.sound and self.sound.get_busy():
            self.sound.stop()
        utils.events.unregister(utils.Event.FIRE, self.fire_laser)
        utils.events.unregister(utils.Event.FIRE, self.release_ball)
        utils.timers.cancel(self.release_ball)

    def normal_handler(self, event):
        """Event handler for normal paddle"""
        if event == "expand":
            action = self.sprite.action.plus(entities.Animate("paddle_grow"))
            self.sprite.set_action(action)
            self.sound = audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
        elif event == "laser":
            action = self.sprite.action.plus(
                entities.Animate("paddle_to_laser").then(
                    entities.Callback(utils.events.register, utils.Event.FIRE, self.fire_laser)))
            self.sprite.set_action(action)
            self.handler = self.laser_handler

    def expanded_handler(self, event):
        """Event handler for extended paddle"""
        if event == "normal":
            action = self.sprite.action.plus(entities.Animate("paddle_shrink"))
            self.sprite.set_action(action)
            self.handler = self.normal_handler
        elif event == "laser":
            action = self.sprite.action.plus(
                entities.Animate("paddle_shrink").then(
                    entities.Animate("paddle_to_laser").then(
                        entities.Callback(utils.events.register,
                                          utils.Event.FIRE,
                                          self.fire_laser))))
            self.sprite.set_action(action)
            self.handler = self.laser_handler

    def laser_handler(self, event):
        """Event handler for laser paddle"""
        if event == "expand":
            action = self.sprite.action.plus(
                entities.Animate("laser_to_paddle").then(
                    entities.Animate("paddle_grow")))
            self.sprite.set_action(action)
            self.sound = audio.play_sound("Enlarge")
            self.handler = self.expanded_handler
            utils.events.unregister(utils.Event.FIRE, self.fire_laser)
        elif event == "normal":
            action = self.sprite.action.plus(
                entities.Animate("laser_to_paddle"))
            self.sprite.set_action(action)
            self.handler = self.normal_handler
            utils.events.unregister(utils.Event.FIRE, self.fire_laser)

    def fire_laser(self, _event):
        """Fire laser"""
        sprite = self.state.scene.names["laser"].clone()

        sprite.rect.center = self.sprite.rect.center
        sprite.rect.bottom = self.sprite.rect.top

        self.state.scene.groups["all"].add(sprite)
        self.state.scene.groups["lasers"].add(sprite)

        self.sound = audio.play_sound("Laser")

    def enable_catch(self):
        """Enable catch mode"""
        self.catch = True

    def disable_catch(self):
        """Disable catch mode"""
        self.catch = False
        self.release_ball(self)

    def catch_ball(self, ball):
        """Catch the given ball"""
        if self.stuck_ball is None:
            self.stuck_ball = ball
            self.stuck_ball.set_action(entities.Follow(self.sprite))
            utils.events.register(utils.Event.FIRE, self.release_ball)
            utils.timers.start(3.0, self.release_ball)

    def release_ball(self, _event=None):
        """Release the caught ball"""
        if self.stuck_ball is not None:
            utils.events.unregister(utils.Event.FIRE, self.release_ball)
            utils.timers.cancel(self.release_ball)
            self.hit_ball(self.stuck_ball)
            self.stuck_ball = None

    def hit(self, ball):
        """Respond to a ball strike on the paddle"""

        # Move ball out of contact based on its velocity vector
        collision.collision_move_to_edge(ball, self.sprite)

        if self.catch:
            self.catch_ball(ball)
        elif self.stuck_ball:
            self.release_ball()
        else:
            self.hit_ball(ball)

    def hit_ball(self, ball):
        """Reflect the moving ball"""
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

        ball.set_action(entities.Move(vel))
        self.sound = audio.play_sound("Low")

        logging.info("paddle/ball d=%s vel=%s", delta, vel)

    def kill(self):
        """Kill the paddle"""
        self.stop()
        action = entities.Animate("explode").then(entities.Die())
        self.sprite.set_action(action)
        self.sound = audio.play_sound("Death")

    def break_(self):
        """Break out of the level"""
        self.stop()

        # pylint: disable=comparison-with-callable
        if self.handler == self.normal_handler:
            animation = "paddle_break"
        elif self.handler == self.expanded_handler:
            animation = "paddle_ext_break"
        elif self.handler == self.laser_handler:
            animation = "laser_break"

        action = entities.Animate(animation).then(
            entities.Die()).plus(
                entities.Move([0.5, 0]))
        self.sprite.set_action(action)
        self.sound = audio.play_sound("Break")

    def alive(self):
        """test whether the paddle is still alive

        It counts as alive if it's killed but the sound is still playing
        """
        return self.sprite.alive() or (self.sound is not None and self.sound.get_busy())


class Capsules:
    """Manage capsules"""

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

        self.break_ = self.scene.names["break"]
        self.break_.kill()

        utils.events.register(utils.Event.CAPSULE, self.on_brick)

    def stop(self):
        """Deregister before teardown"""
        utils.events.unregister(utils.Event.CAPSULE, self.on_brick)

    def available(self):
        """Return # of capusules available to deploy"""
        return len(self.scene.groups["capsules"].sprites())

    def disable(self):
        """Disable capsule creation"""
        self.count = 0
        logging.info("Capsule disabled")

    def enable(self):
        """Enable capsule creation"""
        if self.count == 0:
            self.count = utils.random.randint(1,
                                              utils.config["max_capsule_count"])
            logging.info("Capsule in %d", self.count)

    def block(self, names):
        """Prevent the named capsules from being created"""
        for name in names:
            self.scene.names[name].kill()
            self.total -= 1

    def unblock(self, names):
        """Allow the named capsules to be created"""
        capsules = self.scene.groups["capsules"].sprites()
        for name in names:
            capsule = self.scene.names[name]
            if capsule not in capsules:
                self.scene.groups["capsules"].add(capsule)
                self.total += 1

    def apply(self, capsule):
        """Apply the capsule effect to the paddle"""
        effect = capsule.cfg.get("effect", "")

        logging.info("Apply %s", effect)

        if effect == "catch":
            self.paddle.enable_catch()
            self.block(["capsuleC"])
        else:
            self.paddle.disable_catch()
            self.unblock(["capsuleC"])

        if effect == "break":
            self.scene.groups["all"].add(self.break_)
            self.scene.groups["break"].add(self.break_)
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
                ball.set_action(entities.Move(vel))
                ball.kill()
                self.scene.groups["balls"].add(ball)
                self.scene.groups["all"].add(ball)

            self.disable()

            logging.debug("Vels: %s", vels)
        elif effect == "player":
            utils.events.generate(utils.Event.EXTRA_LIFE)
        elif effect == "slow":
            self.state.ball_speed /= utils.config["ball_speed_multiplier"]

            for ball in self.scene.groups["balls"]:
                if isinstance(ball.action, entities.Move):
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
        utils.events.generate(utils.Event.POINTS, points=points)

    def kill(self, capsule):
        """Kill a capsule - either off the screen or hit the paddle"""
        logging.info("Kill %s", capsule.cfg["effect"])
        capsule.kill()
        self.scene.groups["capsules"].add(capsule)

        self.enable()

    def spawn(self, capsule, position):
        """Spawn a new capsule after a brick was destroyed"""
        logging.info("Spawn %s", capsule.cfg["effect"])
        capsule.rect.topleft = position
        self.scene.groups["capsules"].remove(capsule)
        self.scene.groups["paddle"].add(capsule)
        self.scene.groups["all"].add(capsule)

    def on_brick(self, event):
        """Check whether to spawn a capsule after a brick is hit"""
        if self.total == self.available() and self.count > 0:
            self.count -= 1

            if self.count == 0:
                choices = [capsule for capsule in self.scene.groups["capsules"]
                           for _ in range(capsule.cfg["weight"])]
                capsule = utils.random.choice(choices)
                self.spawn(capsule, event.position)
