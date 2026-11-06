from PyQt5.QtWidgets import QMainWindow, QMessageBox, QLabel
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QPixmap

from . import config, database
from .auth import hash_password, is_hashed, verify_password
from .engine import EngineNotFoundError
from .ui.login_ui import Ui_Form  # login_ui.py'den import


class LoginWindow(QMainWindow, Ui_Form):
    def __init__(self):
        super(LoginWindow, self).__init__()
        self.setupUi(self)

        self.setContentsMargins(0, 0, 0, 0)

        self.girisYapButon.setIcon(QtGui.QIcon(config.image("loginIcon.png")))
        self.girisYapButon.setIconSize(QtCore.QSize(24, 24))

        self.kaydolButon.setIcon(QtGui.QIcon(config.image("registerIcon.png")))
        self.kaydolButon.setIconSize(QtCore.QSize(24, 24))
        self.girisYapButon.clicked.connect(self.handle_login)
        self.kaydolButon.clicked.connect(self.open_register)
        self.passwordEdit.returnPressed.connect(self.handle_login)

        self.logoLabel = QLabel(self)
        pixmap = QPixmap(config.image("logo.png"))
        self.logoLabel.setPixmap(pixmap)
        self.logoLabel.setScaledContents(True)
        self.logoLabel.setFixedSize(200, 200)
        self.logoLabel.move(80, 25)

    def handle_login(self):
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text()
        if not username or not password:
            QMessageBox.warning(self, "Hata", "Geçersiz kullanıcı adı veya şifre")
            return

        conn = database.connect()
        try:
            row = conn.execute('SELECT id, password FROM users WHERE username=?', (username,)).fetchone()
            if row and verify_password(password, row[1]):
                if not is_hashed(row[1]):
                    # Eski sürümden kalan düz metin şifreyi hash'e yükselt
                    conn.execute('UPDATE users SET password=? WHERE id=?', (hash_password(password), row[0]))
                    conn.commit()
                self.accept_login(username)
            else:
                QMessageBox.warning(self, "Hata", "Geçersiz kullanıcı adı veya şifre")
        finally:
            conn.close()

    def accept_login(self, username):
        from .game import ChessApp  # Döngüsel import hatalarını önlemek için burada import ediyoruz
        try:
            self.main_window = ChessApp(username)  # Kullanıcı adını ChessApp'e geçir
        except EngineNotFoundError as e:
            QMessageBox.critical(self, "Stockfish bulunamadı", str(e))
            return
        self.close()
        self.main_window.show()

    def open_register(self):
        from .register import RegisterApp  # Döngüsel import hatalarını önlemek için burada import ediyoruz
        self.register_window = RegisterApp(self)
        self.close()
        self.register_window.show()
