
import string        #load string handling library
import os
import tempfile
import dircache
import cPickle
import fits
from globals import *
try:
  import Numeric
  from Numeric import *
  from Numeric import MLab
  GotNum=1
except ImportError:
  GotNum=0

lastdark=None     #Contains the last Dark image used, to cache the data.
lastbias=None
lastflats=[]      #A cache of the last few flatfield images used.


class FITSosucamera(fits.FITS):
  """FITS image class. Creation accepts two parameters, filename and read mode.
     If the read mode is 'h', the file headers are read, and two dictionaries,
     object.headers and object.comments are created. If the read mode is 'r', 
     the data section is read as well, producing a Numeric Python array 
     attribute, object.data. If the filename is null, an empty (but valid FITS)
     header is constructed, and a 512x512 pixel data section, initialised to 
     zeroes (unless the mode is 'h' for headers only).

     This class builds on the file IO in fits.py by adding reduction methods,
     seperate from fits.py because local customisation would be needed.
     The reduction methods on the image include: bias, dark, and flat.
  """

  def noise(self,region=''):
    t=MLab.std(_parseregion(self,region))
    return _ndmedian(t)

  def median(self,region=''):
    t=_ndmedian(_parseregion(self,region))
    return _ndmedian(t)

  def mean(self,region=''):
    t=MLab.mean(_parseregion(self,region))
    return MLab.mean(t)

  def max(self,region=''):
    t=MLab.max(_parseregion(self,region))
    return MLab.max(t)

  def min(self,region=''):
    t=MLab.min(_parseregion(self,region))
    return MLab.min(t)



  def bias(self, biasfile=None, datasec=None, biassec=None):
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
    global lastdark
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
    lastdark=darkimage                #Save it for next time

    darktemp=float(darkimage.headers['CCDTEMP'])
    deltatemp=float(self.headers['CCDTEMP']) - darktemp
    if abs(deltatemp) > 1.0:
      print "Warning - dark frame and image CCD temps differ by "+`deltatemp`

    eratio=float(self.headers['EXPTIME']) / float(darkimage.headers['EXPTIME'])
    tratio=2.0**( deltatemp/6.0 )
    self.data=self.data - (darkimage.data * eratio * tratio)
    histlog(self,"DARK: "+os.path.abspath(darkimage.filename)+
         " ET=%ss, T=%5.2fC" % (darkimage.headers['EXPTIME'],darktemp))
    histlog(self,"DARK: exp time ratio=%5.3f, temp ratio=%5.3f" %
            (eratio,tratio))
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
    global lastflats
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

    if flatimage not in lastflats:
      lastflats.append(flatimage)        #Add it to the cache
    if len(lastflats)>5:
      lastflats=lastflats[1:]            #Discard old images  
                                         #when the cache gets large.

  def fwhmsky(self):
    try:
      try:
        os.remove('/tmp/fwhmtmp.fits')
      except OSError:
        pass
      self.save('/tmp/fwhmtmp.fits',Int16)
      os.system('/home/dts/bin/fwhmsky /tmp/fwhmtmp.fits')
      tmpdata=string.split(open('input.dophot','r').read())
      try:
        os.remove('input.dophot')
        os.remove('/tmp/fwhmtmp.fits')
      except OSError:
        pass
    except OSError, IOError:
      print "Error with file creation while calculating FWHM, Sky"
      return -1,-1
    try:
      self.headers['FWHM']=tmpdata[0]
      self.comments['FWHM']='Seeing FWHM, in pixels.'
      self.headers['SKY']=tmpdata[1]
      self.comments['SKY']='Sky background, in ADU'
      return float(tmpdata[0]), float(tmpdata[1])
    except:
      print "Error calculating FWHM and Sky"
      return -1,-1


