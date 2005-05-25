
import focuser
import pipeline
import ArCommands
import fits
from pipeline import dObject

coarsestep = 100
finestep = 10


def best(center = 0, step = 100, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end. Pass the image to PyRAF for analysis,
     parse the output, and return the best focus position.
  """
  totpos = 0
  for i in range(average):
    for pos in range(center-4*step, center+5*step, step)
      focuser.Goto(pos)
      ArCommands.foclines(25)
    imgname = ArCommands.foclines(-1)

    #PyRAF processing stuff here
   
    totpos = totpos + guesspos
  return totpos / average


def saveraw(fobj=None, fname=''):
  """Given a FITS file object and a filename, save the data section of the image
     (no headers) as a raw array of 32-bit floats.
  """
  if fobj and fname:
    f = open(fname,'w')
    f.write(fobj.data.astype(fits.Float32))
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


pipeline.Pipelines['FOCUS'] = FocObject

