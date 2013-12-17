
#Local customisation:

PipeHome='/home/observer'   #Root of the PLANET directory tree

pySIShome = '/home/observer/pySIS2.4'

#defmethod = 'dophot'
defmethod = 'pysis'

HoldingDir='/data/PLANET'   #Directory to leave reduced images if there isn't
                            #a Working field set up for them yet.

site='W'             #Prefix for all local images/archives
sitename = 'Perth'

ARTEMISPWFILE = ''
ARTEMISLIST = ''
FID = 0
FRA = 1
FDEC = 2
FEXP = 3
FSI = 4
FMAG = 5
FRATIO = 6
FFLAG = 7

PlanetUser=''
PlanetPassword=''
PlanetPrioritiesPage=''

import re
_regsearch=re.compile("NumStar=(?P<nstar>[0-9]*) .*?X=(?P<x>[0-9,.]*),Y=(?P<y>[0-9,.]*).*?TypRef=(?P<type>[0-9]*)", re.DOTALL)

#**********************************************************
#        End of local customisation                       *
# (See Pevent class for any possible directory structure *
# changes.)                                               *
#**********************************************************

try:
  import matplotlib
  from matplotlib import interactive
  interactive(True)
  matplotlib.use('GTKAgg')
#  from pylab import errorbar, axis, show
except:
  print "No display for GTK"

import improc
import os
import string
import dircache
import glob
import threading
import commands
import urllib
from globals import *
from os.path import basename,samefile,exists,splitext
import xpa
import fcntl

import objects
import pipeline
from pipeline import dObject


os.environ["http_proxy"]="http://squid:3128"


def _queuehandler():
  """Runs in a background thread sending items in the 'queue' list to os.system
     each in their own xterm window, one by one.
  """
  while queue:
    object,method,args,kwds=queue.pop()
    if object:
      if hasattr(object,method):
        m=getattr(object,method)
        if callable(m):
          m(*args, **kwds)
    else:
      if callable(method):
        method(*args,**kwds)


def _addqueue(object,method,args,kwds):
  """Adds a new command line to the queue. If the queue handler is not running,
     create a new handler thread and start it to process the queue.
     Each queue item is a tuple of (object,method,*args,**kwds) (args is a list, kwds a dict)
     If object is None, call method as a normal function, otherwise call it
     as a method of the specified object instance.
  """
  global queuethread
  queue.insert(0,(object, method, args, kwds))
  if not queuethread.isAlive():
    queuethread=threading.Thread(target=_queuehandler,
                                 name="PLANET Queue handler")
    queuethread.setDaemon(0)   #Prosp can't quit till this thread finishes
    queuethread.start()


def _pnparse(obj):
  """
     If obj is a PLANET name, then code,yr,num,filt and imgnum are returned as
     a tuple.  PLANET names have:

  -an optional initial site letter, eg 'W', henceforth ignored.
  -the letter O, M, K, or E.
  -the letter B, S, or L
  -two digit year, equal to '98', '99', '2K', '01-09' or '10-19'
  -a two to four digit event number (a leading 0 is added for two digit cases)
  -an optional filter letter, assumed to be I if missing. If an image 
     number is present, the filter is _not_ optional.
  -an optional image number, returned as '' if missing.

  If the argument is not a valid PLANET name, then None is returned. Check
  that the result is true before attempting to resolve the tuple.

  This should only be used by the constructor in the 'Pevent' class, use
  Pevent for all working code.
  """
  pl=0    #Start by assuming the argument is _not_ valid
  obj=string.upper(obj)

  if len(obj)>1:       #If the first letter is our site, strip it off.
    if obj[0]==site:
      obj=obj[1:]

  if len(obj)>0:             #Second letter must be O, M, or E
    if obj[0]=='O' or obj[0]=='M' or obj[0]=='E' or obj[0]=='K':
      pl=1                   #Seems to be valid so far...

  if len(obj) < 6:
    pl=0                #If it's too short, it can't be valid
  else:
    if (obj[1]<>'B') and (obj[1]<>'S') and (obj[1]<>'L'):
      pl=0              #if the second letter isn't B,S, or L it's not valid
    yr=obj[2:4]         #Test the 3rd and 4th chars for a valid year
    if (yr<>'98') and (yr<>'99') and (yr<>'2K') and ((yr[0]<>'0' and yr[0]<>'1') or 
                                               (yr[1] not in '0123456789')):
      pl=0 

    tail=obj[4:]       #Take the rest of the name
    num=''
    im=''
    filt=''
    gf=0

    #Assign all digits before the first non-digit to 'num', and all
    #digits after the first non-digit to 'im'. The non-digit/s are
    #stored in 'filt'.
    for a in tail:
      if a in string.digits and not gf:
        num=num+a
      else:
        gf=1
        if a in string.digits:
          im=im+a
        else:
          filt=filt+a

    if len(filt)<>0 and len(filt)<>1:
      pl=0       #If filter field is present, but >1 letter, it's invalid
      filt=''

    if (tail<>num+filt+im) or (len(num) > 4) or (len(num) < 2):
      pl=0   #Invalid if any extra junk, or if num/im are too long/short

  if pl==1:
    code=obj[:2]    #eg 'OB'
    if filt=='':    #Default to I
      filt='I'
    if len(num)<3:
      num=string.zfill(num,3)     #Add leading zeroes with zfill
    if im<>'':                  #If there's an image number, pad it out
      im=string.zfill(im,3)
    return (code,yr,num,filt,im)
  else:
    return None


