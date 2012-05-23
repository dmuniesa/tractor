import os
import logging
import numpy as np
import pylab as plt

import pyfits

from astrometry.util.file import *

from tractor import *
from tractor import sdss as st
from tractor.saveImg import *
from tractor import sdss_galaxy as sg
from tractor import basics as ba
from astrometry.util.ngc2000 import *
from astrometry.util.sdss_radec_to_rcf import *

def main():

    for i,j in enumerate(ngc2000):
        if j['id'] == 4258 and j['is_ngc']:
            print j
            break

    rcfs = radec_to_sdss_rcf(j['ra'],j['dec'])
    print rcfs
    
    roi0 = [1000,2000,700,1500]
    roi1 = [0,600,0,400]
    rois = [roi0,roi1]
    
    ra = j['ra']
    dec = j['dec']
    itune1 = 5
    itune2 = 5
    ntune = 0
    IRLS_scale = 25.

    bands=['r','g','u','i','z']
    bandname = 'r'
    flipBands = ['r']

    rerun = 0

    TI = []
    sources = []
    for rcf,roi in zip(rcfs,rois): 
        TI.extend([st.get_tractor_image(rcf[0], rcf[1], rcf[2], bandname,roi=roi,useMags=True) for bandname in bands])
        sources.append(st.get_tractor_sources(rcf[0], rcf[1], rcf[2],bandname,roi=roi,bands=bands))

    timg,info = TI[0]
    photocal = timg.getPhotoCal()

    wcs = timg.getWcs()
    lvl = logging.DEBUG
    logging.basicConfig(level=lvl,format='%(message)s',stream=sys.stdout)

    tims = [timg for timg,tinf in TI]
    tractor = st.SDSSTractor(tims)
    for source in sources:
        tractor.addSources(source)

    zr = np.array([-5.,+5.]) * info['skysig']

    print bands

    prefix = 'ngc4258'
    saveAll('initial-'+prefix, tractor,zr,flipBands,debug=True)
    plotInvvar('initial-'+prefix,tractor)
    bright = None
    lowbright = 1000
    for timg,sources in zip(tims,sources):
        wcs = timg.getWcs()
        xtr,ytr = wcs.positionToPixel(RaDecPos(ra,dec))
    
        print xtr,ytr

        xt = xtr 
        yt = ytr
        r = 250.
        for src in sources:
            xs,ys = wcs.positionToPixel(src.getPosition(),src)
            if (xs-xt)**2+(ys-yt)**2 <= r**2:
                print "Removed:", src
                print xs,ys
                tractor.removeSource(src)

    saveAll('removed-'+prefix, tractor,zr,flipBands,debug=True)
    newShape = sg.GalaxyShape(30.,1.,0.)
    newBright = ba.Mags(r=15.0,g=15.0,u=15.0,z=15.0,i=15.0)
    EG = st.ExpGalaxy(RaDecPos(ra,dec),newBright,newShape)
    print EG
    tractor.addSource(EG)


    saveAll('added-'+prefix,tractor,zr,flipBands,debug=True)

    for i in range(itune1):
        tractor.optimizeCatalogLoop(nsteps=1,srcs=[EG],sky=True)
        tractor.changeInvvar(IRLS_scale)
        saveAll('itune1-%d-' % (i+1)+prefix,tractor,zr,flipBands,debug=True)

    CGPos = EG.getPosition()
    CGShape1 = EG.getShape().copy()
    CGShape2 = EG.getShape().copy()
    EGBright = EG.getBrightness()

    CGr = EGBright[0] + 0.75
    CGg = EGBright[1] + 0.75
    CGu = EGBright[2] + 0.75
    CGz = EGBright[3] + 0.75
    CGi = EGBright[4] + 0.75
    CGBright1 = ba.Mags(r=CGr,g=CGg,u=CGu,z=CGz,i=CGi)
    CGBright2 = ba.Mags(r=CGr,g=CGg,u=CGu,z=CGz,i=CGi)
    print EGBright
    print CGBright1

    CG = st.CompositeGalaxy(CGPos,CGBright1,CGShape1,CGBright2,CGShape2)
    tractor.removeSource(EG)
    tractor.addSource(CG)

    for i in range(itune2):
        tractor.optimizeCatalogLoop(nsteps=1,srcs=[CG],sky=True)
        tractor.changeInvvar(IRLS_scale)
        saveAll('itune2-%d-' % (i+1)+prefix,tractor,zr,flipBands,debug=True)

    for i in range(ntune):
        tractor.optimizeCatalogLoop(nsteps=1,sky=True)
        tractor.changeInvvar(IRLS_scale)
        saveAll('ntune-%d-' % (i+1)+prefix,tractor,zr,flipBands,debug=True)
    plotInvvar('final-'+prefix,tractor)
    makeflipbook(prefix,len(tractor.getImages()),itune1,itune2,ntune)

def makeflipbook(prefix,numImg,itune1=0,itune2=0,ntune=0):
    # Create a tex flip-book of the plots

    def allImages(title,imgpre):
        page = r'''
        \begin{frame}{%s}
        \plot{data-%s}
        \plot{model-%s} \\
        \plot{diff-%s}
        \plot{chi-%s} \\
        \end{frame}'''
        temp = ''
        for j in range(numImg):
            if j % 5 == 0:
                temp+= page % ((title+', %d' % (j),) + (imgpre+'-%d' % (j),)*4)
        return temp

    tex = r'''
    \documentclass[compress]{beamer}
    \usepackage{helvet}
    \newcommand{\plot}[1]{\includegraphics[width=0.5\textwidth]{#1}}
    \begin{document}
    '''
    
    tex+=allImages('Initial Model','initial-'+prefix)
    tex+=allImages('Removed','removed-'+prefix)
    tex+=allImages('Added','added-'+prefix)
    for i in range(itune1):
        tex+=allImages('Galaxy tuning, step %d' % (i+1),'itune1-%d-' %(i+1)+prefix)
    for i in range(itune2):
        tex+=allImages('Galaxy tuning (w/ Composite), step %d' % (i+1),'itune2-%d-' %(i+1)+prefix)
    for i in range(ntune):
        tex+=allImages('All tuning, step %d' % (i+1),'ntune-%d-' % (i+1)+prefix)
    
    tex += r'\end{document}' + '\n'
    fn = 'flip-' + prefix + '.tex'
    print 'Writing', fn
    open(fn, 'wb').write(tex)
    os.system("pdflatex '%s'" % fn)



if __name__ == '__main__':
    import cProfile
    import sys
    from datetime import tzinfo, timedelta, datetime
    cProfile.run('main()','prof-%s.dat' % (datetime.now().isoformat()))
    sys.exit(0)
