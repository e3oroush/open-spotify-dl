import re
import os
import json
import string
import logging
import requests
import youtube_dl
from tqdm import tqdm
from datetime import datetime
from argparse import ArgumentParser

# TODO Bring some usefull comments
# TODO download songs with patterns https://open.spotify.com/track/(.*)

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s: %(asctime)s -'
                    ' %(funcName)s - %(message)s')

log = logging.getLogger('osdl')

remove_punctuation_map = dict((ord(char), None) for char in string.punctuation)

def get_token():
  url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"

  headers = {
    'Accept': 'application/json',
    'spotify-app-version': '1587498528',
    'Cookie': 'sp_t=7153cce27b308aba1128a5a0615e1246; sp_landing=https%3A%2F%2Fopen.spotify.com%2Fget_access_token%3Freason%3Dtransport%26productType%3Dweb_player'
  }

  response = requests.get(url, headers=headers)
  res=response.json()
  return res["accessToken"]

def get_tracks_info(url):
  token=get_token()
  headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}',
    'Cookie': 'sp_t=7153cce27b308aba1128a5a0615e1246'
  }
  response = requests.get(url, headers=headers)
  res = response.json()
  return res

def parse_f(f):
  return {
    "artist_names": [a["name"] for a in f["artists"]], 
    "title": f["name"], 
    "duration_ms": f["duration_ms"], 
    "track_number": f["track_number"] 
  }

def parse_album_info(album,track_id=None):
  tracks=[
    {**parse_f(f)} for f in album["tracks"]["items"] if not track_id or track_id==f["id"]]
  return tracks

def parse_playlist_info(playlist,track_id=None):
  tracks=[
    {**parse_f(f["track"])} for f in playlist.get("tracks",playlist).get("items",[]) if not track_id or track_id==f["track"]["id"]
  ]
  return tracks