def _nonpnparse(obj):
  """
     If obj is a non-PLANET name that fits the DoPhot reduction object name scheme,
     then code,yr,num,filt and imgnum are returned as
     a tuple.  PLANET scheme names have:

  -an optional initial site letter, eg 'W', henceforth ignored.
  -the letter P.
  -an event type code (any number of letters)
  -an event number (any number of digits)
  -an optional filter letter, assumed to be I if missing. If an image 
     number is present, the filter is _not_ optional.
  -an optional image number, returned as '' if missing.

  If the argument doesn't fit, then None is returned. Check
  that the result is true before attempting to resolve the tuple.

  This should only be used by the constructor in the 'Pevent' class, use
  Pevent for all working code.
  """
  pl=0    #Start by assuming the argument is _not_ valid
  obj=string.upper(obj)

  if len(obj)>1:       #If the first letter is our site, strip it off.
    if obj[0]==site:
      obj=obj[1:]

  if len(obj)>0:             #Second letter must be P
    if obj[0]=='P':
      pl=1                   #Seems to be valid so far...

  tail=obj[1:]       #Take the rest of the name
  code=''
  num=''
  yr='XX'
  im=''
  filt=''
  gc=0
  gf=0

  #Assign all non-digits before the first digit to 'code', all digits before the next
  #non-digit to 'num', the next non-digit to 'filt', and any traiing digits to 'im'

  for a in tail:
    if a not in string.digits and not gc:
      code=code+a
    elif a in string.digits and not gf:
      gc=1
      num=num+a
    else:
      gf=1
      if a in string.digits:
        im=im+a
      else:
        filt=filt+a

  if len(filt)<>0 and len(filt)<>1:
    pl=0       #If filter field is present, but >1 letter, it's invalid
    filt=''

  if (tail<>code+num+filt+im):
    pl=0   #Invalid if any extra junk

  if pl==1:
    if filt=='':    #Default to I
      filt='I'
    if im<>'':                  #If there's an image number, pad it out
      im=string.zfill(im,3)
    return (code,yr,num,filt,im)
  else:
    return None



def _vfile(fname):
  """Returns its argument if that file or directory exists, otherwise returns
     a null string.
  """
  if exists(fname):
    return fname
  else:
    return ''


