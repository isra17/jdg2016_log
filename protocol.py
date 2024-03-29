from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto import Random
import binascii
import struct

class RLEMiddleware:
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

class AESMiddleware:
    def __init__(self, driver):
        self.driver_ = driver
        self.key_ = b'ThisKeyIsSecuree'

    def on_send(self, packet):
        iv = Random.new().read(16)
        pad_len = 16 - (len(packet) % 16)
        pad = struct.pack('B', pad_len) * pad_len
        data = packet + pad
        cipher = AES.new(self.key_, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(data)

    def on_recv(self, packet):
        if len(packet) < 32:
            self.driver_.error("La taille d'un paquet chiffré doit être supérieure ou " \
                    "égale à 32 bytes (IV + 1 block). Taille reçue: {}" \
                    .format(len(packet)))
        if len(packet) % 16 != 0:
            self.driver_.error("La taille d'un paquet chiffré doit être un multiple de 16." \
                    "Taille reçue: {}".format(len(packet)))
        iv = packet[:16]
        data = packet[16:]
        cipher = AES.new(self.key_, AES.MODE_CBC, iv)
        text = cipher.decrypt(data)
        return text[:-text[-1]]

class HMACMiddleware:
    def __init__(self, driver):
        self.driver_ = driver
        self.key_ = b'ThisKeyIsSecuree'

    def on_send(self, packet):
        hmac = HMAC.new(self.key_, digestmod=SHA256)
        hmac.update(packet)
        return packet + hmac.digest()

    def on_recv(self, packet):
        hmac = HMAC.new(self.key_, digestmod=SHA256)
        if len(packet) < hmac.digest_size:
            self.driver_.error("La taille du paquet doit être supérieure à la taille " \
                    "d'une signature HMAC-SHA256 ({} bytes). Taille reçue: {}"
                    .format(hmac.digest_size, len(packet)))
        data = packet[:-hmac.digest_size]
        signature = packet[-hmac.digest_size:]
        hmac.update(data)
        expected = hmac.digest()
        if signature != expected:
            self.driver_.error("La signature du HMAC-SHA256 n'est pas valide.\n" \
                    "Reçue: {}\nAttendue: {}"
                    .format(binascii.hexlify(signature),
                            binascii.hexlify(expected)))
        return data

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
        data = struct.pack('<IB', test_id, mission) + test_input.encode()
        data = self.on_send(data)

        try:
            self.driver_.write(
                    struct.pack('<I', len(data)) + data)
            self.driver_.flush()
        except BrokenPipeError as e:
            self.driver_.error('Le programme a fermé stdin', e)

    def recv(self):
        try:
            data = self.driver_.read(4)
            if data:
                size = struct.unpack('<I', data)[0]
                if size >= 4:
                    packet = self.driver_.read(size)
                    packet = self.on_recv(packet)
                    mission = struct.unpack('<I', packet[:4])[0]
                    return (mission, packet[4:].decode('utf'))
                else:
                    self.driver_.error('Taille de réponse invalide: {}'.format(size))
        except Exception as e:
            self.driver_.error('Réponse invalide', e)

        self.driver_.error('Aucune réponse reçue')

class AsciiProtocol(BaseProtocol):
    def send(self, test_id, mission, test_input):
        data = (':'.join([('%08x' % test_id), str(mission), test_input])) \
                    .encode()
        data = self.on_send(data)
        self.driver_.write(data + b'\n')
        self.driver_.flush()

    def recv(self):
        try:
            line = self.driver_.readline()
            if line:
                if line[-1] == 0xa:
                    line = line[:-1]

                line = self.on_recv(line).decode('utf')
                fields = line.split(':')
                if len(fields) != 2:
                    self.driver_.error('Réponse invalide: {}'.format(line))
                r = None
                try:
                    r = int(fields[0], 16)
                except ValueError:
                    self.driver_.error('Réponse invalide: {}'.format(line))
                return (r, fields[1])
        except RuntimeError as e:
            self.driver_.error('Réponse invalide', e)

        self.driver_.error('Aucune réponse reçue')