def search_youtube(track):
  selected_video_id=None
  now=datetime.now()
  try:
    track_title=track["title"]
    artist=' '.join(track["artist_names"])
    duration_ms = track["duration_ms"]
    query=f"{'+'.join(track_title.split())}+{'+'.join(artist.split())}".replace('"','')
    headers = {
      'x-youtube-ad-signals': 'dt=1586550729813&flash=0&frm&u_tz=270&u_his=4&u_java&u_h=1080&u_w=1920&u_ah=1053&u_aw=1920&u_cd=24&u_nplug=2&u_nmime=2&bc=31&bih=953&biw=1105&brdim=0%2C59%2C0%2C59%2C1920%2C27%2C1920%2C1021%2C1120%2C953&vis=1&wgl=true&ca_type=image',
      'x-youtube-client-name': '1',
      'x-youtube-page-label': f'youtube.ytfe.desktop_{now.strftime("%Y%m%d")}_6_RC2',
      'x-youtube-page-cl': '305312232',
      'x-youtube-variants-checksum': 'be75f5f350742e06b11e18727c7bdd45',
      'x-youtube-sts': '18359',
      'x-youtube-device': 'cbr=Chrome&cbrver=80.0.3987.116&ceng=WebKit&cengver=537.36&cos=X11',
      'x-youtube-client-version': '2.20200406.06.02',
      'Cookie': 'VISITOR_INFO1_LIVE=M_Zf0Pgjif0; YSC=95kraKe4V_o; GPS=1'
    }
    r = requests.get("https://www.youtube.com/results?search_query={}&pbj=1".format(query), headers=headers)
    resp = r.json()
    c1=next(filter(lambda x: x.get("response",None), resp))["response"]["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
    contents=next(filter(lambda x: x.get("itemSectionRenderer",None),c1))["itemSectionRenderer"]["contents"]
    min_diff_seconds=1000
    for content in contents:
      videoRenderer=content.get("videoRenderer",None)
      if videoRenderer:
        video_id = videoRenderer["videoId"]
        duration_str = videoRenderer["lengthText"]["simpleText"]
        durations=duration_str.split(":")
        duration_s=int(sum([pow(60,i)*int(c) for i,c in enumerate(reversed(durations))]))
        diff_seconds=abs(duration_ms//1000-duration_s)
        if diff_seconds < 5:
          selected_video_id=video_id
          break
        elif diff_seconds < min_diff_seconds:
          min_diff_seconds = diff_seconds
          selected_video_id = video_id
  except Exception as e:
    log.error(f"Error in getting youtube video id  why ?? {e}")
  return  {**track, "youtube_video_id": selected_video_id}

def download_youtube(track, root):
  filename = os.path.join(root, 
  f'{str(track["track_number"]).zfill(2)} {track["title"]} {track["artist_names"][0]}'\
    .translate(remove_punctuation_map)) + '.mp3'
  if os.path.exists(filename):
    return
  url=f"https://www.youtube.com/watch?v={track['youtube_video_id']}"
  ydl_opts = {
            'outtmpl': filename,
            'format': 'bestaudio/best',
            'noplaylist': True,
            'postprocessor_args': ['-metadata', 'title=' + str(track["title"]),
                                  '-metadata', 'artist=' + str(track["artist_names"][0])],
            'ffmpeg_location': os.environ.get('FFMPEG_PATH','/usr/local/bin/ffmpeg'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        }
  with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    try:
      log.debug(ydl.download([url]))
    except Exception as e:
      log.debug(e)
      log.error('Failed to download: {}'.format(url))

def parse_url(url="https://open.spotify.com/playlist/6sNDAFPubg3k4CuyH1fqrR?si=3Tbf7wL5QxWKMtyNeIKRfA"):
  obj=re.search(r"\?(.*)",url)
  track_id=None
  if obj:
    track_pattern='spotify:track:'
    if track_pattern in url[obj.start():]:
      indx=re.search(track_pattern, url[obj.start():])
      track_id=url[obj.start():][indx.start()+len(track_pattern):]
    url=url[:obj.start()]
  root_url=url.replace("https://open.spotify.com","https://api.spotify.com/v1").replace("playlist","playlists").replace("album","albums")
  url=root_url+"?type=track,episode"
  return url,track_id
  
def get_all_tracks_info(url, mode="playlist"):
  api_url,track_id = parse_url(url)
  if track_id:
    log.info(f"Getting single track from {url}")
  else:
    log.info(f"Getting musics from {mode}")
  tracks=[]
  log.info("Getting track info from Spotify")
  name=""
  while True:
    info=get_tracks_info(api_url)
    if not name:
      name=info["name"].strip()
      pbar=tqdm(total=info["tracks"]["total"])
    if mode.startswith("playlist"):
      tracks.extend(parse_playlist_info(info,track_id))
    elif mode.startswith('album'):
      tracks.extend(parse_album_info(info,track_id))
    # update progress bar
    pbar.update(len(info.get("tracks",info).get("items")))
    if info.get("tracks",info).get("next"):
      api_url=info.get("tracks",info).get("next")
    else:
      break
  log.info(f'Finished getting Spotify track info: {mode} name is: {name}')
  return tracks, name

def main(url,root_path,force_search):
  mode=url.split("/")[3]
  tracks, name = get_all_tracks_info(url, mode)
  if root_path:
    name = root_path
  track_path=os.path.join(name,"track_lists.json")
  if not os.path.exists(track_path) or force_search:
    log.info("Searching sounds from YouTube search ...")
    tracks = [search_youtube(track) for track in tqdm(tracks)]
    log.info("Finished searching from YouTube")
    try:
      os.makedirs(name)
    except:
      pass
    json.dump(tracks,open(track_path,"w"),indent=4)
  else:
    log.info(f"Getting cached track lists from {track_path}")
    tracks=json.load(open(track_path))
  log.info("Starting download from YouTube ...")
  for track in tracks:
    try:
      download_youtube(track, name)
    except Exception as e:
      log.error(f'Error in downloading {track["title"]} why ?? {e}')

def sanity_check(url):
  pattern=re.match("https://open.spotify.com/(playlist|album)/(.*)",url)
  if pattern:
    return True
  return False

def open_spotify_dl():
  arg_parser = ArgumentParser(description="Open and free download music from Spotify")
  arg_parser.add_argument("--url", help="Url of playlist or album of Spotify", required=True)
  arg_parser.add_argument("--root_path", help="Path to store album or playlist in your local. (Keep it empty to save it here by its name)", default="")
  arg_parser.add_argument("--force_search", help="Make it false if you want to search the whole musics from YouTube again!", action='store_true')
  args=arg_parser.parse_args()
  if sanity_check(args.url):
    main(args.url, args.root_path, args.force_search)
  else:
    log.error(f"The requested URL {args.url} is not match with: https://open.spotify.com/(playlist|album)/(.*)\nPlease copy this url to your browser and make sure its live and copy the result url from your browser")


if __name__ == "__main__":
  open_spotify_dl()