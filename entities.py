"""
Sprites, scenes, and their actions
"""

import math
import random

import pygame

import audio
import display
import utils


class Action:
    "Base class for sprite actions"
    # pylint: disable=unused-argument, no-self-use, unnecessary-pass

    def then(self, action):
        "Perform the given action after this action completes"
        return Series([self, action])

    def plus(self, action):
        "Perform the given action while this action runs"
        return Parallel([self, action])

    def update(self, sprite):
        "Perform the action on the given sprite"
        return None

    def start(self, sprite):
        "Called when the action starts running"
        pass

    def stop(self, sprite):
        "Called when the action stops running"
        pass


class Series(Action):
    "Base class for a chain of actions to run in series"

    def __init__(self, actions):
        self.actions = list(actions)
        self.action = self.actions.pop(0)

    def start(self, sprite):
        if self.action:
            self.action.start(sprite)

    def stop(self, sprite):
        if self.action:
            self.action.stop(sprite)

    def update(self, sprite):
        next_action = self.action.update(sprite)

        if next_action is not self.action:
            self.action.stop(sprite)
            self.action = next_action
            self.start(sprite)

        if self.action:
            return self

        if self.actions:
            self.action = self.actions.pop(0)
            self.start(sprite)
            return self

        return None


class Parallel(Action):
    "Base class for actions that run in parallel"

    def __init__(self, actions):
        self.actions = list(actions)

    def start(self, sprite):
        for action in self.actions:
            action.start(sprite)

    def stop(self, sprite):
        for action in self.actions:
            action.stop(sprite)

    def update(self, sprite):
        # Advance each action
        next_actions = [action.update(sprite) for action in self.actions]

        # Issue any stops
        for next_action, prev_action in zip(next_actions, self.actions):
            if next_action is None:
                prev_action.stop(sprite)

        # Filter out any actions that finish
        self.actions = [action for action in next_actions if action]

        return self if self.actions else None


class PaddleMove(Action):
    "Move the paddle sprite"

    def __init__(self, region):
        self.rect = region.copy()
        self.delta = 0

        utils.events.register(utils.Event.PADDLEMOVE, self.on_paddlemove)

    def on_paddlemove(self, event):
        "Event handler for EVT_PADDLEMOVE"
        self.delta += event.delta

    def update(self, sprite):
        sprite.rect.move_ip(self.delta, 0)
        sprite.rect.clamp_ip(self.rect)
        self.delta = 0
        return self


class Move(Action):
    "Move a sprite"

    def __init__(self, delta):
        self.delta = delta
        self.total = [0, 0]

    def update(self, sprite):
        total = [t + d for t, d in zip(self.total, self.delta)]
        delta = [int(i) for i in total]
        self.total = [t-m for t, m in zip(total, delta)]
        sprite.rect.move_ip(delta)
        return self


class MoveLimited(Move):
    "Move a sprite for the given number of frames"

    def __init__(self, delta, frames):
        Move.__init__(self, delta)
        self.frames = frames

    def update(self, sprite):
        Move.update(self, sprite)

        if self.frames > 0:
            self.frames -= 1

        return None if self.frames == 0 else self


class Follow(Action):
    "Follow another sprite"

    def __init__(self, target):
        self.sprite = None
        self.target = target
        self.last = target.rect.center

    def start(self, sprite):
        self.sprite = sprite
        self.target.subscribe(self.callback)

    def stop(self, sprite):
        self.sprite = None
        self.target.unsubscribe(self.callback)

    def update(self, sprite):
        return self

    def callback(self, target):
        "Callback when target sprite is updated"
        pos = target.rect.center
        if pos != self.last:
            delta = [pos[0] - self.last[0], pos[1] - self.last[1]]
            self.sprite.rect.move_ip(delta)
            self.last = pos
        return self


class Blink(Action):
    "Blink the sprite at the given rate"

    def __init__(self, rate):
        # Convert rate from seconds to frames per half cycle
        fps = utils.config["frame_rate"]
        self.rate = int(rate * fps / 2)
        self.frames = 0

    def update(self, sprite):
        self.frames += 1

        if self.frames == self.rate:
            sprite.visible ^= 1
            self.frames = 0
        return self


class Animate(Action):
    "Animate the sprite"

    def __init__(self, name, align="center"):
        cfg = utils.config["animations"][name]
        self.images = [display.get_image(name) for name in cfg["images"]]
        self.speed = cfg["speed"]
        self.loop = cfg.get("loop")
        self.align = align
        self.frame = 0
        self.count = 0

    def update(self, sprite):
        if self.count == 0:
            image = self.images[self.frame]
            sprite.set_image(image, self.align)

        self.count += 1
        if self.count >= self.speed:
            self.frame += 1
            self.count = 0

            if self.frame >= len(self.images):
                if self.loop:
                    self.frame = 0

        return self if self.frame < len(self.images) else None


