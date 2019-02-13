"""
display.py

Display functionality
"""
import logging
import math
import os
import random

import pygame

import audio
import utils

os.environ['SDL_VIDEODRIVER'] = 'directx'

def set_cursor(cursor_strings, hotspot=[0,0], scale=1):
    # Scale the strings larger if requested
    cursor_strings = ["".join([ch * scale for ch in line]) for line in cursor_strings for _ in range(scale)]
    size = [len(cursor_strings[0]), len(cursor_strings)]
    xormask, andmask = pygame.cursors.compile(cursor_strings)
    pygame.mouse.set_cursor(size, hotspot, xormask, andmask)

class Window:
    def __init__(self):
        world_size = utils.config['world_size']
        screen_size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.main = pygame.display.set_mode(screen_size, flags)
        self.screen = pygame.Surface(world_size)

        logging.warning("Driver: %s", pygame.display.get_driver())
        logging.warning("Display Info:\n    %s", str(pygame.display.Info()))

        pygame.display.set_caption(utils.config["title"])

        # Load a white cursor
        set_cursor(pygame.cursors.thickarrow_strings)

    def flip(self):
        pygame.transform.scale(self.screen, self.main.get_size(), self.main)
        pygame.display.flip()

    def clear(self):
        self.screen.fill(utils.color(utils.config["bg_color"]))

def grab_mouse():
    pygame.mouse.set_visible(0)
    pygame.event.set_grab(1)

def release_mouse():
    pygame.mouse.set_visible(1)
    pygame.event.set_grab(0)

def _find_char_offset(char, characters):
    for row, data in enumerate(characters):
        col = data.find(char)
        if col > -1:
            return [col, row]

    raise ValueError("Unsupported Character: %s" % char)

def draw_text(text, font):
    config = utils.config["fonts"][font]
    name = config["image"]
    size = config["size"]
    characters = config["characters"]

    text_split = text.split('\n')
    rows = len(text_split)
    cols = max(map(len, text_split))

    surf = pygame.Surface([size[0] * cols, size[1] * rows], pygame.SRCALPHA).convert_alpha()
    image = get_image(name)
    for row, line in enumerate(text_split):
        for col, char in enumerate(line):
            offset = _find_char_offset(char, characters)
            offset = [offset[i] * size[i] for i in range(2)]

            surf.blit(image, [col * size[0], row * size[1]], pygame.Rect(offset, size), pygame.BLEND_RGBA_MAX)

    return surf

def image_factory(name):
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg.get("size", None)
    offset = cfg.get("offset", None)
    scaled = cfg.get("scaled", None)

    image = pygame.image.load(fname)
    image = image.convert_alpha()

    if size and offset:
        rect = pygame.Rect(offset, size)
        image = image.subsurface(rect)

    if scaled:
        image = pygame.transform.smoothscale(image, scaled)

    return image

_image_cache = utils.Cache(image_factory)

def get_image(name):
    image = _image_cache.get(name)

    return image

class Action:
    def then(self, action):
        return Series([self, action])

    def plus(self, action):
        return Parallel([self, action])

    def update(self, sprite):
        return None

    def start(self, sprite):
        pass

    def stop(self, sprite):
        pass

class Series(Action):
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
        next_actions = list(map(lambda action: action.update(sprite), self.actions))

        # Issue any stops
        for next_action, prev_action in zip(next_actions, self.actions):
            if next_action is None:
                prev_action.stop(sprite)

        # Filter out any actions that finish
        self.actions = list(filter(None, next_actions))

        return self if self.actions else None

class PaddleMove(Action):
    def __init__(self, region):
        self.rect = region.copy()
        self.delta = 0

        utils.events.register(utils.EVT_PADDLEMOVE, self.on_paddlemove)

    def on_paddlemove(self, event):
        self.delta += event.delta

    def update(self, sprite):
        sprite.rect.move_ip(self.delta, 0)
        sprite.rect.clamp_ip(self.rect)
        self.delta = 0
        return self

class Move(Action):
    def __init__(self, delta):
        self.delta = delta
        self.total = [0,0]

    def update(self, sprite):
        total = [t + d for t,d in zip(self.total, self.delta)]
        delta = [int(i) for i in total]
        self.total = [t-m for t,m in zip(total, delta)]
        sprite.rect.move_ip(delta)
        return self

class MoveLimited(Move):
    def __init__(self, delta, frames):
        Move.__init__(self, delta)
        self.frames = frames

    def update(self, sprite):
        Move.update(self, sprite)

        if self.frames > 0:
            self.frames -= 1

        return None if self.frames == 0 else self

