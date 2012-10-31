
import glob
import operator
import time
import math
import logging

CAMERA = 'Andor'
#CAMERA =  'Apogee'

CHILLER = False    #True if chiller unit connected.
FOCUSER = True    #True if focuser unit connected.
OPTICALCOUPLER = True
#OPTICALCOUPLER = False

LOGLEVEL = logging.DEBUG           #Master log level - messages below this will be ignored.
LOGLEVEL_CONSOLE = logging.INFO      #Minimum log level for console messages (INFO, DEBUG, ERROR, CRITICAL, etc)
LOGLEVEL_LOGFILE = logging.DEBUG       #Minimum log level for logfile
SLOGFILE = "/tmp/Andor.log"         #Log file for server process (Andor.py)
CLOGFILE = "/tmp/Prosp.log"         #Log file for client process (th rest of Prosp)


class NullHandler(logging.Handler):
  def emit(self, record):
    pass

logger = None
slogger = None
def InitLogging():
  global logger, slogger
  #create two formatters, one with timestamps for files, the other without, for console
  filef = logging.Formatter("%(asctime)s: %(name)s-%(levelname)s  %(message)s")
  conf = logging.Formatter("%(name)s-%(levelname)s  %(message)s")

  # create two file handlers, for server and client
  try:
    sfh = logging.FileHandler(SLOGFILE)
    cfh = logging.FileHandler(CLOGFILE)
  except IOError:    #Can't open a logfile for writing, probably the wrong user
    sfh = NullHandler()
    cfh = NullHandler()

  sfh.setLevel(LOGLEVEL_LOGFILE)
  sfh.setFormatter(filef)
  cfh.setLevel(LOGLEVEL_LOGFILE)
  cfh.setFormatter(filef)

  # create console handler with a higher log level, and without timestamps
  conh = logging.StreamHandler()
  conh.setLevel(LOGLEVEL_CONSOLE)
  conh.setFormatter(conf)

  # create global logger object
  logger = logging.getLogger("Prosp")
  logger.setLevel(LOGLEVEL)
  slogger = logging.getLogger("Andor")
  slogger.setLevel(LOGLEVEL)

  # add the handlers to the logger
  logger.addHandler(cfh)
  logger.addHandler(conh)
  slogger.addHandler(sfh)
  slogger.addHandler(conh)


InitLogging()

#filters=['Clear', 'Red', '4450', '9500', 'Visual', 'Infrared', 'Empty', '7260']
#Old PLANET filter set, plus Peter's narrowband filters. Clear slot was empty,
#not glass filter.

#filters=['Clear','Red','Ultraviolet','Blue','Visual','Infrared','Empty','Hole']
#New filter set inserted 15/1/2008. New Clear filter in glass included.
#Two empty slots labeled 'Empty' and 'Hole' so they don't have the same
#first letter.

#filters=['Empty','Red','3871','4060','4450','5140','5260','Hole']
#Dave Schleiker's narrowband filter set, inserted 2008/01/30

filters=['Clear','Red','NCN','Blue','Visual','Infrared','Empty','Hole']
#New filter set replaced 2008/02/19 but with Dave's 3871 (NCN) filter instead 
#of Ultraviolet


def filtid(s):
  """Given a filter name, make sure it's in the current filter set, and return
     a filter ID for it. If the filter name is a string, this is the first letter. 
     If it's a narrow-band filter where the name is starts with digits, the ID is
     the entire filter name.
  """
  s = s.strip().lower().capitalize()
  if not s:
    return ''
  sn = ''
  for fn in filters:
    fns = fn.strip().lower().capitalize()
    if (s == fns) or (len(s)==1 and s[0].isalpha() and (s[0] == fns[0])):
      sn = fns
  if not sn:
    return ''
  else:
    if sn[0].isdigit():
      return sn
    else:
      return sn[0]


def filtname(filt=2):
  """Return full filter name given slot number.
     eg: filtname(6)
  """
  if (filt<1) or (filt>8):
    return 'Error'
  return filters[filt-1]


def filtnum(fname):
  "Return filter slot number given a filter ID"
  if fname[0].isdigit():
    id = fname
  else:
    id = fname[0].upper()
  num = 2   #Default if not found
  for nm in filters:
    if (id==nm) or (id==nm[0]):
      num = filters.index(nm)+1
  return num


def distribute(fpat='',function=None,args=None):
  """Takes a single string or a list of strings. Calls 'function' on each file
     specified after looping over the list, and expanding each string for
     wildcards using 'glob'.
     You probably don't want to use this unless you're writing your own
     functions to handle files.
     eg: distribute('/data/myimg*.fits',display)
  """
  donelist=[]
  if type(fpat) <> list:
    fpat=[fpat]
  t1 = reduce(operator.concat,[f.split() for f in fpat])
  t2 = reduce(operator.concat,[glob.glob(f) for f in t1])
  for n in t2:
    if args:
      resn=function(n,args)
    else:
      resn=function(n)
    if resn:
      donelist.append(resn)

  if len(donelist)==0:
    return ''
  elif len(donelist)==1:
    return donelist[0]
  else:
    return donelist


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
    value = value.strip()
    components = value.split(':')
    if len(components)<>3:
      components=value.split(' ')
    if len(components)<>3:
      return None

    h,m,s = tuple([s.strip() for s in components])
    sign=1
    if h[0]=="-":
      sign=-1
    return float(h) + (sign*float(m)/60.0) + (sign*float(s)/3600.0)
  except:
    return None


def julday(data=None):
  "Return full Julian Day for a given time tuple. Use current date/time if no arg given"
  if data:
    year,month,day,hour,minute,second,wd,dnum,dst = data
  else:
    year,month,day,hour,minute,second,wd,dnum,dst = time.gmtime(time.time())

  if (month == 1) or (month == 2):
    year = year - 1
    month = month + 12

  A = math.floor(year/100.0);
  B = 2 - A + math.floor(A/4.0);
  jd = math.floor(365.25 * year) + math.floor(30.6001 * (month + 1))
  jd = jd + day + (hour + (minute/60.0) + (second/3600.0)) / 24.0
  jd = jd + 1720994 + B + 0.5;
  return jd
  

def pjd(data=None):
  return julday(data) - 2450000.0


def caldate(JD=0):
  "Return tuple (year,month,day) for full Julian Day. Use current date/time if no arg given"
  if not JD:
    JD=julday()
  Z = int(JD + 0.5)
  F = (JD + 0.5) - int(JD + 0.5)
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
  if E<13.5:
    month = E - 1
  else:
    month = E - 13
  if month>2.5:
    year = C - 4716
  else:
    year = C - 4715
  return (year,month,day)



def formatpjd(lpjd=None):
  """Returns a formatted string for a given PJD. Use the current date if arg=None
     if the argument can not be converted to a float, return it unchanged.
  """
  if lpjd==None:
    lpjd=pjd()
  try:
    lpjd=round(float(lpjd), 1)
  except:
    return `lpjd`
  year,month,day=caldate(lpjd+2450000)
  month=month-1  #List elements numbered from 0 not 1
  months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct',
          'Nov','Dec']
  return `round(lpjd,1)`+" ("+months[month]+" "+`round(day,1)`+")"
