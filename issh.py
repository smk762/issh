import curses
import curses.ascii
from os import environ
from os.path import join, expanduser, exists
import shlex
import subprocess
import sys
from signal import signal, SIGINT, SIGTERM


class SSHConfigError(Exception):
    """Raised when SSH config is missing or has no valid hosts."""
    pass


class ISSH:

    def __init__(self, screen):
        signal(SIGINT, self.shutdown)
        signal(SIGTERM, self.shutdown)

        self.hosts = list()
        self.ssh_config_path = environ.get('ISSH_CONFIG', join(expanduser("~"), ".ssh", "config"))
        self.check_if_ssh_config_exists()
        self.load_ssh_hosts()
        if not self.hosts:
            raise SSHConfigError('No SSH hosts found in ' + self.ssh_config_path)
        self.active_choice = 0

        self.screen = screen
        self.screen.keypad(1)
        curses.curs_set(0)
        curses.noecho()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def check_if_ssh_config_exists(self):
        if not exists(self.ssh_config_path):
            raise SSHConfigError('No SSH config file detected at ' + self.ssh_config_path)

    def load_ssh_hosts(self):
        self.hosts = list()
        with open(self.ssh_config_path, encoding='utf-8') as ssh_config:
            for line in ssh_config.readlines():
                line = line.rstrip()
                if len(line) == 0 or line[0] == ' ' or line[0] == '\t' or line.lstrip()[0] == '#' or line.find("*") > -1:
                    continue
                try:
                    self.hosts.append(line.split()[1])
                except IndexError:
                    pass  # Skip malformed lines
        self.hosts.sort()

    def run(self):
        self.input_loop()

    def print_options(self):
        self.screen.clear()
        num_header_rows = 2
        self.screen.addstr(0, 0, "Select an SSH host (Press H for help):")

        for i, host in enumerate(self.hosts[self.active_choice:]):
            try:
                if i == 0:
                    self.screen.addstr(i + num_header_rows, 0, f" > {host}", curses.color_pair(1) | curses.A_BOLD)
                else:
                    self.screen.addstr(i + num_header_rows, 0, f"   {host}")
            except curses.error:
                # Stop rendering if list is longer than window
                break
        self.screen.refresh()

    def input_loop(self):
        while True:
            self.print_options()

            char_ord = self.screen.getch()
            char = chr(char_ord) if 0 <= char_ord < 256 else ''

            if char_ord == curses.KEY_DOWN or char.upper() == 'J':  # Down or J
                if self.active_choice < len(self.hosts) - 1:
                    self.active_choice += 1
            elif char_ord == curses.KEY_UP or char.upper() == 'K':  # Up or K
                if self.active_choice > 0:
                    self.active_choice -= 1
            elif char_ord == curses.KEY_RIGHT or char_ord == curses.ascii.LF or char.upper() == 'L':  # Right, Enter or L
                self.connect_to_host()
            elif char_ord == curses.ascii.ESC or char.upper() == 'Q':  # Esc or Q
                self.shutdown()
            elif char == 'g':  # Move to top
                self.active_choice = 0
            elif char == 'G':  # Move to last item
                self.active_choice = len(self.hosts) - 1
            elif char.upper() == 'E':
                self.launch_editor()
            elif char.upper() == 'R':  # Refresh screen
                self.load_ssh_hosts()
            elif char.upper() == 'H':  # Print help screen
                self.print_help_screen()

    def connect_to_host(self):
        """Connect to selected host and return to menu when done."""
        self.cleanup_curses()
        subprocess.run(["ssh", self.hosts[self.active_choice]])
        self.reinit_curses()

    def cleanup_curses(self):
        self.screen.keypad(0)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()

    def reinit_curses(self):
        self.screen.keypad(1)
        curses.curs_set(0)
        curses.noecho()

    def shutdown(self, signum=None, frame=None):
        self.cleanup_curses()
        sys.exit(0)

    def launch_editor(self):
        editor = environ.get('EDITOR')
        if editor is None:  # Default editors
            if sys.platform == 'win32':
                editor = 'notepad.exe'
            elif sys.platform == 'darwin':
                editor = 'nano'
            elif 'linux' in sys.platform:
                editor = 'vi'
        editor_cmd = shlex.split(editor) + [self.ssh_config_path]
        subprocess.run(editor_cmd)
        self.load_ssh_hosts()  # Reload hosts after changes

    def print_help_screen(self):
        self.screen.clear()

        self.screen.addstr(0, 0, "Help information:")
        self.screen.addstr(2, 0, "  H - This help screen")
        self.screen.addstr(3, 0, "  Q or ESC - Quit the program")
        self.screen.addstr(4, 0, "  E - Edit SSH config file")
        self.screen.addstr(5, 0, "  R - Reload SSH hosts from config file")
        self.screen.addstr(6, 0, "  Down or J - Move selection down")
        self.screen.addstr(7, 0, "  Up or K - Move selection up")
        self.screen.addstr(8, 0, "  Right or L or Enter - SSH to current selection")
        self.screen.addstr(9, 0, "  G - Move to last item")
        self.screen.addstr(10, 0, "  g - Move to first item")
        self.screen.addstr(12, 0, "Press any key to continue")

        # Wait for any key press
        self.screen.getch()


def main_wrapper(main_screen):
    issh = ISSH(main_screen)
    issh.run()


def main():
    try:
        curses.wrapper(main_wrapper)
    except SSHConfigError as e:
        print(str(e) + '. Aborting.')
        sys.exit(1)


if __name__ == '__main__':
    main()
