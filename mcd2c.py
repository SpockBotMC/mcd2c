import sys
version = sys.argv[1]
print('Generating version', version)

import mcd2c
mcd2c.run(version)
