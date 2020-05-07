import sys
import argparse
from pathlib import Path
from rads2file.ads import AdsAnalyzer, AdsChanger, NotARarFile, NotARarV5, NotFirstVolume


def print_error(msg):
    print(msg, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='+')
    parser.add_argument('--analyze', '-a', help='Analyze but do not change', action='store_true')
    args = parser.parse_args()
    for file in args.file:
        filepath = Path(file)
        if not filepath.is_file():
            print_error(f'Path {file} does not exists or is not a file')
            sys.exit(1)
        print(f'Processing {file}...')
        an = AdsAnalyzer(file)
        try:
            streams = an.analyze()
        except NotARarFile:
            print_error('Not a rar file')
            sys.exit(2)
        except NotARarV5:
            print_error(f'Only rar version 5 is supported')
            sys.exit(3)
        except NotFirstVolume:
            print_error(f'Not the first volume')
            sys.exit(4)

        print(f'{len(streams)} stream(s) found.')
        if len(streams) > 0 and not args.analyze:
            file_out = filepath.with_suffix('.ads.rar')
            ch = AdsChanger(streams, file, file_out)
            if ch.change():
                print(f'Modified rar file saved to {file_out}')


if __name__ == '__main__':
    main()
