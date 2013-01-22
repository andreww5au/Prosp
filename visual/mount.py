
from visual import *
from visual.text import *
from math import *

lat=-32.0*pi/180.0

saxis=vector(cos(lat),-sin(lat),0)

def sexstring(value=0,sp=':'):
  """Usage: sexstring(value=0,sp=':')
     Convert the floating point 'value' into a sexagecimal string, using
     'sp' as a spacer between components
  """
  try:
    aval=abs(value)
  except:
    aval=0.0
  if value<0:
    outs='-'
  else:
    outs=''
  D=int(aval)
  M=int((aval-float(D))*60)
  S=float(int((aval-float(D)-float(M)/60.0)*36000))/10.0
  outs=outs+`D`+sp+`M`+sp+`S`
  return outs


mount=frame()

sector=cylinder(frame=mount,
                pos=(0,0,0),
                axis=(1,0,0),
                length=0.5,
                radius=0.75,
                color=color.blue)

spike=cylinder(frame=mount,
               pos=(0.5,0,0),
               length=2,
               axis=(1,0,0),
               radius=0.2,
               color=color.blue)

drive=box(frame=mount,
          pos=(2,0,-0.35),
          axis=(1,0,0),
          length=0.75,
          width=0.3,
          height=0.4,
          color=color.blue)

axle=cylinder(frame=mount,
              pos=(2,0,0.4),
              axis=(0,0,-1),
              length=0.4,
              radius=0.1)

hadial=cylinder(frame=mount,
                pos=(0.5,-0.4,0),
                axis=(1,0,0),
                length=0.01,
                radius=0.07,
                color=(1,0,0))

radial=cylinder(frame=mount,
                pos=rotate(vector(0.5,-0.5,0),angle=25.0*pi/180,axis=(1,0,0)),
                axis=(1,0,0),
                length=0.01,
                radius=0.10,
                color=(1,0,0))

decdial=cylinder(frame=mount,
                pos=rotate(vector(0.5,-0.5,0),angle=-25.0*pi/180,axis=(1,0,0)),
                axis=(1,0,0),
                length=0.01,
                radius=0.10,
                up=(-1,0,0),
                color=(1,0,0))

mount.axis=saxis

base=frame()

floor=cylinder(frame=base,
               pos=(1.7,-2,0),
               axis=(0,1,0),
               length=0.05,
               radius=4,
               color=(139.0/256,126.0/256,102.0/256))


ped=box(frame=base,
        pos=(0,-1.75,0),
        length=1.6,
        width=1.6,
        height=0.5)


stand=convex(frame=base,
             pos=[(-0.7,-1.5,0),(0.6,-1.5,0.7),(0.75,-1.5,0),(0.6,-1.5,-0.7),
                   (0,0.5,0)],
             color=color.blue)

ra=''
dec=''

def setra(val):
  global ra
  del ra
  ra=text(pos=(0.81,-1.7,0),
            axis=(0,0,-1),
            height=0.15,
            depth=0.02,
            color=color.black,
            string="RA "+sexstring(val),
            justify='center')


def setdec(val):
    global dec
    del dec
    dec=text(pos=(0.81,-1.9,0),
            axis=(0,0,-1),
            height=0.15,
            depth=0.02,
            color=color.black,
            string="DEC "+sexstring(val),
            justify='center')

#setra(1.0)
#setdec(-32.0)