class Pevent:
  """Defines a class for storing a valid PLANET field or file specifier.
     The argument is parsed according to the rules defined above (see
     'pnparse') and the information is used to fill in various fields in
     the object, including base, Archive, image, etc directories, the 
     name of the template image, and two flags. The 'valid' flag is true 
     if a valid directory has been created for this object under 'PipeHome',
     and the 'good' flag is true if a file called 'good' exists in the 
     objects base directory. The 'good' flag (and file) indicates that the 
     field has a working reduction pipeline, and images should be processed
     and archived for this field. If not defined, the fields default to ''.

     This function will probably need to be customised for each local
     directory layout, but changes to any other code to cope with
     differing directories should be very minimal. 

  """
  def __init__(self,str=''):
    "Constructor for Pevent, called when a 'var=Pevent(str)' is executed"
    resp = _pnparse(str)    #Parse the argument string
    resn = _nonpnparse(str)  #See if it's a non-PLANET event but in the name scheme
    if resp:          #If it's a valid planet name, assign fields
      self.valid = 1
      self.planet = 1
      self.code,self.yr,self.num,self.filt,self.imgnum = resp
      self.root = self.code + self.yr + self.num
      self.name = self.code + '-' + self.yr + '-' + self.num
      self.lockfile = None

      self.basedir = _vfile(PipeHome+'/'+self.yr+'Season/'+self.root)
      self.imdir = _vfile(self.basedir+'/Images')
      self.rawdir = _vfile(self.basedir+'/Raw')
      self.paramdir = _vfile(self.basedir+'/Par')
      self.workdir = _vfile(self.basedir+'/Work')
      self.archivedir = _vfile(self.basedir+'/Archive')
      self.pysisdir = _vfile(self.basedir+'/pysis')

      self.refresh()   #Load current data (template, flags, etc ) from files in event dir
    elif resn:
      self.valid = 1
      self.planet = 0
      self.code,self.yr,self.num,self.filt,self.imgnum = resn
      self.root = 'P' + self.code + self.num
      self.name = 'P' + '-' + self.code + '-' + self.num
      self.lockfile = None

      self.basedir = _vfile(PipeHome+'/'+self.yr+'Season/'+self.root)
      self.imdir = _vfile(self.basedir+'/Images')
      self.rawdir = _vfile(self.basedir+'/Raw')
      self.paramdir = _vfile(self.basedir+'/Par')
      self.workdir = _vfile(self.basedir+'/Work')
      self.archivedir = _vfile(self.basedir+'/Archive')
      self.pysisdir = _vfile(self.basedir+'/pysis')

      self.refresh()   #Load current data (template, flags, etc ) from files in event dir
    else:
      self.valid = 0     #Otherwise flag it as invalid
      self.planet = 0
      #Set all fields empty in case something tries to access them
      self.code,self.yr,self.num,self.filt,self.imgnum = '','','','',''
      self.root = ''
      self.basedir = ''
      self.imdir = ''
      self.rawdir = ''
      self.paramdir = ''
      self.workdir = ''
      self.archivedir = ''
      self.pysisdir = ''
      self.photmethod = defmethod
      self.working = 0
      self.good = 0
      self.template = {}
      self.archmax = {}
      self.pytemplate = ''


  def refresh(self):
    "Load current data (template, flags, etc ) from files in event dir"
    self.working = exists(self.basedir)
    self.good = exists(self.basedir+'/good')
    if exists(self.basedir+'/usepysis'):
      self.photmethod = 'pysis'
    elif exists(self.basedir+'/usedophot'):
      self.photmethod = 'dophot'
    else:
      self.photmethod = defmethod
    self.template={}
    tl = glob.glob(self.basedir+'/Tplate*')
    for tn in tl:
      f = open(tn,'r')
      if tn == 'Tplate':
        self.template[self.filt] = string.strip(f.readline())
      else:
        self.template[tn[-1]] = string.strip(f.readline())
      f.close()
    if exists(self.pysisdir+'/ref_list'):
      f = open(self.pysisdir+'/ref_list','r')
      self.pytemplate = map(string.strip, f.readlines())
      f.close()
    else:
      self.pytemplate = ''
    self.archmax = {}
    nal = glob.glob(self.basedir+'/num*.archived')
    for na in nal:
      f = open(na,'r')
      if os.path.basename(na) == 'num.archived':
        self.archmax[self.filt] = int(string.strip(f.readline()))
      else:
        self.archmax[os.path.basename(na)[3]] = int(string.strip(f.readline()))
      f.close()
  

  def lock(self, block=1):
    self.lockfile=open(self.basedir+'/lock','w')
    mode=fcntl.LOCK_EX
    if not block:
      mode=mode+fcntl.LOCK_NB
    print "Acquiring lock on "+self.root
    fcntl.flock(self.lockfile.fileno(), mode)


  def unlock(self):
    if self.lockfile:
      fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_UN)
      self.lockfile.close()
      os.remove(self.basedir+'/lock')
      self.lockfile=None
      print "Unlocked "+self.root


  def dotemplate(self, popup=1):
    """Carries out a deep DoPhot reduction on the specified image, and record 
       the name of the template used for use in further processing.
       If the option 'popup' is true (by default), run the command in an xterm, 
       otherwise it produces output to stdout.
       The return value is 1 if successful, 0 otherwise. This return value does
       not take the dophot reduction process into account, only the initial
       argument parsing.
    """
    if (not self.valid) or (not self.working):
      logger.error("Not a valid PLANET event with pipeline directory tree")
      return 0
    if not self.imgnum:
      logger.error("A valid image number and filter must be specified for an event template")
      return 0

    tname=site+self.root+self.filt+self.imgnum
    cline="source "+self.basedir+"/setup ; "
    cline=cline+"template "+tname+" "

    self.lock()
    self.refresh()  #Get changes to event data since instance was created

    if popup:   
      cline=cline+" ; echo Finished... ; sleep 30 "
      os.system("xterm -e csh -c '"+cline+"'")
    else:
      os.system("csh -c '"+cline+"' ")

    #Write the template name into 'Tplate' in the base directory.
    if exists(self.paramdir+'/varm'+tname+'.par'):
      f=open(self.basedir+'/Tplate'+self.filt,'w')
      f.write(tname)
      f.close()
      self.unlock()
      return 1
    else:
      logger.error('planet.template - Error during processing')
      self.unlock()
      return 0


  def process(self, popup=1):
    """Use the offproc shell script to process all .fits files for a given object.
       All files waiting in that objects Raw directory are processed. If 
       the option 'background' is true (by default), run the command in the 
       background in an xterm, otherwise return when the processing is finished.
       eg: process('ob2k24')
           process('EB2K005',popup=0)
    """
    if (not self.valid) or (not self.working):
      logger.error("Not a valid PLANET event with pipeline directory tree")
      return 0

    self.lock()
    self.refresh()  #Get changes to event data since instance was created

    if not exists(self.paramdir+'/varm'+self.template.get(self.filt,'')+'.par'):
      logger.error("planet.process - Template not yet created.")
      self.unlock()
      return 0

    #Create a temporary file and record the names of all unprocessed files
    #(ones that still have a .fits extension) for processing by 'offproc'
    tmpfile='/tmp/offproc-'+self.root+self.filt+'.lst'
    f=open(tmpfile,'w')
    gotone=0
    for name in glob.glob(self.rawdir+'/'+site+self.root+self.filt+'*.fits'):
      f.write(splitext(basename(name))[0]+'\n')
      gotone=1
    f.close()

    if gotone:            #If we have at least one file to process:
      wd=os.getcwd()
      os.chdir(self.basedir)
      cline='cd '+self.basedir+' ; source setup ; cleanup ; '
      cline=cline+'offproc '+self.template[self.filt]+' '+tmpfile+' ; '
      cline=cline+'grep -i error '+self.workdir+'/offlog.* '

      #shell the created command line, or spawn an xterm to do it.
      if popup:
        cline=cline+' ; echo Finished... ; sleep 30'
        os.system("xterm -e csh -c '"+cline+"'")
      else:
        os.system("csh -c '"+cline+"'")
      os.chdir(wd)
      self.unlock()
      return 1
    else:
      logger.info("No images to PLANET-process.")
      self.unlock()
      return 1


  def archive(self, snum=0, fnum=0, create=0, popup=1):
    """Use the archive script to archive a PLANET objects .DOP files.
       Parameters: archive(oname='',snum=0,fnum=0,create=0,background=1)
       Where snum = First image number to archive
             fnum = Last image number to archive
             create = 1 to create the archive file, 0 to append.
             popup = 1 to run in an xterm, 0 to run in Prosp.

       If snum is 0 or not given, and 'create' is false, it starts archiving at 
       the next available image after the last one archived. If create is true,
       it starts at the first available image instead. Beware - if there is no
       dophot result file for the image you specify as a starting point, the 
       whole archiving process will fail.

       If fnum is 0 or not given, it defaults to the last image file.

       Normal usage is, for example,

       archive('ob2k26')
       (Add any outstanding processed dophot files to the archive for OB2K026).

       archive('eb2k05',create=1)
       (recreate the entire archive for this object, processing all files).

       archive('OB2K024',snum=45,fnum=50)
       (append teh data for images 45 through 50 to the archive).

    """
    if (not self.valid) or (not self.working):
      logger.error("Not a valid PLANET event with pipeline directory tree")
      return 0

    self.lock()
    self.refresh()  #Get changes to event data since instance was created

    aname=site+self.root
    wd=os.getcwd()
    os.chdir(self.basedir)

    files=glob.glob(self.rawdir+'/'+aname+self.filt+'*.fits.processed')
    filenums=map(_pfc,files)
    filenums.sort()
    try:
      minn=filenums[0]
      maxn=filenums[-1]
    except:            #no files processed yet
      self.unlock()
      return 0

    if not snum:
      if create:
        snum=minn
      else:
        snum=_nnum(filenums,self.archmax.get(self.filt,0))
        if snum==9999:
          logger.info(self.root+" - Archive up to date.")
          return
        if snum==-1:
          logger.info(self.root+" - invalid archmax value, creating new archive.")
          snum=minn
          create=1
    if not fnum:
      fnum=maxn
    if create:
      c=' X '
    else:
      c=' A '

    #Construct the command line.
    cline='cd '+self.basedir+' ; source setup ; cleanup ; '
    cline=cline+'archive '+aname+' '+aname+' '+self.filt+' '+`snum`+' '+`fnum`+c+' '

    #Shell the command, or spawn an xterm to run it in the background
    print cline
    if popup:
      cline=cline+' ; echo Finished ; sleep 30'
      os.system("xterm -e csh -c '"+cline+"'")
    else:
      os.system("csh -c '"+cline+"'")
    os.chdir(wd)
    f=open(self.basedir+'/num'+self.filt+'.archived','w')
    f.write(`fnum`)
    f.close()
    self.unlock()
    return 1


  def pyclean(self):
    """Remove all the working files from the pySIS directory for an object
    """
    self.lock()
    self.refresh()
    if self.pysisdir:
      files = glob.glob(self.pysisdir+'/*')
      for f in files:
        fn = basename(f)
        if (fn[0] == site) and (fn[-5:] == '.fits'):
          pass  #Keep raw images
        elif (fn[0] == site) and ('failed' in fn):
          os.rename(f,os.path.dirname(f)+'/'+fn[:17])  #rename failed.* images
        elif fn[0] == site:
          pass  #keep all files beginning with sitecode
        elif (fn == 'Ref.include') or (fn == 'Ref.exclude') or (fn[:4] == 'OGLE'):
          pass  #Keep template inc/exc list and OGLE finder chart
        else:
          os.remove(f)
    else:
      print "No pysis dir to run in"
    self.unlock()


  def pysetup(self, idtype='OGLE', popup=1):
    """Runs the pySIS setup script on this event to run the
       template choice and full reduction, or re-run it to choose
       better template images. Use idtype='ds9' for manual lens
       identification, or idtype='OGLE' for automatic.
    """
    self.lock()
    self.refresh()
    if self.pysisdir:
      files = glob.glob(self.pysisdir+'/*')
      for f in files:
        fn = basename(f)
        if (fn[0] == site) and (fn[-5:] == '.fits'):
          pass  #Keep raw images
        elif (fn[0] == site) and ('failed' in fn):
          os.rename(f,os.path.dirname(f)+'/'+fn[:17])  #rename failed.* images
        elif (fn == 'Ref.include') or (fn == 'Ref.exclude') or (fn[:4] == 'OGLE'):
          pass  #Keep template inc/exc list and OGLE finder chart
        else:
          os.remove(f)
      cline = 'cd '+self.pysisdir + ' ; '
      cline += pySIShome+'/bin/setup.py -s '+sitename+' -e '+self.root+' -i '+idtype + ' ; '
      cline += 'ln -f -s '+self.pysisdir+'/W'+self.root+self.filt+'.* /home/observer/OUT/20'+self.yr
      print cline
      if popup:
        cline = cline + ' ; echo Finished ; sleep 30'
        os.system("xterm -e csh -c '"+cline+"'")
      else:
        os.system("csh -c '"+cline+"'")
    else:
      print "No pysis dir to run in"
    self.unlock()


  def pylink(self):
    """Creates the symlinks in ~/OUT/yyyy for the photometry files."""
    cline = 'ln -f -s '+self.pysisdir+'/W'+self.root+self.filt+'.* /home/observer/OUT/20'+self.yr
    os.system(cline)


  def pyupdate(self, popup=1):
    """Runs the pySIS update script on this event to reduce any
       new images since the last reduction.
    """
    self.lock()
    self.refresh()
    if self.pysisdir:
      cline = 'cd '+self.pysisdir + ' ; '
      cline += pySIShome+'/bin/update.py'
      print cline
      if popup:
        cline=cline+' ; echo Finished ; sleep 30'
        os.system("xterm -e csh -c '"+cline+"'")
      else:
        os.system("csh -c '"+cline+"'")
    else:
      print "No pysis dir to run in"
    self.unlock()


  def pyplot(self):
    """Generates a 2D graph of the PySIS output photometry
    """
    self.lock()
    self.refresh()
    if self.pysisdir:
      pfname=self.pysisdir+'/W'+self.root+self.filt+'.pysis'
      if exists(pfname):
        pfile=open(pfname,'r').readlines()
        times=[]
        mags=[]
        errs=[]
        for l in pfile:
          ls = l.split()
          mags.append(float(ls[1]))
          errs.append(float(ls[2]))
          times.append(float(ls[3]))
        errorbar(x=times, y=mags, yerr=errs, fmt='bo')
        ax=axis()
        xext = (ax[1]-ax[0])*0.1        #Extend the X axis by 10% at each end
        axis([ax[0]-xext,ax[1]+xext,ax[3],ax[2]])   #Invert the Y axis
        show()
      else:
        print "No PySIS output file."
    else:
      print "No PySIS working directory."
    


