import curses
import time
from startup import display_startup
from dashboard import display_dashboard
import threading

def main(stdscr):
    curses.curs_set(0) # Hide cursor
    stdscr.nodelay(True) # Don't block on input
    stop_event = threading.Event()
    
    # TODO Iniatilize threads
    
    state = "dashboard"

    while True:
        stdscr.clear()
        if state == "startup":
            display_startup(False, stdscr, 0)
        elif state == "dashboard":
            display_dashboard(stdscr, 0)
        stdscr.addstr(5, 0, "Press 'q' to quit.")
        stdscr.refresh()

        # Non-blocking keypress check
        key = stdscr.getch()
        if key == ord('q'):
            break

        time.sleep(0.1) # Buffer to keep from maxing out the CPU

curses.wrapper(main)