
import time
import tempfile
import commands

from pyraf.iraf import noao
#noao.obsutil() /home/observer/PyDevel/AP72/weather.py:

import improc
import focuser
import pipeline
import Ariel
import ArCommands
import teljoy
import fits
from pipeline import dObject

try:
  import numarray
  from numarray import *
except ImportError:
  import Numeric
  from Numeric import *

focuscmd = './focusat '    #Name and first arg of C program

#coarsestep = 20
#finestep = 5 
coarsestep = 100
finestep = 25 


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


def avglists(totlist):
  """Take a list of lists of focus values and merge them, finding the
     median of N values if there is more than one measurement of FWHM
     for a given focus value.
  """
  totdict = {}
  outlist = []
  for reslist in totlist:
    for fv,fwhm in reslist:
      if totdict.has_key(fv):
        totdict[fv].append(fwhm)
      else:
        totdict[fv] = [fwhm]
  for fv in totdict.keys():
    if len(totdict[fv]) == 1:
      totdict[fv] = totdict[fv][0]
    else:
      lt = len(totdict[fv])
      totdict[fv].sort()
      if divmod(lt,2)[1] == 0:
        totdict[fv] = sum(totdict[fv][(lt/2-1):(lt/2+1)])/2.0
      else:
        totdict[fv] = totdict[fv][lt/2]
  for fv in totdict.keys():
    outlist.append( (fv,totdict[fv]) )
  outlist.sort()
  return outlist
        

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
  
def nparse_starfocus(s):
  """Parses the output of the IRAF 'starfocus' task, and returns a list 
     containing (focusvalue,FWHM) tuples, and the best focus value tuple.
  """
  retlist = []
  for l in s:
    print l
  if (s==[]) or (type(s)<>type([])):
    print "No input to parse_starfocus"
    return [],(0,0)
  if len(s)>4:
    for l in s[3:-2]:
      if len(l)>57:
        try:
          fv,fwhm = map(float,l[40:56].strip().split())
          retlist.append((fv,fwhm))
        except:
          print "Error parsing:'"+l+"'"
  print retlist
  line = s[-1].strip().split()
  if len(line)<>8:
    print "Last line wrong length in input to parse_starfocus"
    return retlist,(0,0)
  if (line[0]<>"Best") or (line[1]<>"focus") or (line[2]<>"of"):
    print "Unexpected text in input to parse_starfocus"
    return retlist,(0,0)
  else:
    return retlist, (float(line[3]), float(line[7]))
  


def center():
  """Take a single image and move the telescope to center the brightest star-like
     object in the field.
  """
  imgname = ArCommands.go()
  f = improc.FITS(imgname,'r')
  y,x = improc.findstar(f)[0]
  teljoy.offset(x+1,y+1)



