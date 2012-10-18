#!/usr/bin/python

import sys
import os
from subprocess import Popen,PIPE

flist = sys.argv[1:]

snum = 100
keepsex = False
keepwcs = False

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
  cmd = 'imwua2 -w -o -p 0.6 -d %s -e %s' % (catfname,fname)
  wcsstd,wcserr = Popen(cmd.split(), stdout=PIPE, stderr=PIPE, close_fds=True).communicate()
  os.remove('test.cat')
  if not keepsex:
    os.remove(catfname)
  if keepwcs:
    logf = open(logfname,'w')
    logf.write(wcsstd+'\n---------------------\n')
    logf.write(wcserr+'\n')
    logf.close()



for f in flist:
  procfile(f)

