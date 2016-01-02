from subprocess import Popen, PIPE
from util import JdGError
import re
import sys
import protocol
import mission

class Driver:
    def __init__(self, command):
        self.test_id_ = 0
        self.protocol_ = None
        self.popen_ = Popen(args=command, shell=True, stdin=PIPE, \
                            stdout=PIPE, stderr=PIPE, bufsize=0)

    def write(self, data):
        return self.popen_.stdin.write(data)

    def read(self, size):
        return self.popen_.stdout.read(size)

    def readline(self):
        return self.popen_.stdout.readline()

    def flush(self):
        return self.popen_.stdout.flush()

    def handshake(self):
        protocol_flags = self.popen_.stdout.readline()
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
        else:
            self.error('Aucune pognée de main reçue %s' % (repr(protocol_flags)))

    def error(self, msg, e=None):
        fmt = '\n[Erreur] ' + msg + '\n'
        sys.stderr.write(fmt)
        if e:
            import traceback
            traceback.print_exc()

        _, stderr = self.popen_.communicate(timeout=1)
        msg = stderr
        try:
            msg = stderr.decode('utf')
        except:
            pass

        if stderr:
            sys.stderr.write('\nErreur du programme (stderr):\n{}\n'.format(stderr.decode('utf')))
        raise JdGError()

def run(target, test_file, include=None):
    driver = Driver(target)
    missions = mission.MissionManager(driver, include)
    missions.load(test_file)
    try:
        driver.handshake()
        missions.run()
    except KeyboardInterrupt:
        import traceback
        traceback.print_exc()
        error('Ctrl-C: Arrêt du programme.', driver)
    except JdGError as e:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
        pass
    missions.print_score()

