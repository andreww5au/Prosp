
import os
import string
import glob
import types
import operator
import time

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