def best(center = 0, step = coarsestep, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end. Pass the image to PyRAF for analysis,
     parse the output, and return the best focus position.
  """
  totres = []
  saveobject = Ariel.status.object
#  saveexp = Ariel.status.exptime  #debugging
  ArCommands.object('FOCTEST: '+`center`+' '+`step`)
#  ArCommands.exptime(saveexp*2)   #debugging
  for i in range(average):
    for p in [4,3,2,1,0,-1,-2,-3]:
      pos = center + p * step      
      focuser.Goto(pos)
      time.sleep(1)
      ArCommands.foclines(25)
#     ArCommands.exptime(saveexp)  #debugging
    focuser.Goto(center-4*step)
    imgname = ArCommands.foclines(-1)
    retlist,ftuple = analyse(imgname=imgname, center=center, step=step)
    totres.append(retlist)
  ArCommands.object(saveobject)
  return totpos / average

def custombest(center = 1000, step = coarsestep, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end.
  """
  totres = zeros([average,10,4],Float)
  saveobject = Ariel.status.object
# saveexp = Ariel.status.exptime  #debugging
  ArCommands.object('FOCTEST: '+`center`+' '+`step`)
# ArCommands.exptime(saveexp*2)   #debugging
  for i in range(average):
    for p in [4,3,2,1,0,-1,-2,-3]:
          pos = center + p * step
          focuser.Goto(pos)
          time.sleep(1)
          ArCommands.foclines(25)
    focuser.Goto(center-4*step)
    imgname = ArCommands.foclines(-1)
#    imgname='/data/rd081216/plat017.fits' # debug
#    print "Analysing image -- ",imgname # debug
    try:
         retlist=[]
         retlist,ftuple = customanalyse(imgname=imgname, center=center, step=step)
    except:
         return

#   Copy results in to hold array
    nmp=0
#   print 'image number = ', i # debug
    for j in range(10):
       nmp=nmp+1
       for k in range(4):
	  try:
            totres[i][j][k] = retlist[j][k]
          except:
            nmp=nmp-1
            break
    print '		Number of focus stars found = ', nmp
    print '		LSQ cetre estimate is ',ftuple[0],' +/- ',ftuple[1]
  ArCommands.object(saveobject)

  oname = tempfile.mktemp(suffix='.lst')
  try:
     f=open(oname,'a')
  except:
     print "Error opening the file ",oname
     return
  for i in range(average):
     for j in range(nmp):    # nmp stars in an image (0..(nmp-1))
    	 try:
      	    s = "%.4f %.4f %.4f %.4f \n" % (totres[i][j][0], totres[i][j][1], totres[i][j][2], totres[i][j][3])
      	    f.write(s)
    	 except:
      	    print "error constructing or writing s:",s
            break
  f.close()
  print oname
  try:
      commands.getstatusoutput('/home/observer/PyDevel/AP72/focussel '+oname)
  except:
      print "There is an error in focussel -- called by custombest"
      return
  print oname
  retlis=[]
  f=open(oname,'r')
  for ll in f.readlines():
      s=ll.strip().split()
      ftuple=[float(x) for x in s]
  f.close()

  fc = int(ftuple[0])
  print '		focus for this image is  =',fc  
  return fc

def analyse(imgname='', center = 0, step = coarsestep):
  """Analyse an existing image on disk, assumed to have 9 star images at different 
     focus positions. If the image was taken with the 'best' funtion (above), extract
     the focus positions from the header, otherwise use the arguments passed to the 
     function. Pass the image to PyRAF for analysis, parse the output, and return
     the best focus position.
  """
  f = improc.FITS(imgname,'r')
  obname = f.headers['OBJECT'][1:-1].strip().split()
  if len(obname) == 3:
    onm,cen,stp = tuple(obname)
    if onm == 'FOCTEST:':
      center = int(cen)
      step = int(stp)
  f.bias()
  oname = tempfile.mktemp(suffix='.fits')
  f.save(oname)
  retlist,ftuple = nparse_starfocus(noao.obsutil.starfocus(images=oname, focus=center-4*step, fstep=step, Stdout=1))
  guesspos,fwhm = ftuple
  print "Focus estimate:",guesspos
  return retlist,ftuple

def customanalyse(imgname='', center = 0, step = coarsestep):
  """Analyse an existing image on disk, assumed to have 9 star images at different 
     focus positions. If the image was taken with the 'best' funtion (above), extract
     the focus positions from the header, otherwise use the arguments passed to the 
     function. Pass the image to focusat for analysis, parse the output, and return
     the best focus position.
  """
  totres=[]
  retlist=[]
  print ' imagename ',imgname
  f = improc.FITS(imgname,'r')
  obname = f.headers['OBJECT'][1:-1].strip().split()
  if len(obname) == 3:
    onm,cen,stp = tuple(obname)
    if onm == 'FOCTEST:':
      center = int(float(cen))
      step = int(stp)
  f.bias()
  oname = tempfile.mktemp(suffix='.raw')
  print ' name of raw image ',oname
  saveraw(fobj=f,fname=oname)
  commands.getstatusoutput('/home/observer/PyDevel/AP72/focusat '+oname)
  oname = oname.replace('.raw','.dat')
  try:
    f=open(oname,'r')
  except:
    print "Can't open results file ",oname
    return
  nmb=0
  for ll in f.readlines():
       s=ll.strip().split()
       print s
       retlist=[float(x) for x in s]
       if retlist[0] != retlist[3]:	# vertex written in both columns
	  nmb=nmb+1
	  totres.append(retlist)
  f.close()
  ftuple= float(retlist[0]), float(retlist[1])
  pos = center+((ftuple[0]-totres[4][0])/25.0)*step    # check the sign on this
  epos = step*ftuple[1]/25.0
  ftuple=pos,epos	# position and error position
  fpos=totres[4][0]
  for i in range(nmb):
  	totres[i][0] = center+((totres[i][0]-fpos)/25.0)*step
  print "Focus estimate is: ",ftuple[0]," +/- ", ftuple[1]
  return totres,ftuple

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
	if (p-4*coarsestep) < 10:
	    p = 10 + 4*coarsestep
        elif (p+4*coarsestep) > 2000:
            p = 2000 - 4*coarsestep
#       q = best(center=p, step=coarsestep, average=2)   #Try -4*coarstep to +4*coarsestep, and return best pos
        q = custombest(center=p, step=coarsestep, average=2)   #Try -4*coarstep to +4*coarsestep, and return best pos
        print " Lastest coarse position is - ", q
        if abs(q-p) < (1*coarsestep):
            fnl=(q+p)/2
            done = 1
	if q < p-2*coarsestep:
            q = p-2*coarsestep
	elif q > p+2*coarsestep:
            q = p+2*coarsestep
        p = q
        tries = tries + 1

      if not done:
        print " ****** Focus not converging at coarse level, shift focuser to the start position."
        focuser.Goto(startpos)
        return
      p=fnl
      print " ****** Focus has converged at the coarse level, best coarse focus is ",p

      tries = 0
      done = 0
      bestcoarse = p   #Save the best coarse position as startpoint for fine steps
      while (tries<5) and (not done):
        print "Fine-step focus run, centered on ", p
#       q = best(center=p, step=finestep, average=2)   #Try -4*coarstep to +4*coarsestep, and return best pos
        q = custombest(center=p, step=finestep, average=3)   #Try -4*coarstep to +4*coarsestep, and return best pos
        print "Latest fine position is - ", q
        if abs(q-p) < (1.5*finestep):
          done = 1
	  fnl=(q+p)/2
	if q < p-2*finestep:
            q = p-2*finestep
	elif q > p+2*finestep:
            q = p+2*finestep
        p = q
        tries = tries + 1

      if not done:
        print " ****** Focus has not converged at the fine level, reverting to best coarse position."
        focuser.Goto(bestcoarse)
        return 

      p=fnl
      print " ****** Focus has converged, the best focus position is - ",p
      focuser.Goto(p)

    else:
      print "Errors: "+self.errors
      return self.errors

tempfile.tmpdir='/tmp'       #Set up temp file name structure
tempfile.template='foctemp'

pipeline.Pipelines['FOCUS'] = FocObject




#  totpos=zeros([nmp,4],Float)
#  for j in range(nmp):   # nmp stars in an image (0..(nmp-1))
#    if float(totres[0][j][1]) > 0.0:
#        for k in range(4):
#	    try:
#	      totpos[j][k]=totres[0][j][k]
#            except:
#              break

#  for i in range(average):
#     for j in range(nmp):
#        if float(totres[i][j][1]) > 0.0:
#           if float(totres[i][j][1]) < float(totpos[j][1]):
#               for k in range(4):
#		  try:
#                    totpos[j][k] = totres[i][j][k]
#                  except:
#                    break


#  for i in range(average):
#     for j in range(nmp):
#         for k in range(4):
#	    try:
#               totpos[j][k] = totpos[j][k]+totres[i][j][k]
#            except:
#               break

#  for j in range(nmp):   # nmp stars in an image (0..(nmp-1))
#      for k in range(4):
#	 try:
#	   totpos[j][k]=totpos[j][k]/average
#         except:
#           break
