"""
display.py

Display functionality
"""
import logging
import os

import pygame

import audio
import utils

class Window:
    def __init__(self):
        world_size = utils.config['world_size']
        screen_size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.main = pygame.display.set_mode(screen_size, flags)
        self.screen = pygame.Surface(world_size)

        logging.info("Driver: %s", pygame.display.get_driver())
        logging.info("Display Info:\n    %s", pygame.display.Info())

        pygame.display.set_caption(utils.config["title"])

    def flip(self):
        pygame.transform.scale(self.screen, self.main.get_size(), self.main)
        pygame.display.flip()

    def clear(self):
        self.screen.fill(utils.color(utils.config["bg_color"]))

def _find_char_offset(char, characters):
    for row, data in enumerate(characters):
        col = data.find(char)
        if col > -1:
            return [col, row]

    raise ValueError("Unsupported Character: %s" % char)

def draw_text(text):
    config = utils.config["font"]
    filename = config["filename"]
    size = config["size"]
    characters = config["characters"]

    surf = pygame.Surface([size[0]*len(text), size[1]])
    image = _load_image(filename)
    pos = 0
    for char in text:
        col, row = _find_char_offset(char, characters)

        offset = (col * size[0], row * size[1])

        surf.blit(image, [pos, 0], pygame.Rect(offset, size))

        pos += size[0]

    return surf

_image_cache = {}

def _load_image(fname, rect=None, scaled=[]):
    image = _image_cache.get(fname)
    if image is None:
        image = pygame.image.load(fname)
        image = image.convert_alpha()
        _image_cache[fname] = image

    if rect:
        image = image.subsurface(rect)

    if scaled:
        image = pygame.transform.smoothscale(image, scaled)

    return image

def get_image(name):
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg["size"]
    offset = cfg["offset"]
    scaled = cfg.get("scaled")

    rect = pygame.Rect(offset, size)

    image = _load_image(fname, rect, scaled)

    return image

class Action:
    def then(self, next):
        return Series([self, next])

    def plus(self, action):
        return Parallel([self, action])

class Series(Action):
    def __init__(self, actions):
        self.actions = list(actions)
        self.action = self.actions.pop(0)

    def update(self, sprite):
        if self.action:
            done = self.action.update(sprite)
            if done:
                self.action = None
                if self.actions:
                    self.action = self.actions.pop(0)

        return self.action is None

class Parallel(Action):
    def __init__(self, actions):
        self.actions = list(actions)

    def update(self, sprite):
        self.actions = filter(lambda action: not action.update(sprite), self.actions)
        done = len(self.actions) == 0
        return done

class MouseMove(Action):
    def __init__(self, region, sensitivity):
        self.rect = region.copy()
        self.delta = [0, 0]
        self.sensitivity = sensitivity

        utils.events.register(utils.EVT_MOUSEMOTION, self.on_mousemove)

    def on_mousemove(self, event):
        self.delta = [self.delta[i] + self.sensitivity[i] * event.rel[i] for i in range(2)]

    def update(self, sprite):
        sprite.move(self.delta)
        sprite.rect.clamp_ip(self.rect)
        self.delta = [0, 0]

class Move(Action):
    def __init__(self, delta):
        self.delta = delta
        self.total = [0,0]

    def update(self, sprite):
        total = [t + d for t,d in zip(self.total, self.delta)]
        move = [int(i) for i in total]
        self.total = [t-m for t,m in zip(total, move)]
        sprite.move(move)

class Follow(Action):
    def __init__(self, target):
        self.target = target
        self.last = target.get_pos()

    def update(self, sprite):
        pos = self.target.get_pos()
        if pos != self.last:
            delta = [pos[0] - self.last[0], pos[1] - self.last[1]]
            sprite.move(delta)
            self.last = pos

class Blink(Action):
    def __init__(self, rate):
        # Convert rate from seconds to frames per half cycle
        fps = utils.config["frame_rate"]
        self.rate = int(rate * fps) / 2
        self.frames = 0

    def update(self, sprite):
        self.frames += 1

        if self.frames == self.rate:
            sprite.visible ^= 1
            self.frames = 0

