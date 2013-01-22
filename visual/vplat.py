#!/usr/bin/python

import sys
sys.path.append('/home/observer/PyDevel')
from Prosp.globals import *
from Prosp.extras import prospclient
from teljoy.extras import tjclient

from visual import *
from visual.text import *
from math import *

LATDEG = -32.0
LATRAD = LATDEG * pi / 180.0

SAXIS = vector(cos(LATRAD), -sin(LATRAD), 0)


class Plat(object):
  def __init__(self):
    self.hastring = None
    self.decstring = None
    self.ha = 0.0
    self.dec = LATDEG
    self.mount = frame()
    self.sector = cylinder(frame=self.mount,
                           pos=(0, 0, 0),
                           axis=(1, 0, 0),
                           length=0.5,
                           radius=0.75,
                           color=color.blue)
    self.spike = cylinder(frame=self.mount,
                          pos=(0.5, 0, 0),
                          length=2,
                          axis=(1, 0, 0),
                          radius=0.2,
                          color=color.blue)
    self.drive = box(frame=self.mount,
                     pos=(2, 0, -0.35),
                     axis=(1, 0, 0),
                     length=0.75,
                     width=0.3,
                     height=0.4,
                     color=color.blue)
    self.axle = cylinder(frame=self.mount,
                         pos=(2, 0, 0.4),
                         axis=(0, 0, -1),
                         length=0.4,
                         radius=0.1)
    self.hadial = cylinder(frame=self.mount,
                           pos=(0.5, -0.4, 0),
                           axis=(1, 0, 0),
                           length=0.01,
                           radius=0.07,
                           color=(1, 0, 0))
    self.radial = cylinder(frame=self.mount,
                           pos=rotate(vector(0.5, -0.5, 0), angle=25.0 * pi / 180, axis=(1, 0, 0)),
                           axis=(1, 0, 0),
                           length=0.01,
                           radius=0.10,
                           color=(1, 0, 0))
    self.decdial = cylinder(frame=self.mount,
                            pos=rotate(vector(0.5, -0.5, 0), angle=-25.0 * pi / 180, axis=(1, 0, 0)),
                            axis=(1, 0, 0),
                            length=0.01,
                            radius=0.10,
                            up=(-1, 0, 0),
                            color=(1, 0, 0))
    self.mount.axis = SAXIS

    self.base = frame()
    self.floor = cylinder(frame=self.base,
                          pos=(1.7, -2, 0),
                          axis=(0, 1, 0),
                          length=0.05,
                          radius=4,
                          color=(139.0 / 256, 126.0 / 256, 102.0 / 256))
    self.ped = box(frame=self.base,
                   pos=(0, -1.75, 0),
                   length=1.6,
                   width=1.6,
                   height=0.5)
    self.stand = convex(frame=self.base,
                        pos=[(-0.7, -1.5, 0), (0.6, -1.5, 0.7), (0.75, -1.5, 0), (0.6, -1.5, -0.7),
                             (0, 0.5, 0)],
                        color=color.blue)

    self.scope = frame(axis=(1, 0, 0))
    self.tube = cylinder(frame=self.scope,
                         pos=(-1, 0, 0),
                         radius=0.4,
                         axis=(1, 0, 0),
                         length=3)
    self.finder = cylinder(frame=self.scope,
                           pos=(-1, 0.4, 0.25),
                           axis=(1, 0, 0),
                           length=1,
                           radius=0.075)
    self.fcap = cylinder(frame=self.scope,
                         pos=(-0.01, 0.4, 0.25),
                         axis=(1, 0, 0),
                         length=0.02,
                         color=color.black,
                         radius=0.07)
    self.feye = cylinder(frame=self.scope,
                         pos=(-1, 0.4, 0.25),
                         axis=(-1, 0, 0),
                         length=0.15,
                         radius=0.025)
    self.cap = cylinder(frame=self.scope,
                        pos=(1.99, 0, 0),
                        axis=(1, 0, 0),
                        radius=0.38,
                        length=0.02,
                        color=color.black)
    self.mbox = box(frame=self.scope,
                    pos=(-1.125, 0, 0),
                    length=0.25,
                    width=0.25,
                    height=0.25,
                    color=(205.0 / 256, 201.0 / 256, 201.0 / 256))
    self.fbox = box(frame=self.scope,
                    pos=(-1.33, 0, 0.1),
                    length=0.16,
                    width=0.45,
                    height=0.45,
                    color=(205.0 / 256, 201.0 / 256, 201.0 / 256))
    self.ccd = cylinder(frame=self.scope,
                        pos=(-1.42, 0, 0),
                        axis=(-1, 0, 0),
                        radius=0.08,
                        length=0.16,
                        color=(108.0 / 256, 123.0 / 256, 139.0 / 256))
    self.setpos(ha=0.0, dec=LATDEG)

  def sethastring(self, val):
    if self.hastring:
      del self.hastring
    self.hastring = text(pos=(0.81, -1.7, 0),
            axis=(0, 0, -1),
            height=0.15,
            depth=0.02,
            color=color.black,
            string="HA " + sexstring(val),
            justify='center')

  def setdecstring(self, val):
    if self.decstring:
      del self.decstring
    self.decstring = text(pos=(0.81, -1.9, 0),
             axis=(0, 0, -1),
             height=0.15,
             depth=0.02,
             color=color.black,
             string="DEC " + sexstring(val),
             justify='center')

  def setposr(self, har, decr):
    self.har = har
    self.decr = decr
    self.mount.up = (0, cos(-self.har), sin(-self.har))
    self.scope.up = (0, cos(-self.har), sin(-self.har))
    p = (0, 0, 0.65)
    q = rotate(p, angle=-self.har, axis=SAXIS)
    self.scope.pos = vector(1.7, 1, 0) + q
    p = (0, 1, 0)
    q = rotate(p, angle=self.decr - LATRAD, axis=(0, 0, 1))
    r = rotate(q, angle=-self.har, axis=SAXIS)
    self.scope.up = SAXIS
    self.scope.axis = r

  def setpos(self, ha, dec):
    self.setposr(har=ha*math.pi/12, decr=dec*math.pi/180)
    self.sethastring(ha)
    self.setdecstring(dec)


