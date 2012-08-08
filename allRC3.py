if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')

import os
import numpy as np
import pylab as plt
import pyfits
import sys

from general import general
from halflight import halflight

#Work in progress...
def main():
    rc3 = pyfits.open('rc3limited.fits')
    entries=[]
    for entry in rc3[1].data:
        if entry['NAME'] != '':
            name = entry['NAME']
        elif entry['ALT_NAME_1'] != '':
            name = entry['ALT_NAME_1']
        elif entry['ALT_NAME_2'] != '':
            name = entry['ALT_NAME_2']
        else:
            name = entry['PGC_NAME']
        if entry['DEC'] < -20.:
            continue
        print (10**entry['LOG_D25'])/10.
        fn = 'RC3_Output/%s.pickle' % (name.replace(' ', '_'))
        print fn
        if os.path.exists(fn):
            print '%s has run successfully already' %name
        else:
            print 'run %s through tractor' %name
            entries.append('%s' %name)
    things=[str(x) for x in entries]

    for entry in things:
        print entry
        newentry=entry.replace(' ', '_')
        print newentry
        try:
            print 'running tractor for %s' %entry
            general(entry,itune1=6,itune2=6,nocache=True)
            os.system('cp flip-%s.pdf RC3_Output' % newentry)
            os.system('cp %s.png RC3_Output' % newentry)
            os.system('cp %s.pickle RC3_Output' % newentry)
            halflight(newentry)

        except AssertionError:
            print sys.exc_info()[0]
            continue
            
#3053 galaxies
if __name__ == '__main__':
    main()