class Animate(Action):
    def __init__(self, name):
        cfg = utils.config["animations"][name]
        self.images = [get_image(name) for name in cfg["images"]]
        self.speed = cfg["speed"]
        self.loop = cfg.get("loop")
        self.frame = 0
        self.count = 0

    def update(self, sprite):
        if self.frame < len(self.images):
            if self.count == 0:
                image = self.images[self.frame]
                sprite.set_image(image)

            self.count += 1
            if self.count >= self.speed:
                self.frame += 1
                self.count = 0

        if self.frame >= len(self.images):
            if self.loop:
                self.frame = 0
            else:
                return True

class Die(Action):
    def update(self, sprite):
        sprite.kill()
        return True

class PlaySound(Action):
    def __init__(self, sound):
        self.sound = audio.play_sound(sound)

    def update(self, sprite):
        return not self.sound.get_busy()

class FireEvent(Action):
    def __init__(self, event, **kwargs):
        self.event = event
        self.kwargs = kwargs

    def update(self, sprite):
        if self.event:
            utils.events.generate(self.event, **self.kwargs)
            self.event = None
        return True

class UpdateVar(Action):
    def __init__(self, name):
        self.name = name
        self.text = ""
        self.dirty = False

        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        if event.name == self.name:
            self.dirty = True
            self.text = str(event.value)

    def update(self, sprite):
        if self.dirty:
            self.dirty = False
            image = draw_text(self.text)
            sprite.set_image(image)

class Delay(Action):
    def __init__(self, delay):
        fps = utils.config["frame_rate"]
        self.frames = int(delay * fps)

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        return self.frames == 0

class Spawn(Action):
    def __init__(self, name, scene):
        self.clone = scene.names[name]
        self.scene = scene

    def update(self, sprite):
        clone = self.clone.clone()

        clone.rect.center = sprite.rect.center
        clone.rect.bottom = sprite.rect.top

        action = Move([0,0.25])

        animation = clone.cfg["animation"]
        if animation:
            action = action.plus(Animate(animation))

        clone.set_action(action)
        self.scene.groups["all"].add(clone)
        self.scene.groups["ball"].add(clone)
        self.scene.groups["paddle"].add(clone)

        return True

class InletMgr(Action):
    def __init__(self, scene):
        self.scene = scene

    def update(self, sprite):
        sprite.set_action(Animate("inlet_open").then(Spawn("alien", self.scene).then(Delay(1.0).then(Animate("inlet_close").then(InletMgr(self.scene))))))

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

    def clone(self):
        return Sprite(self.image, self.cfg.copy())

    def get_pos(self):
        return self.rect.topleft

    def set_pos(self, pos):
        self.rect.x = pos[0]
        self.rect.y = pos[1]

    def move(self, delta):
        self.rect.x += delta[0]
        self.rect.y += delta[1]

    def set_action(self, action=None):
        self.action = action

    def update(self):
        self.last = self.rect.copy()
        if self.action:
            done = self.action.update(self)
            if done:
                self.action = None

    def set_image(self, image):
        old_rect = self.rect.copy()
        self.image = image
        self.rect.size = image.get_size()
        self.rect.center = old_rect.center

    def hit(self, scene):
        sound = self.cfg.get("hit_sound")
        if sound:
            audio.play_sound(sound)

        animation = self.cfg.get("hit_animation")
        if animation:
            self.set_action(Animate(animation))

        hits = self.cfg.get("hits")
        if hits:
            hits -= 1
            self.cfg["hits"] = hits
            if hits == 0:
                self.kill()

                death_animation = self.cfg.get("death_animation")
                if death_animation:
                    self.set_action(Animate(death_animation).then(Die()))
                    scene.groups["all"].add(self)

                death_action = self.cfg.get("on_death")
                if death_action == "create_capsule":
                    utils.events.generate(utils.EVT_CAPSULE, position=self.get_pos())

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
                    image = draw_text(key)

                key = cfg.pop("var", "")
                if key:
                    text = str(var_dict[key])
                    image = draw_text(text)
                    action = UpdateVar(key)

                key = cfg.pop("image", "")
                if key:
                    image = get_image(key)

                position = cfg.pop("position", [0,0])

                group_names = cfg.pop("groups", [])

                sprite = Sprite(image, cfg)
                sprite.set_pos(position)
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