def _allocatefile(fname):
  """Usage: _allocatefile('fname')
     Moves the given file into the appropriate PLANET object working directory
     (eg /home/observer/2KSeason/MB00012/Raw) if it exists, or into a holding
     directory (eg /data/PLANET) if a suitable object directory does not exist.
     The return value is the name of the file after being moved, or '' if it was
     not moved due to the presence of an existing file with the same name at
     the destination.
  """
  if not exists(fname):
    logger.error('planet._allocatefile - File '+fname+' not found!')
    return ''
  bname=basename(fname)
  bn,ext=os.path.splitext(bname)
  field=Pevent(string.upper(bn))
  if field.imdir:
    if exists(field.imdir+'/'+bname):
      logger.error('planet._allocatefile - '+field.imdir+'/'+bname+' exists!')
      return ''
    else:
      os.system('mv ' + fname + ' ' + field.imdir + ' ; ' +
                'cd ' + field.rawdir + ' ; ' +
                'ln -s ' + field.imdir+'/'+bname + ' ; ' +
                'cd ' + field.pysisdir + ' ; ' +
                'ln -s ' + field.imdir+'/'+bname )
      return field.imdir+'/'+bname
  elif field.rawdir:
    if exists(field.rawdir+'/'+bname):
      logger.error('planet._allocatefile - '+field.rawdir+'/'+bname+' exists!')
      return ''
    elif exists(field.rawdir+'/'+bname+'.processed'):
      logger.error('planet._allocatefile - '+field.rawdir+'/'+bname+'.processed exists!')
      return ''
    else:
      os.system('mv '+fname+' '+field.rawdir)
      return field.rawdir+'/'+bname
  elif exists(HoldingDir+'/'+bname):
    if samefile(HoldingDir+'/'+bname,fname):
      return HoldingDir+'/'+bname
    else:
      logger.error('planet._allocatefile - '+HoldingDir+'/'+bname+' Already exists!')
      return ''
  else:
    os.system('mv '+fname+' '+HoldingDir)
    return HoldingDir+'/'+bname


