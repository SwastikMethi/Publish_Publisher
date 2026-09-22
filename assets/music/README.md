# Background music

Normally this folder can stay empty. `scripts/compose.py` writes an original track for every
video, composed to the edit plan's beat grid (drop on the title, break under the stats card),
so nothing here is needed and nothing has to be licensed.

Drop audio files here (`.mp3`, `.m4a`, `.wav`) only as a fallback: when `numpy` is not
installed and the composer cannot run, or when you want a specific track and point the plan's
`music.file` at it. The render then trims it to the video length and fades it out at the end,
but its beats will not line up with the cuts.

Only add tracks you are licensed to use on LinkedIn. Royalty-free libraries with a clear
licence (for example the YouTube Audio Library, Pixabay Music, or a paid subscription) are
fine; a song from your own library is not, and LinkedIn mutes or removes videos with flagged
audio. Keep a note of the source next to each file, like `calm-01.SOURCE.txt`. Tracks that
`compose.py` produced and you chose to keep can be saved here too; their `.SOURCE.txt` should
say they were generated.
