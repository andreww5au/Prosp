#Fits image handling in Python. Andrew Williams, Feb 2000
#  andrew@physics.uwa.edu.au
#
# or
#
#  andrew@longtable.org
#
# Defines a class 'FITS'.
#  Creates two dictionaries, 'headers', containing key,value pairs for all FITS
#  cards with a defined value, and 'comments' containing all comments. 
#  Comments preceded by 'COMMENT' or 'HISTORY' are stored in comments['COMMENT']
#  and comments['HISTORY'] respectively, with one line per original FITS card.
#  Comments associated with a particular card are stored by key name
#  eg 'comments['EXPTIME'].
#
# If you supply mode 'h' on init, it just reads the headers in, and if you
# supply mode 'r', it reads the entire data section in as well, into a
# numeric python array (.data). Use of '-r' and operations on the data section 
# depend on the presence of the Numeric library. If this is not present, the
# module will load without errors, but using '-r' will give a warning and only
# load the header block.
#
# Use as:
#
# import fits
#
# f=fits.FITS('/path/test.fits','r')
#
# et=float(f.headers['EXPTIME'])
# print 'Exptime=',et,' and comment was:',f.comments['EXPTIME']
# print 'History of ',f.filename,':'
# print f.comments['HISTORY']
# print 'Comments:'
# print f.comments['COMMENT']
# print "Value at 256,256 was: ",f.data[255,255]  #python arrays start at 0
# f.data[255,255]=2000
# print "But now = 2000"
#
# g=fits.FITS('/path/test2.fits','r')
# f.data=(f.data-g.data)*1000
#
# f.save("/tmp/outfile.fits",fits.Float32)   #Save as 32-bit float: BITPIX=-32

import string        #load string handling library
import types
import os
import time
import tempfile
try:
  import Numeric
  from Numeric import *
  GotNum=1
except ImportError:
  GotNum=0

lastdark=None     #Contains the last Dark image used, to cache the data.
lastflats=[]      #A cache of the last few flatfield images used.

#Define two lists of cards that will be saved in the specified order, one at
#the start of the FITS headers, one at the end. The rest will be in
#alphabetical order between the two groups.

hfirst=['SIMPLE','BITPIX','NAXIS','NAXIS1','NAXIS2','EXTEND','COMMENT',
        'CREATOR','OBSERVAT','TELESCOP','LATITUDE','LONGITUD','INSTRUME',
        'DETECTOR','INSTID','OBSERVER','OBJECT','EXPTIME']
hlast=['CCDTEMP','GAIN','FILENAME','BSCALE','BZERO','HISTORY','END']




