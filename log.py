import sys
from datetime import datetime
from colorama import Fore, Style, init


class CustomLogger:
    def __init__(self):
        init(autoreset=True)

    def print_colored(self, color, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(color + f"[{timestamp}] " + message + Style.RESET_ALL)

    def info(self, message):
        self.print_colored(Fore.GREEN, f"[INFO] {message}")

    def warning(self, message):
        self.print_colored(Fore.YELLOW, f"[WARNING] {message}")

    def error(self, message):
        self.print_colored(Fore.RED, f"[ERROR] {message}")
        sys.exit(1)


logger = CustomLogger()
