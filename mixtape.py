import argparse
from   collections import namedtuple
import numpy
import os.path
import subprocess
import sys
import tempfile

import scipy.io.wavfile
import sounddevice

Wav = namedtuple('Wav', ['sample_rate', 'data'])
Segment = namedtuple('Segment', ['time', 'wav'])


def convert_mp3_to_wav(mp3filename, wavfilename):
    """
    Convert an MP3 file to a WAV filename
    :param mp3filename: path of mp3. Assumed to exist.
    :param wavfilename: path to wav to write. Existing file will not be overwritten.
    """
    if not os.path.exists(wavfilename):
        cmd = ['ffmpeg',
               '-n',
               '-i',
               mp3filename,
               wavfilename]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def convert_wav_to_mp3(wavfilename, mp3filename, force):
    """
    Convert a WAV file to an MP3 file
    :param wavfilename: path of wav. Assumed to exist.
    :param mp3filename: path to mp3 to write. Existing file will be overwritten only if force is True
    :param force: Whether to overwrite existing output file
    """
    cmd = ['ffmpeg',
           '-y' if force else '-n',
           '-i',
           wavfilename,
           mp3filename]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_wav(wavfilename):
    """
    :param wavfilename: Filename to read
    :return: Wav
    """
    return Wav._make(scipy.io.wavfile.read(wavfilename))


def write_segments_to_wav(segments, outwavfilename):
    """
    :param wavdata: Wav to write
    :param outwavfilename: Filename to write to
    """
    sample_rate = segments[0].wav.sample_rate
    assert(all((segment.wav.sample_rate == sample_rate) for segment in segments))
    outwav_data = numpy.concatenate([segment.wav.data for segment in segments])
    scipy.io.wavfile.write(outwavfilename, sample_rate, outwav_data)


def play_segments(segments):
    """
    Play the given list of segments, reporting progress to stdout
    :param segments: list of Segment
    """
    try:
        for segment in segments:
            print(segment.time, end='\r')
            sounddevice.play(segment.wav.data, segment.wav.sample_rate)
            sounddevice.wait()
    except KeyboardInterrupt:
        pass
    except:
        raise
    print('')


def format_time(seconds):
    """
    Format a time for printing
    :param seconds: integer number of seconds
    :return: string representation of minutes and seconds
    """
    mins, secs = divmod(seconds, 60)
    return '%u:%02u' % (mins, secs)


def input_wav(args, input_filename):
    """
    Read an input file into memory, coping with multiple file formats
    :param args: Program arguments - return value from parse_args()
    :param input_filename: File to read
    :return: Wav
    """
    if input_filename.endswith('.mp3'):
        leafname = os.path.splitext(os.path.basename(input_filename))[0] + '.wav'
        inwav_filename = os.path.join(args.tmpdir.name, leafname)
        convert_mp3_to_wav(input_filename, inwav_filename)
    elif input_filename.endswith('.wav'):
        inwav_filename = input_filename
    else:
        raise Exception("Unrecognised input file format: "+input_filename)
    return read_wav(inwav_filename)


def extract_beginning(args, inputs):
    """
    Extract the segment at the beginning of the first input file
    :param args: Program arguments - return value from parse_args()
    :param inputs: Files to read
    :return: list of Segment
    """
    inwav = input_wav(args, inputs[0])
    begin_pos = 0
    end_pos = int(args.length * inwav.sample_rate)
    return [Segment('%s: First %s seconds' % (os.path.basename(inputs[0]), args.length), Wav(inwav.sample_rate, inwav.data[begin_pos:end_pos]))]


def extract_end(args, inputs):
    """
    Extract the segment at the end of the first input file
    :param args: Program arguments - return value from parse_args()
    :param inputs: Files to read
    :return: list of Segment
    """
    inwav = input_wav(args, inputs[0])
    begin_pos = -int(args.length * inwav.sample_rate)
    return [Segment('%s: Last %s seconds' % (os.path.basename(inputs[0]), args.length), Wav(inwav.sample_rate, inwav.data[begin_pos:]))]


