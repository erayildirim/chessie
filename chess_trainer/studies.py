import chess
from PyQt5.QtWidgets import QMainWindow, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PyQt5.QtGui import QFont, QPixmap
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from . import config, database
from .ui.studies_ui import Ui_MainWindow  # studies_ui.py'den import


class StudiesApp(QMainWindow, Ui_MainWindow):
    def __init__(self, username):
        super().__init__()
        self.setupUi(self)
        self.username = username
        self.board = chess.Board()
        self.cells = {}
        self.rank_labels = []  # Satır etiketleri için liste
        self.file_labels = []  # Sütun etiketleri için liste
        self.piece_to_svg = config.PIECE_TO_SVG
        self.last_move = None  # Son hamleyi saklamak için
        self.move_stack = []  # Geri alma ve ileri alma için hamleleri saklamak için
        self.redo_stack = []  # İleri almak için hamleleri saklamak için
        self.solution_moves = []  # Çözüm hamlelerini saklamak için
        self.puzzle_active = False  # Aktif (henüz sonuçlanmamış) bir soru var mı
        self.current_puzzle_id = None
        self.current_puzzle_rating = None
        self.create_board()

        self.yeniSoruButon.clicked.connect(self.load_next_puzzle)
        self.cozumButon.clicked.connect(self.show_solution)
        self.geriDonButon.clicked.connect(self.goBack)

        self.load_user_rating()

        # Elo graph setup
        self.figure = Figure()
        self.ax = self.figure.add_subplot()
        self.canvas = FigureCanvas(self.figure)
        self.verticalLayout.addWidget(self.canvas)

        self.load_elo_history()
        self.update_elo_graph()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.time_left = 15

    theme1White = 'rgb(253, 253, 219)'
    theme1Black = 'rgb(132, 165, 100)'

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

        for i in range(8):
            rank_label = QLabel(self)
            rank_label.setText(str(8 - i))
            rank_label.setAlignment(Qt.AlignCenter)
            rank_label.setFont(QFont("Arial", 8))
            rank_label.setStyleSheet("color: black; padding-left: 5px;")
            self.gridLayout.addWidget(rank_label, i, 8)
            self.rank_labels.append(rank_label)

        for i in range(8):
            file_label = QLabel(self)
            file_label.setText(chr(97 + i))
            file_label.setAlignment(Qt.AlignCenter)
            file_label.setFont(QFont("Arial", 8))
            file_label.setStyleSheet("color: black;")
            self.gridLayout.addWidget(file_label, 8, i)
            self.file_labels.append(file_label)

        self.update_board()

    def load_next_puzzle(self):
        conn = database.connect()
        cursor = conn.cursor()

        cursor.execute('SELECT completedStudies, incorrectStudies FROM users WHERE username=?', (self.username,))
        row = cursor.fetchone() or ("", "")
        completed_puzzles = set(database.split_ids(row[0]))
        incorrect_puzzles = set(database.split_ids(row[1])) - completed_puzzles

        # Önce hiç denenmemiş, sonra yanlış çözülmüş sorular
        cursor.execute('SELECT id, fen, solution, type, rating FROM studies ORDER BY id')
        puzzles = cursor.fetchall()
        conn.close()
        attempted = completed_puzzles | incorrect_puzzles
        result = next((p for p in puzzles if str(p[0]) not in attempted), None)
        if result is None:
            result = next((p for p in puzzles if str(p[0]) in incorrect_puzzles), None)

        if result:
            puzzle_id, fen, solution, puzzle_type, puzzle_rating = result
            self.current_puzzle_id = puzzle_id
            self.current_puzzle_rating = puzzle_rating
            self.board.set_fen(fen)
            self.last_move = None
            self.move_stack.clear()
            self.redo_stack.clear()
            self.solution_moves = solution.split()
            self.puzzle_active = True
            self.cozum.setText("")
            self.soruTipi.setText(f"Soru tipi: {self.get_puzzle_type_text(puzzle_type)}")
            self.soruRating.setText(f"Soru rating değeri: {puzzle_rating}")
            self.update_board()
            self.update_turn_label()
            self.sonuc.setText("")
            self.ratingDegisimi.setText("")

            # Timer'ı başlat
            self.time_left = 15
            self.kalanSure.setText(str(self.time_left))
            self.timer.start(1000)  # 1 saniye (1000 ms) aralıklarla güncelle

        else:
            self.show_message("Hata", "Çözülmemiş puzzle bulunamadı.")


    def update_timer(self):
        self.time_left -= 1
        self.kalanSure.setText(str(self.time_left))
        if self.time_left <= 0:
            self.timer_expired()

    def finish_puzzle(self, success):
        """Soruyu sonuçlandırır (her soru için yalnızca bir kez puanlanır)."""
        if not self.puzzle_active:
            return
        self.puzzle_active = False
        self.timer.stop()
        if success:
            self.mark_puzzle_as_solved()
        else:
            self.mark_puzzle_as_incorrect()
        self.update_elo(self.current_puzzle_rating, success=success)

    def timer_expired(self):
        if not self.puzzle_active:
            self.timer.stop()
            return
        self.sonuc.setText("Süre doldu")
        self.sonuc.setStyleSheet("color: red;")
        self.finish_puzzle(success=False)
        self.show_message("Zaman Doldu", "Puzzle çözme süresi doldu. Başarısız sayıldınız.")


    def get_puzzle_type_text(self, puzzle_type):
        if puzzle_type == "matein2":
            return "2 hamlede mat"
        elif puzzle_type == "matein3":
            return "3 hamlede mat"
        elif puzzle_type == "matein4":
            return "4 hamlede mat"
        else:
            return puzzle_type

    def update_turn_label(self):
        turn = self.board.fen().split()[1]
        if turn == 'w':
            self.hamleSirasi.setText("Hamle sırası: Beyaz")
        elif turn == 'b':
            self.hamleSirasi.setText("Hamle sırası: Siyah")

    def on_cell_click(self, row, col):
        if not self.puzzle_active:
            return  # Aktif soru yoksa hamle yapılamaz
        pos = self.coord_to_chess_pos(row, col)
        piece = self.board.piece_at(pos)
        self.reset_highlighted_squares()
        if hasattr(self, 'selected_square'):
            move = chess.Move(self.selected_square, pos)
            moving = self.board.piece_at(self.selected_square)
            if moving and moving.piece_type == chess.PAWN and chess.square_rank(pos) in (0, 7):
                move.promotion = chess.QUEEN
            if move in self.board.legal_moves:
                san_move = self.board.san(move)
                gives_mate = self._is_mating(move)
                expected = self.solution_moves[0] if self.solution_moves else None
                if expected and (san_move == expected or gives_mate):
                    self.solution_moves.pop(0)  # İlk hamleyi doğru yapıldıysa listeden çıkar
                    self.animate_move(self.selected_square, pos)
                    self.board.push(move)
                    self.move_stack.append(move)
                    self.redo_stack.clear()  # Yeni hamle yapıldığında redo_stack temizlenir
                    self.last_move = move  # Son hamleyi sakla
                    if gives_mate:
                        self.solution_moves.clear()  # alternatif mat da kabul edilir
                    self.update_board()
                    self.highlight_last_move()  # Son hamleyi vurgula
                    if self.solution_moves:
                        ai_move = self.board.parse_san(self.solution_moves.pop(0))
                        self.board.push(ai_move)
                        self.move_stack.append(ai_move)
                        self.last_move = ai_move
                        self.update_board()
                    if not self.solution_moves:
                        self.sonuc.setText("Tebrikler")
                        self.sonuc.setStyleSheet("color: green;")
                        self.finish_puzzle(success=True)
                        self.show_message("Başarılı", "Tebrikler! Puzzle çözüldü.")
                else:
                    self.sonuc.setText("Başarısız")
                    self.sonuc.setStyleSheet("color: red;")
                    self.finish_puzzle(success=False)
                    self.show_message("Hata", "Yanlış hamle. Çözümü görebilir veya yeni soruya geçebilirsiniz.")
            else:
                self.show_message("Hata", "Geçersiz hamle. Lütfen doğru bir hamle yapın.")
            delattr(self, 'selected_square')
        elif piece and piece.color == self.board.turn:
            self.selected_square = pos
            self.highlight_possible_moves(pos)

    def _is_mating(self, move):
        self.board.push(move)
        try:
            return self.board.is_checkmate()
        finally:
            self.board.pop()

    def _update_id_list(self, column, add=None, remove=None):
        # column yalnızca sabit kod içinden gelir (kullanıcı girdisi değil)
        if column not in ("completedStudies", "incorrectStudies"):
            raise ValueError(column)
        conn = database.connect()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {column} FROM users WHERE username=?', (self.username,))
        row = cursor.fetchone()
        ids = database.split_ids(row[0] if row else "")
        if add is not None and str(add) not in ids:
            ids.append(str(add))
        if remove is not None:
            ids = [i for i in ids if i != str(remove)]
        cursor.execute(f'UPDATE users SET {column}=? WHERE username=?', (','.join(ids), self.username))
        conn.commit()
        conn.close()

    def mark_puzzle_as_solved(self):
        self._update_id_list("completedStudies", add=self.current_puzzle_id)
        self._update_id_list("incorrectStudies", remove=self.current_puzzle_id)

    def mark_puzzle_as_incorrect(self):
        self._update_id_list("incorrectStudies", add=self.current_puzzle_id)

    def show_solution(self):
        if self.solution_moves:
            solution_text = " ".join(self.solution_moves)
            self.cozum.setText(f"Çözüm: {solution_text}")

            self.reset_highlighted_squares()

            for move_san in self.solution_moves:
                try:
                    move = self.board.parse_san(move_san)
                except ValueError:
                    move = None
                    for legal_move in self.board.legal_moves:
                        if self.board.san(legal_move) == move_san:
                            move = legal_move
                            break
                if move:
                    self.board.push(move)
                    self.last_move = move
                    from_square = move.from_square
                    to_square = move.to_square

                    from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
                    to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

                    self.cells[(from_row, from_col)].setStyleSheet('background-color: rgb(255, 223, 186);')
                    self.cells[(to_row, to_col)].setStyleSheet('background-color: rgb(255, 223, 186);')

            if self.puzzle_active:
                self.sonuc.setText("Başarısız")
                self.sonuc.setStyleSheet("color: red;")
            self.solution_moves = []
            self.finish_puzzle(success=False)

        # Timer'ı durdur
        self.timer.stop()

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

    def highlight_last_move(self):
        if self.last_move:
            from_square = self.last_move.from_square
            to_square = self.last_move.to_square

            from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
            to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

            self.cells[(from_row, from_col)].setStyleSheet('background-color: rgb(255, 223, 186);')
            self.cells[(to_row, to_col)].setStyleSheet('background-color: rgb(255, 223, 186);')

    def show_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def animate_move(self, from_square, to_square):
        from_row, from_col = 7 - chess.square_rank(from_square), chess.square_file(from_square)
        to_row, to_col = 7 - chess.square_rank(to_square), chess.square_file(to_square)

        piece_label = self.cells[(from_row, from_col)]
        target_label = self.cells[(to_row, to_col)]

        # Mevcut pozisyonu al
        start_rect = piece_label.geometry()
        start_pos = start_rect.center()

        # Hedef pozisyonu hesapla
        end_rect = target_label.geometry()
        end_pos = end_rect.center()

        # Geçici QLabel oluştur
        temp_label = QLabel(self)
        temp_label.setPixmap(piece_label.pixmap())
        temp_label.setGeometry(start_rect)
        temp_label.resize(60, 60)  # Taş boyutunu ayarla
        temp_label.move(start_pos - QPoint(temp_label.width() // 2, temp_label.height() // 2))
        temp_label.raise_()
        temp_label.show()

        # Orijinal kareyi temizle
        piece_label.clear()

        # Hedef kareyi gizle
        target_label.setVisible(False)

        # Animasyon oluştur
        self.animation = QPropertyAnimation(temp_label, b"pos")
        self.animation.setDuration(500)  # Animasyon süresi (milisaniye cinsinden)
        self.animation.setStartValue(QPoint(start_pos.x() - 29, start_pos.y() - 29))  # Taşın merkezi konumunu başlat
        self.animation.setEndValue(QPoint(end_pos.x() - 29, end_pos.y() - 29))  # Taşın merkezi konumunu bitir
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

        # Animasyon tamamlandığında taşları güncelle
        def on_animation_finished():
            target_label.setVisible(True)
            target_label.setPixmap(temp_label.pixmap())
            temp_label.deleteLater()
            self.update_board()

        self.animation.finished.connect(on_animation_finished)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def load_user_rating(self):
        conn = database.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT studyElo FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        try:
            self.user_elo = int(result[0])
        except (TypeError, ValueError):
            self.user_elo = 1500
        self.rating.setText(f"Ratinginiz: {self.user_elo}")

    def load_elo_history(self):
        conn = database.connect()
        cursor = conn.cursor()

        # Kullanıcının ELO değerini al
        cursor.execute('SELECT studyElo, studyEloHistory FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            elo_history = result[1]

            self.elo_history = database.parse_int_list(elo_history) or [self.user_elo]
        else:
            self.elo_history = [1000]  # Varsayılan değer, eğer kullanıcı bulunamazsa

    def update_elo_graph(self):
        self.ax.clear()
        self.ax.plot(self.elo_history, marker='o', linestyle='-', color='b')
        self.ax.set_title('Elo Rating History')
        self.ax.set_xlabel('Puzzles')
        self.ax.set_ylabel('Elo Rating')
        self.canvas.draw()

    def update_elo(self, puzzle_rating, success):
        old_elo = self.user_elo
        k_factor = 32
        expected_score = 1 / (1 + 10 ** ((puzzle_rating - self.user_elo) / 400))

        if success:
            self.user_elo += k_factor * (1 - expected_score)
        else:
            self.user_elo += k_factor * (0 - expected_score)

        self.user_elo = round(self.user_elo)
        self.rating.setText(f"Ratinginiz: {self.user_elo}")

        if success:
            elo_change_text = f"+{self.user_elo - old_elo}"
            self.ratingDegisimi.setStyleSheet("color: green;")
        else:
            elo_change_text = f"{self.user_elo - old_elo}"
            self.ratingDegisimi.setStyleSheet("color: red;")

        self.ratingDegisimi.setText(elo_change_text)

        conn = database.connect()
        cursor = conn.cursor()

        # studyEloHistory alanını güncellemeden önce mevcut değeri kontrol edilir
        cursor.execute('SELECT studyEloHistory FROM users WHERE username=?', (self.username,))
        result = cursor.fetchone()
        if result and result[0]:
            study_elo_history = result[0] + f",{old_elo}"
        else:
            study_elo_history = str(old_elo)

        cursor.execute('UPDATE users SET studyElo=?, studyEloHistory=? WHERE username=?',
                       (self.user_elo, study_elo_history, self.username))
        conn.commit()
        conn.close()

        self.elo_history.append(self.user_elo)
        self.update_elo_graph()

    def goBack(self):
        self.timer.stop()
        self.close()
        from .game import ChessApp
        self.main_window = ChessApp(self.username)  # Kullanıcı adını ChessApp'e geçir
        self.main_window.show()
