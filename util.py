import traceback
import json
import sys

def error(msg, driver=None, e=None):
    fmt = '[Erreur] ' + msg
    print(fmt, file=sys.stderr)
    if e:
        traceback.print_exc()

    if driver:
        stderr = driver.popen_.stderr.read().decode('utf')
        if stderr:
            print('\nErreur du programme (stderr):\n{}'.format(stderr), file=sys.stderr)
    sys.exit(-1)

def load_data(path):
    return json.load(open(path, 'r'))

