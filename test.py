#!/usr/bin/env python3
import sys
import struct
import protocol

def rle_encode(packet):
    rle_packet = b''
    size = len(packet)
    i = 0
    while i < size:
        b = packet[i]
        count = 1
        while i+count < size and b == packet[i+count] and count < 255:
            count += 1
        if count > 1:
            rle_packet += struct.pack('BBB', b, b, count)
        else:
            rle_packet += struct.pack('B', b)
        i += count
    return rle_packet

def recv():
    size = struct.unpack('<I', sys.stdin.buffer.read(4))[0]
    print('recv: ' + repr(sys.stdin.buffer.read(size)), file=sys.stderr)
    sys.stderr.flush()

def send(test_id, data):
    packet = struct.pack('<I', test_id) + data
    packet = rle_encode(packet)
    sys.stdout.buffer.write(struct.pack('<I', len(packet)) + packet)
    print('sent: ' + repr(packet), file=sys.stderr)
    sys.stdout.flush()

print(str(0b1111))
sys.stdout.flush()
recv()
send(1, b'foobar')
