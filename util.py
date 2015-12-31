import traceback
import json
import sys

class JdGError(Exception):
    pass

def error(msg, driver=None, e=None):
    fmt = '\n[Erreur] ' + msg + '\n'
    sys.stderr.write(fmt)
    if e:
        traceback.print_exc()

    if driver:
        _, stderr = driver.popen_.communicate(timeout=1)
        msg = stderr
        try:
            msg = stderr.decode('utf')
        except:
            pass

        if stderr:
            sys.stderr.write('\nErreur du programme (stderr):\n{}\n'.format(stderr.decode('utf')))
    raise JdGError()

