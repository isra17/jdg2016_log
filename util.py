import traceback
import json
import sys

def error(msg, driver=None, e=None):
    fmt = '[Erreur] ' + msg
    print(fmt, file=sys.stderr)
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
            print('\nErreur du programme (stderr):\n{}'.format(stderr.decode('utf')), file=sys.stderr)
    sys.exit(-1)

def load_data(path):
    return json.load(open(path, 'r'))

