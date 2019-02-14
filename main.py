"""Arkanoid clone"""

import logging

import pygame

import display
import engine
import utils

EngineClass = engine.Engine


def main():
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


if __name__ == '__main__':
    utils.setup_logging("logging.json")

    try:
        main()
    except Exception as exc:    # pylint: disable=broad-except
        logging.exception("Uncaught exception!")