def extract_slice(args, inputs):
    """
    Extract the slice of segments across all input files.
    :param args: Program arguments - return value from parse_args()
    :param inputs: Files to read
    :return: list of Segment
    """
    segments = []
    for filename in inputs:
        begin_pos = 0
        pos_name = 0
        inwav = input_wav(args, filename)
        while begin_pos < len(inwav.data):
            end_pos = int(begin_pos + args.length * inwav.sample_rate)
            segments.append(Segment('%s: %s' % (os.path.basename(filename), format_time(pos_name)),
                                    Wav(inwav.sample_rate, inwav.data[begin_pos:end_pos])))
            begin_pos += int((args.length + args.skip) * inwav.sample_rate)
            pos_name += args.length + args.skip
    return segments


def extract_transition(args, inputs):
    """
    Extract the segment at the end of one file and the beginning of the next.
    :param args: Program arguments - return value from parse_args()
    :param inputs: Files to read
    :return: list of Segment
    """
    segments = []
    index = 0
    while index < len(inputs)-1:
        segments.extend(extract_end(args, inputs[index:index+1]))
        index += 1
        segments.extend(extract_beginning(args, inputs[index:index+1]))
    return segments


def parse_args():
    """
    Parse program command-line arguments
    :return: ArgumentParser namespace.
    """
    parser = argparse.ArgumentParser()
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument('-o', '--output',
                              help="Specify the output filename")
    output_group.add_argument('--play', action='store_true',
                              help="Play, rather than writing an output file")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Force overwrite existing output file.")
    extraction_group = parser.add_mutually_exclusive_group(required=True)
    extraction_group.add_argument('--beginning', action='store_const', const=extract_beginning, dest='extractor',
                                  help="Play/extract the beginning few seconds of music")
    extraction_group.add_argument('--end', action='store_const', const=extract_end, dest='extractor',
                                  help="Play/extract the last few seconds of music")
    extraction_group.add_argument('--slice', action='store_const', const=extract_slice, dest='extractor',
                                  help="Play/extract slices of music throughout the track")
    extraction_group.add_argument('--transition', action='store_const', const=extract_transition, dest='extractor',
                                  help="Play/extract the end of one song and the beginning of the next. "
                                       "Multiple transitions are supported.")
    selector_group = parser.add_argument_group()
    selector_group.add_argument('-l', '--length', action='store', type=float,
                                help="For --beginning/--end: Specify length of music to extract (in seconds)."
                                     "For --slice: Specify length of sections of music to keep (in seconds).")
    selector_group.add_argument('-k', '--skip', action='store', type=float,
                                help="For --slice: Specify length of sections of music to skip (in seconds).")
    parser.add_argument('input', nargs='+',
                        help="Specify the input filename. May be specified multiple times for --transition and --slice.")
    parser.set_defaults(input=[], output=None, play=False)
    args = parser.parse_args()
    if (args.length <= 0) or (args.skip <= 0):
        parser.error("Length and skip lengths must be greater than 0")
    if args.length is None:
        args.length = 30.0 if (args.extractor in (extract_beginning, extract_end, extract_transition)) else 1
    if (args.extractor == extract_slice) and (args.skip is None):
        args.skip = 5.0
    if (args.extractor == extract_transition) and (len(args.input) < 2):
        parser.error("2 or more input files are required for transition mode")
    args.tmpdir = tempfile.TemporaryDirectory()
    return args


def main():
    """
    Main function
    """
    args = parse_args()
    for filename in args.input:
        if not os.path.exists(filename):
            sys.exit("%s not found" % filename)
    if args.output and os.path.exists(args.output) and not args.force:
        sys.exit("Output file exists. Refusing to overwrite.")
    segments = args.extractor(args, args.input)
    if args.play:
        play_segments(segments)
    else:
        if args.output.endswith('.mp3'):
            outwavfilename = os.path.join(args.tmpdir.name, 'output.wav')
            write_segments_to_wav(segments, outwavfilename)
            convert_wav_to_mp3(outwavfilename, args.output, args.force)
        else:
            write_segments_to_wav(segments, args.output)


if __name__ == '__main__':
    main()