def FollowLoop(plat=None):
  """Given a visual telescope object (a subclass of vplat.Plat), run
     continuously, updating the position of the virtual telescope to match
     the real coordinates obtained via RPC from teljoy.

     Returns immediately if teljoy can't be contacted.
  """
  connected = tjclient.Init()
  if not connected:
    return

  dt = 1.0
  slewvel = tjclient.status.prefs.SlewRate/20.0/3600/15  #convert from steps/sec to hours/sec
  slewtime = 0
  lastHA = tjclient.status.current.RaC/15.0/3600-tjclient.status.current.Time.LST
  lastDec = tjclient.status.current.DecC/3600.0

  while 1:
    rate(1 / dt)
    tjclient.status.update()
    if not tjclient.status.Moving:
      lastHA = tjclient.status.current.RaC/15.0/3600-tjclient.status.current.Time.LST
      lastDec = tjclient.status.current.DecC/3600.0
      plat.setpos(lastHA,lastDec)
      #     mount.setra(status.RawRA)
      #     mount.setdec(status.RawDec)
      slewtime = 0
      dt = 1.0
    else:
      dt = 0.2
      hslewlen = ((tjclient.status.current.RaC/15.0/3600-tjclient.status.current.Time.LST) - lastHA)
      dslewlen = (tjclient.status.current.DecC/3600.0 - lastDec)
      htime = abs(hslewlen / slewvel)
      dtime = abs(dslewlen / slewvel)
      slewtime = slewtime + dt
      hpos = lastHA
      dpos = lastDec
      if htime > 0.0:
        hpos = lastHA + hslewlen*(dt/htime)
      if dtime > 0.0:
        dpos = lastDec + dslewlen*(dt/dtime)
      plat.setpos(hpos, dpos)