def newevent(tname='', refresh=True):
  """Creates a new directory structure for the event, including the OSU
     pipeline directories, the pysis subdir, and a directory ./Images
     for the incoming images. Each new image processed with 'allocate'
     is placed in ./Images if it exists, and symlinks created in ./Raw
     for DoPhot, and ./pysis for pySIS
  """
  e = Pevent(tname)
  print "Downloading event list from PLANET home page..."

  cline =  'cd ' + PipeHome+'/'+e.yr+'Season ; ' 
  cline += 'newfield ' + e.root + ' ; '
  cline += 'mkdir ' + e.root +'/Images' + ' ; '
  cline += 'mkdir ' + e.root +'/pysis '
  os.system(cline)
  print "Directory structure created for " + e.root + "."

  if refresh:
    os.system('rsync -azu --password-file %s %s .' % (ARTEMISPWFILE, ARTEMISLIST))
  lines = open(ARTEMISLIST.split('/')[1],'r').readlines()
  if not lines:
    print "No objects in list"
    return 0

  for l in lines:
    line = l.split()
    try:
      name = line[FID]
      ra = line[FRA]
      dec = line[FDEC]
      si = line[FSI]
      mag = line[FMAG]
      flag = line[FFLAG]
      if name == e.name:
        print line
        o = PlanetObject(e.root)
        if o.ObjRA:
          print tname + " already in Objects list."
        else:
          o.name = e.name
          o.ObjRA = ra
          o.ObjDec = dec
          o.ObjEpoch = 2000.0
          o.filtnames = 'I'
          o.filtname = 'I'
          o.exptimes = 600.0
          o.sublist = [('I',600.0)]
          o.exptime = 600
          o.type = 'PLANET'
          if '(' in mag:
            o.comment = "Current Mag I=%s (guess based on PSPL curve), " % mag
          else:
            o.comment = "Current Mag I=%s (PSPL), " % mag
          if 'ORD' in flag:
            o.comment = "Ordinary light curve."
          elif 'CHK' in flag:
            o.comment = "Possible anomaly - not confirmed."
          elif 'ANO' in flag:
            o.comment += "ANOMALY!"
          try:
            o.period = float(si)/1440.0    #Convert from minutes to days
            if o.period < 0.0021:
              o.period = 0.0021
          except ValueError:
            print "Invalid sample interval for " + name + ": " + `si`
            o.period = 0.0
          o.save(ask=0, force=1)
          print "Object " + o.ObjID + " added to database."
    except IndexError:
      pass


def allocate(fpat=''):
  """Moves the given files into the appropriate PLANET working directory
     (eg /home/observer/2KSeason/MB00012/Raw) if it exists, or into a holding
     directory (eg /data/PLANET) if a suitable object directory does not exist.

     It handles a list of files as well as a single filename, and for
     each argument, expands wildcards. It returns a list of filenames, or one
     filename if only one file was processed. Each returned name is the final
     path and file name of the input files after being moved.
     eg: allocate('/data/rd000922/reduced/WOB*.fits')
  """
  #print "rsend disabled - fix when chianti is back up"
  return distribute(fpat,_allocatefile)  #Call allocatefile for each target


