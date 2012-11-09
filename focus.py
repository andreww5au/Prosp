
import time
import tempfile
import commands

USE_IRAF = False       #Set to True to enable IRAF focus functions (adds to startup time)

if USE_IRAF:
  try:
    from pyraf.iraf import noao
    noao()
    noao.obsutil()
    GotIRAF = True
  except:
    GotIRAF = False
else:
  GotIRAF = False

import Andor
import AnCommands

import improc
import focuser
import pipeline
import teljoy
import service

FOCUSATCMD = '/home/observer/PyDevel/AP72/focusat/focusat'    #Path and filename
FOCUSSELCMD = '/home/observer/PyDevel/AP72/focussel/focussel'

coarsestep = 4000
finestep = 1000

if GotIRAF:
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
  

def centerstar():
  """Take a single image and move the telescope to center the brightest star-like
     object in the field.
  """
  imgname = AnCommands.go()
  f = improc.FITS(imgname,'r')
  y,x = improc.findstar(f)[0]
  teljoy.offset(x+1,y+1)


def AndorBest(center = 50000, step = coarsestep, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end.
  """
#Do some custom stuff here
  mode('bin2fast')
  oname = '/tmp/focuspos.lst'
  onamefit = '/tmp/focuspos.fit'
  saveobject = Andor.status.object
  sftp = 0.0
  errftp = 0.0
  AnCommands.object('FOCTEST: '+`center`+' '+`step`)
  try:
    f = open(oname,'a') #append, so we're fitting all values taken so far this focus run
  except:
    print "Error opening the file ",oname
    return

  for i in range(average):	# move the focuser take an image
    tryagain = 0
    while (tryagain <= 2):
      for p in [4,3,2,1,0,-1,-2,-3]:
        pos = center + p * step
        focuser.Goto(pos)
        time.sleep(1)
	imgname = go()
#       AnCommands.foclines(25)
	try:
            retlist,ftuple = Analyse_Ralph(imgname=imgname, center=center, step=step) # name of fits start pos  step size 
      	except:
            print "Problem analysing the image."
            tryagain = tryagain + 1
            continue
      focuser.Goto(center-4*step)
#      imgname = AnCommands.foclines(-1)
      
      if (len(retlist) != 9.0):
        print "Not enough stars in this image."
        tryagain = tryagain + 1
        continue
      print "Saved to file retlist [0] & [1], i, j", retlist[0][0]
      nmp = 0
      for j in range(9):   # read stars pos only
        nmp = nmp + 1
        try:
          print '%.4f %.4f %.4f %.4f' % (retlist[j][0], retlist[j][1], retlist[j][2], retlist[j][3])
       	  s = '%.4f %.4f %.4f %.4f \n' % (retlist[j][0], retlist[j][1], retlist[j][2], retlist[j][3])
      	  f.write(s)
        except:
          nmp = nmp - 1
          print 'Problem writing to file focupos.lst.'
          break
      print "Number of focus stars found = ", nmp
      break
    else:
      print "Tried %d times, Can't calculate focus fit." % (tryagain,)
      return
#   print "LSQ centre estimate is ",ftuple[0]," +/- ",ftuple[1]
    sftp = sftp + ftuple[0]

  f.close() # close the file oname
  AnCommands.object(saveobject)

  try:
    echeck, stuff = commands.getstatusoutput(FOCUSSELCMD + ' ' + oname)
    if (echeck != 0):
      print "Problem analysing the sample on N images."
      return
  except:
    print "There is an error in focussel -- called by FindBest in focus.py"
    return

  retlis = []
  try:
    f = open(onamefit,'r')
  except:
    print "There is an error opening file /tmp/focuspos.fit"
    return
  for ll in f.readlines():
    s = ll.strip().split()
    ftuple = [float(x) for x in s]     #This only returns the last line in the file - *check* AW
  f.close()

  fc = int(ftuple[0])
  print 'Focus for this image = ',fc
  return fc


def FindBest(center = 1000, step = coarsestep, average = 1):
  """Take images at 9 focus positions, from center-4*step to center+4*step
     At each position, open the shutter and shift the readout 25 lines, then
     read out the whole image at the end.
  """
  oname = '/tmp/focuspos.lst'
  onamefit = '/tmp/focuspos.fit'
  saveobject = Andor.status.object
  sftp = 0.0
  errftp = 0.0
  AnCommands.object('FOCTEST: '+`center`+' '+`step`)
  try:
    f = open(oname,'a') #append, so we're fitting all values taken so far this focus run
  except:
    print "Error opening the file ",oname
    return

  for i in range(average):
    tryagain = 0
    while (tryagain <= 2):
      for p in [4,3,2,1,0,-1,-2,-3]:
        pos = center + p * step
        focuser.Goto(pos)
        time.sleep(1)
        AnCommands.foclines(25)
      focuser.Goto(center-4*step)
      imgname = AnCommands.foclines(-1)
      try:
        retlist,ftuple = Analyse_Ralph(imgname=imgname, center=center, step=step)
      except:
        print "Problem analysing the sample."
        tryagain = tryagain + 1
        continue
      if (len(retlist) != 9.0):
        print "Not enough stars in this image."
        tryagain = tryagain + 1
        continue
      print "Saved to file retlist [0] & [1], i, j", retlist[0][0]
      nmp = 0
      for j in range(9):   # read stars pos only
        nmp = nmp + 1
        try:
          print '%.4f %.4f %.4f %.4f' % (retlist[j][0], retlist[j][1], retlist[j][2], retlist[j][3])
       	  s = '%.4f %.4f %.4f %.4f \n' % (retlist[j][0], retlist[j][1], retlist[j][2], retlist[j][3])
      	  f.write(s)
        except:
          nmp = nmp - 1
          print 'Problem writing to file focupos.lst.'
          break
      print "Number of focus stars found = ", nmp
      break
    else:
      print "Tried %d times, Can't calculate focus fit." % (tryagain,)
      return
#   print "LSQ centre estimate is ",ftuple[0]," +/- ",ftuple[1]
    sftp = sftp + ftuple[0]

  f.close() # close the file oname
  AnCommands.object(saveobject)

  try:
    echeck, stuff = commands.getstatusoutput(FOCUSSELCMD + ' ' + oname)
    if (echeck != 0):
      print "Problem analysing the sample on N images."
      return
  except:
    print "There is an error in focussel -- called by FindBest in focus.py"
    return

  retlis = []
  try:
    f = open(onamefit,'r')
  except:
    print "There is an error opening file /tmp/focuspos.fit"
    return
  for ll in f.readlines():
    s = ll.strip().split()
    ftuple = [float(x) for x in s]     #This only returns the last line in the file - *check* AW
  f.close()

  fc = int(ftuple[0])
  print 'Focus for this image = ',fc
  return fc


def Analyse_IRAF(imgname='', center = 0, step = coarsestep):
  """Analyse an existing image on disk, assumed to have 9 star images at different 
     focus positions. If the image was taken with the 'best' funtion (above), extract
     the focus positions from the header, otherwise use the arguments passed to the 
     function. Pass the image to PyRAF for analysis, parse the output, and return
     the best focus position.
  """
  if not GotIRAF:
    print "IRAF disabled in focus.py, function Analyse_IRAF not available"
    return
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


def Analyse_Ralph(imgname='', center = 0, step = coarsestep):
  """Analyse an existing image on disk, assumed to have 9 star images at different 
     focus positions. If the image was taken with the 'best' funtion (above), extract
     the focus positions from the header, otherwise use the arguments passed to the 
     function. Pass the image to focusat for analysis, parse the output, and return
     the best focus position.
  """
  totres=[]
  retlist=[]
  f = improc.FITS(imgname,'r')
  obname = f.headers['OBJECT'][1:-1].strip().split()
  if len(obname) == 3:
    onm,cen,stp = tuple(obname)
    if onm == 'FOCTEST:':
      center = int(float(cen))
      step = int(stp)
  f.bias()
  oname = tempfile.mktemp(suffix='.raw')
  f.saveraw(fname=oname)
  try:
    echeck,stuff = commands.getstatusoutput(FOCUSATCMD + ' ' + oname)
    if echeck != 0:
      return
  except:
    print "Can't open fits file from focus.Analyse_Ralph ",oname
    return
  oname = oname.replace('.raw','.dat')

  try:
    f = open(oname,'r')      # open .dat file
  except:
    print "Can't open results file ",oname
    return
  nmb = 0
  for ll in f.readlines():
    s = ll.strip().split()
    print s
    retlist = [float(x) for x in s]
    if retlist[0] != retlist[3]:	# vertex written in both columns
      nmb = nmb + 1
      totres.append(retlist)
  f.close() #close .dat file

  ftuple = float(retlist[0]), float(retlist[1])
  pos = center + ((ftuple[0]-totres[4][0])/25.0)*step    # check the sign on this
  epos = step*ftuple[1]/25.0
  ftuple = pos,epos	# position and error position
  fpos = totres[4][0]
  for i in range(nmb):
    totres[i][0] = center+step*round((totres[i][0]-fpos)/25.0)
# print "Focus estimate is: ",ftuple[0]," +/- ", ftuple[1]
  return totres,ftuple


class FocObject(pipeline.dObject):
  def take(self):
   #Save the existing camera state
   oldmode = status.mode
   oldfilename = status.filename
   oldexptime = status.exptime

    "Carry out a full refocus using this object."
    self.errors = ""
    self.jump()

    if not self.errors:
      self.fileprefix()   # Set the filename prefix (everything except the auto-incrementing image number)
      self.set()
      self.updatetime()
      oname = '/tmp/focuspos.lst'
      f = open(oname,'w')    # Delete the contents of the focus list file, make a clean start to the fitting.
      f.close()

#     centerstar()   # center the star
      startpos = focuser.status.pos
      tries = 0
      done = False
      p = startpos
      foclist = []
      while (tries<5) and (not done):
        if (p-4*coarsestep) < 10:
          p = 10+4*coarsestep
        elif (p+4*coarsestep) > 104000:
          p = 104000-4*coarsestep
        try:
          q = FindBest(center=p, step=coarsestep, average=1)   #Try -4*step to +4*step
        except:
          print "Coarse Focus was NOT determined -- object may not be centred or it is cloudy."
          focuser.Goto(startpos)
          return
          
        print "Latest coarse position is %d for try number %d" % (q,tries)
        foclist.append(q)
        # See if any of the previous estimates are with one coarsestep of the current value
        for focvalue in foclist[:-1]:   # Loop through previous focus value estimates
          if abs(q-focvalue) < (1.0*coarsestep): # found coarse focus?
            fnl = (q+focvalue)/2.0
            done = True
        # Make sure the new focus centre value is inside the range tested in this run
        if q < p-4*coarsestep:
          q = p-4*coarsestep
        elif q > p+4*coarsestep:
          q = p+4*coarsestep
        tries = tries + 1
        p = q
       
      if not done:
        print "****** Focus didn't converge at coarse level, shift focuser to the start position."
        focuser.Goto(startpos)
	#Restore the original camera state
	exptime(oldexptime)
	filename(oldfilename)
	mode(oldmode)
        return
      p = fnl #best estimate of coarse focus
      print "****** Focus has converged at the coarse level using %d sets of images, coarse focus is %d" % (tries, p)
       
      foclist = []
      tries = 0
      done = False
      bestcoarse = p  #Save the best coarse position as startpoint for fine steps
      while (tries<4) and (not done):
#       print "Fine-step focus run, centered on ", p
        if (p-4*finestep) < 10:
          p = 10+4*finestep
        elif (p+4*finestep) > 2000:
          p = 2000-4*finestep
        try:
          q = FindBest(center=p, step=finestep, average=1)  #Try -4*finestep to +4*finestep
#         q = best(center=p, step=finestep, average=2)
        except:
          print "Fine Focus was not determined -- object may not be centred or it is cloudy."
          focuser.Goto(bestcoarse)
          return
           
        foclist.append(q)
        print "Latest fine position is %d for try number %s" % (q,tries)
        for focvalue in foclist[:-1]:   # Loop through previous focus value estimates
          if abs(q-focvalue) < (1.0*finestep): # found fine focus?
            fnl = (q+focvalue)/2.0
            done = True
        # Make sure new fine focus centre value is inside the central half of the range tested in this run
        if q < p-2*finestep:
          q = p-2*finestep
        elif q > p+2*finestep:
          q = p+2*finestep
        p = q
        tries = tries + 1
            
      if not done:
        print " ****** Focus has NOT converged at the fine level, reverting to best coarse position."
        focuser.Goto(bestcoarse)
        service.LastFocusTime = time.time()
	#Restore the original camera state
	exptime(oldexptime)
	filename(oldfilename)
	mode(oldmode)
        return 
        
      p = fnl
      print " ****** Focus has converged using 2 sets of images, best focus is ",p
      focuser.Goto(p+20)
      service.LastFocusTime = time.time()
    else:
      print "Errors: " + self.errors
      return self.errors

tempfile.tmpdir = '/tmp'       #Set up temp file name structure
tempfile.template = 'foctemp'

pipeline.Pipelines['FOCUS'] = FocObject




