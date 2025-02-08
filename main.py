import os
import re
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius
from dotenv import load_dotenv
from thefuzz import fuzz, process
import random
import asyncio
import sqlite3

load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

genius = Genius(os.getenv("GENIUS_CLIENT_ACCESS_TOKEN"))

def get_playlist_tracks(playlist_id):
  results = sp.playlist_tracks(playlist_id)
  tracks = results['items']

  while results['next']:
    results = sp.next(results)
    tracks.extend(results['items'])

  return tracks
  

def list_tracks(tracks):
  playlist_tracklist = []
   
  for track in tracks:
    track_info = {
      "name": track['track']['name'],
      "artist": track['track']['artists'][0]['name']
    }

    playlist_tracklist.append(track_info)

  return playlist_tracklist


playlist_id = "7ieg8bD3edzzcbwNDu5BEv"
tracklist = list_tracks(get_playlist_tracks(playlist_id))

def clean_lyrics(lyrics):
  cleaned = re.sub(r'^.*?Lyrics', '', lyrics, flags=re.DOTALL).strip()
  
  cleaned = re.sub(r'See .*? LiveGet tickets as low as .*?You might also like', '', cleaned, flags=re.DOTALL).strip()

  cleaned = re.sub(r'\d+Embed.*$', '', cleaned, flags=re.DOTALL).strip()

  cleaned = re.sub(r'\n+', ' ', cleaned).strip()

  cleaned = re.sub(r'[\u2000-\u200F]', ' ', cleaned).strip()

  return cleaned

# for i in range(20, 30):
#   song = genius.search_song(tracklist[i]['name'], tracklist[i]['artist'])

#   if song:
#       cleaned_lyrics = clean_lyrics(song.lyrics)
#       tracklist[i]['lyrics'] = cleaned_lyrics
#   else:
#       tracklist[i]['lyrics'] = None

  # print(f"Cleaned lyrics for {tracklist[i]['name']}:")
  # print(tracklist[i]['lyrics'])

# number of concurrent requests
SEMAPHORE = asyncio.Semaphore(3)

async def fetch_lyrics(track_dict):

  async with SEMAPHORE:
    retries = 0

    cursor = conn.execute("SELECT lyrics FROM lyrics WHERE name = ? AND artist = ?", (track_dict['name'], track_dict['artist']))
    row = cursor.fetchone()

    if row: 
      existing_lyrics = row[0]

      if existing_lyrics:
        print(f"skipping API call for {track_dict['name']} by {track_dict['artist']} (already in DB)")
        return


    while retries < 5:
      await asyncio.sleep(1 + random.uniform(0, 0.5))

      try:
        song = await asyncio.to_thread(genius.search_song, track_dict['name'], track_dict['artist'])

        if song:
          new_lyrics = clean_lyrics(song.lyrics)
        else:
          new_lyrics = None


        if new_lyrics:
          conn.execute("""
                        INSERT INTO lyrics (name, artist, lyrics)
                        VALUES (?, ?, ?)
                        ON CONFLICT(name, artist) DO UPDATE SET lyrics = excluded.lyrics
                    """, (track_dict['name'], track_dict['artist'], new_lyrics))
          print(f"Updated lyrics for {track_dict['name']} by {track_dict['artist']}")
        else:
          print(f"No lyrics found for {track_dict['name']} by {track_dict['artist']}")
        return

      except Exception as e:
        if "429" in str(e):
          retries += 1
          wait_time = 2 ** retries
          print(f"Hit 429 error, retrying in {wait_time} seconds...")
          await asyncio.sleep(wait_time)
        else:
          print(f"Unexpected error: {e}")
          return

async def fetch_all_lyrics(tracklist):
    tasks = [fetch_lyrics(track) for track in tracklist]
    await asyncio.gather(*tasks)
    conn.commit() 

def save_playlist_tracks():
  with open('playlist-tracks', 'w') as fout:
    return json.dump(tracklist, fout, indent=4)

def load_playlist_tracks(file_path):
  with open(file_path, 'r') as fin:
    return json.load(fin)


def search_by_lyrics(lyric, file_path='playlist-tracks'):
  tracklist = load_playlist_tracks(file_path)

  lyrics_dict = {track["lyrics"]: (track["name"], track["artist"]) for track in tracklist if track.get("lyrics")}

  matches = process.extract(lyric, lyrics_dict.keys(), limit=3, scorer=fuzz.partial_ratio)

  results = []
  for match, score in matches:
    song_name, artist = lyrics_dict[match]
    results.append({"name": song_name, "artist": artist, "score": score})

  return results

def print_lyric_matches(matches):
  for match in matches:

    print(f"{match['name']} by {match['artist']} (score: {match['score']})")

def create_table():  
  conn.execute('''CREATE TABLE IF NOT EXISTS lyrics
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name text NOT NULL,
              artist text NOT NULL,
              lyrics text,
              UNIQUE(name, artist))''')


def delete_duplicates():
  conn.execute("""
  DELETE FROM lyrics
  WHERE id NOT IN (
      SELECT id FROM (
          SELECT id, name, artist, lyrics,
                RANK() OVER (
                    PARTITION BY name, artist 
                    ORDER BY 
                        CASE 
                            WHEN lyrics IS NOT NULL AND lyrics <> '' THEN 1
                            ELSE 2 
                        END, id ASC
                ) AS rnk
          FROM lyrics
      ) WHERE rnk = 1
  );
  """)
  conn.commit()

conn = sqlite3.connect('playlist-tracks.db')

create_table()

# asyncio.run(fetch_all_lyrics(tracklist))

# save_playlist_tracks()

cursor = conn.execute("SELECT * from lyrics")

for row in cursor:
  print(row)

conn.close()

# search_query = "bang bang and it's customary"
# matches = search_by_lyrics(search_query)
# print_lyric_matches(matches)
