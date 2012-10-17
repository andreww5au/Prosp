
from math import *
import time
import copy

from xyglobs import *
import dohgsc
import donomad

f = 13.5*0.61      #????? focal length, meters}
rotation = 60      #rot angle in degrees}
nmax = 0.06        #max and min values for non-reflected+rotated visible}
Emax = 0.06        #area, for coarse search. In same units as focal length}
nmin = -0.06
Emin = -0.06


class Cartesian:
  def __init__(self, x=0.0, y=0.0):
    self.x = x
    self.y = y


def DoPrecess(ci, ep_i, ep_f):
  """Precesses position ci (in hours/deg) from ep_i to ep_f (in years)
  """
  radeg = ci.a*15
  dec = ci.d
  a,d = precess(jd1=year_jd(ep_i), jd2=year_jd(ep_f), ra=radeg, dec=dec)
  cf = Coord(d=d, a=a/15)
  return cf


# * * * Equ2Std * * * }

def Rotate(r1, theta):
  """Procedure Rotate(r1:cartesian;theta:double;var r:cartesian);
     converted to function, returns r as Cartesian
  """
  rot = theta*pi/180
  r = Cartesian()
  r.x = (r1.x*cos(rot)) + (r1.y*sin(rot))
  r.y = -(r1.x*sin(rot)) + (r1.y*cos(rot))
  return r


def Eq2St(s0, s):
  """Procedure Eq2St(s0,s:Coord; var p:Cartesian);
     converted to function, returns p as Cartesian
  """
  a0 = s0.a*pi/12
  d0 = s0.d*pi/180
  a = s.a*pi/12
  d = s.d*pi/180
  q = atan(tan(d) / cos(a-a0))
  p = Cartesian()
  p.x = f*tan(q-d0)
  p.y = f*cos(q)*tan(a-a0) / cos(q-d0)
  return p 


def St2Eq(p, s0):
  """Procedure St2Eq(p:Cartesian; s0:Coord; var s:Coord);
     converted to function, returns s as Coord
  """
  a0 = s0.a*pi/12
  d0 = s0.d*pi/180
  q = atan(p.x/f) + d0
  a = atan(p.y*cos(q-d0)/(f*cos(q))) + a0
  d = atan(tan(q)*cos(a-a0))
  s = Coord(d=d*180/pi, a=a*12/pi)
  if s.a < 0:
    s.a = s.a + 24
  return s


def Eq2XY(s, s0):
  """Procedure Eq2XY(s,s0:coord;var r:cartesian);
     converted to function, returns r as Cartesian
  """
  r1 = Eq2St(s,s0)
  r = Rotate(r1,rotation)
  r.x, r.y = r.y, r.x
  return r


def XY2Eq(r, s0):
  """Procedure XY2Eq(r:cartesian;s0:coord;var s:coord);
     converted to function, returns s as Coord
  """
  r1 = Cartesian(x=r.y, y=r.x)
  r2 = Rotate(r1,-1*rotation)
  s = St2Eq(r2,s0)
  return s


def FindExtremes(s0, d1, d2):
  """Procedure FindExtremes(s0:coord;d1,d2:real;var amax,amin,dmax,dmin:degrees);
     converted to function, returns amax, amin, dmax, dmin in degrees
  """
  p = Cartesian(x=nmin, y=Emin)
  s = []
  s.append(DoPrecess(St2Eq(p,s0),d1,d2))
  p.y = Emax
  s.append(DoPrecess(St2Eq(p,s0),d1,d2))
  p.x = nmax
  s.append(DoPrecess(St2Eq(p,s0),d1,d2))
  p.y = Emin
  s.append(DoPrecess(St2Eq(p,s0),d1,d2))
  amax, amin, dmax, dmin = s[0].a, s[0].a, s[0].d, s[0].d
  for i in range(4):
