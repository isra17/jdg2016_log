from util import error
import struct

class RLE:
    def __init__(self, driver):
        self.driver_ = driver

    def on_send(self, packet):
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

    def on_recv(self, rle_packet):
        packet = b''
        size = len(rle_packet)
        i = 0
        while i < size:
            b = rle_packet[i]
            count = 1
            if i+2 < size and b == rle_packet[i+1]:
                count = rle_packet[i+2]
                i += 3
            else:
                count = 1
                i += 1
            packet += struct.pack('B', b) * count
        return packet

class AES:
    def __init__(self, driver):
        self.driver_ = driver

    def on_send(self, packet):
        pass

    def on_recv(self, packet):
        pass

class HMAC:
    def __init__(self, driver):
        self.driver_ = driver

    def on_send(self, packet):
        pass

    def on_recv(self, packet):
        pass

class BaseProtocol:
    def __init__(self, driver):
        self.driver_ = driver
        self.middlewares = []

    def on_send(self, data):
        for middleware in self.middlewares:
            data = middleware.on_send(data)
        return data

    def on_recv(self, data):
        for middleware in reversed(self.middlewares):
            data = middleware.on_recv(data)
        return data

class BinProtocol(BaseProtocol):
    def send(self, test_id, mission, test_input):
        data = struct.pack('<II', test_id, mission) + test_input.encode()
        data = self.on_send(data)

        self.driver_.popen_.stdin.write(
                struct.pack('<I', len(data)) + data)
        self.driver_.popen_.stdin.flush()

    def recv(self):
        try:
            data = self.driver_.popen_.stdout.read(4)
            if data:
                size = struct.unpack('<I', data)[0]
                if size >= 4:
                    packet = self.driver_.popen_.stdout.read(size)
                    packet = self.on_recv(packet)
                    mission = struct.unpack('<I', packet[:4])[0]
                    return (mission, packet[4:].decode('utf'))
                else:
                    error('Taille de réponse invalide: {}'.format(size), self.driver_)
        except Exception as e:
            error('Réponse invalide', self.driver_, e)

        error('Aucune réponse reçue', self.driver_)

class AsciiProtocol(BaseProtocol):
    def __init__(self, driver):
        self.driver_ = driver

    def send(self, test_id, mission, test_input):
        data = (':'.join([str(test_id), str(mission), test_input]) + '\n') \
                    .encode()
        data = self.on_send(data)
        self.driver_.popen_.stdin.write(data)
        self.driver_.popen_.stdin.flush()

    def recv(self):
        try:
            line = self.driver_.popen_.stdout.readline().decode('utf')
            if line:
                if line[-1] == '\n':
                    line = line[:-1]

                line = self.on_recv(line)
                fields = line.split(':')
                if len(fields) != 2:
                    error('Réponse invalide: {}'.format(line), self.driver_)
                return (int(fields[0]), fields[1])
        except Exception as e:
            error('Réponse invalide', self.driver_, e)

        error('Aucune réponse reçue', self.driver_)

