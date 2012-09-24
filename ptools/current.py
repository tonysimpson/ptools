import sys

if sys.platform.startswith('linux'):
    from ptools.linux import *
elif sys.platform.startswith('win'):
    from ptools.win import *
else:
    raise ImportError('Unsupported plaform')
