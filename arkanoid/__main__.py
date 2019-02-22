"""Arkanoid clone"""

import inspect
import logging
import os
import sys

import pygame

import display
import engine
import utils

EngineClass = engine.Engine


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


def get_script_dir():
    """Get directory that includes this script.  Pulled from
    https://stackoverflow.com/questions/3718657/how-to-properly-determine-current-script-directory/22881871#22881871
    """
    if getattr(sys, 'frozen', False):  # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    path = os.path.realpath(path)
    return os.path.dirname(path)


def main():
    """Top level function!"""

    # No PYC files
    sys.dont_write_bytecode = True

    # Switch to the install directory to load data files
    os.chdir(get_script_dir())

    utils.setup_logging("logging.json")

    # Run the game
    try:
        main_loop()
    except Exception:    # pylint: disable=broad-except
        logging.exception("Uncaught exception!")


if __name__ == '__main__':
    main()
