import os
import re
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius
from dotenv import load_dotenv
from thefuzz import fuzz, process

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

# for track_dict in tracklist:

#   song = genius.search_song(track_dict['name'], track_dict['artist'])

#   if song:
#     cleaned_lyrics = clean_lyrics(song.lyrics)
#     track_dict['lyrics'] = cleaned_lyrics
#   else:
#     track_dict['lyrics'] = None

# with open('playlist-tracks', 'w') as fout:
#   json.dump(tracklist, fout)


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

search_query = "I ain't been in my feelings"
matches = search_by_lyrics(search_query)

for match in matches:

  print(f"{match['name']} by {match['artist']} (score: {match['score']})")

# print(process.extract(lyric), playlist_tracks_file, limit=3, scorer=fuzz.token_sort_ratio)