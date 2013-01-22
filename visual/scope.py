from visual import *
from math import *

scope=frame(axis=(1,0,0))

tube=cylinder(frame=scope,
              pos=(-1,0,0),
              radius=0.4,
              axis=(1,0,0),
              length=3)

finder=cylinder(frame=scope,
                pos=(-1,0.4,0.25),
                axis=(1,0,0),
                length=1,
                radius=0.075)

fcap=cylinder(frame=scope,
              pos=(-0.01,0.4,0.25),
              axis=(1,0,0),
              length=0.02,
              color=color.black,
              radius=0.07)

feye=cylinder(frame=scope,
              pos=(-1,0.4,0.25),
              axis=(-1,0,0),
              length=0.15,
              radius=0.025)

cap=cylinder(frame=scope,
             pos=(1.99,0,0),
             axis=(1,0,0),
             radius=0.38,
             length=0.02,
             color=color.black)

mbox=box(frame=scope,
         pos=(-1.125,0,0),
         length=0.25,
         width=0.25,
         height=0.25,
         color=(205.0/256,201.0/256,201.0/256))

fbox=box(frame=scope,
         pos=(-1.33,0,0.1),
         length=0.16,
         width=0.45,
         height=0.45,
         color=(205.0/256,201.0/256,201.0/256))

ccd=cylinder(frame=scope,
             pos=(-1.42,0,0),
             axis=(-1,0,0),
             radius=0.08,
             length=0.16,
             color=(108.0/256,123.0/256,139.0/256))





