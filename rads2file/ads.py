import struct
import rarfile as rf
from typing import List, BinaryIO
from datetime import datetime

CHAR_COLON = 58  # ':'
ADS_FILENAME = 'STM'
ADS_FiLE_PREFIX = b'ADS'
ADS_FILE_SEPARATOR = b'-'


class AppException(Exception):
    pass


class NotARarFile(AppException):
    pass


class NotARarV5(AppException):
    pass


class NotFirstVolume(AppException):
    pass


class VPack:
    def __init__(self):
        self.data = bytearray()

    def bytes(self, value: bytes, insert: bool = False):
        if insert:
            for b in value[::-1]:
                self.data.insert(0, b)
        else:
            self.data.extend(value)

    def int(self, value: int, min_bytes: int = 1, insert: bool = False):
        out = bytearray()
        while value:
            out.append(value & 0x7f | 0x80)
            value >>= 7
        for i in range(len(out), min_bytes):
            out.append(0x80)
        out[-1] &= 0x7f
        self.bytes(out, insert=insert)

    def le32(self, value: int, insert: bool = False):
        self.bytes(struct.pack('<L', value), insert=insert)

    def str(self, value: bytes):
        self.int(len(value))
        self.bytes(value)

    def __len__(self):
        return len(self.data)


class ServiceHeader:
    def __init__(self, header: rf.Rar5ServiceInfo):
        self.__dict__['h'] = header
        self.h.block_flags &= ~rf.RAR5_BLOCK_FLAG_DEPENDS_PREV
        self.h.block_flags &= ~rf.RAR5_BLOCK_FLAG_EXTRA_DATA

    def __getattr__(self, name: str):
        if hasattr(self.h, name):
            return getattr(self.h, name)

    def __setattr__(self, name: str, value):
        setattr(self.h, name, value)

    def pack(self):
        h = self.h
        file_flags = h.file_flags
        if h.mtime is None:
            file_flags &= ~rf.RAR5_FILE_FLAG_HAS_MTIME
        else:
            file_flags |= rf.RAR5_FILE_FLAG_HAS_MTIME
        p = VPack()
        p.int(h.block_type)
        p.int(h.block_flags)
        if h.block_flags & rf.RAR5_BLOCK_FLAG_DATA_AREA:
            p.int(h.add_size, min_bytes=3)
        p.int(file_flags)
        p.int(h.file_size, min_bytes=3)
        p.int(h.mode)
        if file_flags & rf.RAR5_FILE_FLAG_HAS_MTIME:
            p.le32(int(datetime.timestamp(h.mtime)))
        if h.file_flags & rf.RAR5_FILE_FLAG_HAS_CRC32:
            p.le32(h.CRC)
        p.int(h.file_compress_flags)
        p.int(h.file_host_os)
        p.str(h.orig_filename)
        p.int(len(p), insert=True)
        p.le32(rf.rar_crc32(p.data), insert=True)
        return p.data


class AdsHeader:
    def __init__(self, header: rf.Rar5ServiceInfo, file_header: rf.Rar5FileInfo):
        self._header = ServiceHeader(header)
        self._file_header = file_header

    @property
    def offset(self):
        return self._header.header_offset

    def ads_filename(self, suffix: bytes):
        return self._file_header.orig_filename + ADS_FILE_SEPARATOR + suffix

    def change(self, fin: BinaryIO):
        data = fin.read(self._header.header_size)  # type: bytes
        extra_data = data[-self._header.block_extra_size:]
        if len(extra_data) > 3 \
                and extra_data[0] == self._header.block_extra_size - 1 and extra_data[1] == rf.RAR5_XFILE_SERVICE \
                and extra_data[2] == CHAR_COLON:
            suffix = extra_data[3:]
        else:
            suffix = ADS_FiLE_PREFIX + hex(self._header.header_offset)[2:].encode()
        self._header.block_type = rf.RAR5_BLOCK_FILE
        self._header.orig_filename = self.ads_filename(suffix)
        self._header.mtime = self._file_header.mtime
        self._header.mode = self._file_header.mode
        return self._header.pack()


class AdsChanger:
    def __init__(self, headers: List[AdsHeader], filein: str, fileout: str):
        self._headers = headers
        self._filein = filein
        self._fileout = fileout

    def change(self):
        if len(self._headers) == 0:
            return False
        with open(self._filein, 'rb') as fin:
            with open(self._fileout, 'wb') as fout:
                for header in self._headers:
                    fout.write(fin.read(header.offset - fin.tell()))
                    fout.write(header.change(fin))
                fout.write(fin.read())
        return True


class AdsAnalyzer:
    def __init__(self, filename: str):
        self._filename = filename
        self._last_file_header = None
        self._headers = []

    def _info_callback(self, h: rf.Rar5Info):
        if h.block_type == rf.RAR5_BLOCK_FILE:
            self._last_file_header = h
        elif h.block_type == rf.RAR5_BLOCK_SERVICE and h.filename == ADS_FILENAME:
            self._headers.append(AdsHeader(h, self._last_file_header))

    def analyze(self):
        version = rf._get_rar_version(self._filename)
        if version == 0:
            raise NotARarFile()
        if version != 5:
            raise NotARarV5()
            return
        try:
            rar = rf.RarFile(self._filename, info_callback=self._info_callback)
            rar.close()
        except rf.NeedFirstVolume:
            raise NotFirstVolume()
        return self._headers
