#XPA (X Public Transport Access) in Python. (C) Andrew Williams, 2000, 2001
#  andrew@physics.uwa.edu.au
#
# or
#
#  andrew@longtable.org
#
import commands
import string
import os
from subprocess import Popen,PIPE,STDOUT

import globals
import fits

viewer='ds9'      #Default to ds9 unless otherwise overriden


class marker:
  """Defines a class for storing SAO(tng/ds9) regions. Should work with any
     type that defined by x, y, and size (eg circle), only tested for points.
     Create an instance with:  m=xpa.marker(123.4, 345.6, 'lens'), for example.
  """
  def __init__(self,x=0,y=0,label='',type='point',size=0):
    self.x=x
    self.y=y
    self.label=label
    self.type=type
    self.size=size
  def display(self):   #Sends an XPA message to the viewer to show this marker
    if self.type=='point':  #Points don't have a size attribute
      if viewer=='SAOtng':
        cmd="regions '#"+self.label+"; "+self.type+" "+`self.x`+" "+`self.y`+"'"
        commands.getoutput('echo "'+cmd+'" | xpaset '+viewer)
      else:
        cmd="'"+self.type+" "+`self.x`+" "+`self.y`+" # text={"+self.label+"} '"
        commands.getoutput('echo '+cmd+' | xpaset '+viewer+' regions')
    print cmd


class wcsmarker:
  """Defines a class for storing SAO(tng/ds9) regions where x and y are
     strings containing sexagesimal RA and Dec in FK5, J2000. Size, if
     relevant for the marker type (eg circle) can be, for example 5" 
     (5 arcseconds) or 0.5' (half an arcminute).
     Create an instance with:  m=xpa.marker('12:34:56', '-32:10:54, 'lens'),
     for example.
  """
  def __init__(self,x='',y='',label='',type='point',size=''):
    self.x=x
    self.y=y
    self.label=label
    self.type=type
    self.size=size
  def display(self):   #Sends an XPA message to the viewer to show this marker
    if self.type=='point':  #Points don't have a size attribute
      cmd="'wcs; "+self.type+" "+self.x+" "+self.y+" # text={"+self.label+"} '"
      commands.getoutput('echo '+cmd+' | xpaset '+viewer+' regions')
    print cmd


def deleteregions():
  """Send an XPA message to the viewer to delete all markers.
  """
  if viewer=='SAOtng':
    commands.getoutput('echo "regions delete" | xpaset '+viewer)
  else:
    commands.getoutput('echo "regions deleteall" | xpaset '+viewer)


def showmlist(mlist=[]):
  """When called with a list of markers, call the display method for
     each marker in the list.
  """
  for m in mlist:
    m.display()


def getregions():
  """Ask the viewer what regions are defined, parse the output, and 
     return a list of marker objects.
  """
  #Call the xpaget command, get the output, and split it into a list of lines
  if viewer=='ds9':
    out=string.split(commands.getoutput('xpaget ds9 regions'),'\n')
    label=''
    mlist=[]
    for r in out:       #For each line
      if r.find('(') <= 0:
        pass
      else:
        print r
        hs=string.find(r,'#')
        ob=string.find(r,'(')
        cb=string.find(r,')')
        try:
          type = r[:ob]
          print type
        except:
          print "region type unknown: "+r
          type='point'
        ocb=string.find(r,'{')
        ccb=string.find(r,'}')
        if ocb > 0:   #There is a label
          label=r[ocb+1:ccb]   #The label is between curly brackets
        else:
          label = ''   #No label for this point
        if type=='point':
          x,y=eval(r[ob+1:cb])  #Grab the X and Y values for a point
          m=marker(x,y,label,type)  #Create a marker object
        else:
          x,y,size=eval(r[ob+1:cb]) #Grab X,Y, and Size for a circle, etc
          m=marker(x,y,label,type,size)  #Create a marker object
        mlist.append(m)   #Add the object to the list
    return mlist
  else:
    out=string.split(commands.getoutput('xpaget SAOtng regions'),'\n')
    label=''
    mlist=[]
    for r in out:       #For each line
      if r[0]=='#':     #This line is a label that refers to the next region
        label=r[1:]
      else:
        ob=string.find(r,'(')
        cb=string.find(r,')')
        type=r[1:ob]     #type is the string between the leading + and the (
        if type=='point':
          x,y=eval(r[ob+1:cb])  #Grab the X and Y values for a point
          m=marker(x,y,label,type)  #Create a marker object
        else:
          x,y,size=eval(r[ob+1:cb]) #Grab X,Y, and Size for a circle, etc
          m=marker(x,y,label,type,size)  #Create a marker object
        label=''     #Clear label so it won't get attached to the next marker
        mlist.append(m)   #Add the object to the list
    return mlist


def _displayfile(fname, iraf=0):
  """Usage: display(fname, iraf=0)
     Send an image to SAOtng or DS9 for display - if iraf=1 then send in 8-bit
     IRAF format.
  """
  fullfilename=os.path.abspath(os.path.expanduser(fname))
  if iraf:
    os.system('/usr/local/dts/bin/display '+fullfilename)
  else:
    os.system('echo file '+fullfilename+' | xpaset '+viewer)
    os.system('echo orient y | xpaset '+viewer)
    if viewer=='ds9':
      os.system('echo scale mode zscale | xpaset '+viewer)
    else:
      os.system('echo scale histeq | xpaset '+viewer)
    os.system('echo saveas jpeg /tmp/ds9.jpeg | xpaset '+viewer)


def displayimage(im, iraf=0):
  """Send a FITS image array directly to DS9, without saving to disk.
  """
  xdim = int(im.headers['NAXIS1'])
  ydim = int(im.headers['NAXIS2'])
  p = Popen(['/usr/local/bin/xpaset', 'ds9', 'array', '[xdim=%d,ydim=%d,bitpix=-32,arch=littleendian]' % (xdim,ydim)], stdin=PIPE)
  p.communicate(input=im.data.astype(fits.Float32).tostring())
  os.system('echo scale mode zscale | xpaset ds9')


def display(fpat, iraf=0):
  """Display the specified file/s on the viewer program (eg SAOtng).
      If no filename is given, display the last image taken.
      if iraf=1 then the image is displayed in 8-bit IRAF format (so 'imexam'
      will work)
      eg: display('/data/junk001.fits')
          display('/data/junk002.fits',iraf=1)
          display( reduce('/data/comet*.fits') )
          display()
  """
  
  globals.distribute(fpat,_displayfile,iraf)