class FITSnewcamera(FITSosucamera):
  """FITS image class. Creation accepts two parameters, filename and read mode.
     If the read mode is 'h', the file headers are read, and two dictionaries,
     object.headers and object.comments are created. If the read mode is 'r', 
     the data section is read as well, producing a Numeric Python array 
     attribute, object.data. If the filename is null, an empty (but valid FITS)
     header is constructed, and a 512x512 pixel data section, initialised to 
     zeroes (unless the mode is 'h' for headers only).

     This subclasses FITSosucamera and overrides the 'bias' method to do bias
     image subtraction needed for the new Perth AP7.
     The reduction methods on the image include: bias, dark, and flat.
  """

  def bias(self, biasfile='', datasec=None, biassec=None):
    """Trims and Bias subtracts the image, using 'bias.fits' in the current dir.
       If 'biasfile' is specified, that file is used. If 'biasfile' is None, 
       then no bias image is subtracted.

    """
    global lastbias
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
    bias=sum(sort(ravel(bregion))[100:-100]) / (product(bregion.shape) - 200)

    biasimage=None
    if biasfile<>None:
      if type(biasfile)==types.StringType and biasfile<>'':
        biasimage=FITS(biasfile)      #If a filename is supplied, load the image
      elif isinstance(biasfile,fits.FITS):
        biasimage=biasfile           #If it's a FITS image, use it as-is
      else:                     #Use the default bias frame
        if lastbias:            #The cached image if the file directory matches
          if (os.path.abspath(os.path.dirname(self.filename))==
              os.path.abspath(os.path.dirname(lastbias.filename))):
            biasimage=lastbias
      if not biasimage:
        biasfile=os.path.abspath(os.path.dirname(self.filename))+'/bias.fits'
        if os.path.exists(biasfile):
          biasimage=FITS(biasfile,'r')  #All has failed, load 'bias.fits'
        else:
          print "Bias image not found, using constant estimate"
      lastbias=biasimage                #Save it for next time

    if biasimage:
      biastemp=float(biasimage.headers['CCDTEMP'])
      deltatemp=biastemp - float(self.headers['CCDTEMP'])
      if abs(deltatemp) > 1.0:
        print "Warning - bias frame and image temp differ by "+`deltatemp`
      bdregion=_parseregion(biasimage,datasec)
      self.data=dregion - bias - bdregion
      histlog(self,"BIAS: of "+`bias`+" and bias.fits at "+`biastemp`+"C")
    else:
      self.data=dregion - bias                      #Subtract and trim image
      histlog(self,"BIAS: of "+`bias`)

    self.headers['NAXIS1']=`self.data.shape[1]`   #Update cards after trimming
    self.headers['NAXIS2']=`self.data.shape[0]`
    return 1


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
  temps=[]
  for i in l:
    if not hasattr(i,'data'):
      print "FITS object has no data section to operate on."
      return 0
    myl.append(i.data)
    temps.append(float(i.headers['CCDTEMP']))
  out=FITS()
  out.headers=l[0].headers
  out.comments=l[0].comments
  out.data=_ndmedian(array(myl))
  out.headers['CCDTEMP']=`_ndmedian(array(temps))`
  return out



def med10(files='', bias=0):
  """Takes one or more FITS image filenames in any combination of names and
     wildcards. Loads them, ten by ten, medians each group, then medians the
     result. Returns a FITS image object. If more than 100 images names are 
     are passed, this function will be called recursively on the results of
     the first grouping pass.

     Note that this is best called with multiples of ten images - if called with
     11 images, for example, the median of the first 10 images (low noise) will
     be averaged with a single image, the one remaining. This will _increase_
     the noise in the result, not improve it.

     If the optional parameter 'bias' is true, the bias() method will be called
     on each image before it is medianed (but only on the first pass).

  """
  tempfile.tmpdir='/big/tmp'       #Set up temp file name structure
  tempfile.template='medtemp'
  allfiles=distribute(files,(lambda x: x))    #expand any wildcards
  numfiles=len(allfiles)
  if numfiles==0:                #No files to process, give up
    return
  elif numfiles<11:              #Can do a normal median call
    tenlist=[]
    for i in range(10):          #Load up to ten images
      if allfiles:
        tenlist.append(FITS(allfiles[0],'r'))
        if bias==1:
          tenlist[-1].bias()
        elif bias==-1:
          tenlist[-1].bias(biasfile=None)
        allfiles=allfiles[1:]
    tmp=median(tenlist)     #And call the normal median function
    return tmp
  else:                          #More than ten images to do
    tmplist=[]
    while allfiles:
      tenlist=[]
      for i in range(10):        #Load up to ten files
        if allfiles:
          tenlist.append(FITS(allfiles[0],'r'))
          if bias==1:
            tenlist[-1].bias()
          elif bias==-1:
            tenlist[-1].bias(biasfile=None)
          allfiles=allfiles[1:]
      tmp=median(tenlist)      #Find the median of those ten files
      tenlist=[]                         #free up all that memory
      tmpname=tempfile.mktemp()     #Save the median of ten in a temp file
      tmp.save(tmpname)
      tmplist.append(tmpname)

    tmp=med10(tmplist, bias=0)  #recursivly call med10 on all of the temp files
    for n in tmplist:
      os.remove(n)            #remove all the temporary files
    return tmp


def reduce(fpat=''):
  """Trim, flatfield, bias a set of image, leave in subdirectory 'reduced'.
     If the 'reduced' directory doesn't exist, it will be created.

     If no filename argument is given, it defaults to the last CCD image
     taken (status.path+status.lastfile).

     The return value will be a list of names and paths of the reduced images
     if successful. This return value can be passed to other commands, eg
     display(allocate(reduce('/data/M*.fits')))
     
     eg: reduce('/data/myVimg*.fits /data/myIimg*')
  """
  if fpat=='':
    fpat=status.path+status.lastfile
  return distribute(fpat,_reducefile)


