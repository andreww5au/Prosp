#!/usr/bin/python
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

def ha(h):
    global han
    han=h*pi/12
    mount.mount.up=(0,cos(han),sin(han))
    scope.scope.up=(0,cos(han),sin(han))
    p=(0,0,0.65)
    q=rotate(p,angle=han,axis=mount.saxis)
    scope.scope.pos=vector(1.7,1,0)+q
    dec(decl)

ha(0)
dec(-32)

while 1:
  str=raw_input("Enter HA,dec: ")
  print str
  h=float(string.split(str,',')[0])
  d=float(string.split(str,',')[1])
  ha(h)
  dec(d)
