from subprocess import Popen, PIPE
from util import error, load_data
import sys
import protocol

class Driver:
    def __init__(self, command):
        self.test_id_ = 0
        self.protocol_ = None
        self.popen_ = Popen(args=command, shell=True, stdin=PIPE, \
                            stdout=PIPE, stderr=PIPE)

    def handshake(self):
        protocol_flag = self.popen_.stdout.readline()
        if protocol_flag:
            try:
                protocol_flag = int(protocol_flag)
            except ValueError as e:
                error('Poignée de main invalide', self, e)

            if protocol_flag & 1:
                self.protocol_ = protocol.BinProtocol(self)
            else:
                self.protocol_ = protocol.AsciiProtocol(self)

            if protocol_flag & 0b0010:
                self.protocol_.middlewares.append(protocol.RLEMiddleware(self))

            if protocol_flag & 0b0100:
                self.protocol_.middlewares.append(protocol.AESMiddleware(self))

            if protocol_flag & 0b1000:
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

