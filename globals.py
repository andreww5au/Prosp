
import os
import string
import glob
import types
import operator
import time
import math

statusfile='/tmp/ProspLog'
errorfile='/tmp/ProspErrors'

try:
  sfile=open(statusfile,'a')
  efile=open(errorfile,'a')
except:
  sfile=open('/dev/null','a')
  efile=open('/dev/null','a')

filters=['Clear', 'Red', '4450', '9500', 'Visual', 'Infrared', '5260', '7260']


def filtname(filt=2):
  """Return filter name given number.
     eg: filtname(6)
  """
  if (filt<1) or (filt>8):
    return 'Error'
  return filters[filt-1]


def distribute(fpat='',function=None,args=None):
  """Takes a single string or a list of strings. Calls 'function' on each file
     specified after looping over the list, and expanding each string for
     wildcards using 'glob'.
     You probably don't want to use this unless you're writing your own
     functions to handle files.
     eg: distribute('/data/myimg*.fits',display)
  """
  donelist=[]
  if type(fpat)<>types.ListType:
    fpat=[fpat]
  t1=reduce(operator.concat,map(string.split,fpat))
  t2=reduce(operator.concat,map(glob.glob,t1))
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
  outs=outs+`D`+sp+`M`+sp+`S`
  if error:
    return ''
  else:
    return outs


def swrite(s='swrite called with null string.'):
  "Write a status message to screen and status logfile"
  sfile.write(time.strftime("%Y%m%d%H%M%S:",time.localtime(time.time()))+s+'\n')
  print s


def ewrite(s='ewrite called with null string.'):
  "Write an error message to screen, status log, and error log "
  sfile.write(time.strftime("%Y%m%d%H%M%S:",time.localtime(time.time()))+s+'\n')
  efile.write(time.strftime("%Y%m%d%H%M%S:",time.localtime(time.time()))+s+'\n')
  print s


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
  jd = jd + day + (hour + (minute/60.0) + (second/360.0)) / 24.0
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