class Follow(Action):
    def __init__(self, target):
        self.sprite = None
        self.target = target
        self.last = target.rect.center

    def start(self, sprite):
        self.sprite = sprite
        self.target.subscribe(self.notify)

    def stop(self, sprite):
        self.sprite = None
        self.target.unsubscribe(self.notify)

    def update(self, sprite):
        return self

    def notify(self, target):
        pos = target.rect.center
        if pos != self.last:
            delta = [pos[0] - self.last[0], pos[1] - self.last[1]]
            self.sprite.rect.move_ip(delta)
            self.last = pos
        return self

class Blink(Action):
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
    def __init__(self, name, align="center"):
        cfg = utils.config["animations"][name]
        self.images = [get_image(name) for name in cfg["images"]]
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
    def update(self, sprite):
        sprite.kill()
        return None

class PlaySound(Action):
    def __init__(self, sound):
        self.sound = audio.play_sound(sound)

    def update(self, sprite):
        done = self.sound is None or not self.sound.get_busy()
        return None if done else self

class FireEvent(Action):
    def __init__(self, event, **kwargs):
        self.event = event
        self.kwargs = kwargs

    def update(self, sprite):
        if self.event:
            utils.events.generate(self.event, **self.kwargs)
            self.event = None
        return None

class Callback(Action):
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
    def __init__(self, name, font="white", fmt="%s"):
        self.name = name
        self.font = font
        self.fmt = fmt
        self.text = ""
        self.dirty = False

        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        if event.name == self.name:
            self.dirty = True
            self.text = self.fmt % event.value

    def update(self, sprite):
        if self.dirty:
            self.dirty = False
            image = draw_text(self.text, self.font)
            sprite.set_image(image)
        return self

class Delay(Action):
    def __init__(self, delay):
        fps = utils.config["frame_rate"]
        self.frames = int(delay * fps)

    def update(self, sprite):
        self.frames -= 1
        return self if self.frames > 0 else None

class Spawn(Action):
    def __init__(self, name, scene):
        self.clone = scene.names[name]
        self.scene = scene

    def update(self, sprite):
        clone = self.clone.clone()

        clone.rect.center = sprite.rect.center
        clone.rect.bottom = sprite.rect.top

        action = MoveLimited([0,0.25], 96).then(AlienEscape(self.scene))

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
    def __init__(self, scene):
        self.scene = scene
        self.states = [("down", "left"), ("left", "up"),  ("down", "right"), ("right", "up")]
        self.index = 0
        self.tests = {
            "up" : [0, -1],
            "down" : [0, 1],
            "left" : [-1, 0],
            "right" : [1, 0],
        }
        self.speed = 0.25

        Move.__init__(self, [0,0])

    def attempt(self, sprite, direction):
        success = False
        delta = self.tests[direction]

        # Temporarily move in the requested direction
        sprite.rect.move_ip(delta)

        # if it only collides with itself, we're good
        others = pygame.sprite.spritecollide(sprite, self.scene.groups["ball"], False)
        if len(others) == 1:
            success = True

        # Move back
        sprite.rect.move_ip([-i for i in delta])

        return success

    def move(self, sprite):
        initial = self.index
        while True:
            first, second = self.states[self.index]

            # Try the preferred directions first
            for direction in [first, second]:
                if self.attempt(sprite, direction):
                    self.delta = [i * self.speed for i in self.tests[direction]]
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
        rect = pygame.Rect(0,0,0,0)
        for brick in self.scene.groups["bricks"].sprites():
            rect.union_ip(brick.rect)

        if sprite.rect.top >= rect.bottom:
            return AlienDescend(self.scene)

        return self

class AlienDescend(MoveLimited):
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
    def __init__(self, scene, xdir):
        self.scene = scene
        self.init()
        self.deltas = [[x * xdir, y] for x,y in self.deltas]
        self.index = 0
        self.set()

    def init(self):
        self.deltas = [[0.25, 0.5], [0.5, 0.5], [0.5, 0.25], [0.25, 0.5]]
        self.frame_counts = [10, 30, 10, 10]

    def set(self):
        delta = self.deltas[self.index]
        frames = self.frame_counts[self.index]
        MoveLimited.__init__(self, delta, frames)

    def update(self, sprite):
        if MoveLimited.update(self, sprite) is None:
            self.index += 1

            if self.index < len(self.deltas):
                self.set()
            else:
                return AlienDescend(self.scene)

        return self