class FITS:
  """FITS image class. Creation accepts two parameters, filename and read mode.
     If the read mode is 'h', the file headers are read, and two dictionaries,
     object.headers and object.comments are created. If the read mode is 'r', 
     the data section is read as well, producing a Numeric Python array 
     attribute, object.data. If the filename is null, an empty (but valid FITS)
     header is constructed, and a 512x512 pixel data section, initialised to 
     zeroes (unless the mode is 'h' for headers only).

     The class includes reduction methods on the image: bias, dark, and flat.
     It also includes the 'save' method, for writing the image to a file, or
     just the header block if there is no data section.
  """

  def __init__(self, filename='', mode='r'): 
                                  #mode is 'h' (headers) or 'r' (data+headers)
    self.filename=filename
    if mode=='h':          #Mode h opens file, reads headers, closes the file
      if not filename:
        self.headers={'SIMPLE':'T', 'EXTEND':'T', 'NAXIS':'2'}
        self.comments={'COMMENT':'Empty header','HISTORY':''}
      else:
        self.file=open(self.filename,'r')
        self.headers={}
        self.comments={}
        self.finished=0
        while not self.finished:
          self.line=self.file.read(80)            #Read 80-byte cards
          self.finished=_parseline(self,self.line)
        self.file.close()
        if not self.comments.has_key('HISTORY'):
          self.comments['HISTORY']=''            #Add a blank HISTORY card

    if mode=='r':          #Mode h opens file, reads headers and data
      if not filename:
        self.headers={'SIMPLE':'T', 'EXTEND':'T', 'NAXIS':'2', 
                      'NAXIS1':'512', 'NAXIS2':'512'}
        self.comments={'COMMENT':'Empty header & data','HISTORY':''}
        if GotNum:
          self.data=zeros((512,512),Float)
        else:
          print "Numeric library not present, can't create data section."
      else:
        self.file=open(self.filename,'r')
        self.headers={}
        self.comments={}
        self.finished=0
        while not self.finished:
          self.line=self.file.read(80)            #Read 80-byte cards
          self.finished=_parseline(self,self.line)
        if not self.comments.has_key('HISTORY'):
          self.comments['HISTORY']=''            #Add a blank HISTORY card

        if GotNum:         #If we've got Numeric, load the data section too.
          self.file.seek(2880*(self.file.tell()/2880+1))
          bp=int(self.headers['BITPIX'])
          if bp==16:
            type=Int16
          elif bp==32:
            type=Int32
          elif bp==-32:
            type=Float32
          else:
            print "Unrecognised BITPIX value: ",bp
            return None

          shape=[]
          len=1
          for i in range(int(self.headers['NAXIS'])):
            shape.append(int(self.headers['NAXIS'+`i+1`]))
            len=len*shape[-1]
          if type==Int16:
            len=len*2   #Two bytes per element
          else:
            len=len*4   #Four bytes per element
          shape.reverse()  #take axes in opposite order
          self.data=fromstring(self.file.read(len),type).byteswapped().astype(Float64)
          self.data.shape=tuple(shape)

          if self.headers.has_key('BSCALE') and self.headers.has_key('BZERO'):
            bscale=float(self.headers['BSCALE'])
            bzero=float(self.headers['BZERO'])
            multiply(self.data,bscale,self.data)
            add(self.data,bzero,self.data)
        else:
          print "Numeric library not present, can't load data section."

        self.file.close()


  def save(self, fname='/tmp/out.fits',type='s'):
    """Saves image to a given file name. The type is a Numeric Python data
       type, such as Int16 or Float32, that specifies the output FITS file
       format. The BITPIX card is set appropriately for the data type, and
       the NAXIS1 and NAXIS2 cards are updated to fit the data. If the data
       section doesn't exist, or the type is specified as None or '', then
       just the header block is saved. If the type is not given, it defaults
       to Int16 (given here as the internal code 's' in case Numeric is not
       loaded).
    """
    self.filename=fname
    if not (GotNum and hasattr(self,'data')):
      type=None
    if not type:
      tmpdata=None
    elif type==Int16 or type==Int32:   #Pick bscale, bzero & rescale
      amax=argmax(self.data)  #row containing indices for max in each column
      amin=argmin(self.data)  #row containing indices for min in each column
      ma,mi = [], []
      for i in range(len(amax)):
        ma.append(self.data[i,amax[i]])  #Create rows with the max/min values
        mi.append(self.data[i,amin[i]])
      dmin=min(mi)         #Lowest and highest data values in the image
      dmax=max(ma)

      if type==Int16:
        fitsmin=-32767.0
        fitsmax=32767.0
        self.headers['BITPIX']='16'
      else:
        fitsmin=-2147483647.0
        fitsmax=2147483647.0
        self.headers['BITPIX']='32'

      #Calculate BZERO and BSCALE for integer output
      bzero = (dmin*fitsmax - dmax*fitsmin) / (fitsmax-fitsmin)
      if dmax>dmin:
        bscale = (dmax-dmin) / (fitsmax-fitsmin)
      else:
        bscale=1.0

      tmpdata=self.data - bzero     #Creates copy of data so original is safe
      divide(tmpdata,bscale,tmpdata)    
      self.headers['BSCALE']=`bscale`
      self.headers['BZERO']=`bzero`
    elif type==Float32:               #For floating point, don't scale the data
      self.headers['BITPIX']='-32'
      self.headers['BSCALE']='1'
      self.headers['BZERO']='0'
      tmpdata=self.data
    else:
      print "Unsupported output type",type
      return 0

    if GotNum and hasattr(self,'data'):
      self.headers['NAXIS']='2'   
      self.headers['NAXIS1']=`self.data.shape[1]`  #Update the array shape/size
      self.headers['NAXIS2']=`self.data.shape[0]`  #in the FITS cards

    f=open(fname,'w')

    for h in hfirst:            #Write the initial header cards
      f.write(_fh(self, h))
    tmplist=self.headers.keys()
    tmplist.sort()
    for h in tmplist:           #Write most of the header cards, sorted
      if (h not in hfirst) and (h not in hlast):
        f.write(_fh(self, h))
    for h in hlast:             #Write the final header cards
      f.write(_fh(self, h))
    if type:                  #Write the data section unless type is None
      f.write(' ' * (2880*(f.tell()/2880+1)-f.tell()) )    #Pad the header block
      f.write(tmpdata.astype(type).byteswapped().tostring())
      f.write('\0' * (2880*(f.tell()/2880+1)-f.tell()) )    #Pad the data
    f.close()
    return 1


  def bias(self, datasec=None, biassec=None):
    """Bias subtracts the image, using the images bias region.

       If the data and bias regions are not given, the relevant areas are 
       determined from the DATASEC and BIASSEC cards. If they are given, they
       must be strings in the form: [xs,xe:ys,ye]. Note that the xs
       (starting X) for the bias region is _not_ inclusive, whereas xs for the
       data region _is_ inclusive. For example, our data and bias regions are
       generally [1,512:1,512] and [512,544:1,512] respectively, for a 512x512
       data area and a 32x512 (not 33x512) bias area.

       This behaviour is to work around the format of OSU software generated
       FITS headers, unlikely to be changed.

       The bias value is found by discarding the highest and lowest 200 pixels
       in the bias region, and calculating the mean of the remainder. The bias
       section is then removed, leaving only the data section.
    """
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if string.find(self.comments["HISTORY"],"BIAS: ")>-1:
      print "Can't bias subtract, image already bias subtracted."
      return 0
    if not (datasec and biassec):     #If both regions are not supplied
      if ( not self.headers.has_key('DATASEC') or
           not self.headers.has_key('BIASSEC')    ):   #or in the header
        print "DATASEC and BIASSEC region keywords not found in FITS header"
        return 0
      else:                               #Extract regions from header
        datasec=self.headers['DATASEC']
        biassec=self.headers['BIASSEC']

    #Now turn the region string specifiers into Numeric array subregions
    dregion=_parseregion(self, datasec)
    bregion=_parseregion(self, biassec)[:,1:]
                #Omit first column to correct for BIASSEC inconsistency. 
                #In data section, startx and endx are inclusive, but
                #in bias region, startx is _not_ inclusive. That's
                #true for all images from Ariel++, and seems
                #unlikely to be fixed.

    #bias=sum(sum(bregion)) / product(bregion.shape)  #Mean
    #bias=sort(ravel(bregion))[product(bregion.shape)/2]   #Median
    bias=sum(sort(ravel(bregion))[100:-100]) / (product(bregion.shape) - 200)
         #Mean with highest and lowest 200 points discarded

    self.data=dregion - bias                      #Subtract and trim image
    self.headers['NAXIS1']=`self.data.shape[1]`   #Update cards after trimming
    self.headers['NAXIS2']=`self.data.shape[0]`
    histlog(self,"BIAS: of "+`bias`+" and trimmed")
    return 1


  def dark(self,darkfile=None):
    """Dark subtracts the image, using the dark frame given or the default.

       The dark frame can either be passed directly (as a filename or a FITS
       image), or if none is given, the file 'dark.fits' in the same directory
       as the image will be used. After being used, the dark image is saved in
       the global 'lastdark' variable. On subsequent calls to dark(), the 
       image in lastdark is used if its directory is the same as that for the
       new image, to avoid reloading the same dark image every time.

       The dark frame must be the same shape and size as the image, and must
       have been bias subtracted. Typically one would create a master dark
       frame by calculating the median of several (bias subtracted and trimmed)
       dark images.

       Before carrying out the dark subtraction, the CCD temperatures (FITS
       key 'CCDTEMP') are compared, and a warning given if there is more than
       0.5C difference. The exposure times are used to calculate the correct
       ratio for the dark subtraction.
    """
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if string.find(self.comments["HISTORY"],"BIAS: ")==-1:
      print "Can't dark subtract, image not bias corrected and trimmed."
      return 0
    if string.find(self.comments["HISTORY"],"DARK: ")>-1:
      print "Can't dark subtract, image already dark subtracted."
      return 0

    darkimage=None
    if type(darkfile)==types.StringType and darkfile<>'':
      darkimage=FITS(darkfile)      #If a filename is supplied, load the image
    elif isinstance(darkfile,FITS):
      darkimage=darkfile           #If it's a FITS image, use it as-is
    else:                     #Use the default dark frame
      if lastdark:            #The cached image if the file directory matches
        if (os.path.abspath(os.path.dirname(self.filename))==
            os.path.abspath(os.path.dirname(lastdark.filename))):
          darkimage=lastdark
    if not darkimage:
      darkfile=os.path.abspath(os.path.dirname(self.filename))+'/dark.fits'
      if os.path.exists(darkfile):
        darkimage=FITS(darkfile,'r')  #All has failed, load 'dark.fits'
      else:
        print "Dark image not found."
        return 0
    global lastdark
    lastdark=darkimage                #Save it for next time

    if abs(float(darkimage.headers['CCDTEMP']) -
           float(self.headers['CCDTEMP'])) > 0.5:
      print "Warning - dark frame CCD temp does not match image CCD temp."

    eratio=float(self.headers['EXPTIME']) / float(darkimage.headers['EXPTIME'])
    self.data=self.data - (darkimage.data * eratio)
    histlog(self,"DARK: "+os.path.abspath(darkimage.filename)+
             " ratio=%6.4f" % eratio)
    return 1


  def flat(self,flatfile=None):
    """Divides image by an appropriate flat field image, or the one specified.

       The flatfield to be used can either be passed directly (as a filename 
       or a FITS image), or if none is given, a default will be used.

       This default will either be the most recent image in the flatfield
       cache list that is both in the same directory as the raw image, and
       taken with the same filter, or a file of the form 'flatX.fits' in the 
       same directory as the image, where X is the first letter of the filter
       ID (case insensitive).

       The flatfield must be the same shape and size as the image, and must
       have been bias subtracted. Typically one would create a master flatfield 
       for each filter by calculating the median of several (bias subtracted
       and trimmed) flatfield images. If exposure times are not very short,
       the flatfields should be dark subtracted as well as bias corrected.

    """
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if string.find(self.comments["HISTORY"],"BIAS: ")==-1:
      print "Can't flatfield, image not bias corrected and trimmed."
      return 0
    if string.find(self.comments["HISTORY"],"DARK: ")==-1:
      print "Can't flatfield, image not dark subtracted."
      return 0
    if string.find(self.comments["HISTORY"],"FLAT: ")>-1:
      print "Can't flatfield, image already flatfield corrected."
      return 0

    flatimage=None
    if type(flatfile)==types.StringType and flatfile<>'':
      flatimage=FITS(flatfile)         #If given a filename, load the image
    elif isinstance(flatfile,FITS):
      flatimage=flatfile               #If given a FITS image, use as-is
    else:                            #Look in our cache for a match
      for flt in lastflats:
        if (os.path.abspath(os.path.dirname(self.filename))==
            os.path.abspath(os.path.dirname(flt.filename))  and
            self.headers['FILTERID']==flt.headers['FILTERID'] ):
          flatimage=flt
    if not flatimage:              #Look for the default filename/s
      filedir=os.path.abspath(os.path.dirname(self.filename))
      filt=self.headers['FILTERID'][1]  #Get first letter of filter name
      if filt==' ':
        filt='I'     #Default filter is I on Ariel startup
      if not os.path.exists(filedir+'/flat'+filt+'.fits'):
        if os.path.exists(filedir+'/flat'+string.lower(filt)+'.fits'):
          filt=string.lower(filt)
        elif os.path.exists(filedir+'/flat'+string.upper(filt)+'.fits'):
          filt=string.upper(filt)
        else:
          print 'Flatfield not found for filter',filt
          return None
      flatfile=filedir+'/flat'+filt+'.fits'
      if os.path.exists(flatfile):
        flatimage=FITS(flatfile,'r')
      else:
        print "Flatfield not found in "+filedir+" for filter "+filt
        return 0

    self.data = self.data / flatimage.data
    histlog(self,"FLAT: "+os.path.abspath(flatimage.filename))

    global lastflats
    if flatimage not in lastflats:
      lastflats.append(flatimage)        #Add it to the cache
    if len(lastflats)>5:
      lastflats=lastflats[1:]            #Discard old images  
                                         #when the cache gets large.


