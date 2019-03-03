"""
debug assistance
"""
import logging
import tracemalloc

import pygame

import collision
import display
import engine
import entities
import utils


def log_mem():
    """Log memory statistics"""
    memory_stats = tracemalloc.get_traced_memory()
    logging.info("Memory usage - Current: %.1fkB, Peak: %.1fkB",
                 memory_stats[0] / 1024,
                 memory_stats[1] / 1024)


SCENES = {
    "collision_test": [
        {
            "name": "ball",
            "image": "ball",
            "position": [100, 80]
        },
        {
            "name": "brick",
            "image": "red",
            "position": [100, 100]
        }
    ]
}


class DebugState(engine.State):
    "Special engine state for debugging"

    def __init__(self, eng, data):
        engine.State.__init__(self, eng, data)

        # Register the faux JSON from the debug file
        utils.config["scenes"].update(SCENES)


class CollisionTest(DebugState):
    "State to test collisions"

    def __init__(self, eng, data):
        DebugState.__init__(self, eng, data)

        self.scene = entities.Scene(["collision_test"])

        self.ball = self.scene.names["ball"]
        self.brick = self.scene.names["brick"]

        utils.events.register(utils.Event.KEYDOWN, self.on_keydown)

    def on_keydown(self, event):
        "Respond to keypress events"
        delta = [0, 0]

        if event.key == pygame.K_UP:
            delta = [0, -1]
        elif event.key == pygame.K_DOWN:
            delta = [0, 1]
        elif event.key == pygame.K_LEFT:
            delta = [-1, 0]
        elif event.key == pygame.K_RIGHT:
            delta = [1, 0]

        self.scene.names["ball"].rect.move_ip(delta)

        if pygame.sprite.collide_rect(self.ball, self.brick):
            side = collision.collision_side(self.ball, self.brick)
            print(side)
        else:
            print()

    def update(self):
        self.scene.groups["all"].update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class DebugEngine(engine.Engine):
    """Special engine for debugging"""

    def __init__(self):
        engine.Engine.__init__(self)
        self.__running = True

    def _pause_on(self):
        self.__running = False
        display.release_mouse()

    def _pause_off(self):
        self.__running = True
        display.grab_mouse()

    def _pause_toggle(self):
        if self.__running:
            self._pause_on()
        else:
            self._pause_off()

    def input(self, event):
        if event.type == utils.Event.KEYDOWN:
            if event.key == pygame.K_n:
                self.state.next_level()
            elif event.key == pygame.K_l:
                self.state.jump_level(36)
            elif event.key == pygame.K_r:
                self.set_state(engine.StartState, {})
            elif event.key == pygame.K_p:
                self._pause_toggle()
            elif event.key == pygame.K_s:
                if self.__running:
                    self._pause_on()
                else:
                    self._step()

        if self.__running:
            return engine.Engine.input(self, event)
        return False

    def update(self):
        if self.__running:
            self._step()

    def _step(self):
        engine.Engine.update(self)

    def reset(self):
        # Hook for debug actions on reset
        engine.Engine.reset(self)

        log_mem()


if __name__ == "__main__":
    utils.setup_logging("debug.json")

    engine.EngineClass = DebugEngine

    # engine.Engine.INITIAL_STATE = CollisionTest

    # Trace memory consumption - debug only
    tracemalloc.start()

    try:
        engine.main_loop()
    except:  # pylint: disable=bare-except
        logging.exception("Uncaught exception!")

    # Close memory tracking
    log_mem()
    tracemalloc.stop()
