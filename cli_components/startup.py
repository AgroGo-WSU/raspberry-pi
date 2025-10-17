def display_startup(logged_in, stdscr, start_line):
    if not logged_in:
        # TODO, put actual QR code here and use Firebase to authenticate
        stdscr.addstr(start_line, 0, "User not logged in, sign in by scanning the QR code below")
    if logged_in:
        stdscr.addstr(start_line, 0, "User logged in, initializing sensor readings")