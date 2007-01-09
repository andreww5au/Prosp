
"""Interface to PyEphem, which must be installed into your python site-packages
   directory. You can get PyEphem from http://www.rhodesmill.org/pyephem/
   (Python version 1.5.x only). For later Python versions, use the source code
   and compile, or I have an RPM I've made up for 2.x).
"""
import time
import math
import ephem
import string


pi=math.pi
halfpi=math.pi/2.0
twopi=math.pi*2.0

obslat=ephem.degrees('-32:00:29.1')
obslong=ephem.degrees('116:8:6.1')
twilight=12/180.0*pi    #Nautical Twilight, 12 degrees below horizon
fullday=-6/180.0*pi     #Full daytime, sun 6 degrees above horizon


def mjdnow():
  year,month,day,hour,minute,second,wkday,daynum,dsf=time.gmtime(time.time())
  fday=day+hour/24.0+minute/1440.0+second/86400.0
  return ephem.fromGregorian(month,fday,year)


def radRA(raString):
# convert RA string in hours minutes and seconds to radians
  try:
    RAradians=ephem.hours(raString)
    return RAradians 
  except:
    return -1


def radDec(decString):
# convert dec string in degrees minutes and seconds to radians
  try:
    Decradians=ephem.degrees(decString)
    return Decradians 
  except:
    return -1


def tosecs(mjd):
  month,fday,year=ephem.toGregorian(mjd)
  day=int(fday)
  fhour=(fday-day)*24.0
  hour=int(fhour)
  fmin=(fhour-hour)*60.0
  min=int(fmin)
  fsec=(fmin-min)*60.0
  print year,month,day,hour,min,fsec
  t=time.mktime(year,month,day,hour,min,fsec,0,0,-1)
  t=t-time.timezone
  return t


def herenow():
  c=ephem.Observer()
  c.date=ephem.now()
  c.lat=obslat
  c.long=obslong
  c.pressure=1013.0
  c.temp=20.0
  c.epoch=2000
  return c


def isdark():
  h = herenow()
  sun = ephem.Sun()
  sun.compute(h)
  if (float(sun.alt)*180/pi) > -12:
    return 0
  else:
    return 1


def isday():
  h = herenow()
  sun = ephem.Sun()
  sun.compute(h)
  if float(sun.alt) > 0:
    return 1
  else:
    return 0


def precess(ra=0.0, dec=-0.5587):
# written by Ralph Martin April 2003
  c=herenow()
  mjd=c.mjd
  pra,pdec = ephem.ap_as(c,mjd,ra,dec)
  return pra,pdec


def altaz(ra=0.0, dec=-0.5587, epoch=2000):
  obj=ephem.FixedBody()
  obj._ra=ra
  obj._dec=dec
  obj._epoch=epoch
  obj.compute(herenow())
  return float(obj.alt)*180/pi, float(obj.az)*180/pi


def alaz(ra=0.0,dec=-0.5587):
# written by Ralph Martin April 2003
# calculate an altitude and azimuth for a given ra and dec
  c=herenow()
  pra,pdec=precess(float(ra),float(dec))  #precess ra and dec
# input ra and dec in radians 
  st=ephem.computeSiderealTime(c)  #sidereal time (hours)
  stRadians=pi*st/12.0
  H=stRadians-ra
  aa=math.cos(H)*math.sin(obslat)-math.tan(dec)*math.cos(obslat)
  aziTan=math.sin(H)/aa
  azi=math.atan(aziTan) # objects's azimuth
  altSin=math.sin(obslat)*math.sin(dec)+math.cos(obslat)*math.cos(dec)*math.cos(H)
  alt=math.asin(altSin)
  return alt,azi


def seperation (ra=0.0,deltara=0.0008,dec=-0.5587,deltadec=0.0008):
# written by Ralph Martin April 2003
# calculate a newra and newdec for a given ra/deltara and dec/deltadec
# all angles are radians. deltara and deltadec are assumed to be small(<10 arcminutes)

# near the pole the dec is small and the value of deltara is large
  if dec == halfpi or dec == -halfpi:
      newra=ra
  else:
      newra=ra+deltara/math.cos(dec)
  newdec=dec+deltadec
# check that the declination is between -90 degrees and 90 degrees
# if it isn't add 180 degrees to the ra and correct th3.14e declination
  if newdec > halfpi:   # is greater than 90 degrees
    newdec=pi-newdec
    newra=pi+newra      # add 180 degrees to the ra
  elif newdec < -halfpi: # is less than -90 degrees
    newdec=-pi-newdec
    newra=newra+pi
# check that the ra of the object is between 0 degrees and <360 degrees
  fracra,intra=math.modf(newra/twopi)
  newra=fracra*twopi
  if newra < 0.0:
    newra=twopi+newra
  return newra,newdec 