def dobias(files=[]):
  """Take a list of bias frame filenames and turn them into a median bias image.

     Each image is loaded, and the median of all
     the images is written to the file 'bias.fits' in the same directory as the
     first FITS file.
  """
  nfiles=distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if not nfiles:
    swrite("dobias - No images to process.")
    return 0
  im=med10(nfiles, bias=-1)    #Signal overscan subtraction only for each image
  outfile=os.path.abspath(os.path.dirname(nfiles[0]))+'/bias.fits'
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, Float32)


def dodark(files=[]):
  """Take a list of dark frame filenames and turn them into a median dark image.

     Each image is loaded, bias subtracted and trimmed, and the median of all
     the images is written to the file 'dark.fits' in the same directory as the
     first FITS file.
  """
  nfiles=distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if not nfiles:
    swrite("dodark - No images to process.")
    return 0
  im=med10(nfiles, bias=1)   #Signal overscan and bias image subtraction
  outfile=os.path.abspath(os.path.dirname(nfiles[0]))+'/dark.fits'
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, Float32)


def doflat(files=[], filt=None):
  """Take a list of flatfield filenames and turn them into a median flatfield.

     Each image is loaded, bias & dark subtracted and trimmed, and divided by
     the mean pixel value in that image. A median image is then derived, and
     written to the file 'flatX.fits' in the same directory as the first FITS
     file, where 'X' is the first letter of the filter-ID for the first image
     The filter is always taken from the FILTERID card in the FITS header, 
     unless that card is not present, in which case the supplied 'filt' 
     argument is used to generate the filename.
  """
  nfiles=distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if len(nfiles)>8:
    swrite("doflat - Too many files to median, truncating to first 8 images.")
    nfiles=nfiles[:8]
  if not nfiles:
    swrite("doflat - No images to process.")
    return 0
  di=[]
  for d in nfiles:
    im=FITS(d,'r')
    im.bias()
    im.dark()
    divide(im.data, sum(sum(im.data))/product(im.data.shape), im.data)
    di.append(im)
  im=median(di)
  if im.headers.has_key('FILTERID'):
    filt=im.headers['FILTERID'][1]          #First letter of filter name
  outfile=os.path.abspath(os.path.dirname(di[0].filename))+'/flat'+filt+'.fits'
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, Float32)


#
# Utility functions used internally, probably not useful elsewhere.
#


def _rlog(fname=''):
  """Record an image file reduction in ./reducelog so that it won't be
     reduced again.
  """
  fullfile=os.path.abspath(os.path.expanduser(fname))
  filedir=os.path.dirname(fullfile)
  filename=os.path.basename(fullfile)
  dir=dircache.listdir(filedir)
  if not 'reducelog' in dir:
    redlist=[]
    redlist.append(filename)
    f=open(filedir+'/reducelog','w')
    cPickle.dump(redlist,f)
    swrite('initialised reducelog for '+filedir)
    f.close()
  else:
    f=open(filedir+'/reducelog','r')
    redlist=cPickle.load(f)
    f.close()
    f=open(filedir+'/reducelog','w')
    redlist.append(filename)
    cPickle.dump(redlist,f)
    f.close()


def _reducefile(fname=''):
  """Usage: reducefile(fname)
     Trim, flatfield, bias an image, leave in subdir 'reduced' under the
     current path - if the 'reduced' directory doesn't exist, it will be
     created.

     The return value will be the name and path of the reduced image if
     successful, or '' if the reduction failed.
  """
  fullfile=os.path.abspath(os.path.expanduser(fname))
  filedir=os.path.dirname(fullfile)
  filename=os.path.basename(fullfile)
  outfile=filedir+'/reduced/'+filename
  darkfile=filedir+'/dark.fits'

  if not os.path.isdir(filedir+'/reduced'):
    os.mkdir(filedir+'/reduced')

  if not os.path.exists(fullfile):
    ewrite('reducefile - Input image file not found: '+fullfile)
    return None

  img=FITS(fullfile,'r')    #Load the file
  img.bias()                      #Subtract bias and trim overscan
  img.dark()                      #Subtract scaled dark image
  img.flat()                      #Divide by appropriate flatfield
  fwhm,sky=img.fwhmsky()
  img.save(outfile,Int16)   #Save in Int16 format
  _rlog(fname)
  swrite(filename+' reduced: FWHM=%4.2f pixels, Sky=%d ADU' % (fwhm,sky))
  return outfile



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
  if not r:
    return im.data
  else:
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


###   Module init  ####

FITS=FITSnewcamera

