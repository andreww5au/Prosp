
from math import *

from globals import *
import xpa
import improc

def calcflex(fname):
  f = improc.FITS(fname)
  ra = stringsex(f.headers['RA'][1:-1])
  dec = stringsex(f.headers['DEC'][1:-1])

  aRArads = ra / 12 * pi         # hours to radians
  aDecrads = dec / 180 * pi      # degrees to radians
  nu = (y - y_cent) * scaleS 
  eta = (x - x_cent) * scaleS 

  dRA = atan(eta / cos(aDecrads)/(1 - nu * tan(aDecrads)))
  dDec = dec - 180 / pi * atan((nu + tan(aDecrads)) * cos(dRA)/(1 - nu * tan(aDecrads)))

  rRA = ra + dRA*12/pi
  rDec = dec + dDec

  rRAstr = sexstring(rRA)
  rDECstr = sexstring(rDEC)

  return aRAstr+' '+aDECstr+'     '+rRAstr+' '+rDECstr+'    '+f.headers['LST'][1:-1]


def doflex(fpat=''):
  outf = open('/tmp/flex_cal.dat','w')
  outf.write('Flexure Data for TPoint\n')
  outf.write('-32 0 29.1\n')

  olist = distribute(fpat,calcflex)
  if olist:
    if type(olist) == str:
      outf.write(olist)
    else:
      outf.write('\n'.join(olist))
  outf.close()
