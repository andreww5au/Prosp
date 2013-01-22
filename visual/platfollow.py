#!/usr/bin/python

sys.path.append('/home/observer/PyDevel')
from Prosp.globals import *
from Prosp import weather
from Prosp.extras import prospclient
from teljoy.extras import tjclient

from visual import *
from math import *
import string

lat=-32*pi/180
han=0
decl=-32

import mount
import scope


def dec(d):
    global decl
    decl=d
    dr=d*pi/180
    p=(0,1,0)
    q=rotate(p,angle=dr-lat, axis=(0,0,1))
    r=rotate(q, angle=han, axis=mount.saxis)
    scope.scope.up=mount.saxis
    scope.scope.axis=r

def sgn(n):
    if n<0:
        return -1
    else:
        if n>0:
            return 1
        else:
            return 0

def ha(h):
    global han
    han=-h*pi/12
    mount.mount.up=(0,cos(han),sin(han))
    scope.scope.up=(0,cos(han),sin(han))
    p=(0,0,0.65)
    q=rotate(p,angle=han,axis=mount.saxis)
    scope.scope.pos=vector(1.7,1,0)+q
    dec(decl)

status=teljoy.status

dt=1.0
hvel=1.5/15.0
dvel=1.5
slewtime=0
status.update()
lastHA=status.RawHourAngle
lastDec=status.RawDec

while 1:
  rate(1/dt)
  status.update()
  if not status.moving:
     lastHA=status.RawHourAngle
     lastDec=status.RawDec
     ha(lastHA)
     dec(lastDec)
#     mount.setra(status.RawRA)
#     mount.setdec(status.RawDec)
     slewtime=0
     dt=1.0
  else:
      dt=0.2
      hslew=(status.RawHourAngle-lastHA)
      dslew=(status.RawDec-lastDec)
      hlen=abs(hslew/hvel)
      dlen=abs(dslew/dvel)
      slewtime=slewtime+dt
      if slewtime<abs(hlen):
         ha(lastHA+hvel*slewtime*sgn(hslew))
      else:
          ha(status.RawHourAngle)
      if slewtime<dlen:
         dec(lastDec+dvel*slewtime*sgn(dslew))
      else:
          dec(status.RawDec)


