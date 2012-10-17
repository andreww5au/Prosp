
import time
import math
import string

hole_radius = 0.025   #in same units as focal length}
Xmax = 0.04       #max and min values for real XY stage}
Ymax = 0.03       #in same units as focal length}
Xmin = -0.037
Ymin = -0.026

X_Steps = 40000   # Number of steps (+ only) on }
Y_Steps = 40000   #XY stage per unit in X and Y directions}
                  #one 'unit' is the same unit as that measuring focal length}


class Coord:
  def __init__(self, d=0.0, a=0.0):
    self.d = d
    self.a = a


class Guidestar:
  def __init__(self, name='', pos=None, epoch=2000.0, mag=0.0):
    self.name = name
    if pos:
      self.pos = pos
    else:
      self.pos = Coord()
    self.epoch = epoch
    self.mag = mag
    self.visible = 0
    self.x, self.y = 0,0


def sexstring(value=0,sp=':'):
  """Convert the floating point 'value' into a sexagecimal string.
     The character in 'sp' is used as a spacer between components. Useful for
     within functions, not on its own.
     eg: sexstring(status.TJ.ObjRA,' ')
  """
  try:
    aval=abs(value)
    error=0
  except:
    aval=0.0
    error=1
  if value<0:
    outs='-'
  else:
    outs=''
  D=int(aval)
  M=int((aval-float(D))*60)
  S=float(int((aval-float(D)-float(M)/60)*36000))/10
  outs=outs+str(D)+sp+str(M)+sp+str(S)
  if error:
    return ''
  else:
    return outs


def stringsex(value=""):
  """Convert the sexagesimal coordinate 'value' into a floating point
     result. Handles either a colon or a space as seperator, but currently
     requires all three components (H:M:S not H:M or H:M.mmm).
  """
  try:
    components=value.split(':')
    if len(components)<>3:
      components=value.split(' ')
    if len(components)<>3:
      return None

    h,m,s=tuple(map(string.strip, components))
    sign=1
    if h[0]=="-":
      sign=-1
    return float(h) + (sign*float(m)/60.0) + (sign*float(s)/3600.0)
  except:
    return None


# Nothing past here is actually used by the guidestar code (yet)
# I scavenged it from other code in case it might be useful for 
# debugging

J2000 = 2451544.5

def juldate(data=None):
  "Return full Julian Day for a given time tuple. Use current date/time if no arg given"
  if data:
    year,month,day,hour,minute,second,wd,dnum,dst = data
  else:
    year,month,day,hour,minute,second,wd,dnum,dst = time.gmtime(time.time())

  if (month == 1) or (month == 2):
    year = year - 1
    month = month + 12

  A = math.floor(year/100.0)
  B = 2 - A + math.floor(A/4.0)
  jd = math.floor(365.25 * year) + math.floor(30.6001 * (month + 1))
  jd = jd + day + (hour + (minute/60.0) + (second/3600.0)) / 24.0
  jd = jd + 1720994 + B + 0.5
  return jd
  

def caldate(jd=0):
  "Return tuple (year,month,day) for full Julian Day. Use current date/time if no arg given"
  if not jd:
    jd = juldate()
  Z = int(jd + 0.5)
  F = (jd + 0.5) - int(jd + 0.5)
  if Z<2299161:
    A = Z
  else:
    alpha = int( (Z - 1867216.25)/36524.25 )
    A = Z + 1 + alpha - int(alpha/4)
  B = A + 1524
  C = int( (B - 122.1)/365.25 )
  D = int( 365.25*C )
  E = int( (B - D)/30.6001 )
  day = B - D - int(30.6001*E) + F
  if E < 13.5:
    month = E - 1
  else:
    month = E - 13
  if month > 2.5:
    year = C - 4716
  else:
    year = C - 4715
  return (year,month,day)


def jd_year(jd=None):
  "Turn a JD into a decimal year"
  if not jd:
    jd = juldate()
  y,m,d = caldate(jd)
  if y == -1:
    y = -2
  e0 = juldate(data=(y,1,1,0,0,0,0,0,0))
  e1 = juldate(data=(y+1,1,1,0,0,0,0,0,0))
  return y + (jd-e0)/(e1-e0)

def year_jd(year=None):
  "Turn a decimal year into a JD"
  if not year:
    year = jd_year()   #Use current time as JD if not given
  jd = J2000 - (2000.0-year)*365.246
  return jd

def JDtoT(jd=None):
  "Return T value, decimal century, from JD"
  return (float(jd)-2415020.0)/36525
                                                                                
def inrange(v=0, r=360.0):
  "ensures that v is in the range 0 <= v < r"
  return v - r*math.floor(v/r)

def dsin(x):
  return math.sin(float(x)/180.0*math.pi)

def dcos(x):
  return math.cos(float(x)/180.0*math.pi)

def dtan(x):
  return dsin(x)/dcos(x)

def dasin(x):
  return math.asin(x)*180/math.pi

def datan2(y,x):
  return math.atan2(y,x)*180/math.pi


def precess(jd1=None, jd2=None, ra=None, dec=None):
  "Precess coords (in degrees) from epoch jd1 to jd2"
  alpha_in = ra
  delta_in = dec
  
  #precession progresses about 1 arc second in .047 years */
  #From from_equinox to 2000.0 */
  if (abs(jd1 - J2000)/365.25) > .04:
    T = JDtoT(jd1) - 1
    zeta_A  = 0.6406161* T + 0.0000839* T*T + 0.0000050* T*T*T
    z_A     = 0.6406161* T + 0.0003041* T*T + 0.0000051* T*T*T
    theta_A = 0.5567530* T - 0.0001185* T*T - 0.0000116* T*T*T
                                                                                
    A = dsin(alpha_in - z_A) * dcos(delta_in)
    B = ( dcos(alpha_in - z_A) * dcos(theta_A) * dcos(delta_in)
                               + dsin(theta_A) * dsin(delta_in) )
    C = (-dcos(alpha_in - z_A) * dsin(theta_A) * dcos(delta_in)
                              + dcos(theta_A) * dsin(delta_in) )
                                                                                
    alpha2000 = datan2(A,B) - zeta_A
    alpha2000 = inrange (alpha2000, 360.0)
    delta2000 = dasin(C)
  else:
    alpha2000 = alpha_in
    delta2000 = delta_in

  #From 2000.0 to to_equinox */
  if (abs(jd2 - J2000)/365.25) > .04:
    T = JDtoT(jd2) - 1
    zeta_A  = 0.6406161* T + 0.0000839* T*T + 0.0000050* T*T*T
    z_A     = 0.6406161* T + 0.0003041* T*T + 0.0000051* T*T*T
    theta_A = 0.5567530* T - 0.0001185* T*T - 0.0000116* T*T*T
                                                                                
    A = dsin(alpha2000 + zeta_A) * dcos(delta2000)
    B = ( dcos(alpha2000 + zeta_A) * dcos(theta_A) * dcos(delta2000)
         - dsin(theta_A) * dsin(delta2000) )
    C = ( dcos(alpha2000 + zeta_A) * dsin(theta_A) * dcos(delta2000)
         + dcos(theta_A) * dsin(delta2000) )
                                                                                   
    alpha = datan2(A,B) + z_A
    alpha = inrange(alpha, 360.0)
    delta = dasin(C)
  else:
    alpha = alpha2000
    delta = delta2000
                                                                                
  return alpha, delta

