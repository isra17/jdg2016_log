from subprocess import Popen, PIPE
from util import JdGError
import re
import sys
import protocol
import mission
import socket
import serial
import argparse
import random

MISSION_ID = 42

class MajeurDriver(object):
  def __init__(self, serial_port, baudrate, port):
    self.serial_port = serial_port
    self.baudrate = int(baudrate)
    self.port = int(port)

    self.protocol_ = None
    self.fd_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.fd_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.fd_.bind(('', self.port))
    self.fd_.listen(1)
    self.conn_ = None
    self.serial_ = serial.Serial(serial_port, baudrate=self.baudrate, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=1, xonxoff=0, rtscts=0)

  def accept_connection(self):
    print('Waiting for a connection...')
    self.conn_, addr = self.fd_.accept()
    print('Connected by {}'.format(addr))
    #self.conn_.close()

  def write(self, data):
    return self.conn_.send(data)

  def read(self, size):
    return self.conn_.recv(size)

  def readline(self):
    s = b''
    while True:
      data = self.conn_.recv(1)
      if not data:
        break
      if data == b'\n':
        break
      s += data
    print('< {}'.format(s))
    return s

  def flush(self):
    pass

  def handshake(self):
    protocol_flags = self.readline()
    self.protocol_flags = protocol_flags
    if protocol_flags:
      if re.match(b'[^TBRCS]', protocol_flags.strip()):
        self.error('Poignée de main invalide')

      if (b'T' in protocol_flags) == (b'B' in protocol_flags):
        self.error('Le protocol doit être soit binaire ou texte')
      elif b'B' in protocol_flags:
        self.protocol_ = protocol.BinProtocol(self)
      else:
        self.protocol_ = protocol.AsciiProtocol(self)

      if any(x in protocol_flags for x in b'RCS') and \
              b'T' in protocol_flags:
        self.error('Le protocol binaire doit être utilisé pour supporter'\
                ' les fonctionnalitées avancées')

      if b'R' in protocol_flags:
        self.protocol_.middlewares.append(protocol.RLEMiddleware(self))

      if b'C' in protocol_flags:
        self.protocol_.middlewares.append(protocol.AESMiddleware(self))

      if b'S' in protocol_flags:
        self.protocol_.middlewares.append(protocol.HMACMiddleware(self))

      print('Handshake recu: {}'.format(self.protocol_flags))
    else:
      self.error('Aucune pognée de main reçue')

  def error(self, msg, e=None):
    fmt = '\n[Erreur] ' + msg + '\n'
    sys.stderr.write(fmt)
    if e:
      traceback.print_exc()
    raise JdGError()

class MajeurMission(object):

  def __init__(self, driver):
    self.driver_ = driver
    return

  def run(self):
    while True:
      s = self.driver_.serial_.readline()
      s = str(s, 'utf8').strip()
      print('<s {}'.format(s))
      if ' ' not in s:
        continue
      name, value = s.split(' ', 1)
      if name == 'ANGLE':
        # broadcast angle
        r = random.randint(0,0xffffffff)
        self.driver_.protocol_.send(r, MISSION_ID, value)
    return

def run(serial_port, baudrate, port):
  driver = MajeurDriver(serial_port, baudrate, port)
  mission = MajeurMission(driver)
  while True:
    try:
      driver.accept_connection()
      driver.handshake()
      mission.run()
    except KeyboardInterrupt:
      import traceback
      traceback.print_exc()
      driver.error('Ctrl-C: Arrêt du programme.')
    except JdGError as e:
      pass
    except Exception:
      import traceback
      traceback.print_exc()
      pass

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Compétition majeure serveur')
  parser.add_argument('--serial', '-s', help='Port série', default='/dev/ttyUSB0')
  parser.add_argument('--port', '-p', help='Port du serveur', default='12345')
  parser.add_argument('--baudrate', '-b', help='Baud rate', default='115200')

  args = parser.parse_args()
  run(args.serial, args.baudrate, args.port)
