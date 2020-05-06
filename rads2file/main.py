import sys
import argparse
import rarfile as rf

CRC_LEN = 4
MAX_HDR_LEN = 3
MAX_BLOCK_TYPE_LEN = 2

def print_error(msg):
    print(f'ERROR: {msg}', file=sys.stderr)

def to_vint(value):
    out = bytearray()
    while value:
        out.append(value & 0x7f | 0x80)
        value >>= 7
    out[-1] &= 0x7f
    return out

def fatal_error(code, msg):
    print_error(msg)
    sys.exit(code)


class RarADS:
    def __init__(self, filename: str):
        self.filename = filename
        self._headers = []

    def _change_header(self, f, offset, size):
        f.seek(offset)
        hdata = bytearray(f.read(size))
        _, start_bt = rf.load_vint(hdata, CRC_LEN)
        # Technically the current and previous block type could have differnt sizes but it is unlikely
        hdata[start_bt] = rf.RAR5_BLOCK_FILE
        hdata[:CRC_LEN] = rf.S_LONG.pack(rf.rar_crc32(memoryview(hdata[4:])))
        f.seek(offset)
        f.write(hdata[:start_bt+1])

    def change(self):
        if len(self._headers) == 0:
            return
        with open(self.filename, 'rb+') as f:
            for offset, size in self._headers:
                self._change_header(f, offset, size)

    def _info_callback(self, h: rf.Rar5Info):
        if h.block_type == rf.RAR5_BLOCK_SERVICE and h.filename == 'STM':
            print(f'Found ADS size: {h.file_size} bytes')
            self._headers.append([h.header_offset, h.header_size])

    def analyze(self):
        print(f'Processing file "{self.filename}"')
        version = rf._get_rar_version(self.filename)
        if version == 0:
            print_error('Not a rar file')
            return
        if version != 5:
            print_error(f'Only rar version 5 is supported (version {version} found)')
            return
        try:
            rar = rf.RarFile(self.filename, info_callback=self._info_callback)
        except rf.NeedFirstVolume:
            print_error('Not the first volume')
            return
        if len(self._headers) == 0:
            print('No ADS found')
            return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='+')
    parser.add_argument('--analyze', '-a', help='Analyze but do not change', action='store_true')
    args = parser.parse_args()
    for file in args.file:
        rar = RarADS(file, args.prefix)
        rar.analyze()
        if not args.analyze:
            rar.change()


if __name__ == '__main__':
    main()
