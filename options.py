#scons parameters file
#use this file to pass custom parameter to SConstruct script

#build_prefix="build_scons"

import sys
if('win32' in sys.platform):
    #compiler='msvc'
    compiler= 'mingw' # by default on windows
else:
    compiler= 'gcc' # by default otherwise