#    print s[i].a, s[i].d
    if (amax < s[i].a):
      amax = s[i].a
    if (amin > s[i].a):
      amin = s[i].a
    if (dmax < s[i].d):
      dmax = s[i].d
    if (dmin > s[i].d):
      dmin = s[i].d
  return amax, amin, dmax, dmin 


def PrecessList(Obslist):
  """Procedure PrecessList(Obs:ObjArray);
     {Converts object array to epoch of date}
     left as procedure, modifies list of objects in place
  """
  EpochNow = jd_year()
  for element in Obslist:
    element.pos = DoPrecess(element.pos,element.epoch,EpochNow)
    element.epoch = EpochNow


def CoarseSelect(Cpos,Cepoch):
  """Procedure CoarseSelect(Obj:ObjType; var Objs:ObjArray);
     {Accepts center position to any epoch, converts to epoch of each}
     {catalog, searches catalog, and returns array of RA's, Dec's, and}
     {mags of all stars nearby, precessed to epoch-of-date}
     converted to function, returns list of object recs
  """
  Smax, Smin = Coord(), Coord()
  Smax.a,Smin.a,Smax.d,Smin.d = FindExtremes(Cpos,Cepoch,2000.0)
  Objs = donomad.doNOMADSearch(ra=Cpos.a*15, dec=Cpos.d, radius=0.35)
  if len(Objs) < 100:
    Objs += dohgsc.HGSCSearch(Smin.a*15,Smin.d,Smax.a*15,Smax.d)
  PrecessList(Objs)  #Precess list to epoch-of-date for later use
  Cpos = DoPrecess(Cpos, Cepoch, jd_year())  #Precess center too for comparison
  Cepoch = jd_year()
  for element in Objs:
    p = Eq2XY(element.pos,Cpos)
    tst1 = ( (p.x<Xmax) and (p.x>Xmin) and (p.y<Ymax) and (p.y>Ymin) )
    tst2 = ( sqrt(p.x**2 + p.y**2 ) > hole_radius)
    element.visible = (tst1 and tst2)
    element.x = p.x * X_Steps   #Convert from meters to steps
    element.y = p.y * Y_Steps   #Convert from meters to steps
  return Objs


def getstars(ra,dec,epoch=2000.0):
  pos = Coord()
  try:
    if type(ra) == type(''):
      pos.a = stringsex(ra)
    else:
      pos.a = float(ra)
    if type(dec) == type(''):
      pos.d = stringsex(dec)
    else:
      pos.d = float(dec)
    epoch = float(epoch)
  except:
    print "Coordinates invalid for guidestar search in starposc.getstars"
    return []

  pos, epoch = DoPrecess(pos, epoch, 2000.0), 2000.0
#  print 'Precessed: RA=', sexstring(pos.a)
#  print 'Precessed: Dec=', sexstring(pos.d)

  reslist = CoarseSelect(pos, epoch)
#  print len(reslist), ' Candidates returned.'
  return reslist


def best(slist=[]):
  """Given a slist of guidestar records, return the index of the 'best' one to use
  """
  vlist = [copy.copy(s) for s in slist if s.visible]
  if not vlist:
    return None
  for s in vlist:
    if sqrt(s.x**2 + s.y**2) > 1400.0:
      s.mag = s.mag + 0.5   #If the star is >1400pix from center, 
                            #it counts as half a mag fainter
  vlist.sort(lambda x,y: cmp(x.mag,y.mag))
  best = vlist[0]
  for i in range(len(slist)):
    if best.name == slist[i].name:
      return i
  

def test(ra,dec,epoch=2000.0):
  slist = getstars(ra,dec,epoch)
  i = 0
  for s in slist:
    if s.visible:
      print i,': Name=',s.name,' RA=',sexstring(s.pos.a),' DEC=',sexstring(s.pos.d),
      print ' Mag=%5.2f, x=%d, y=%d' % (s.mag, s.x, s.y)
    i = i + 1
  return slist


