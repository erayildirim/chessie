import chess
import chess.engine
import chess.pgn
import requests
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox, QDialog, QPushButton, QTextEdit, QProgressBar, QLineEdit
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, QPoint, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtMultimedia import QSoundEffect

from . import config, database, ai_explainer
from .engine import open_engine, set_engine_elo
from .ui.chess_ui import Ui_MainWindow  # chess_ui.py'den import
from .ui.settings_ui import Ui_Dialog  # settings_ui.py'den import

START_BUTTON_STYLE = """
                QPushButton#baslatButon {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #1B2631, 
                                      stop:0.5 #34495E, 
                                      stop:1 #1B2631);
                    border: 2px solid #1B2631;
                    color: white;
	                border-radius: 10px;
                }
                QPushButton#baslatButon:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                    stop:0 #4CA1AF, 
                                                    stop:0.5 #2C3E50, 
                                                    stop:1 #4CA1AF);
                }

                QPushButton#baslatButon:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                    stop:0 #2C3E50, 
                                                    stop:0.5 #4CA1AF, 
                                                    stop:1 #2C3E50);
                    border: 2px solid #2C3E50;
                    color: white;
                    padding: 5px;
                    border-radius: 10px;
                    font-size: 16px;
                }
            """

class SettingsDialog(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.buttonBox.clicked.connect(self.accept)
        self.comboBox.addItems(["1 dakika", "2 dakika", "3 dakika", "4 dakika", "5 dakika", "10 dakika", "15 dakika", "20 dakika"])

    def get_selected_time(self):
        time_text = self.comboBox.currentText()
        time_value = int(time_text.split()[0])
        return time_value * 60

class Worker(QThread):
    """Runs the (potentially slow) AI request off the UI thread."""
    finished = pyqtSignal(str)

    def __init__(self, board, engine_lines):
        super().__init__()
        self.board = board
        self.engine_lines = engine_lines

    def run(self):
        try:
            response = ai_explainer.explain(self.board, self.engine_lines)
        except Exception as e:
            response = f"Hata: {e}"
        self.finished.emit(response)

class ChessApp(QMainWindow, Ui_MainWindow):
    def __init__(self, username):
        super().__init__()
        self.setupUi(self)
        self.username = username
        self.board = chess.Board()
        self.cells = {}

        self.setFixedSize(1280, 677)

        self.piece_to_svg = config.PIECE_TO_SVG
        self.last_move = None
        self.move_stack = []
        self.redo_stack = []
        self.create_board()
        self.labelWhiteTime.setFont(QFont("Arial", 16))
        self.labelBlackTime.setFont(QFont("Arial", 16))
        self.labelStEvaluation.setFont(QFont("Segoe UI", 12))

        self.fenValue = self.findChild(QLineEdit, 'fenValue')
        self.fenValue.setReadOnly(True)

        self.fenKopyalaButon = self.findChild(QPushButton, 'fenKopyalaButon')
        self.fenKopyalaButon.clicked.connect(self.copy_fen_to_clipboard)

        self.baslatButon = self.findChild(QPushButton, 'baslatButon')
        self.baslatButon.clicked.connect(self.start_game)

        self.aiOneriButon = self.findChild(QPushButton, 'aiOneriButon')
        self.aiOneriButon.clicked.connect(self.show_ai_recommendations)

        self.aiOneriButon2 = self.findChild(QPushButton, 'aiOneriButon2')
        self.aiOneriButon2.clicked.connect(self.explain_position)

        self.motorOneriButon = self.findChild(QPushButton, 'motorOneriButon')
        self.motorOneriButon.clicked.connect(self.show_stockfish_recommendation)

        self.aiOnerileri = self.findChild(QTextEdit, 'aiOnerileri')
        self.aiOnerileri.setReadOnly(True)

        self.motorOneri = self.findChild(QLabel, 'motorOneri')

        self.aiOnerileri2 = self.findChild(QTextEdit, 'aiOnerileri2')
        self.aiOnerileri2.setReadOnly(True)

        self.progressBar = self.findChild(QProgressBar, 'progressBar')
        self.progressBar.setVisible(False)
        
        self.pgn = self.findChild(QTextEdit, 'pgn')
        self.pgn.setReadOnly(True)

        self.pgnKopyalaButon = self.findChild(QPushButton, 'pgnKopyalaButon')
        self.pgnKopyalaButon.clicked.connect(self.copy_pgn_to_clipboard)

        self.ileriButon = self.findChild(QPushButton, 'ileriButon')
        self.ileriButon.clicked.connect(self.redo_move)

        self.geriButon = self.findChild(QPushButton, 'geriButon')
        self.geriButon.clicked.connect(self.undo_move)

        self.puzzleButon = self.findChild(QPushButton, 'puzzleButon')
        self.puzzleButon.clicked.connect(self.openStudies)

        self.initial_white_time = 1000
        self.initial_black_time = 1000
        self.white_time_left = self.initial_white_time
        self.black_time_left = self.initial_black_time
        self.current_turn = 'white'

        self.settingsButton = self.findChild(QPushButton, 'settingsButton')
        self.settingsButton.clicked.connect(self.open_settings)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress_bar)

        self.engine = open_engine()
        self.worker = None

        self.move_sound = QSoundEffect()
        self.move_sound.setSource(QtCore.QUrl.fromLocalFile(config.sound("move.wav")))

        self.aiButtonSound = QSoundEffect()
        self.aiButtonSound.setSource(QtCore.QUrl.fromLocalFile(config.sound("ai.wav")))

        self.profilButon.setIcon(QtGui.QIcon(config.image("profile.png")))
        self.profilButon.setIconSize(QSize(24, 24))
        self.profilButon.clicked.connect(self.openProfilePage)

        self.puzzleButon.setIcon(QtGui.QIcon(config.image("puzzles.png")))
        self.puzzleButon.setIconSize(QSize(24, 24))

        self.load_user_rating()
        self.update_fen_position()
        self.update_pgn()

    theme1White = 'rgb(253, 253, 219)'
    theme1Black = 'rgb(132, 165, 100)'

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            selected_time = dialog.get_selected_time()
            self.initial_white_time = selected_time
            self.initial_black_time = selected_time
            self.reset_board_and_timers()  # Ayar değiştikten sonra tahtayı ve süreleri sıfırla

    def create_board(self):
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        for row in range(8):
            for col in range(8):
                label = QLabel(self)
                label.setFixedSize(80, 80)
                label.setAlignment(Qt.AlignCenter)
                white_rgb = self.theme1White
                black_rgb = self.theme1Black
                color = white_rgb if (row + col) % 2 == 0 else black_rgb
                label.setStyleSheet(f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')
                self.gridLayout.addWidget(label, row, col)
                label.mousePressEvent = lambda event, r=row, c=col: self.on_cell_click(r, c)
                self.cells[(row, col)] = label

        self.update_board()

    def on_cell_click(self, row, col):
        if not self.timer.isActive():
            return  # Oyun başlamadıysa hamle yapılamaz
        pos = self.coord_to_chess_pos(row, col)
        piece = self.board.piece_at(pos)
        self.reset_highlighted_squares()
        if hasattr(self, 'selected_square'):
            move = chess.Move(self.selected_square, pos)
            moving = self.board.piece_at(self.selected_square)
            if moving and moving.piece_type == chess.PAWN and chess.square_rank(pos) in (0, 7):
                move.promotion = chess.QUEEN  # otomatik vezir terfisi
            if move in self.board.legal_moves:
                self.animate_move(self.selected_square, pos)
                self.board.push(move)
                self.move_stack.append(move)
                self.redo_stack.clear()  # Yeni hamle yapıldığında redo_stack temizlenir
                self.last_move = move  # Son hamleyi sakla
                self.current_turn = 'black' if self.current_turn == 'white' else 'white'
                self.update_board()
                self.highlight_last_move()  # Son hamleyi vurgula
                self.update_fen_position()  # FEN pozisyonunu güncelle
                self.update_pgn()  # PGN güncelle
                self.move_sound.play()
                if self.board.is_checkmate():
                    self.on_game_end(success=True)
                elif self.board.is_game_over(claim_draw=True):
                    self.end_game("Oyun Bitti", "Beraberlik!", None)

                else:
                    if self.current_turn == 'black':
                        QTimer.singleShot(500, self.make_ai_move)
            delattr(self, 'selected_square')
        elif piece and piece.color == chess.WHITE:
            self.selected_square = pos
            self.highlight_possible_moves(pos)

    def on_game_end(self, success):
        if success:
            self.end_game("Oyun Bitti", "Tebrikler, kazandınız!", True)
        else:
            self.end_game("Oyun Bitti", "Maalesef, kaybettiniz.", False)


    def undo_move(self):
        if self.board.move_stack:
            move = self.board.pop()
            self.redo_stack.append(move)
            # Oyun sırasında hamle sırası tekrar beyaza (oyuncuya) gelsin
            if self.timer.isActive() and self.board.turn == chess.BLACK and self.board.move_stack:
                self.redo_stack.append(self.board.pop())
            self.after_history_change()
        else:
            QMessageBox.information(self, "Bilgi", "Geri alınacak hamle yok.")

    def redo_move(self):
        if self.redo_stack:
            self.board.push(self.redo_stack.pop())
            if self.timer.isActive() and self.board.turn == chess.BLACK and self.redo_stack:
                self.board.push(self.redo_stack.pop())
            self.after_history_change()
        else:
            QMessageBox.information(self, "Bilgi", "İleri alınacak hamle yok.")

    def after_history_change(self):
        self.current_turn = 'white' if self.board.turn == chess.WHITE else 'black'
        self.last_move = self.board.peek() if self.board.move_stack else None
        self.update_board()
        self.update_fen_position()
        self.update_pgn()
        self.update_evaluation()
        if self.timer.isActive() and self.current_turn == 'black':
            QTimer.singleShot(500, self.make_ai_move)

    def coord_to_chess_pos(self, row, col):
        return chess.square(col, 7 - row)

    def update_board(self):
        for row in range(8):
            for col in range(8):
                piece = self.board.piece_at(self.coord_to_chess_pos(row, col))
                if piece:
                    svg_path = self.piece_to_svg[piece.symbol()]
                    self.set_piece_image(self.cells[(row, col)], svg_path)
                else:
                    self.cells[(row, col)].clear()
                white_rgb = self.theme1White
                black_rgb = self.theme1Black
                color = white_rgb if (row + col) % 2 == 0 else black_rgb
                self.cells[(row, col)].setStyleSheet(
                    f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')
        if self.last_move:
            self.highlight_last_move()

    def set_piece_image(self, label, svg_path):
        pixmap = QPixmap(svg_path)
        label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def highlight_possible_moves(self, square):
        possible_moves = [move.to_square for move in self.board.legal_moves if move.from_square == square]
        for move in possible_moves:
            row, col = 7 - chess.square_rank(move), chess.square_file(move)
            self.cells[(row, col)].setStyleSheet('background-color: rgb(190, 93, 77);')

    def reset_highlighted_squares(self):
        for row in range(8):
            for col in range(8):
                white_rgb = self.theme1White
                black_rgb = self.theme1Black
                color = white_rgb if (row + col) % 2 == 0 else black_rgb
                self.cells[(row, col)].setStyleSheet(
                    f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')
    
    def format_time(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def update_timer(self):
        if self.current_turn == 'white':
            self.white_time_left -= 1
            self.labelWhiteTime.setText(f"{self.format_time(self.white_time_left)}")
            if self.white_time_left == 0:
                self.end_game("Oyun Bitti", "Siyah Kazandı!", success=False)
        else:
            self.black_time_left -= 1
            self.labelBlackTime.setText(f"{self.format_time(self.black_time_left)}")
            if self.black_time_left == 0:
                self.end_game("Oyun Bitti", "Beyaz Kazandı!", success=True)

    def show_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def make_ai_move(self):
        # Oyun bittiyse / pes edildiyse veya sıra motorda değilse hamle yapma
        if not self.timer.isActive() or self.board.turn != chess.BLACK:
            return
        if not self.board.is_game_over():
            result = self.engine.play(self.board, chess.engine.Limit(time=1.0))
            self.board.push(result.move)
            self.move_stack.append(result.move)  # AI hamlesini yığına ekle
            self.last_move = result.move  # Son hamleyi sakla
            self.update_evaluation()
            self.current_turn = 'white'
            self.update_board()
            self.highlight_last_move()  # Son hamleyi vurgula
            self.update_fen_position()  # FEN pozisyonunu güncelle
            self.update_pgn()  # PGN güncelle
            if self.board.is_checkmate():
                self.end_game("Oyun Bitti", "Şah Mat!", success=False)
            elif self.board.is_game_over(claim_draw=True):
                self.end_game("Oyun Bitti", "Beraberlik!", success=None)

    def update_evaluation(self):
        if self.board.is_game_over():
            self.labelStEvaluation.setText("###")
            return
        info = self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
        evaluation = info['score'].relative.score(mate_score=10000)
        if evaluation is not None:
            eval_text = f"{evaluation / 100.0:.2f}"
        else:
            eval_text = "###"
        self.labelStEvaluation.setText(eval_text)

    def set_stockfish_elo(self, elo):
        set_engine_elo(self.engine, elo)

    def highlight_last_move(self):
        if self.last_move:
            from_square = self.last_move.from_square
            to_square = self.last_move.to_square

            from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
            to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

            self.cells[(from_row, from_col)].setStyleSheet('background-color: rgb(255, 223, 186);')
            self.cells[(to_row, to_col)].setStyleSheet('background-color: rgb(255, 223, 186);')

    def update_fen_position(self):
        fen = self.board.fen()
        self.fenValue.setText(fen)

    def update_pgn(self):
        pgn = chess.pgn.Game()
        node = pgn

        for move in self.board.move_stack:
            try:
                node = node.add_variation(move)
            except Exception as e:
                print(f"Error converting move to SAN: {move}, {e}")
                continue

        exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
        pgn_text = pgn.accept(exporter)
        self.pgn.setPlainText(pgn_text)

    def copy_fen_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.fenValue.text())
        QMessageBox.information(self, "Bilgi", "FEN Kopyalandı")

    def copy_pgn_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.pgn.toPlainText())
        QMessageBox.information(self, "Bilgi", "PGN Kopyalandı")

    def start_game(self):
        self.reset_board_and_timers()  # Tahtayı ve süreleri sıfırla
        self.baslatButon.setText("Pes Et")
        self.baslatButon.setStyleSheet("""
        QPushButton {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #ff4e4e, 
                                              stop:0.5 #ff0000, 
                                              stop:1 #ff4e4e);
            color: white;
            border: 2px solid #ff0000;
            border-radius: 10px;
        }
        QPushButton:hover {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #ff9999, 
                                              stop:0.5 #ff4e4e, 
                                              stop:1 #ff9999);
        }
        QPushButton:pressed {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #ff0000, 
                                              stop:0.5 #ff4e4e, 
                                              stop:1 #ff0000);
            border: 2px solid #ff0000;
        }
    """)
        icon_path = config.image("resign.png")
        self.baslatButon.setIcon(QtGui.QIcon(icon_path))
        self.baslatButon.clicked.disconnect()
        self.baslatButon.clicked.connect(self.resign_game)
        self.timer.start(1000)  # Timer'ı başlat


    def resign_game(self):
        reply = QMessageBox.question(self, 'Emin misiniz?', 'Pes etmek istediğinizden emin misiniz?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # end_game butonu "Oyunu Başlat" durumuna geri döndürür
            self.end_game("Oyun Bitti", "Pes ettiniz! Rakibiniz kazandı.", success=False)


    def reset_board_and_timers(self):
        self.board.reset()
        self.last_move = None
        self.move_stack.clear()  # Hamle yığınını temizle
        self.redo_stack.clear()  # İleri alma yığınını temizle
        self.update_board()
        self.white_time_left = self.initial_white_time
        self.black_time_left = self.initial_black_time
        self.labelWhiteTime.setText(f"{self.format_time(self.white_time_left)}")
        self.labelBlackTime.setText(f"{self.format_time(self.black_time_left)}")
        self.current_turn = 'white'
        self.update_fen_position()
        self.update_pgn()  # PGN pozisyonunu sıfırla

    def end_game(self, title, message, success=None):
        self.timer.stop()
        self.show_message(title, message)
        self.baslatButon.setEnabled(True)  # Oyun bitince butonu tekrar aktif et
        self.baslatButon.setText("Oyunu Başlat")
        self.baslatButon.setStyleSheet(START_BUTTON_STYLE)
        icon_path = config.image("play.png")
        self.baslatButon.setIcon(QtGui.QIcon(icon_path))
        self.baslatButon.clicked.disconnect()
        self.baslatButon.clicked.connect(self.start_game)
        self.update_pgn()
    
        # Başarı durumu kontrolü
        if success is not None:
            self.update_elo(success)
        else:
            # Beraberlik durumu
            self.save_game_result(0, self.user_elo)


    def update_elo(self, success):
        old_elo = self.user_elo
        k_factor = 32
        expected_score = 1 / (1 + 10 ** ((self.user_elo - self.user_elo) / 400))

        if success:
            self.user_elo += k_factor * (1 - expected_score)
            self.labelEloChange.setText(f"+{round(self.user_elo - old_elo)}")
            self.labelEloChange.setStyleSheet("""
                QLabel#labelEloChange {
                    border: 2px solid black;
                    border-radius: 5px;
                    padding: 5px;
                    background-color: white;
                    color: green;
                    font: bold 20px;
                    text-align: center;
                }
            """)
        else:
            self.user_elo += k_factor * (0 - expected_score)
            self.labelEloChange.setText(f"{round(self.user_elo - old_elo)}")
            self.labelEloChange.setStyleSheet("""
                QLabel#labelEloChange {
                    border: 2px solid black;
                    border-radius: 5px;
                    padding: 5px;
                    background-color: white;
                    color: red;
                    font: bold 20px;
                    text-align: center;
                }
            """)

        self.user_elo = round(self.user_elo)
        self.labelUserElo.setText(f"ELO: {self.user_elo}")

        conn = database.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT eloHistory FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        if result and result[0]:
            elo_history = result[0] + f",{old_elo}"
        else:
            elo_history = str(old_elo)
        
        cursor.execute('UPDATE users SET elo=?, eloHistory=? WHERE username=?', 
                       (self.user_elo, elo_history, self.username))
        
        conn.commit()
        conn.close()
        
        # Oyunu veritabanına kaydet
        result = 1 if success else -1
        self.save_game_result(result,old_elo)



    def show_ai_recommendations(self):
        """Lichess bulut analizinden en iyi devamı gösterir."""
        try:
            response = requests.get('https://lichess.org/api/cloud-eval',
                                    params={'fen': self.board.fen()}, timeout=10)
        except requests.RequestException:
            self.aiOnerileri.setText("Hata: Lichess API'ya bağlanılamadı.")
            return
        if response.status_code == 200:
            data = response.json()
            if data.get('pvs'):
                best_move = data['pvs'][0]['moves']
                self.aiOnerileri.setText(f"{best_move}")
                self.highlight_best_move(best_move.split()[0])
            else:
                self.aiOnerileri.setText("Öneri bulunamadı.")
        elif response.status_code == 404:
            self.aiOnerileri.setText("Öneri bulunamadı (pozisyon Lichess bulut veritabanında yok).")
        else:
            self.aiOnerileri.setText("Hata: Lichess API'ya bağlanılamadı.")

        self.aiButtonSound.play()

    def explain_position(self):
        """Pozisyonu Stockfish ile analiz edip AI modeline açıklatır."""
        if self.worker is not None and self.worker.isRunning():
            return  # önceki istek hâlâ sürüyor
        board = self.board.copy()
        try:
            lines = [] if board.is_game_over() else ai_explainer.analyse_position(self.engine, board)
        except Exception as e:
            self.aiOnerileri2.setText(f"Motor analizi başarısız: {e}")
            return

        self.aiOneriButon2.setEnabled(False)
        self.aiOnerileri2.setText("Analiz ediliyor...")
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.progress_timer.start(400)

        self.worker = Worker(board, lines)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

        self.highlight_scan_animation(duration=2000)
        self.aiButtonSound.play()

    def update_progress_bar(self):
        current_value = self.progressBar.value()
        if current_value < 80:
            self.progressBar.setValue(current_value + 5)

    def on_worker_finished(self, response):
        self.progress_timer.stop()
        self.progressBar.setValue(100)
        QTimer.singleShot(500, lambda: self.progressBar.setVisible(False))
        self.aiOnerileri2.setText(response)
        self.aiOneriButon2.setEnabled(True)

    def highlight_best_move(self, move, color='rgb(173, 216, 230)'):
        from_square = chess.parse_square(move[:2])
        to_square = chess.parse_square(move[2:4])

        from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
        to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

        self.cells[(from_row, from_col)].setStyleSheet(f'background-color: {color};')
        self.cells[(to_row, to_col)].setStyleSheet(f'background-color: {color};')

    def show_stockfish_recommendation(self):
        if not self.board.is_game_over():
            info = self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
            best_move = info['pv'][0]
            move_uci = best_move.uci()
            self.motorOneri.setText(f"{move_uci}")
            self.highlight_best_move(move_uci, color='rgb(0, 0, 255)')
            self.aiButtonSound.play()

    def animate_move(self, from_square, to_square):
        from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
        to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

        piece_label = self.cells[(from_row, from_col)]
        target_label = self.cells[(to_row, to_col)]

        start_rect = piece_label.geometry()
        start_pos = start_rect.center()

        end_rect = target_label.geometry()
        end_pos = end_rect.center()

        temp_label = QLabel(self)
        temp_label.setPixmap(piece_label.pixmap())
        temp_label.setGeometry(start_rect)
        temp_label.resize(60, 60)
        temp_label.move(start_pos - QPoint(temp_label.width() // 2, temp_label.height() // 2))
        temp_label.raise_()
        temp_label.show()

        piece_label.clear()

        target_label.setVisible(False)

        self.animation = QPropertyAnimation(temp_label, b"pos")
        self.animation.setDuration(500)
        self.animation.setStartValue(QPoint(start_pos.x() - 29, start_pos.y() - 29))
        self.animation.setEndValue(QPoint(end_pos.x() - 29, end_pos.y() - 29))
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

        def on_animation_finished():
            target_label.setVisible(True)
            target_label.setPixmap(temp_label.pixmap())
            temp_label.deleteLater()
            self.update_board()

        self.animation.finished.connect(on_animation_finished)

    def openStudies(self):
        self.close()
        from .studies import StudiesApp
        self.main_window = StudiesApp(self.username)
        self.main_window.show()

    def openProfilePage(self):
        self.close()
        from .profile_page import ProfilePage
        self.main_window = ProfilePage(self.username)
        self.main_window.show()
    
    def closeEvent(self, event):
        self.timer.stop()
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(2000)
        try:
            self.engine.quit()
        except Exception:
            pass
        super().closeEvent(event)

    def load_user_rating(self):
        conn = database.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT elo FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        try:
            self.user_elo = int(result[0])
        except (TypeError, ValueError):
            self.user_elo = 1500

        self.set_stockfish_elo(self.user_elo)
        self.labelUserElo.setText(f"ELO: {self.user_elo}")

    def save_game_result(self, result, old_elo=None):
        if old_elo is None:
            old_elo = self.user_elo
        conn = database.connect()
        cursor = conn.cursor()

        # Kullanıcı ID'sini al
        cursor.execute('SELECT id FROM users WHERE username=?', (self.username,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            return
        user_id = row[0]

        # Oyun verilerini kaydet
        cursor.execute('INSERT INTO games (userId, sonuc, eskiElo, yeniElo, pgn) VALUES (?, ?, ?, ?, ?)', 
                    (user_id, result, old_elo, self.user_elo, self.pgn.toPlainText()))
        conn.commit()
        conn.close()

    def highlight_scan_animation(self, duration):
        colors = [
            "rgb(173, 216, 230)",
            "rgb(187, 230, 243)",
            "rgb(200, 240, 255)",
            "rgb(213, 250, 255)",
            "rgb(225, 255, 255)",
            "rgb(213, 250, 255)",
            "rgb(200, 240, 255)",
            "rgb(187, 230, 243)"
        ]
        interval = duration // (8 * len(colors))
        
        def change_cell_color(row, col, color):
            label = self.cells[(row, col)]
            label.setStyleSheet(f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')

        def reset_cell_color(row, col):
            label = self.cells[(row, col)]
            white_rgb = self.theme1White
            black_rgb = self.theme1Black
            color = white_rgb if (row + col) % 2 == 0 else black_rgb
            label.setStyleSheet(f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')
        
        def animate_row(row):
            if row >= 0:
                for col in range(8):
                    for i, color in enumerate(colors):
                        QTimer.singleShot(i * interval + col * interval, lambda r=row, c=col, clr=color: change_cell_color(r, c, clr))
                    QTimer.singleShot(len(colors) * interval + col * interval, lambda r=row, c=col: reset_cell_color(r, c))
                QTimer.singleShot(len(colors) * interval + 8 * interval, lambda: animate_row(row - 1))
        
        animate_row(7)

    def reset_board_colors(self):
        for row in range(8):
            for col in range(8):
                label = self.cells[(row, col)]
                white_rgb = self.theme1White
                black_rgb = self.theme1Black
                color = white_rgb if (row + col) % 2 == 0 else black_rgb
                label.setStyleSheet(f'background-color: {color}; margin: 0px; padding: 0px; border: 0px;')

if __name__ == "__main__":
    from .app import main
    main()