def elements(name=None):
  """Takes an optional name (if missing, you will be prompted for a name), and
     returns an ephemeris object describing that solar system object. If you
     specify the sun, moon, or any planet, the ephemeris data will be
     generated automatically, with no further input needed. If you give
     any other name, you will be prompted for an orbit type and all data.
     The object returned must be assigned to a variable, and that variable
     can then be used for position lookups, jumps, etc.
     Usage:
       frog=elements('moon')
       t2=elements("Linear/T2")
       ephemrate(frog)
       ephempos(t2)
       ephemjump(t2)
  """
  planets={'sun':ephem.SUN, 'moon':ephem.MOON, 'mercury':ephem.MERCURY,
           'venus':ephem.VENUS, 'mars':ephem.MARS, 'jupiter':ephem.JUPITER,
           'saturn':ephem.SATURN, 'uranus':ephem.URANUS,
           'neptune':ephem.NEPTUNE, 'pluto':ephem.PLUTO}
  obj=ephem.Obj()
  if not name:
    name=raw_input("Enter object name: ")
  name=string.strip(string.lower(name))
  obj.name=name
  if name in planets.keys():
    obj.any.type=ephem.PLANET
    obj.pl.code=planets[name]
    return obj
  print "Elliptical elements have a semimajor axis (a), not a period."
  print "Hyperbolic elements an eccentricity (e)."
  print "Parabolic orbits specify perihelion data, but not eccentricity."
  tp=raw_input("enter 'e', h' or 'p' for elliptical, hyperbolic, parabolic: ")
  if tp:
    tp=string.strip(string.lower(tp))[0]
  inc=float(raw_input("Inclination in degrees (i): "))
  Omega=float(raw_input("Longitude of ascending node (Omega): "))
  omega=float(raw_input("Argument of perihelion (omega): "))
  epoch=ephem.J2000
  
  if tp=='e':  
    obj.any.type=ephem.ELLIPTICAL
    T=float(raw_input("Period, in years: "))
    obj.e.a=(T*T)**(1.0/3.0)
    obj.e.e=float(raw_input("Eccentricity (e): "))
    obj.e.inc=inc
    obj.e.Omega=Omega
    obj.e.omega=omega
    obj.e.epoch=epoch
    obj.e.M=0.0
    eps=raw_input("Epoch of Perihelion (YYYY/M/D.dd or YYYY.yyyy): ")
    d,m,y=ephem.scanDate(eps,ephem.YMD)
    obj.e.cepoch=ephem.fromGregorian(d,m,y)
    
  elif tp=='h':
    obj.any.type=ephem.HYPERBOLIC
    eps=raw_input("Epoch of Perihelion (YYYY/M/D.dd or YYYY.yyyy): ")
    d,m,y=ephem.scanDate(eps,ephem.YMD)
    obj.h.ep=ephem.fromGregorian(d,m,y)
    obj.h.e=float(raw_input("Eccentricity (e): "))
    obj.h.qp=float(raw_input("Perihelion Dist. in AU (Q): "))
    obj.h.inc=inc
    obj.h.Omega=Omega
    obj.h.omega=omega
    obj.h.epoch=epoch

  elif tp=='p':
    obj.any.type=ephem.PARABOLIC
    eps=raw_input("Epoch of Perihelion (YYYY/M/D.dd or YYYY.yyyy): ")
    d,m,y=ephem.scanDate(eps,ephem.YMD)
    obj.p.ep=ephem.fromGregorian(d,m,y)
    obj.p.qp=float(raw_input("Perihelion Dist. in AU (Q): "))
    obj.p.inc=inc
    obj.p.Omega=Omega
    obj.p.omega=omega
    obj.p.epoch=epoch

  else:
    print "Invalid object type."
    return None

  return obj


def ephempos(o=None):
  """Takes an ephemeris object (created with the elements() function) and
     returns the name, RA, and Dec at the current time.
     Usage:
       frog=elements('mars')
       ephempos(frog)
  """
  try:
    ephem.computeLocation(herenow(), o)
    id=o.name
    ra=ephem.formatSexagesimal(o.any.ra/pi*12, 2, 360000)
    dec=ephem.formatSexagesimal(o.any.dec/pi*180, 3, 36000)
    return id, ra, dec
  except:
    print "Problem with the object - use 'elements' to create an object."


def ephemrate(o=None):
  """Takes an ephemeris object (created with the elements() function) and
     prints the non-sidereal offset rates for that object at the current
     time.
     Usage: 
       frog=elements('mars')
       ephemrate(frog)
  """
  try:
    hn=herenow()
    hn.mjd=hn.mjd-1.0/48.0     #Half an hour before now
    ephem.computeLocation(hn, o)
    ra1,dec1=o.any.ra,o.any.dec
    hn.mjd=hn.mjd+1.0/24.0
    ephem.computeLocation(hn, o)
    ra2,dec2=o.any.ra,o.any.dec
    print "RA  Trackrate (sec of RA per hour):", (ra2-ra1)/pi*(12*60*60)
    print "DEC Trackrate (arcsec per hour):   ", (dec2-dec1)/pi*(180*60*60)
  except:
    print "Problem with the object - use 'elements' to create an object."

