import json
import os
import shutil
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3

CONFIG_JSON_PATH = "config/song.json"
MUSIC_FILE_PATH = "music/"


def load_songs():
    if os.path.exists(CONFIG_JSON_PATH):
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_songs(songs):
    os.makedirs(os.path.dirname(CONFIG_JSON_PATH), exist_ok=True)
    with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(songs, f, indent=4)


def get_duration(filepath):
    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".m4a":
            audio = MP4(filepath)
        elif ext == ".mp3":
            audio = MP3(filepath)
        else:
            print(f"Unsupported file type for duration: {filepath}")
            return 0
        return int(audio.info.length)
    except Exception as e:
        print(f"Could not get duration for {filepath}: {e}")
        return 0


def get_song_type(song_name):
    while True:
        print(f"\nSelect type for song: {song_name}")
        print("1. Static")
        print("2. Normal")
        print("3. Unknown")
        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            return "Static"
        elif choice == "2":
            return "Normal"
        elif choice == "3":
            return "Unknown"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def main():
    source_dir = input("Enter path to source music directory: ").strip()
    if not os.path.isdir(source_dir):
        print(f"Invalid directory: {source_dir}")
        return

    songs = load_songs()
    existing_files = {song['filename'] for song in songs}

    # Ensure music directory exists
    os.makedirs(MUSIC_FILE_PATH, exist_ok=True)

    # Find supported files in source directory
    source_files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.m4a', '.mp3'))]

    new_songs = []
    for sf in source_files:
        source_file_path = os.path.join(source_dir, sf)

        # Clean filename if needed
        new_name = sf.replace("[SPOTDOWNLOADER.COM]", "").strip()
        dest_file_path = os.path.join(MUSIC_FILE_PATH, new_name)

        # Copy file to music directory
        try:
            shutil.copy2(source_file_path, dest_file_path)
            print(f"Copied '{sf}' to '{dest_file_path}'")
        except Exception as e:
            print(f"Failed to copy '{sf}': {e}")
            continue

        # Add new song if not already in config
        if new_name not in existing_files:
            duration = get_duration(dest_file_path)
            song_name = os.path.splitext(new_name)[0]
            song_type = get_song_type(song_name)

            new_song = {
                "name": song_name,
                "type": song_type,
                "duration": duration,
                "filename": new_name,
                "extension": os.path.splitext(new_name)[1]
            }
            new_songs.append(new_song)
            print(f"Added {song_name} as type '{song_type}' with duration {duration} seconds")

    if new_songs:
        songs.extend(new_songs)
        save_songs(songs)
        print(f"\nAdded {len(new_songs)} new song(s) to the JSON.")
    else:
        print("\nNo new songs found. JSON is up to date.")


if __name__ == "__main__":
    main()