def preduce(fname):
  """Trim, flatfield, and bias subtract a set of images, and carry out PLANET
     preprocessing tasks (FWHM and Threshold TSMIN TSMAX estimation). The
     reduced images are placed in appropriate object directory, under
     'PipeHome', or in a 'HoldingDir'. The return values will be a list of
     names and paths of the reduced images if successful.
     eg: preduce('/data/rd000922/W*.fits')
  """
  return allocate(improc.reduce(fname))
    

def preduced(fname):
  """Reduce and display a set of images, PLANET defaults, with output images
     moved to appropriate directories (see 'allocate' and 'preduce') and then
     displayed.
     eg: preduced('/data/rd000922/W*.fits')
  """
  return xpa.display(preduce(fname))


def template(tname='', background=1):
  """Use filename 'tname' (without .fits extension) as a PLANET template.
     Carries out a deep DoPhot reduction on the specified image, and record 
     the name of the template used for use in further processing.
     If the option 'background' is true (by default), run the command in the
     background in an xterm, otherwise return when the processing is finished.
     The return value is 1 if successful, 0 otherwise. This return value does
     not take the dophot reduction process into account, only the initial
     argument parsing.
     eg: template('WOB2K024I006',background=0)
         template('WOB2K026I002')
  """
  field=Pevent(tname)
  if (not field.valid) or (not field.imgnum):
    logger.error("You must specify a valid field, filter and image number to use for a template.")
    return 0
  if background:
    _addqueue(field, 'dotemplate', [], {'popup':1})
  else:
    field.dotemplate(popup=0)



def process(oname='',background=1):
  """Use the offproc shell script to process all .fits files for a given object.
     All files waiting in that objects Raw directory are processed. If 
     the option 'background' is true (by default), run the command in the 
     background in an xterm, otherwise return when the processing is finished.
     eg: process('ob2k24')
         process('EB2K005',background=0)
  """
  field=Pevent(oname)
  if field.valid:
    if background:
      _addqueue(field, 'process', [], {'popup':1})
    else:
      field.process(popup=0)
  else:
    logger.error('planet.process - Object directory for '+oname+' not found.')
    return 0


def pysetup(oname='',idtype='OGLE',background=1):
  """Use the pySIS setup script to initialise or completely re-reduce the
     images for the given event. If the option 'background' is true (by default),
     run the command in the background in an xterm, otherwise return when the
     processing is finished. If idtype is 'ds9', bring up an image for manual
     lens identification, otherwise identify it automatically using the OGLE
     finder chart.
     eg: pysetup('ob2k24')
         pysetup('EB2K005',idtype='ds9',background=0)
  """
  field=Pevent(oname)
  if field.valid and field.pysisdir:
    if background:
      _addqueue(field, 'pysetup', [], {'popup':1, 'idtype':idtype})
    else:
      field.pysetup(popup=0, idtype=idtype)
  else:
    logger.error('planet.pysetup - PySIS directory for '+oname+' not found.')
    return 0


def pyupdate(oname='',background=1):
  """Use the pySIS setup script to initialise or completely re-reduce the
     images for the given event. If the option 'background' is true (by default),
     run the command in the background in an xterm, otherwise return when the
     processing is finished. 
     eg: pyupdate('ob2k24')
         pyupdate('EB2K005',background=0)
  """
  field=Pevent(oname)
  if not field.pytemplate:
    logger.error('planet.pyupdate - event '+field.root+': need to run pysetup first.')
  elif field.valid and field.pysisdir:
    if background:
      _addqueue(field, 'pyupdate', [], {'popup':1})
    else:
      field.pyupdate(popup=0)
  else:
    logger.error('planet.pyupdate - PySIS directory for '+oname+' not found.')
    return 0


def pyclean(oname=''):
  """Clean the pysis directory for the given event, leaving any config files
     like Ref.exclude, etc, as well as the output files, and the raw images.
  """
  field = Pevent(oname)
  if field.valid and field.pysisdir:
    field.pyclean()
  else:
    logger.error('planet.pyclean - PySIS directory for '+oname+' not found.')
    return 0


def pylink(oname=''):
  """Create symlinks in ~/OUT/yyyy for the pySIS photometry output files for an event.
  """
  field = Pevent(oname)
  if field.valid and field.pysisdir:
    field.pylink()
  else:
    logger.error('planet.pylink - PySIS directory for '+oname+' not found.')
    return 0


def pyplot(oname=''):
  """Produce a plot of the PySIS photometry
  """
  field = Pevent(oname)
  if field.valid and field.pysisdir:
    field.pyplot()
  else:
    logger.error('planet.pylink - PySIS directory for '+oname+' not found.')
    return 0


def _pfc(s=''):
  "Return the file number given a PLANET filename with a .processed extension"
#  print "_pfc('"+s+"')"
  flist = _pnparse(os.path.basename(s).split('.')[0])
  if not flist:
    flist = _nonpnparse(os.path.basename(s).split('.')[0])
  code,yr,num,filt,im = flist
  return int(im)


def _nnum(l=[],c=0):
  """Returns the element in l that comes after the value in c. If c=0, return
     the first element in l. If c is the largest element in l, return 9999.
     If c is not in l, return -1 to indicate an error.
  """
  l.sort()
  if c==0:
    return l[0]
  else:
    try:
      i=l.index(c)
    except ValueError:
      return -1
    if i==len(l)-1:
      return 9999
    return l[i+1]
  

