########### WARNING: THREAD-SAFETY ISSUE ################
#                                                       #
#  Avoid excessive keybinding modifications!            #
#  Avoid excessive mouse/keyboard spamming !            #
#  Code not fully optimized for multi-threading, yet.   #
#                                                       #
#                                                       #
#  May crash with:                                      #
#  -1073740791 (0xC0000409)                             #
#                                                       #
#########################################################


import json
import os
import threading
import vlc
import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QSlider,
    QLineEdit, QPlainTextEdit, QStackedWidget, QStyleOptionHeader, QStyle, QComboBox, QMenu,
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu
)
from PyQt6.QtGui import (
    QMovie, QIcon, QPixmap, QFont, QColor, QPainter, QBrush, QKeyEvent
)
from PyQt6.QtCore import Qt, QSize, QObject, QEvent, QPoint, QMetaObject, QTimer

CONFIG_JSON_PATH = "config/song.json"
MUSIC_FILE_PATH = 'music/'

class LeftAlignedHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def paintSection(self, painter, rect, logicalIndex):
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = rect
        option.section = logicalIndex
        option.textAlignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        option.text = self.model().headerData(logicalIndex, self.orientation(), Qt.ItemDataRole.DisplayRole)

        style = self.style()
        style.drawControl(QStyle.ControlElement.CE_Header, option, painter, self)

