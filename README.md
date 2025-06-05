
# 🎵 Music Player App – Technical Documentation

## Overview

This project is a desktop music player application built using **Python**, **PyQt6** for GUI, and **VLC Python bindings** for audio playback. It provides a smooth user experience for playing local music tracks with a dark-themed, Spotify-like interface.

- **Primary file**: `app.py`  
- **Dependencies**: PyQt6, python-vlc, json, os, threading  
- **Data location**: Track metadata is stored in `config/song.json`; actual audio files are in the `music/` folder.  
- **Main developer**: AkanoSz2

---

## Application Architecture

### 1. `MusicPlayerWindow(QMainWindow)`
- Main application window.
- Contains a `QStackedWidget` with two pages:
  - `MusicPlayerPage`: The actual music player UI.
  - `DownloadPage`: A placeholder UI with a joke message.
- Sets up icon, theme, dimensions, and layout.

### 2. `MusicPlayerPage(QWidget)`
Handles:
- Track loading and filtering  
- VLC media player setup and control  
- Interactive tracklist UI  
- Playback controls (buttons and keyboard)  
- UI updates based on player events  

### 3. `DownloadPage(QWidget)`
- Simple page with a back button  
- Displays a joke message about broken YouTube download feature  
- Demonstrates navigation using `QStackedWidget`  

---

## 🎧 Features

### Playback
- Play/pause, next, previous  
- Highlight currently playing track  
- Progress bar updates in real time  
- Displays current and total track time  
- Uses `vlc` backend for audio

### UI
- Custom-designed dark theme with hover effects  
- Responsive layout using Qt's layout managers  
- Left-aligned table headers  
- Real-time search bar toggle  
- Filter by "Type" (Static, Normal, All)

### Keyboard Navigation

| Key     | Action                   |
|---------|--------------------------|
| Enter   | Play/pause selected track |
| →       | Play next track          |
| ←       | Play previous track      |
| Space   | Toggle play/pause        |

### Tracklist Table
- Displays: `#`, `Title`, `Type`, `Duration`  
- Loaded from `song.json`, displayed with `QTableWidget`  
- Alphabetical sort  
- Hover effects highlight row

### 🎮 Filtering
- Click “Type” column to open custom QMenu  
- Filter songs by type (Static/Normal)  
- Table updates and remaps track index

---

## ⚠️ Current Issues

### YouTube & `pytube`
YouTube often breaks tools like `pytube`, making it hard to download music directly.

### Alternative Script
Instead, use a helper script to add your own `.mp3` or `.m4a` files to the app.

It does the following:
1. Asks where your music files are
2. Finds `.mp3`/`.m4a` files in that folder
3. Copies them into the `music/` directory
4. Reads how long each track is
5. Asks you to pick a type: Static, Normal, or Unknown
6. Saves the info into `config/song.json`

---

## 🧾 Data Format

Example `config/song.json` entry:
```json
{
  "name": "Lo-fi Chill",
  "filename": "lofi-chill.mp3",
  "type": "Static",
  "duration": 134
}
```

### Track Filtering Logic
- Filters songs by type  
- Sorts them alphabetically  
- Remaps them to table rows

---

## 🚨 Warnings

- **Thread Safety**: App may misbehave if buttons are spammed  
- **Crash**: Can exit with code `-1073740791` under heavy load  
- **Download feature**: Just a joke — not implemented

---

## 🚀 How To Run

1. Make sure Python 3.8+ is installed  
2. Install dependencies:
    ```bash
    pip install PyQt6 python-vlc
    ```
3. Put your music files in the `music/` folder  
4. Update `config/song.json` accordingly  
5. Run the app:
    ```bash
    python app.py
    ```

---

## 🤖 Developer Tips

- Filtered index ≠ original index in JSON  
- Playback uses filtered list but reads from full data  
- Use `highlight_current_track()` after play to sync UI  
- UI reacts to VLC events  
- You can expand `DownloadPage` later using tools like `yt-dlp`

---

## 💡 Future Changes

- Add real download logic via `yt-dlp`  
- Playlist save/load  
- Volume/mute support  
- Drag-and-drop for new music  
- Save last played song  
- Add system tray or mini-player mode

---

## 🎓 Credits

Developed by **AkanoSz2** — inspired by modern music apps, but designed to be lightweight and local.

---

## ✨ Final Thoughts

This project shows how you can use **PyQt6** and **VLC** together to build a sleek, customizable music player for the desktop.

---

## 📁 Extra Info

- GitHub Repository: https://github.com/AkanoSz2/MusicApp
