#!/usr/bin/python

import sys
import os
import string
import traceback
from subprocess import Popen,PIPE
from numpy import *

snum = 100
keepsex = False
keepwcs = False
FWHMCUT = 1.5    #Ignore any object with an FWHM (in pixels) less than this value when calculating the median FWHM


def fwhmsky(catfile):
  try:
    ar = array(map(lambda x: map(float,x), map(string.split,open(catfile,'r').readlines()[5:])))
    fwhm = median(ar[:,3][ar[:,3] > FWHMCUT])
    sky = median(ar[:,4][ar[:,3] > FWHMCUT])
  except:
    print "imsex.py - error reading test.cat: %s" % traceback.format_exc()
    fwhm,sky = 0.0, 0.0
  return fwhm,sky


def procfile(fname):
  basefname = os.path.splitext(fname)[0]
  catfname = basefname + '.sex'
  logfname = basefname + '.wcslog'
  cmd = 'sex -c /home/observer/PyDevel/Prosp/etc/default.sex ' + fname + ';'
  sexstd,sexerr = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True).communicate()
  sostr = sexstd + sexerr
  sostru = sostr.upper()
  if ('WARNING' in sostru) or ('ERROR' in sostru) or ('INACCURACY' in sostru):
    print 'WCS fit for ' + basefname + ' failed source extraction:'
    for s in sostr.split('\n'):
      if s.strip():
        print s
    print
    os.remove('test.cat')
    return
  cmd += 'sort -n -k 3 test.cat | head -%d > %s' % (snum,catfname)
  sorstd,sorerr = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True).communicate()
#  print basefname + 'sort output: ' + sorstd + '\n---------\n' + sorerr
  cmd = 'imwgsc2 -w -e -p 0.675 -o -q rs -l -r 270 -d %s %s' % (catfname,fname)
  wcsstd,wcserr = Popen(cmd.split(), stdout=PIPE, stderr=PIPE, close_fds=True).communicate()
  fwhm,sky = fwhmsky('test.cat')
  if not keepsex:
    os.remove('test.cat')
    os.remove(catfname)
  if keepwcs:
    logf = open(logfname,'w')
    logf.write(wcsstd+'\n---------------------\n')
    logf.write(wcserr+'\n')
    logf.close()
  return fwhm,sky



if __name__ == '__main__':
  flist = sys.argv[1:]
  for f in flist:
    print os.path.basename(f) + ": FWHM=%5.2f SKY=%6.1f" % procfile(f)

