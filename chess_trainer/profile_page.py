from PyQt5.QtWidgets import QMainWindow, QMessageBox, QDialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from . import database
from .auth import hash_password, verify_password
from .ui.profile_ui import Ui_Form  # profile_ui.py'den import
from .ui.password_change_ui import Ui_Dialog  # password_change_ui.py'den import

class PasswordChangeDialog(QDialog, Ui_Dialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.username = username
        self.changeButton.clicked.connect(self.change_password)
        self.cancelButton.clicked.connect(self.reject)

    def change_password(self):
        old_password = self.oldPasswordEdit.text()
        new_password = self.newPasswordEdit.text()

        if not new_password.strip():
            QMessageBox.warning(self, "Hata", "Yeni şifre boş olamaz.")
            return

        conn = database.connect()
        cursor = conn.cursor()

        try:
            # Veritabanından şifreyi çek
            cursor.execute('SELECT password FROM users WHERE username=?', (self.username,))
            result = cursor.fetchone()

            if result:
                stored_password = result[0]
                # Şifreyi kontrol et
                if verify_password(old_password, stored_password):
                    cursor.execute('UPDATE users SET password=? WHERE username=?',
                                   (hash_password(new_password), self.username))
                    conn.commit()
                    QMessageBox.information(self, "Başarılı", "Şifre başarıyla değiştirildi.")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Hata", "Eski şifre yanlış.")
            else:
                QMessageBox.warning(self, "Hata", "Kullanıcı bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Bir hata oluştu: {e}")
        finally:
            conn.close()


class ProfilePage(QMainWindow, Ui_Form):
    def __init__(self, username):
        super().__init__()
        self.setupUi(self)
        self.username = username
        self.load_user_data()
        self.updateButton.clicked.connect(self.update_user_data)
        self.plot_elo_history()
        self.plot_study_elo_history()
        self.load_game_statistics()
        self.changePasswordButton.clicked.connect(self.open_password_change_dialog)
        self.geriDonButon.clicked.connect(self.goBack)

    def load_user_data(self):
        conn = database.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT username, name, surname FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            username, name, surname = result
            self.usernameEdit.setText(username)
            self.nameEdit.setText(name)
            self.surnameEdit.setText(surname)
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı bulunamadı")

    def update_user_data(self):
        new_username = self.usernameEdit.text().strip()
        new_name = self.nameEdit.text().strip()
        new_surname = self.surnameEdit.text().strip()

        if not new_username:
            QMessageBox.warning(self, "Hata", "Kullanıcı adı boş olamaz")
            return

        conn = database.connect()
        cursor = conn.cursor()

        try:
            if new_username != self.username:
                cursor.execute('SELECT 1 FROM users WHERE username=?', (new_username,))
                if cursor.fetchone():
                    QMessageBox.warning(self, "Hata", "Kullanıcı adı zaten kayıtlı!")
                    return
            cursor.execute('UPDATE users SET username=?, name=?, surname=? WHERE username=?', 
                           (new_username, new_name, new_surname, self.username))
            conn.commit()
            QMessageBox.information(self, "Başarılı", "Kullanıcı bilgileri güncellendi")

            if new_username != self.username:
                self.username = new_username

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Bir hata oluştu: {e}")

        finally:
            conn.close()

    def plot_elo_history(self):
        conn = database.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT eloHistory FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        elo_history = database.parse_int_list(result[0]) if result else []

        fig = Figure()
        ax = fig.add_subplot()
        ax.plot(elo_history, marker='o')
        ax.set_title("ELO History")
        ax.set_xlabel("Game Number")
        ax.set_ylabel("ELO")

        canvas = FigureCanvas(fig)
        self.eloLayout.addWidget(canvas)

    def plot_study_elo_history(self):
        conn = database.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT studyEloHistory FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        study_elo_history = database.parse_int_list(result[0]) if result else []

        fig = Figure()
        ax = fig.add_subplot()
        ax.plot(study_elo_history, marker='o')
        ax.set_title("Study ELO History")
        ax.set_xlabel("Puzzle Number")
        ax.set_ylabel("Study ELO")

        canvas = FigureCanvas(fig)
        self.puzzleLayout.addWidget(canvas)

    def load_game_statistics(self):
        conn = database.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username=?', (self.username,))
        user_id_result = cursor.fetchone()
        if not user_id_result:
            conn.close()
            return

        user_id = user_id_result[0]

        cursor.execute('SELECT COUNT(*), COALESCE(SUM(CASE WHEN sonuc=1 THEN 1 ELSE 0 END), 0), COALESCE(SUM(CASE WHEN sonuc=-1 THEN 1 ELSE 0 END), 0) FROM games WHERE userId=?', (user_id,))
        result = cursor.fetchone()
        total_games = result[0]
        total_wins = result[1]
        total_losses = result[2]
        win_rate = (total_wins / total_games) * 100 if total_games > 0 else 0

        cursor.execute('SELECT completedStudies, incorrectStudies FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        completed_puzzles = len(database.split_ids(result[0]))
        incorrect_puzzles = len(database.split_ids(result[1]))
        total_puzzles = completed_puzzles + incorrect_puzzles
        success_rate = (completed_puzzles / total_puzzles) * 100 if total_puzzles > 0 else 0

        self.gamesPlayed.setText("Toplam oyun: "+str(total_games))
        self.gamesWon.setText("Kazanılan: "+str(total_wins))
        self.winRate.setText("Oran: "+f"{win_rate:.2f}%")
        self.puzzlesTotal.setText("Toplam soru: "+str(total_puzzles))
        self.puzzlesSuccess.setText("Çözülen: "+str(completed_puzzles))
        self.puzzleSuccessRate.setText("Oran: "+f"{success_rate:.2f}%")

        conn.close()

    def open_password_change_dialog(self):
        dialog = PasswordChangeDialog(self.username, self)
        dialog.exec_()

    def goBack(self):
        self.close()
        from .game import ChessApp
        self.main_window = ChessApp(self.username)  # Kullanıcı adını ChessApp'e geçir
        self.main_window.show()