class HoverableTable(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.hovered_row = -1

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            if self.hovered_row != index.row():
                self.hovered_row = index.row()
                self.viewport().update()
        else:
            if self.hovered_row != -1:
                self.hovered_row = -1
                self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_row != -1:
            self.hovered_row = -1
            self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.hovered_row < 0:
            return

        painter = QPainter(self.viewport())
        rect = self.visualRect(self.model().index(self.hovered_row, 0))
        rect.setLeft(0)
        rect.setWidth(self.viewport().width())
        hover_color = QColor(60, 60, 60, 120)
        painter.fillRect(rect, QBrush(hover_color))
        painter.end()

class DownloadPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Back button
        back_button = QPushButton("← Back to Player")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border: none;
                padding: 5px;
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        back_button.clicked.connect(self.switch_to_player)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Placeholder message
        message = QLabel("Youtube messed up the library :)")
        message.setStyleSheet("color: white; font-size: 16px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

    def switch_to_player(self):
        player_page = self.parent_window.stacked_widget.widget(0)  # MusicPlayerPage
        if hasattr(player_page, "reload_tracks"):
            player_page.reload_tracks()
        self.parent_window.stacked_widget.setCurrentIndex(0)

class MusicPlayerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # VLC player setup - create instance with quiet options to reduce spam
        try:
            self.vlc_instance = vlc.Instance('--quiet', '--no-video-title-show', '--no-stats')
            self.player = self.vlc_instance.media_player_new()
            if not self.player:
                raise Exception("Failed to create VLC player instance")
        except Exception as e:
            print("VLC initialization failed:", e)

        self.setup_ui()

        self.tracks = self.load_tracks()
        self.current_track_index = 0

        self.table.cellDoubleClicked.connect(self.play_selected_track)

        self.is_playing = False

        self.table.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # # Hook keys
        # keyboard.add_hotkey('enter', self.handle_enter_key)
        # keyboard.add_hotkey('right', self.handle_right_key)
        # keyboard.add_hotkey('left', self.handle_left_key)
        # keyboard.add_hotkey('space', self.handle_space_key)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Top controls (search, download) same as your original...
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)
        controls_layout.addStretch()

        self.search_icon_btn = QPushButton()
        self.search_icon_btn.setIcon(QIcon("icons/search.png"))
        self.search_icon_btn.setIconSize(QSize(30, 30))
        self.search_icon_btn.setFixedSize(30, 30)
        self.search_icon_btn.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: transparent; }
        """)
        self.search_icon_btn.clicked.connect(self.show_search_input)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedHeight(30)
        self.search_input.setVisible(False)
        self.search_input.setMinimumWidth(0)
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #222;
                border: 1px solid #555;
                border-radius: 5px;
                color: white;
                padding-left: 8px;
            }
        """)
        controls_layout.addWidget(self.search_input)

        self.download_btn = QPushButton()
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setMinimumWidth(20)
        self.download_btn.setIcon(QIcon("icons/download.png"))
        self.download_btn.setIconSize(QSize(30, 30))
        self.download_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
                transition: background-color 0.3s ease;
            }
        """)
        self.download_btn.clicked.connect(self.switch_to_download)
        controls_layout.addWidget(self.download_btn)

        # main_layout.addWidget(controls_widget)

        # Playlist info container (cover + info) as in your code
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(20)

        cover_label = QLabel()
        cover_pixmap = QPixmap("icons/arturia.png")
        if cover_pixmap.isNull():
            cover_pixmap = QPixmap(160, 160)
            cover_pixmap.fill(QColor("#333333"))
        else:
            cover_pixmap = cover_pixmap.scaled(160, 160,
                                               Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)
        cover_label.setPixmap(cover_pixmap)
        cover_label.setFixedSize(160, 160)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        info_text_layout = QVBoxLayout()
        info_text_layout.setSpacing(4)

        playlist_type = QLabel("Music Player")
        playlist_type.setStyleSheet("color: #B3B3B3;")
        playlist_type.setFont(QFont("Arial", 9))
        # info_text_layout.addWidget(playlist_type)

        playlist_title = QLabel("What's on yo mind?")
        playlist_title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        info_text_layout.addWidget(playlist_title)

        playlist_description = QLabel("A collection of mellow, laid-back tracks to relax to.")
        playlist_description.setStyleSheet("color: #B3B3B3;")
        playlist_description.setFont(QFont("Arial", 11))
        playlist_description.setWordWrap(True)
        info_text_layout.addWidget(playlist_description)

        self.creator_label = QLabel("By AkanoSz2 • loading songs...")
        self.creator_label.setStyleSheet("color: #B3B3B3;")
        self.creator_label.setFont(QFont("Arial", 9))
        info_text_layout.addWidget(self.creator_label)
        self.update_creator_label()

        info_layout.addWidget(cover_label)
        info_layout.addLayout(info_text_layout)

        main_layout.addWidget(info_container)

        # Tracklist Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Title", "Type", "Duration"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 80)

        # Add this line for header text alignment:
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: white;
                gridline-color: transparent;
                border: none;
                outline: none;
            }
            QHeaderView::section {
                background-color: #121212;
                color: #B3B3B3;
                border: none;
                border-bottom: 1px solid #282828;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QTableWidget::item {
                border: none;
                padding: 12px 8px;
            }
            QTableWidget::item:selected {
                background-color: #000;
                color: white;
            }
        """)

        self.type_filter_menu = QMenu(self)
        self.type_filter_menu.setStyleSheet("""
            QMenu {
                border: 1px solid white;
                background-color: #121212;  /* your dark background */
                color: white;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #000000;
            }
        """)


        for type_option in ["All", "Static", "Normal"]:
            action = self.type_filter_menu.addAction(type_option)
            action.triggered.connect(lambda checked, t=type_option: self.filter_by_type(t))

        # Connect the header click signal
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)

        sample_tracks = self.load_tracks()
        self.table.setRowCount(len(sample_tracks))
        for row, track in enumerate(sample_tracks):
            for col, item in enumerate(track):
                table_item = QTableWidgetItem(item)
                table_item.setFlags(table_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, table_item)

        main_layout.addWidget(self.table)

        # Footer Player Controls (progress slider, buttons)
        footer_widget = QWidget()
        footer_widget.setStyleSheet("""
            background-color: #181818;
            border-top: 1px solid #282828;
        """)
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        footer_layout.setSpacing(5)

        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(10)

        self.current_time = QLabel("0:00")
        self.current_time.setFont(QFont("Arial", 12))
        self.current_time.setStyleSheet("color: #b3b3b3;")
        progress_layout.addWidget(self.current_time)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #535353;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #b3b3b3;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: none;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)
        progress_layout.addWidget(self.progress_slider)

        self.total_time = QLabel("0:00")
        self.total_time.setFont(QFont("Arial", 8))
        self.total_time.setStyleSheet("color: #b3b3b3;")
        progress_layout.addWidget(self.total_time)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(15)

        controls_layout.addStretch()

        back_btn = QPushButton()
        back_btn.setIcon(QIcon("icons/back.png"))
        back_btn.setIconSize(QSize(30, 30))
        back_btn.setStyleSheet("border:none; color: white;")
        controls_layout.addWidget(back_btn)
        back_btn.clicked.connect(self.play_previous_track)

        self.play_pause_btn = QPushButton()
        self.play_icon = QIcon("icons/play.png")
        self.pause_icon = QIcon("icons/pause.png")

        self.play_pause_btn.setIcon(self.play_icon)
        self.play_pause_btn.setIconSize(QSize(30, 30))
        self.play_pause_btn.setFixedSize(40, 40)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.play_pause_btn)

        forward_btn = QPushButton()
        forward_btn.setIcon(QIcon("icons/next.png"))
        forward_btn.setIconSize(QSize(30, 30))
        forward_btn.setStyleSheet("border:none; color: white;")
        controls_layout.addWidget(forward_btn)
        forward_btn.clicked.connect(self.play_next_track)

        controls_layout.addStretch()

        footer_layout.addLayout(controls_layout)
        footer_layout.addLayout(progress_layout)

        main_layout.addWidget(footer_widget)

        self.installEventFilter(self)

        # VLC event manager to update UI
        self.vlc_events = self.player.event_manager()
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerPlaying, self.on_vlc_playing)
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerPaused, self.on_vlc_paused)
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_vlc_ended)
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.on_vlc_time_changed)

        self.table.setFocus(Qt.FocusReason.OtherFocusReason)

    # --- UI Handlers ---

    def update_creator_label(self):
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                songs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            songs = []

        total_songs = len(songs)
        total_seconds = sum(song.get("duration", 0) for song in songs)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours} hr "
        time_str += f"{minutes} min"

        self.creator_label.setText(f"By AkanoSz2 • {total_songs} songs, {time_str}")

    def handle_header_click(self, logicalIndex):
        if logicalIndex == 2:  # The "Type" column index
            header = self.table.horizontalHeader()
            pos = self.table.mapToGlobal(
                QPoint(header.sectionPosition(logicalIndex), header.height())
            )
            self.type_filter_menu.popup(pos)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj == self.table and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.handle_enter_key()
                print("enter")
                return True
            elif key == Qt.Key.Key_Right:
                self.handle_right_key()
                print("right")
                return True
            elif key == Qt.Key.Key_Left:
                self.handle_left_key()
                print("left")
                return True
            elif key == Qt.Key.Key_Space:
                self.handle_space_key()
                print("space")
                return True

        return super().eventFilter(obj, event)

    def show_search_input(self):
        self.search_icon_btn.setVisible(False)
        self.search_input.setVisible(True)
        self.search_input.setFocus()

    def switch_to_download(self):
        self.parent_window.stacked_widget.setCurrentIndex(1)

    # --- Track List Management ---

    def load_tracks(self, filter_type="All"):
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                songs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        # Filter if needed
        if filter_type != "All":
            filtered = [(i, s) for i, s in enumerate(songs) if s.get("type", "") == filter_type]
        else:
            filtered = list(enumerate(songs))

        # Sort by song name (case insensitive)
        filtered.sort(key=lambda x: x[1].get("name", "").lower())

        tracks = []
        for display_idx, (orig_idx, song) in enumerate(filtered, start=1):
            name = song.get("name", "Unknown")
            type_ = song.get("type", "Unknown")
            duration_sec = song.get("duration", 0)
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"
            # Store original JSON index as well, for playback
            tracks.append((str(display_idx), name, type_, duration_str, orig_idx))

        return tracks

    def reload_tracks(self):
        self.table.setRowCount(0)
        new_tracks = self.load_tracks()
        self.table.setRowCount(len(new_tracks))
        for row, track in enumerate(new_tracks):
            for col, item in enumerate(track):
                table_item = QTableWidgetItem(item)
                table_item.setFlags(table_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, table_item)
        self.tracks = new_tracks

    def filter_by_type(self, selected_type):
        filtered_tracks = self.load_tracks(filter_type=selected_type)
        self.table.setRowCount(0)
        self.table.setRowCount(len(filtered_tracks))
        for row, track in enumerate(filtered_tracks):
            for col, item in enumerate(track):
                table_item = QTableWidgetItem(item)
                table_item.setFlags(table_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, table_item)

        self.tracks = filtered_tracks
        self.current_track_index = 0
        self.highlight_current_track()

    def find_filtered_track_index(self, title):
        normalized_title = title.strip().lower()
        for i, track in enumerate(self.tracks):
            # track[1] is the displayed name in the filtered list
            filtered_title = track[1].strip().lower()
            if filtered_title == normalized_title:
                return i
        return -1

    # --- Track Playback Control ---

    def load_track(self, filtered_index):
        if filtered_index < 0 or filtered_index >= len(self.tracks):
            print("Invalid filtered track index:", filtered_index)
            return

        orig_index = self.tracks[filtered_index][4]  # original JSON index

        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                songs = json.load(f)
            song = songs[orig_index]
            filename = song.get("filename")
            if not filename:
                print(f"No filename found for track {orig_index}")
                return

            full_path = os.path.join(MUSIC_FILE_PATH, filename)
            if not os.path.isfile(full_path):
                print(f"File does not exist: {full_path}")
                return

            media = self.vlc_instance.media_new(full_path)
            if not media:
                print("Failed to create media object")
                return
            else:
                print(f"Currently playing {full_path}")

            self.player.set_media(media)
            if self.player.play() == -1:
                print("Failed to play media")
                return

            self.current_track_index = filtered_index
            self.is_playing = True
            self.play_pause_btn.setIcon(self.pause_icon)
            self.highlight_current_track()

        except Exception as e:
            print("Error loading track:", e)

    def play_selected_track(self, row, column):
        self.current_track_index = row
        self.load_track(row)
        self.highlight_current_track()
        self.is_playing = True
        self.play_pause_btn.setIcon(self.pause_icon)

    def play_track_by_title(self, title):
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                full_songs = json.load(f)
        except Exception as e:
            print("Error loading songs JSON:", e)
            return

        for idx, song in enumerate(full_songs):
            if song.get("name") == title:
                self.load_track(idx)
                return
        print(f"Track '{title}' not found in full songs list.")

    def play_previous_track(self):
        if not self.tracks or self.current_track_index < 0:
            return
        current_title = None
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                full_songs = json.load(f)
            if 0 <= self.current_track_index < len(full_songs):
                current_title = full_songs[self.current_track_index].get("name")
        except Exception as e:
            print("Error reading songs for previous track:", e)
            return

        if current_title is None:
            return

        filtered_pos = self.find_filtered_track_index(current_title)
        if filtered_pos > 0:
            prev_title = self.tracks[filtered_pos - 1][1]
            self.play_track_by_title(prev_title)

    def play_next_track(self):
        if not self.tracks or self.current_track_index < 0:
            return
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                full_songs = json.load(f)
            if 0 <= self.current_track_index < len(full_songs):
                current_title = full_songs[self.current_track_index].get("name")
            else:
                return
        except Exception as e:
            print("Error reading songs for next track:", e)
            return

        filtered_pos = self.find_filtered_track_index(current_title)
        if 0 <= filtered_pos < len(self.tracks) - 1:
            next_title = self.tracks[filtered_pos + 1][1]
            self.play_track_by_title(next_title)

    def toggle_play_pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.play_pause_btn.setIcon(self.play_icon)
        else:
            if not self.player.get_media():
                self.load_track(self.current_track_index)
            else:
                self.player.play()
            self.is_playing = True
            self.play_pause_btn.setIcon(self.pause_icon)

    def highlight_current_track(self):
        # Reset all rows background
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor("#121212"))

        # Highlight the current track
        if 0 <= self.current_track_index < self.table.rowCount():
            for col in range(self.table.columnCount()):
                item = self.table.item(self.current_track_index, col)
                if item:
                    item.setBackground(QColor("#000000"))

            # Clear previous selection and select current row explicitly
            self.table.clearSelection()
            self.table.selectRow(self.current_track_index)

    # --- VLC Event Handlers ---

    def on_vlc_playing(self, event):
        self.is_playing = True
        self.play_pause_btn.setIcon(self.pause_icon)
        length_ms = self.player.get_length()
        if length_ms > 0:
            total_sec = length_ms // 1000
            self.total_time.setText(f"{total_sec // 60}:{total_sec % 60:02d}")
        from PyQt6.QtCore import QMetaObject

        QTimer.singleShot(0, self.highlight_current_track)


    def on_vlc_paused(self, event):
        self.is_playing = False
        self.play_pause_btn.setIcon(self.play_icon)

    def on_vlc_ended(self, event):
        self.is_playing = False
        self.play_pause_btn.setIcon(self.play_icon)
        self.play_next_track()

    def on_vlc_time_changed(self, event):
        current_ms = self.player.get_time()
        total_ms = self.player.get_length()
        if total_ms > 0:
            self.progress_slider.setMaximum(total_ms)
            self.progress_slider.setValue(current_ms)
            current_sec = current_ms // 1000
            self.current_time.setText(f"{current_sec // 60}:{current_sec % 60:02d}")

    def seek(self, position):
        if self.player.is_playing():
            self.player.set_time(position)

    # --- Keyboard and Navigation Handlers ---

    def handle_enter_key(self):
        if not self.isActiveWindow():
            return

        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()

        if self.current_track_index == row and self.player.is_playing():
            self.toggle_play_pause()
        else:
            self.play_selected_track(row, 0)
            self.current_track_index = row

    def handle_right_key(self):
        if not self.isActiveWindow():
            return

        current_row = self.table.currentRow()
        if current_row + 1 < self.table.rowCount():
            new_row = current_row + 1
            self.table.selectRow(new_row)
            self.current_track_index = new_row
            print("Next song:", self.tracks[new_row][1])  # Song title is column 1
            self.load_track(new_row)

    def handle_space_key(self):
        if not self.isActiveWindow():
            return

        self.toggle_play_pause()

    def handle_left_key(self):
        if not self.isActiveWindow():
            return

        current_row = self.table.currentRow()
        if current_row > 0:
            new_row = current_row - 1
            self.table.selectRow(new_row)
            self.current_track_index = new_row
            print("Previous song:", self.tracks[new_row][1])  # Song title is column 1
            self.load_track(new_row)


class MusicPlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Music Player")
        self.setGeometry(200, 100, 400, 600)
        self.setFixedSize(600, 700)  # Make window non-resizable
        self.setStyleSheet("background-color: #121212; color: white;")

        # Set window icon (optional here, since app icon is set globally)
        self.setWindowIcon(QIcon('icons/app_icon.ico'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create stacked widget
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create pages
        self.player_page = MusicPlayerPage(self)
        self.download_page = DownloadPage(self)

        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.player_page)
        self.stacked_widget.addWidget(self.download_page)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application-wide icon here
    app.setWindowIcon(QIcon('icons/app_icon.ico'))
    window = MusicPlayerWindow()
    window.player_page.table.setFocus()
    window.show()
    sys.exit(app.exec())