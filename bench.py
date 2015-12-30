from subprocess import Popen, PIPE
from util import error, load_data
import re
import sys
import protocol

class Driver:
    def __init__(self, command):
        self.test_id_ = 0
        self.protocol_ = None
        self.popen_ = Popen(args=command, shell=True, stdin=PIPE, \
                            stdout=PIPE, stderr=PIPE)

    def handshake(self):
        protocol_flags = self.popen_.stdout.readline()
        if protocol_flags:
            if re.match(b'[^TBRCS]', protocol_flags.strip()):
                error('Poignée de main invalide', self)

            if (b'T' in protocol_flags) == (b'B' in protocol_flags):
                error('Le protocol doit être soit binaire ou texte', self)
            elif b'B' in protocol_flags:
                self.protocol_ = protocol.BinProtocol(self)
            else:
                self.protocol_ = protocol.AsciiProtocol(self)

            if b'R' in protocol_flags:
                self.protocol_.middlewares.append(protocol.RLEMiddleware(self))

            if b'C' in protocol_flags:
                self.protocol_.middlewares.append(protocol.AESMiddleware(self))

            if b'S' in protocol_flags:
                self.protocol_.middlewares.append(protocol.HMACMiddleware(self))
        else:
            error('Aucune pognée de main reçue', self)

    def challenges(self, mission_id, test):
        self.protocol_.send(self.test_id_, mission_id, test['request'])

        test_id, response = self.protocol_.recv()
        if test_id != self.test_id_:
            error('ID de mission invalide: {}'.format(test_id), self)

        self.test_id_ += 1
        return (test['expected'] == response, response)

def run():
    tests_data = load_data('./tests.json')
    driver = Driver(sys.argv[1])
    try:
        driver.handshake()
        for data in tests_data['missions']:
            mission_id = data['id']
            for i, test in enumerate(data['tests']):
                success, response = driver.challenges(mission_id, test)
                if success:
                    print('Challenge "{}" #{} passé'.format(data['name'], i+1))
                else:
                    print('Challenge "{}" #{} échoué:\n' \
                          '\tRéponse attendue: {}\n' \
                          '\tRéponse reçue: {}'
                          .format(data['name'], i+1, repr(test['expected']),
                                  repr(response)))
    except KeyboardInterrupt:
        import traceback
        traceback.print_exc()
        error('Ctrl-C: Arrêt du programme.', driver)

