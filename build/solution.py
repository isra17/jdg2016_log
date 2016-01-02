import sys
print('T')
sys.stdout.flush()
mid, _, msg = sys.stdin.readline().split(':')
print(':'.join([mid, msg]))
sys.stdout.flush()