def archive(oname='',snum=0,fnum=0,create=0,background=1):
  """Use the archive script to archive a PLANET objects .DOP files.
     Parameters: archive(oname='',snum=0,fnum=0,create=0,background=1)
     Where oname = Objects Name
           snum = First image number to archive
           fnum = Last image number to archive
           create = 1 to create the archive file, 0 to append.
           background = 1 to run in an xterm, 0 to run in Prosp.

     If snum is 0 or not given, and 'create' is false, it starts archiving at 
     the next available image after the last one archived. If create is true,
     it starts at the first available image instead. Beware - if there is no
     dophot result file for the image you specify as a starting point, the 
     whole archiving process will fail.

     If fnum is 0 or not given, it defaults to the last image file.

     Normal usage is, for example,

     archive('ob2k26')
     (Add any outstanding processed dophot files to the archive for OB2K026).

     archive('eb2k05',create=1)
     (recreate the entire archive for this object, processing all files).

     archive('OB2K024',snum=45,fnum=50)
     (append teh data for images 45 through 50 to the archive).

  """
  field=Pevent(oname)
  if field.valid:
    if background:
      _addqueue(field, 'archive', [], {'snum':snum, 'fnum':fnum, 'create':create, 'popup':1})
    else:
      field.archive(snum=snum, fnum=fnum, create=create, popup=0)
  else:
    logger.error('planet.archive - Object directory for '+oname+' not found.')
    return 0


def processall(yr='2K'):
  """Run DoPhot on all waiting PLANET images in season directory (default 2K).
     Does not run in the background and can take quite a long time. Run this
     (or preferably the 'doall' command which archives as well) last thing
     before you go home in the morning, and leave it running.
     eg: processall()
  """
  for name in dircache.listdir(PipeHome+'/'+yr+'Season'):
    field=Pevent(name)
    if field.good:
      process(field.root,0)


def archiveall(yr='2K'):
  """Updates archive files for all PLANET fields in season dir (default 2K).
     eg: archiveall('99')
  """
  for name in dircache.listdir(PipeHome+'/'+yr+'Season'):
    field=Pevent(name)
    if field.good:
      archive(oname=field.root,background=0)


def plotref(oname='', m=None, x=None, r=None, a=None, b=None, quiet=None):
  """Runs 'plotref' to create a light curve plot of the specified object.
     Params:  m is the minimum day number to plot.
              x is the maximum day number to plot.
              r (if given) is the magnitude scale (mean +/- r value)
              a (if given) is the minimum (brightest) magnitude to plot
              b (if given) is the maximum (dimmest) magnitude to plot
     All parameters (except object name) are optional. It is an error to give
     both r and a,b.

     Examples:  plotref('ob2k12')
                plotref('ob2k23',1712,1715)
                plotref('ob2k23',r=1.2)
                plotref('ob2k34',m=1712,a=18,b=17)
  """
  field=Pevent(oname)
  params=''
  if m<>None:
    params=params+' -m '+`m`
  if x<>None:
    params=params+' -x '+`x`
  if r<>None:
    params=params+' -r '+`r`
  if a<>None:
    params=params+' -a '+`a`
  if b<>None:
    params=params+' -b '+`b`
  cline='cd '+field.archivedir+' ; '
  cline=cline+'plotref -4 '+site+field.root+field.filt+' plout '+params
  if not quiet:
    cline += ' -i '
  os.system("csh -c '"+cline+"'")


def showrefs(arc=''):
  """Displays the template for the field, with markers.
     All reference stars in the archive, plus the microlens, are marked and
     labelled.
     eg: showrefs('eb2k05')
  """
  field=Pevent(arc)

  if field.good:
    wd=os.getcwd()
    os.chdir(field.archivedir)
    print site+field.root+field.filt
    xpa.display(site+field.root+field.filt+'.fits') #Display template

    #Call plotref to create a temporary file with the lens and ref stars
    tmpfile='/tmp/SRtmp'+site+field.root+field.filt
    os.system('rm -f '+tmpfile+'*')
    commands.getoutput('plotref -4 '+site+field.root+field.filt+' '+tmpfile)
    xy=open(tmpfile+'XY')
    lines=xy.readlines()
    mlist=[]

    #Parse each non-commented line for star number, X, and Y
    for l in lines:
      if l[0]<>'#':
        ll=string.split(l)    #split into a list of space-delimited values
        #Create a marker object and append it to our list
        m=xpa.marker(float(ll[2]),float(ll[3]),ll[0])
        mlist.append(m)

    if len(mlist):     #Label the first star as the lens
      mlist[0].label='lens'
    xpa.showmlist(mlist)       #Display the markers.
    os.system('rm -f '+tmpfile+'*')


def countimgs(dir='/'):
  """Counts the number and type of PLANET images in the specified directory.
     Returns a dictionary with name:count pairs for all PLANET images found,
     based on parsing the filename.
  """
  counts={}
  for name in dircache.listdir(dir):
    field=Pevent(name[:8])
    if field.valid:
      counts[field.root]=counts.get(field.root,0)+1
  return counts


def _search(aname, x, y):
  """Search the given archive file for the star at x,y, with a radius of
     2 pixels.
  """
  wd=os.getcwd()
  field=Pevent(aname)
  if field.valid:
    os.chdir(field.archivedir)
    res=commands.getoutput('searchXY -5 '+site+field.root+field.filt+
                           ' tt '+`x`+' '+`y`+' 2 0')
    info=_regsearch.findall(res)
    os.chdir(wd)
    if len(info)==1:
      print "Got star: ",info[0]
      return info[0]
    elif len(info)>1:
      print "Multiple stars:",info
      return None
    else:
      print "No matching stars."
      return None
                         
  