#
#Some support functions that might be of use externally:
#

def histlog(im,str):
  """Adds a HISTORY line containing 'str' to the image.
     Used to log actions performed on an image. A 20 character time stamp
     is added as a prefix, and the result is split across up to three cards
     if it is too long to fit in one. Any extra text is truncated.
  """
  value=time.strftime("%Y/%m/%d %H:%M:%S ",time.gmtime(time.time()) )+str
  if len(value)>70:
    value=value[:70]+'\n'+value[70:]
  if len(value)>141:
    value=value[:141]+'\n'+value[141:]
  if len(value)>212:
    value=value[:212]
  if im.comments.has_key("HISTORY"):
    im.comments["HISTORY"]=im.comments["HISTORY"]+'\n'+value
  else:
    im.comments["HISTORY"]=value


def median(l=[]):
  """Returns a FITS object which is the median of all the provided FITS
     objects (either as a list or a tuple).
  """
  myl=[]
  for i in l:
    if not hasattr(i,'data'):
      print "FITS object has no data section to operate on."
      return 0
    myl.append(i.data)
  out=FITS()
  out.headers=l[0].headers
  out.comments=l[0].comments
  out.data=_ndmedian(array(myl))
  return out



def med10(files=''):
  """Takes one or more FITS image filenames in any combination of names and
     wildcards. Loads them, ten by ten, medians each group, then medians the
     result. Returns a FITS image object. If more than 100 images names are 
     are passed, this function will be called recursively on the results of
     the first grouping pass.

     Note that this is best called with multiples of ten images - if called with
     11 images, for example, the median of the first 10 images (low noise) will
     be averaged with a single image, the one remaining. This will _increase_
     the noise in the result, not improve it.

  """
  tempfile.tmpdir='/big/tmp'       #Set up temp file name structure
  tempfile.template='medtemp'
  allfiles=globals.distribute(files,(lambda x: x))    #expand any wildcards
  numfiles=len(allfiles)
  if numfiles==0:                #No files to process, give up
    return
  elif numfiles<11:              #Can do a normal median call
    tenlist=[]
    for i in range(10):          #Load up to ten images
      if allfiles:
        tenlist.append(fits.FITS(allfiles[0],'r'))
        allfiles=allfiles[1:]
    tmp=median(tenlist)     #And call the normal median function
    return tmp
  else:                          #More than ten images to do
    tmplist=[]
    while allfiles:
      tenlist=[]
      for i in range(10):        #Load up to ten files
        if allfiles:
          tenlist.append(fits.FITS(allfiles[0],'r'))
          allfiles=allfiles[1:]
      tmp=median(tenlist)      #Find the median of those ten files
      tenlist=[]                         #free up all that memory
      tmpname=tempfile.mktemp()     #Save the median of ten in a temp file
      tmp.save(tmpname)
      tmplist.append(tmpname)

    tmp=med10(tmplist)        #recursivly call med10 on all of the temp files
    for n in tmplist:
      os.remove(n)            #remove all the temporary files
    return tmp


