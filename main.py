"""
Arkanoid clone

Goal is to produce a complete game without having to worry about any game design or resources.  Just code!
"""

import logging
import os
import time

import pygame

import display
import engine
import utils

class Timer:
    def __init__(self):
        """Track time deltas to the millisecond"""
        self.last = time.time()

    def get(self):
        """Get the time in milliseconds since last call"""
        now = time.time()
        delta = now - self.last
        self.last = now
        return delta

def main():
    """Arkanoid main loop"""

    utils.init()                    # Lazy initialization to give time to set up logging

    pygame.init()

    window = display.Window()

    eng = engine.Engine()

    clock = pygame.time.Clock()
    frame_timer = Timer()
    utilization_timer = Timer()

    while True:
        utilization_timer.get()

        # Event pump
        for event in pygame.event.get():
            logging.debug("Event: %s", pygame.event.event_name(event.type))

            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
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

if __name__ == '__main__':
    utils.setup_logging("logging.json")

    try:
        main()
    except Exception as exc:
        logging.exception("Uncaught exception!")