def searchXY(arch='', x=None, y=None):
  """If given x,y run 'searchXY' on the given archive for those coordinates.
     If x and y are not specified, the template image for the specified 
     archive is displayed and the user is prompted to select stars. Once all
     the desired regions have been selected in the viewer (SAO tng/ds9),
     press 'Enter', and the archive is searched for those regions.
  """
  field=Pevent(arch)
  if field.valid:
    print site+field.root+field.filt
    xpa.display(field.archivedir+'/'+site+field.root+field.filt+'.fits')
    if x and y:
      num=_search(site+field.root+field.filt, x, y)
      r=xpa.marker(x,y,label=`num`)
      r.display()
      return `num`
    else:
      raw_input('Select desired star/s and press "Enter" when finished:')
      rl=xpa.getregions()
      nums=''
      foundlist=[]
      for r in rl:
        info=_search(site+field.root+field.filt, r.x, r.y)
        if info:
          r.label=info[0]+'='+info[3]
          r.x=float(info[1])
          r.y=float(info[2])
          nums=nums+' '+info[0]
          foundlist.append(r)
      xpa.deleteregions()
      xpa.showmlist(foundlist)
      return nums
  else:
    logger.error("You must specify an archive name to searchXY.")
    return None


def pyreview(arch):
  field=Pevent(arch)
  if field.valid:
    print site+field.root+field.filt
    os.chdir(field.pysisdir)
    sts = glob.glob('*.ps')
    os.system('ds9 -zscale `cat ref_list`')
    for s in sts:
      os.system('gv '+s+' &')



def dophout(arch):
  field = Pevent(arch)
  if field.valid:
    flist = []
    alist = glob.glob(field.archivedir+'/'+site+field.root+'?')
    for aname in alist:
      flist.append(aname[-1])
    for f in flist:
      os.system('rm '+field.archivedir+'/plout*')
      plotref(site+field.root+f, quiet=1)
      os.system('cp '+field.archivedir+'/ploutSM.dat /tmp/'+site+field.root+f+'.dat')
      os.system('cp '+field.archivedir+'/ploutXY /tmp/'+site+field.root+f+'.XY')
      os.system('cp '+field.archivedir+'/'+site+field.root+f+'.fits /tmp')
      print 'Created output data files: /tmp/'+site+field.root+f+'.dat, /tmp/'+site+field.root+f+'.XY'
      print 'Copied reference image: /tmp/'+site+field.root+f+'.fits'
    


def tryplanetname(str):
  "Map from an abbreviated planet name to the full name"
  p=Pevent(str)
  if p.valid:
    return p.root
  else:
    return ""


class PlanetObject(dObject):
  def preset(self):
    "Set the Pevent for this event"
    self.pevent=Pevent(self.ObjID)

  def fileprefix(self, prefix=""):
    "Sets the filename prefix for this object"
    if prefix:
      dObject.fileprefix(self,prefix)
    else:
      dObject.fileprefix(self,site+self.pevent.root+filtid(self.filtname))

  def reduce(self):
    self.filename=_allocatefile(self.filename)
    if self.pevent.photmethod == 'dophot':
      process(self.pevent.root+filtid(self.filtname))
      archive(self.pevent.root+filtid(self.filtname))
    else:
      pyupdate(self.pevent.root+filtid(self.filtname))

  def log(self):
    #print "rsend disabled - fix when chianti is back up."
    pass



def cname(n='HB-2K-060'):
  return n[:2]+n[3:5]+n[6:]


class PlanetURLopener(urllib.FancyURLopener):
  """Subclasses the urllib class and overrides the 'prompt_user_passwd' function
     to return a hardwired pair for the PLANET private pages.
  """
  def prompt_user_passwd(self, host, realm):
    print "Returning username/password for "+host+", "+realm+"\n"
    return (PlanetUser, PlanetPassword)


def UpdatePriorities(interactive=1, refresh=True):
  """Connect to the PLANET web server and download the current priorities list,
     including sampling rates, to update the intervals in the local objects
     database. If 'interactive' is true, then any new objects will result in 
     the user being prompted for guider camera positions, exposure times
  """
  if refresh:
    os.system('rsync -azu --password-file %s %s .' % (ARTEMISPWFILE, ARTEMISLIST))
  lines = open(ARTEMISLIST.split('/')[1],'r').readlines()
  if not lines:
    print "No objects in list"
    return 0

  objects.ZapPeriods(period=0.0, type='PLANET')  #Ignore all not in the current list

  for l in lines:
    line = l.split()
    print line
    try:
      name = line[FID]
      ra = line[FRA]
      dec = line[FDEC]
      si = line[FSI]
      mag = line[FMAG]
      flag = line[FFLAG]
      o = PlanetObject(cname(name))
      
      if '(' in mag:
        o.comment = "Current Mag I=%s (guess based on PSPL curve), " % mag
      else:
        o.comment = "Current Mag I=%s (PSPL), " % mag
      if 'ORD' in flag:
        o.comment = "Ordinary light curve."
      elif 'CHK' in flag:
        o.comment = "Possible anomaly - not confirmed."
      elif 'ANO' in flag:
        o.comment += "ANOMALY!"
      try:
        o.period = float(si)/1440.0    #Convert from hours to days
        if o.period < 0.0021:
          o.period = 0.0021
      except ValueError:
        print "Invalid sample interval for "+name+": "+`si`

      if o.ObjRA:       #Already in our local database, so adjust period
        o.save(ask=0, force=1)
      else:
        newevent(cname(name), refresh=False)
    except IndexError:
      pass



#Module initialisation:

queue=[]
queuethread=threading.Thread(target=_queuehandler, name="PLANET Queue handler")
print "created queuethread"

pipeline.Pipelines['PLANET']=PlanetObject
pipeline.TryNames.append(tryplanetname)

