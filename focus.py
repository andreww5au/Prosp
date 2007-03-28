
import time
import tempfile

from pyraf.iraf import noao
noao.obsutil()

import improc
import focuser
import pipeline
import ArCommands
import teljoy
import fits
from pipeline import dObject

coarsestep = 20
finestep = 5 

noao()
noao.obsutil()

noao.obsutil.starfocus.nexposures = 9
noao.obsutil.starfocus.step = 25
noao.obsutil.starfocus.direction = "+line"
noao.obsutil.starfocus.gap = "none"
noao.obsutil.starfocus.logfile = ""
noao.obsutil.starfocus.coords = "center"
noao.obsutil.starfocus.wcs = "physical"
noao.obsutil.starfocus.display = "No"
noao.obsutil.starfocus.level = 0.5
noao.obsutil.starfocus.size = "MFWHM"   #Radius, FWHM, GFWHM, MFWHM
noao.obsutil.starfocus.beta = "INDEF"
noao.obsutil.starfocus.scale = 1.0
noao.obsutil.starfocus.radius = 15
noao.obsutil.starfocus.sbuffer = 15
noao.obsutil.starfocus.swidth = 15
noao.obsutil.starfocus.saturation = 65500
noao.obsutil.starfocus.ignore_sat = "No"
noao.obsutil.starfocus.iterations = 3
noao.obsutil.starfocus.logfile = ""
noao.obsutil.starfocus.imagecur = "/dev/null"
noao.obsutil.starfocus.graphcur = "/dev/null"
noao.obsutil.starfocus.mode = "al"


def parse_starfocus(s):
  """Parses the output of the IRAF 'starfocus' task, and returns a tuple 
     containing the best focus value and best FWHM determined.
  """
  for l in s:
    print l
  if (s==[]) or (type(s)<>type([])):
    print "No input to parse_starfocus"
    return 0,0
  line = s[-1].strip().split()
  if len(line)<>8:
    print "Last line wrong length in input to parse_starfocus"
    return 0,0
  if (line[0]<>"Best") or (line[1]<>"focus") or (line[2]<>"of"):
    print "Unexpected text in input to parse_starfocus"
    return 0,0
  else:
    return float(line[3]), float(line[7])
  


def center():
  """Take a single image and move the telescope to center the brightest star-like
     object in the field.
  """
  imgname = ArCommands.go()
  f = improc.FITS(imgname,'r')
  y,x = improc.findstar(f)
  teljoy.offset(x+1,y+1)



def best(center = 0, step = coarsestep, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end. Pass the image to PyRAF for analysis,
     parse the output, and return the best focus position.
  """
  totpos = 0
  for i in range(average):
    for p in [-4,-3,-2,-1,0,1,2,3]:
      pos = center + p * step
      focuser.Goto(pos)
      time.sleep(1)
      ArCommands.foclines(25)
    focuser.Goto(center+4*step)
    imgname = ArCommands.foclines(-1)
    f = improc.FITS(imgname,'r')
    f.bias()
    oname = tempfile.mktemp(suffix='.fits')
    f.save(oname)
    guesspos,fwhm = parse_starfocus(noao.obsutil.starfocus(images=oname, focus=center-4*step, fstep=step, Stdout=1))
    print "Focus estimate:",guesspos
    totpos = totpos + guesspos
  return totpos / average


def saveraw(fobj=None, fname=''):
  """Given a FITS file object and a filename, save the data section of the image
     (no headers) as a raw array of 32-bit floats.
  """
  if fobj and fname:
    f = open(fname,'w')
    f.write(fobj.data.astype(fits.Float32).tostring())
    f.close()


class FocObject(dObject):
  def take(self):
    "Carry out a full refocus using this object."
    self.errors=""
    self.jump()
    if not self.errors:
      self.set()
      self.updatetime()
      startpos = focuser.status.pos
      print "Focussing. Original focus position: ", startpos

      tries = 0
      done = 0
      p = startpos
      while (tries<5) and (not done):
        print "Coarse-step focus run, centered on ", p
        q = best(center=p, step=coarsestep, average=2)   #Try -4*coarstep to +4*coarsestep, and return best pos
        print "Best pos is ", q
        if abs(q-p) < (3*coarsestep):
          done = 1
        p = q
        tries = tries + 1

      if not done:
        print "Focus not converging at coarse level, aborting."
        focuser.Goto(startpos)
        return 
      
      tries = 0
      done = 0
      bestcoarse = p   #Use best coarse position as startpoint for fine steps
      while (tries<5) and (not done):
        print "Fine-step focus run, centered on ", p
        q = best(center=p, step=coarsestep, average=3)   #Try -4*coarstep to +4*coarsestep, and return best pos
        print "Best pos is ", q
        if abs(q-p) < (3*finestep):
          done = 1
        p = q
        tries = tries + 1

      if not done:
        print "Focus not converging at fine level, reverting to best coarse position."
        focuser.Goto(bestcoarse)
        return 

      print "Focus converged. Best position is now ",p
      focuser.Goto(p)

    else:
      print "Errors: "+self.errors
      return self.errors

tempfile.tmpdir='/tmp'       #Set up temp file name structure
tempfile.template='foctemp'

pipeline.Pipelines['FOCUS'] = FocObject

