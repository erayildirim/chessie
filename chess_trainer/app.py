import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from . import config, database


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Chess Trainer")
    app.setWindowIcon(QIcon(config.image("logo.png")))
    database.init_db()

    from .login import LoginWindow
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