#Some handler functions for FITS card support, most not very useful 
#externally.

def _parseline(ob,line):
  """Parse each header line, finding key, value, and comment.
     Return value is 0 unless the FITS card parsed is the 'END' marker,
     in which case 1 is returned to signal the end of the FITS cards.

     Most FITS cards are stored in the ob.headers dictionary,
     and if a line has a key/value and an inline comment, that
     comment is stored with the same key value but in the ob.comments
     dictionary. The 'COMMENT' and 'HISTORY' keys are handled specially.
     Both end up in the ob.comments dictionary, but all COMMENT
     lines are joined together, seperated by newlines, and stored with
     the 'COMMENT' key. The 'HISTORY' key is handled the same way.

     All values are stored as strings, with any strings present in the FITS
     cards retaining thier enclosing quotation marks. These quote marks are
     necessary, so that the file save code can determine whether to format the
     card for string or numeric data. They can be stripped off using string
     slicing when used - eg object.headers['FILTERID'][1:-1]. White space
     inside the quotation marks is also retained, but any other white space
     is stripped.
  """

  key=string.strip(line[:8])   #First 8 chars with whitespace stripped
  value=string.strip(line[9:]) #Rest of line with whitespace stripped
  comment=''                   #Empty comment field for now

  if key == 'COMMENT':    #Handle case where comment takes up the whole line
    if ob.comments.has_key('COMMENT'):
      ob.comments['COMMENT']=ob.comments['COMMENT']+'\n'+value
    else:
      ob.comments['COMMENT']=value
  elif key == 'HISTORY':  #Handle 'HISTORY' like 'COMMENT'
    if ob.comments.has_key('HISTORY'):
      ob.comments['HISTORY']=ob.comments['HISTORY']+'\n'+value
    else:
      ob.comments['HISTORY']=value

