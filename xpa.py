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
import globals

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
        cmd="regions '"+self.type+" "+`self.x`+" "+`self.y`+' text="'+self.label+'" font="system 8 normal" '+"'"
        commands.getoutput('echo '+cmd+' | xpaset '+viewer)
    print cmd


def deleteregions():
  """Send an XPA message to the viewer to delete all markers.
  """
  commands.getoutput('echo "regions delete" | xpaset '+viewer)


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


def _displayfile(fname, histeq=1):
  """Usage: display(fname, histeq=1)
     Send an image to SAOtng for display with optional histogram equalisation.
  """
  fullfilename=os.path.abspath(os.path.expanduser(fname))
  os.system('echo file '+fullfilename+' | xpaset '+viewer)
  if histeq:
    if viewer=='ds9':
      os.system('echo scale zscale | xpaset '+viewer)
    else:
      os.system('echo scale histeq | xpaset '+viewer)

def display(fpat, histeq=1):
  """Display the specified file/s on the viewer program (eg SAOtng).
      If no filename is given, display the last image taken.
      eg: display('/data/junk001.fits')
          display( reduce('/data/comet*.fits') )
          display()
  """
  globals.distribute(fpat,_displayfile,histeq)


