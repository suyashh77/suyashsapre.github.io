"""
Spotify vs Local Music Library Comparator

This script compares a Spotify playlist with your local music library.
It identifies tracks that are in your Spotify playlist but missing in your local files,
then creates a new Spotify playlist containing those missing tracks.

Author: Your Name
License: MIT
"""

import os
import logging
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mutagen.easyid3 import EasyID3
from rapidfuzz import fuzz, process

# ==============================
# CONFIGURATION
# ==============================
load_dotenv()  # Load .env file if present

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/")
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"

# Change these for your setup
LOCAL_MUSIC_DIR = os.getenv("LOCAL_MUSIC_DIR", r"C:\Users\Example\Music")
SPOTIFY_PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# ==============================
# AUTHENTICATION
# ==============================
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE
))

# ==============================
# STEP 1: GET SONGS FROM SPOTIFY PLAYLIST
# ==============================
def get_spotify_tracks(playlist_id):
    """Retrieve all track names from a Spotify playlist."""
    results = sp.playlist_items(playlist_id, additional_types=['track'])
    tracks = []

    while results:
        for item in results['items']:
            track = item['track']
            if track:
                name = track['name']
                artist = track['artists'][0]['name']
                tracks.append(f"{artist} - {name}")
        results = sp.next(results) if results['next'] else None

    logging.info(f"Fetched {len(tracks)} tracks from Spotify playlist.")
    return tracks

# ==============================
# STEP 2: GET SONGS FROM LOCAL FILES
# ==============================
def get_local_tracks(music_dir):
    """Retrieve track metadata from local music files."""
    local_tracks = []
    for root, _, files in os.walk(music_dir):
        for file in files:
            if file.lower().endswith((".mp3", ".flac", ".wav")):
                filepath = os.path.join(root, file)
                try:
                    meta = EasyID3(filepath)
                    artist = meta.get("artist", ["Unknown"])[0]
                    title = meta.get("title", [file])[0]
                    local_tracks.append(f"{artist} - {title}")
                except Exception:
                    local_tracks.append(file)  # fallback to filename
    logging.info(f"Found {len(local_tracks)} local tracks.")
    return local_tracks

# ==============================
# STEP 3: COMPARE TRACK LISTS
# ==============================
def find_missing_tracks(spotify_tracks, local_tracks, threshold=80):
    """Find tracks from Spotify playlist that are missing in local library."""
    missing = []
    for sp_song in spotify_tracks:
        match = process.extractOne(sp_song, local_tracks, scorer=fuzz.token_sort_ratio)
        if not match or match[1] < threshold:
            missing.append(sp_song)

    logging.info(f"Identified {len(missing)} missing tracks.")
    return missing

# ==============================
# STEP 4: CREATE NEW SPOTIFY PLAYLIST
# ==============================
def create_missing_playlist(missing_tracks):
    """Create a new Spotify playlist with missing songs."""
    if not missing_tracks:
        logging.info("No missing tracks to add.")
        return None

    user_id = sp.me()['id']
    new_playlist = sp.user_playlist_create(user_id, "Missing Songs", public=False)
    uris = []

    for item in missing_tracks:
        results = sp.search(q=item, type="track", limit=1)
        if results['tracks']['items']:
            uris.append(results['tracks']['items'][0]['uri'])

    if uris:
        sp.playlist_add_items(new_playlist['id'], uris)
        logging.info(f"Created new playlist with {len(uris)} missing tracks!")
    else:
        logging.warning("No URIs found for missing tracks.")

    return new_playlist

# ==============================
# MAIN EXECUTION
# ==============================
if __name__ == "__main__":
    spotify_tracks = get_spotify_tracks(SPOTIFY_PLAYLIST_ID)
    local_tracks = get_local_tracks(LOCAL_MUSIC_DIR)
    missing_tracks = find_missing_tracks(spotify_tracks, local_tracks)
    create_missing_playlist(missing_tracks)
