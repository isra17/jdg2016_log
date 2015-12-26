from subprocess import Popen, PIPE
import json
import sys

class AsciiProtocol:
    def __init__(self, driver):
        self.driver_ = driver

    def send(self, test_id, mission, test_input):
        self.driver_.popen_.stdin.write(
                (':'.join([str(test_id), str(mission), test_input]) + '\n')
                    .encode())

    def recv(self):
        try:
            line = self.driver_.popen_.stdout.readline().decode('utf')
            if line:
                fields = line.split(':')
                if len(fields) != 2:
                    error('Réponse invalide', self.driver_)
                return (int(fields[0]), fields[1])
        except Exception as e:
            error('Réponse invalide', self.driver_, e)

        error('Aucune réponse reçue', self.driver_)

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
                pass
            else:
                self.protocol_ = AsciiProtocol(self)
        else:
            error('Aucune pognée de main reçue', self)

    def challenges(self, mission_id, test):
        self.protocol_.send(self.test_id_, mission_id, test['request'])
        self.test_id_ += 1

        test_id, response = self.protocol_.recv()
        if test_id != self.test_id_:
            error('ID de mission invalide: {}'.format(test_id), self)

        return (test['expected'] == response, response)

def error(msg, driver=None, e=None):
    fmt = '[Erreur] ' + msg
    if e:
        fmt += '\nException: [{}] {}'.format(e.__class__.__name__, str(e))
    print(fmt, file=sys.stderr)

    if driver:
        stderr = driver.popen_.stderr.read().decode('utf')
        if stderr:
            print('Erreur du programme (stderr):\n{}'.format(stderr), file=sys.stderr)
    sys.exit(-1)

def load_data(path):
    return json.load(open(path, 'r'))

def run():
    tests_data = load_data('./tests.json')
    driver = Driver('./test.py')
    driver.handshake()
    for data in tests_data['missions']:
        mission_id = data['id']
        for test in data['tests']:
            success, response = driver.challenges(mission_id, test)
            if not success:
                print('Challenge "{}" #{} échoué:\n' \
                      '\tRéponse attendue: {}\n' \
                      '\tRéponse reçue: {}'
                      .format(data['name'], mission_id, repr(test['expected']),
                              repr(response)))