class AlienCircle(AlienJuke):
    def init(self):
        self.deltas = [[0.25, 0.5], [0.5, 0.5], [0.5, 0.25], [0.5, -0.25], [0.5, -0.5], [0.25, -0.5], [-0.25, -0.5], [-0.5, -0.5], [-0.5, -0.25], [-0.5, 0.25], [-0.5, 0.5], [-0.25, 0.5]]
        self.frame_counts = [10, 30, 10, 10, 30, 10, 10, 30, 10, 10, 30, 10]

class InletMgr(Action):
    def __init__(self, scene):
        self.scene = scene

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
                return Animate("inlet_open").then(Spawn("alien", self.scene).then(Delay(1.0).then(Animate("inlet_close").then(InletMgr(self.scene)))))
            self._randomize()
        return self

class DohMgr(Action):
    def __init__(self, scene):
        self.scene = scene
        self.set_state(self.state_open, 1)

    def start(self, sprite):
        self.set_closed(sprite)

    def delay(self, delay):
        self.frames = delay * utils.config["frame_rate"]

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        else:
            self.state(sprite)
        return self

    def set_open(self, sprite):
        sprite.set_image(get_image("doh_open"))
        sprite.cfg["hit_animation"] = "doh_hit_open"

    def set_closed(self, sprite):
        sprite.set_image(get_image("doh"))
        sprite.cfg["hit_animation"] = "doh_hit"

    def set_state(self, handler, delay):
        self.state = handler
        self.delay(delay)

    def fire(self, sprite):
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
        self.set_open(sprite)
        self.set_state(self.state_fire1, 0.0)

    def state_fire1(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_fire2, 0.5)

    def state_fire2(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_fire3, 0.5)

    def state_fire3(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_close, 0.0)

    def state_close(self, sprite):
        self.set_closed(sprite)
        self.set_state(self.state_open, 4)

class Sprite(pygame.sprite.DirtySprite):
    def __init__(self, image, cfg={}):
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
        return Sprite(self.image, self.cfg.copy())

    def set_action(self, new_action=None):
        old_action = self.action

        # Stop the previous action
        if old_action and old_action is not new_action:
            old_action.stop(self)

        self.action = new_action

        # Start the new action
        if new_action and old_action is not new_action:
            new_action.start(self)

    def update(self):
        self.last = self.rect.copy()

        if self.action:
            new_action = self.action.update(self)
            self.set_action(new_action)

        self.notify()

    def subscribe(self, callback):
        self.callbacks.add(callback)

    def unsubscribe(self, callback):
        self.callbacks.discard(callback)

    def notify(self):
        for callback in self.callbacks:
            callback(self)

    def set_image(self, image, align="center"):
        old_rect = self.rect.copy()
        self.image = image
        self.rect.size = image.get_size()
        setattr(self.rect, align, getattr(old_rect, align))

    def hit(self, scene):
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
            utils.events.generate(utils.EVT_POINTS, points=hit_points)

        hits = self.cfg.get("hits")
        if hits:
            hits -= 1
            self.cfg["hits"] = hits
            if hits == 0:
                self.kill()

                death_animation = self.cfg.get("death_animation")
                if death_animation:
                    align = self.cfg.get("death_animation_align", "center")
                    self.set_action(Animate(death_animation, align).then(Die()))
                    scene.groups["all"].add(self)

                death_action = self.cfg.get("on_death")
                if death_action == "create_capsule":
                    utils.events.generate(utils.EVT_CAPSULE, position=self.rect.topleft)

                points = self.cfg.get("points", 0)
                if points:
                    utils.events.generate(utils.EVT_POINTS, points=points)

# Scene requirements:
# - named Sprites for specific processing - paddle, ball, bg, etc
# - multiple groups for things like collision handling and ball tracking
# - single group for rendering everything
# - share definitions for block reuse
# - control persistence - some need to be reinstantiated, others need persistence
class Scene:
    Group = pygame.sprite.LayeredDirty
    def __init__(self, names, var_dict={}):
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
                    image = draw_text(key, font)

                key = cfg.pop("var", "")
                if key:
                    fmt = cfg.pop("fmt", "%s")
                    text = fmt % var_dict[key]
                    font = cfg.pop("font", "white")
                    image = draw_text(text, font)
                    action = UpdateVar(key, font, fmt)

                key = cfg.pop("image", "")
                if key:
                    image = get_image(key)

                position = cfg.pop("position", [0,0])

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
        for key, source in scene.groups.items():
            dest = self.groups.setdefault(key, Scene.Group())
            dest.add(source)
        self.names.update(scene.names)
