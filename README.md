# mixtape

## Summary

mixtape plays, or extracts, sections of audio to help when putting together mixtapes or playlists.

### Modes of operation

mixtape can extract audio segments from the beginning of files, from the end of files, and short sections from across a file.

## Prerequisites/Setup

So far, has been tested only on macOS High Sierra, with Python 3.6.3

```
pyenv virtualenv 3.6.3 mixtape
pyenv local mixtape
pip install scipy
pip install sounddevice
```

Relies on `ffmpeg` existing on the path.

## Usage

`python mixtape.py --help` will show the full list of arguments and the short-form of option specifiers. This readme describes the purpose of, and the relationship between, options.

### Specifying input

Input files are specified as positional arguments on the command-line.  

### Specifying output

Output can either be to a file or played to the output speaker.

`--output OUTPUT` Specify the output filename. WAV and MP3 output file formats are supported.

`--force` Overwrite an existing output file. Default behaviour is to refuse to overwrite an existing file.

`--play` Play the audio, rather than exporting to an output file.

### Specifying which audio segment to extract

`--beginning` Extract a segment from the beginning of the file. Only one input file is supported in this mode of operation.

`--end` Extract a segment from the end of the file. Only one input file is supported in this mode of operation.

`--slice` Extract brief segments from across the file(s). Multiple input files are supported in this mode of operation.

`--transition` Extract a segment from the end of one file, and the beginning of the next. Two or more input files are required for this mode of operation. If three files are specified (A, B and C), the extracted segments will be: the end of A, the beginning of B, the end of B and then the beginning of C. If a fourth is specified, the end of C is extracted, followed by the beginning of D. Etc.

### Length of audio segment

`--length LENGTH` specifies the length of the audio segment to extract, in seconds. Defaults to 30 seconds for `--beginning`, `--end` and `--transition`; 1 second for `--slice`.

`--skip SKIP` specifies the interval between audio segments in the `--slice` mode of operation. Default is 5s.

## Notes

Minimal error handling has been implemented, so be nice to it.