class Die(Action):
    "Kill the sprite"

    def update(self, sprite):
        sprite.kill()
        return None


class PlaySound(Action):
    "Play the given sound"

    def __init__(self, sound):
        self.sound = audio.play_sound(sound)

    def update(self, sprite):
        done = self.sound is None or not self.sound.get_busy()
        return None if done else self


class FireEvent(Action):
    "Action to fire the given event on first update"

    def __init__(self, event, **kwargs):
        self.event = event
        self.kwargs = kwargs

    def update(self, sprite):
        if self.event:
            utils.events.generate(self.event, **self.kwargs)
            self.event = None
        return None


class Callback(Action):
    "Action to invoke a callback on the first update"

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def update(self, sprite):
        if self.callback:
            self.callback(*self.args, **self.kwargs)
            self.callback = None
        return None


class UpdateVar(Action):
    "Update a sprite with rendered text from a given variable"

    def __init__(self, name, font="white", fmt="%s"):
        self.name = name
        self.font = font
        self.fmt = fmt
        self.text = ""
        self.dirty = False

        utils.events.register(utils.Event.VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        "Event handler for EVT_VAR_CHANGE"
        if event.name == self.name:
            self.dirty = True
            self.text = self.fmt % event.value

    def update(self, sprite):
        if self.dirty:
            self.dirty = False
            image = display.draw_text(self.text, self.font)
            sprite.set_image(image)
        return self


class Delay(Action):
    "Do nothing for the given number of frames"

    def __init__(self, delay):
        fps = utils.config["frame_rate"]
        self.frames = int(delay * fps)

    def update(self, sprite):
        self.frames -= 1
        return self if self.frames > 0 else None


class Spawn(Action):
    "Spawn a new alien"

    def __init__(self, name, scene):
        self.clone = scene.names[name]
        self.scene = scene

    def update(self, sprite):
        clone = self.clone.clone()

        clone.rect.center = sprite.rect.center
        clone.rect.bottom = sprite.rect.top

        action = MoveLimited([0, 0.25], 96).then(AlienEscape(self.scene))

        animation = clone.cfg["animation"]
        if animation:
            action = action.plus(Animate(animation))

        clone.set_action(action)
        self.scene.groups["all"].add(clone)
        self.scene.groups["ball"].add(clone)
        self.scene.groups["paddle"].add(clone)
        self.scene.groups["aliens"].add(clone)

        return None


class AlienEscape(Move):
    "Algorithm for the aliens to escape the blocks"

    def __init__(self, scene):
        self.scene = scene
        self.states = [("down", "left"), ("left", "up"),
                       ("down", "right"), ("right", "up")]
        self.index = 0
        self.tests = {
            "up": [0, -1],
            "down": [0, 1],
            "left": [-1, 0],
            "right": [1, 0],
        }
        self.speed = 0.25

        Move.__init__(self, [0, 0])

    def attempt(self, sprite, direction):
        "Return boolean indicating if the alien can move in the given direction."
        success = False
        delta = self.tests[direction]

        # Temporarily move in the requested direction
        sprite.rect.move_ip(delta)

        # if it only collides with itself, we're good
        others = pygame.sprite.spritecollide(sprite,
                                             self.scene.groups["ball"],
                                             False)
        if len(others) == 1:
            success = True

        # Move back
        sprite.rect.move_ip([-i for i in delta])

        return success

    def move(self, sprite):
        "Attempt to move the sprite"
        initial = self.index
        while True:
            first, second = self.states[self.index]

            # Try the preferred directions first
            for direction in [first, second]:
                if self.attempt(sprite, direction):
                    self.delta = [i * self.speed
                                  for i in self.tests[direction]]
                    Move.update(self, sprite)
                    return

            # If both fail, roll to the next state
            self.index = (self.index + 1) % len(self.states)

            # Do nothing if we try all the options and can't find an out
            if self.index == initial:
                break

    def update(self, sprite):
        self.move(sprite)

        # check whether to change behavior
        rect = pygame.Rect(0, 0, 0, 0)
        for brick in self.scene.groups["bricks"].sprites():
            rect.union_ip(brick.rect)

        if sprite.rect.top >= rect.bottom:
            return AlienDescend(self.scene)

        return self


class AlienDescend(MoveLimited):
    "Algorithm for alien behavior on descend"

    def __init__(self, scene):
        MoveLimited.__init__(self, [0, 0.25], 60)
        self.scene = scene

    def update(self, sprite):
        if MoveLimited.update(self, sprite) is None:
            actions = [AlienDescend(self.scene)]
            playspace = self.scene.names["bg"].rect

            if sprite.rect.right < playspace.right - 32:
                actions += [AlienJuke(self.scene, 1)]

            if sprite.rect.right < playspace.right - 40:
                actions += [AlienCircle(self.scene, 1)]

            if sprite.rect.left > playspace.left + 32:
                actions += [AlienJuke(self.scene, -1)]

            if sprite.rect.left > playspace.left + 40:
                actions += [AlienCircle(self.scene, -1)]

            return random.choice(actions)

        return self


class AlienJuke(MoveLimited):
    "Action for alien's juke move"

    def __init__(self, scene, xdir):
        # pylint: disable=super-init-not-called; called in reset()
        self.scene = scene
        self.init()
        self.deltas = [[x * xdir, y] for x, y in self.deltas]
        self.index = 0
        self.reset()

    def init(self):
        "Hook to initialize alien movement variables"
        self.deltas = [[0.25, 0.5], [0.5, 0.5], [0.5, 0.25], [0.25, 0.5]]
        self.frame_counts = [10, 30, 10, 10]

    def reset(self):
        "Reset the limited move action to the currently selected parameters"
        delta = self.deltas[self.index]
        frames = self.frame_counts[self.index]
        MoveLimited.__init__(self, delta, frames)

    def update(self, sprite):
        if MoveLimited.update(self, sprite) is None:
            self.index += 1

            if self.index < len(self.deltas):
                self.reset()
            else:
                return AlienDescend(self.scene)

        return self


class AlienCircle(AlienJuke):
    "Alien's circle action"

    def init(self):
        self.deltas = [
            [0.25, 0.5],
            [0.5, 0.5],
            [0.5, 0.25],
            [0.5, -0.25],
            [0.5, -0.5],
            [0.25, -0.5],
            [-0.25, -0.5],
            [-0.5, -0.5],
            [-0.5, -0.25],
            [-0.5, 0.25],
            [-0.5, 0.5],
            [-0.25, 0.5]
        ]

        self.frame_counts = [10, 30, 10, 10, 30, 10, 10, 30, 10, 10, 30, 10]


class InletMgr(Action):
    "Algorithm for alien inlets"

    def __init__(self, scene):
        self.scene = scene
        self.max_delay = 0
        self.max_aliens = 0
        self.frames = 0

    def start(self, sprite):
        self.max_delay = sprite.cfg["max_delay"] * utils.config["frame_rate"]
        self.max_aliens = sprite.cfg["max_aliens"]
        self._randomize()

    def _randomize(self):
        self.frames = random.random() * self.max_delay

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        else:
            if len(self.scene.groups["aliens"].sprites()) < self.max_aliens:
                return Animate("inlet_open").then(
                    Spawn("alien", self.scene).then(
                        Delay(1.0).then(
                            Animate("inlet_close").then(
                                InletMgr(self.scene)))))
            self._randomize()
        return self


class DohMgr(Action):
    "Algorithm for Doh"

    def __init__(self, scene):
        self.scene = scene
        self.frames = 0
        self.set_state(self.state_open, 1)

    def start(self, sprite):
        self.set_closed(sprite)

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        else:
            self.state(sprite)
        return self

    def set_open(self, sprite):
        "Open Doh's mouth"
        sprite.set_image(display.get_image("doh_open"))
        sprite.cfg["hit_animation"] = "doh_hit_open"

    def set_closed(self, sprite):
        "Close Doh's mouth"
        sprite.set_image(display.get_image("doh"))
        sprite.cfg["hit_animation"] = "doh_hit"

    def set_state(self, handler, delay):
        "Set the Doh state"
        self.state = handler
        self.frames = delay * utils.config["frame_rate"]

    def fire(self, sprite):
        "Fire a Doh projectile"
        shot = self.scene.names["doh_shot"].clone()

        shot.rect.center = sprite.rect.center

        start = shot.rect.center
        target = self.scene.names["paddle"].rect.center

        delta = [target[i] - start[i] for i in range(2)]
        magnitude = math.sqrt(delta[0]**2 + delta[1]**2)
        speed = 3
        delta = [speed * value / magnitude for value in delta]

        action = Move(delta)

        animation = shot.cfg["animation"]
        if animation:
            action = action.plus(Animate(animation))

        shot.set_action(action)
        self.scene.groups["all"].add(shot)
        self.scene.groups["paddle"].add(shot)

    def state_open(self, sprite):
        "State to open mouth"
        self.set_open(sprite)
        self.set_state(self.state_fire1, 0.0)

    def state_fire1(self, sprite):
        "State to fire first projectile"
        self.fire(sprite)
        self.set_state(self.state_fire2, 0.5)

    def state_fire2(self, sprite):
        "State to fire second projectile"
        self.fire(sprite)
        self.set_state(self.state_fire3, 0.5)

    def state_fire3(self, sprite):
        "State to fire third projectile"
        self.fire(sprite)
        self.set_state(self.state_close, 0.0)

    def state_close(self, sprite):
        "State to close mouth"
        self.set_closed(sprite)
        self.set_state(self.state_open, 4)


class Sprite(pygame.sprite.DirtySprite):
    "Base class for all game entities"

    def __init__(self, image, cfg):
        pygame.sprite.DirtySprite.__init__(self)

        self.image = image
        self.rect = image.get_rect()
        self.last = self.rect
        self.dirty = 2
        self.blendmode = 0
        self.source_rect = None
        self.visible = 1

        self._layer = cfg.get("layer", 10)

        self.action = None

        self.cfg = cfg
        self.callbacks = set()

    def clone(self):
        "Create a clone of this sprite"
        return Sprite(self.image, self.cfg.copy())

    def set_action(self, new_action=None):
        "Start an action for this sprite"
        old_action = self.action

        # Stop the previous action
        if old_action and old_action is not new_action:
            old_action.stop(self)

        self.action = new_action

        # Start the new action
        if new_action and old_action is not new_action:
            new_action.start(self)

    def update(self):
        "Update the sprite for the current frame"
        # Update the previous position
        self.last = self.rect.copy()

        # Update any active actions
        if self.action:
            new_action = self.action.update(self)
            self.set_action(new_action)

        # Notify any listeners of changes
        for callback in self.callbacks:
            callback(self)

    def subscribe(self, callback):
        "Track listener callbacks"
        self.callbacks.add(callback)

    def unsubscribe(self, callback):
        "Untrack listener callbacks"
        self.callbacks.discard(callback)

    def set_image(self, image, align="center"):
        "Update the sprite's image"
        old_rect = self.rect.copy()
        self.image = image
        self.rect.size = image.get_size()
        setattr(self.rect, align, getattr(old_rect, align))

    def hit(self, scene):
        "Respond to a hit event"
        sound = self.cfg.get("hit_sound")
        if sound:
            audio.play_sound(sound)

        animation = self.cfg.get("hit_animation")
        if animation:
            action = Animate(animation)
            if self.action:
                action = self.action.plus(action)
            self.set_action(action)

        hit_points = self.cfg.get("hit_points")
        if hit_points:
            utils.events.generate(utils.Event.POINTS, points=hit_points)

        hits = self.cfg.get("hits")
        if hits:
            hits -= 1
            self.cfg["hits"] = hits
            if hits == 0:
                self.kill()

                death_animation = self.cfg.get("death_animation")
                if death_animation:
                    align = self.cfg.get("death_animation_align", "center")
                    self.set_action(
                        Animate(death_animation, align).then(Die()))
                    scene.groups["all"].add(self)

                death_action = self.cfg.get("on_death")
                if death_action == "create_capsule":
                    utils.events.generate(utils.Event.CAPSULE,
                                          position=self.rect.topleft)

                points = self.cfg.get("points", 0)
                if points:
                    utils.events.generate(utils.Event.POINTS, points=points)


class Scene:
    """Scene class for tracking all sprites in the current scene.

    Scene requirements:
    - named Sprites for specific processing - paddle, ball, bg, etc
    - multiple groups for things like collision handling and ball tracking
    - single group for rendering everything
    - share definitions for block reuse
    - control persistence - some need to be reinstantiated, others need persistence
    """
    Group = pygame.sprite.LayeredDirty

    def __init__(self, names, var_dict):
        self.groups = {}
        self.names = {}

        for name in names:
            sprites = utils.config["scenes"][name]

            for cfg in sprites:
                cfg = cfg.copy()

                action = None

                key = cfg.pop("text", "")
                if key:
                    font = cfg.pop("font", "white")
                    image = display.draw_text(key, font)

                key = cfg.pop("var", "")
                if key:
                    fmt = cfg.pop("fmt", "%s")
                    text = fmt % var_dict[key]
                    font = cfg.pop("font", "white")
                    image = display.draw_text(text, font)
                    action = UpdateVar(key, font, fmt)

                key = cfg.pop("image", "")
                if key:
                    image = display.get_image(key)

                position = cfg.pop("position", [0, 0])

                group_names = cfg.pop("groups", [])

                sprite = Sprite(image, cfg)
                sprite.rect.topleft = position
                sprite.set_action(action)

                for group_name in group_names + ["all"]:
                    group = self.groups.setdefault(group_name, Scene.Group())
                    group.add(sprite)

                sprite_name = cfg.get("name")
                if sprite_name:
                    self.names[sprite_name] = sprite

    def merge(self, scene):
        "Merge another scene's groups and names into this scene"
        for key, source in scene.groups.items():
            dest = self.groups.setdefault(key, Scene.Group())
            dest.add(source)
        self.names.update(scene.names)
