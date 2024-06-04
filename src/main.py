import logging

from gui import MainWindow

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = MainWindow()
    app.root.mainloop()
