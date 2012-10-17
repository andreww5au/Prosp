
import subprocess
import signal

import xyglobs


def handler(signum, frame):
  raise IOError("Taking too long!")


def doNOMADSearch(ra=None, dec=None, radius=0.35):
  """Use CDS client command line tool to grab stars from Vizier in a cone search
     around the given center position.
     Arguments are all in decimal degrees, including search radius.
  """
  p = subprocess.Popen(args=['findnomad1', `ra`, `dec`, '-r', `radius*60`, '-scR', '-m', '100'], 
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE )

  # Set the signal handler and a 5-second alarm
  signal.signal(signal.SIGALRM, handler)
  signal.alarm(10)
  try:
    data,errs = p.communicate()
    signal.alarm(0)          # Disable the alarm
  except IOError:
    return []
  
  candidates = []
  for line in data.split('\n'):
    if (not line.startswith('#')) and (len(line)>120):
      name = line[:12]
      ras = line[19:30]
      decs = line[30:41]
      mags = line[114:120]
      try:
        ra = float(ras)
        dec = float(decs)
      except:
        continue
      try:
        mag = float(mags)
      except:
        mag = 99.0

      cand = xyglobs.Guidestar()
      cand.name = name
      cand.pos.a = ra/15.0
      cand.pos.d = dec
      cand.epoch = 2000.0
      cand.mag = mag
      candidates.append(cand)
  return candidates
