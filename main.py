import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


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

for track_dict in tracklist:
  print(f"name: {track_dict['name']}\nartist: {track_dict['artist']}")