#For both HISTORY and COMMENT, build up one value, with newlines seperating
#each line in the FITS file. Otherwise, it's one dictionary entry per line

  elif key == 'END':
    return 1
  else:
    if string.find(value,'/')>-1:    #Strip the comment off
      comment=string.strip(value[string.find(value,'/')+1:])
      value=string.strip(value[:string.find(value,'/')])

#Add dictionary entries for the key value, and key comment if it exists
    ob.headers[key]=value
    if comment<>'':
      ob.comments[key]=comment
    return 0



def _fh(fim=None, h=''):
  """Given an image and a header key, return the 80-byte formatted header card.

     A null card is returned for an error, and can be ignored since it's safe
     to write an empty string to the FITS header.
  """
  h=string.upper(h)
  if not fim:
    return '' 
  try:
    if h=='END':
      return string.ljust('END',80)
    elif h=='COMMENT' or h=='HISTORY':
      lines=string.split(fim.comments[h],'\n')
      out=''
      for l in lines:
        out=out+string.ljust(string.ljust(h,10)+l, 80)
      return out
    elif h not in fim.headers.keys():
      return ''
    else:
      v=fim.headers[h]
      out=string.ljust(h,8)+'= '
      if v[0]=='"' or v[0]=="'":
        out=out+string.ljust(v,20)
      else:
        out=out+string.rjust(v,20)
      if fim.comments.has_key(h):
        out=out+' / '+fim.comments[h]
      out=string.ljust(out,80)
      if len(out)>80:
        out=out[:80]
    return out
  except KeyError:
    return ''


def _parseregion(im=None, r=''):
  """Returns an array slice from a FITS object given a region string.
     For example, a region string might be '[512,544:1,512]', and the Numeric
     array returned would be im.data[0:512, 511:544].

     Note that due to a bug in Ariel++ BIASSEC headers, the region returned
     includes one row of actual image data, which must be stripped out using 
     slicing outside this function to keep the code here consistent.
  """
  r1,r2=tuple(string.split(r[2:-2],':'))
  xs,xe=tuple(string.split(r1,','))
  ys,ye=tuple(string.split(r2,','))
  return im.data[int(ys)-1:int(ye), int(xs)-1:int(xe)]
    

def _msort(m):
  """_msort(m) returns a sort along the first dimension of m as in MATLAB.
  """
  return transpose(sort(transpose(m)))


def _ndmedian(m):
  """median(m) returns a mean of m along the first dimension of m. Parameter
     is a Numeric array, not a FITS object. Called with a 3-dimensional
     array (N two dimensional images) to create a median image.
  """
  n=m.shape[0]
  if n==0:
    return None
  if n==1:
    return m
  dv,md=divmod(n,2)
  ms=_msort(m)
  if md==0:
    return (ms[dv-1] + ms[dv])/2
  else:
    return ms[dv]

