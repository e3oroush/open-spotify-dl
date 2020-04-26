# Open Spotify Downloader
This repo is a simple script that uses public APIs of Spotify and YouTube to retrieve Spotify musics from YouTube.  
The whole idea I borrowed from [this repo](https://github.com/SathyaBhat/spotify-dl/), but it uses official APIs of YouTube and Spotify which incurs some restriction (like search limit in YouTube API). So I decided to implement it using public, ananymous APIs of those websites.

We are using youtube-dl package to download youtube videos and ffmpeg to convert them to mp3, make sure to download them correctly.  
If you got problems with ffmpeg, provide ffmpeg path with `FFMPEG_PATH` environment variable.

## Install requirements
You need to have ffmpeg installed in your system with the flag of limemp3.  
And install the following requirements:
```bash
pip install -r requirements.txt
```

## Usage
1. Download a playlist or album: Copy the spotify URL
```bash
$ open_spotify_dl --url URL_PATH
```
If you want to store the songs in a custom directory give it as an argument to
```bash
$ open_spotify_dl --url URL_PATH --root_path
```
By default, for the sake of speed and resumeness, open spotify downloader youtube search is performed once and sotored in track_lists.json, but if you want to perform the search again you can force it by `--force_search`

## Issues and Contact
Please raise bugs/issues under Github issues if you faced any trouble. I am on twitter at [@e3oroush](https://twitter.com/e3oroush) or you can email me at [ebrahim.soroush@gmail.com](mailto:ebrahim.soroush@gmail.com)
