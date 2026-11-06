from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow

from . import database
from .auth import hash_password
from .ui.register_ui import Ui_Form  # register_ui.py'den import

MIN_ELO, MAX_ELO, DEFAULT_ELO = 100, 3500, 1500


class RegisterApp(QMainWindow, Ui_Form):
    def __init__(self, login_window):
        super(RegisterApp, self).__init__()
        self.login_window = login_window
        self.setupUi(self)
        self.kaydolButon.clicked.connect(self.handle_register)
        self.geriDonButon.clicked.connect(self.go_back)

    def handle_register(self):
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        name = self.nameEdit.text().strip()
        surname = self.surnameEdit.text().strip()
        elo_text = self.eloEdit.text().strip()

        # Boş alan kontrolü
        if not username or not password or not name or not surname:
            QtWidgets.QMessageBox.warning(self, 'Hata', 'Lütfen tüm alanları doldurun')
            return

        # ELO kontrolü (boş bırakılırsa varsayılan değer)
        if elo_text:
            try:
                elo = int(elo_text)
            except ValueError:
                elo = None
            if elo is None or not MIN_ELO <= elo <= MAX_ELO:
                QtWidgets.QMessageBox.warning(self, 'Hata', f'ELO {MIN_ELO} ile {MAX_ELO} arasında bir sayı olmalıdır')
                return
        else:
            elo = DEFAULT_ELO

        conn = database.connect()
        try:
            # Kullanıcı adı kontrolü
            if conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
                QtWidgets.QMessageBox.warning(self, 'Hata', 'Kullanıcı adı zaten kayıtlı!')
                return

            # Yeni kullanıcı ekleme (şifre hash'lenerek saklanır)
            conn.execute('''
                INSERT INTO users (username, password, name, surname, elo, eloHistory, studyElo, studyEloHistory, completedStudies, incorrectStudies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, hash_password(password), name, surname, elo, "", elo, "", "", ""))
            conn.commit()
        finally:
            conn.close()

        QtWidgets.QMessageBox.information(self, 'Başarılı', 'Kullanıcı başarıyla kaydedildi')
        self.clear_fields()

    def clear_fields(self):
        self.usernameEdit.clear()
        self.passwordEdit.clear()
        self.nameEdit.clear()
        self.surnameEdit.clear()
        self.eloEdit.clear()

    def go_back(self):
        self.close()
        self.login_window.show()
