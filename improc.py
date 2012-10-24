
import os
import tempfile
import fits
from globals import *

if fits.Gotnumpy:
  import numpy as num
  from numpy.numarray import mlab
  from numpy.numarray.nd_image import convolve
elif fits.Gotnumarray:
  import numarray as num
  from numarray import mlab
  from numarray.nd_image import convolve
elif fits.Gotnumeric:
  import Numeric as num
  import MLab as mlab
  import Numeric.convolve


lastdark = None     #Contains the last Dark image used, to cache the data.
lastbias = None
lastflats = []      #A cache of the last few flatfield images used.


class FITS(fits.FITS):
  """FITS image class. Creation accepts two parameters, filename and read mode.
     If the read mode is 'h', the file headers are read, and two dictionaries,
     object.headers and object.comments are created. If the read mode is 'r', 
     the data section is read as well, producing a Numeric Python array 
     attribute, object.data. If the filename is null, an empty (but valid FITS)
     header is constructed, and a 512x512 pixel data section, initialised to 
     zeroes (unless the mode is 'h' for headers only).

     This class builds on the file IO in fits.py by adding reduction methods,
     separate from fits.py because local customisation would be needed.
     The reduction methods on the image include: bias, dark, and flat.
  """

  def noise(self,region=''):
    t = mlab.std(_parseregion(self,region))
    return _ndmedian(t)

  def median(self,region=''):
    t = _ndmedian(_parseregion(self,region))
    return _ndmedian(t)

  def mean(self,region=''):
    t = mlab.mean(_parseregion(self,region))
    return mlab.mean(t)

  def max(self,region=''):
    t = mlab.max(_parseregion(self,region))
    return mlab.max(t)

  def min(self,region=''):
    t = mlab.min(_parseregion(self,region))
    return mlab.min(t)

  def bias(self, biasfile=None):
    """Trims and Bias subtracts the image, using 'bias.fits' in the current dir.
       If 'biasfile' is specified, that file is used instead. The last bias image used
       is cached in the 'lastbias' global, to save re-loading a bias image every time.
    """
    global lastbias
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if self.comments["HISTORY"].find("BIAS: ") > -1:
      print "Can't bias subtract, image already bias subtracted."
      return 0

    biasimage = None
    if type(biasfile) == str and biasfile <> '':
      biasimage = FITS(biasfile)      #If a filename is supplied, load the image
    elif isinstance(biasfile,fits.FITS):
      biasimage = biasfile           #If it's a FITS image, use it as-is
    else:                     #Use the default bias frame
      if lastbias:            #The cached image if the file directory matches
        if (os.path.abspath(os.path.dirname(self.filename)) ==
            os.path.abspath(os.path.dirname(lastbias.filename))):
          if ('MODE' not in self.headers.keys()) or ('MODE' not in lastbias.headers.keys()):
            biasimage = lastbias   #Always use cached image if there's no mode field in either image
          elif self.headers['MODE'] == lastbias.headers['MODE']:
            biasimage = lastbias   #If there is a mode field, only use the cached image if the mode matches
    if not biasimage:
      if 'MODE' not in self.headers.keys():
        bfile = 'bias.fits'
      else:
        bfile = 'bias-%s.fits' % self.headers['MODE'][1:-1]
      biasfile = os.path.abspath(os.path.dirname(self.filename)) + '/' + bfile
      if os.path.exists(biasfile):
        biasimage = FITS(biasfile,'r')  #All has failed, load 'bias.fits'
      else:
        print "Default bias image not found: %s" % biasfile
        return 0
    lastbias = biasimage                #Save it for next time

    biastemp = float(biasimage.headers['CCDTEMP'])
    deltatemp = biastemp - float(self.headers['CCDTEMP'])
    if abs(deltatemp) > 1.0:
      print "Warning - bias frame and image temp differ by " + `deltatemp`
    self.data -= biasimage.data
    self.histlog("BIAS: Image %s (%6.2fC) subtracted" % (os.path.abspath(biasimage.filename), biastemp))
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
       0.5C difference. The temperatures are then used to multiply the dark image
       by 2^(delta-T/6) to correct for the theoretical dependence of dark current
       on CCD temperature. The exposure times are used to calculate the exposure
       ratio for the dark subtraction.
    """
    global lastdark
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if self.comments["HISTORY"].find("BIAS: ") == -1:
      print "Can't dark subtract, image not bias corrected."
      return 0
    if self.comments["HISTORY"].find("DARK: ") > -1:
      print "Can't dark subtract, image already dark subtracted."
      return 0

    darkimage = None
    if type(darkfile) == str and darkfile <> '':
      darkimage = FITS(darkfile)      #If a filename is supplied, load the image
    elif isinstance(darkfile,FITS):
      darkimage = darkfile           #If it's a FITS image, use it as-is
    else:                     #Use the default dark frame
      if lastdark:            #The cached image if the file directory matches
        if (os.path.abspath(os.path.dirname(self.filename)) ==
            os.path.abspath(os.path.dirname(lastdark.filename))):
          if ('MODE' not in self.headers.keys()) or ('MODE' not in lastdark.headers.keys()):
            darkimage = lastdark   #Always use cached image if there's no mode field in either image
          elif self.headers['MODE'] == lastdark.headers['MODE']:
            darkimage = lastdark   #If there is a mode field, only use the cached image if the mode matches
    if not darkimage:
      if 'MODE' not in self.headers.keys():
        dfile = 'dark.fits'
      else:
        dfile = 'dark-%s.fits' % self.headers['MODE'][1:-1]
      darkfile = os.path.abspath(os.path.dirname(self.filename)) + '/' + dfile
      if os.path.exists(darkfile):
        darkimage = FITS(darkfile,'r')  #All has failed, load 'dark.fits'
      else:
        print "Default dark image not found: %s" % darkfile
        return 0
    lastdark = darkimage                #Save it for next time

    darktemp = float(darkimage.headers['CCDTEMP'])
    deltatemp = float(self.headers['CCDTEMP']) - darktemp
    if abs(deltatemp) > 1.0:
      print "Warning - dark frame and image CCD temps differ by " + `deltatemp`

    eratio = float(self.headers['EXPTIME']) / float(darkimage.headers['EXPTIME'])
    tratio = 2.0**( deltatemp/6.0 )
    self.data = self.data - (darkimage.data * eratio * tratio)
    self.histlog("DARK: %s ET=%ss, T=%5.2fC" % (os.path.abspath(darkimage.filename), darkimage.headers['EXPTIME'], darktemp))
    self.histlog("DARK: exp time ratio=%5.3f, temp ratio=%5.3f" %
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
       for each filter by calculating the median of several (bias subtracted)
       flatfield images. If exposure times are not very short,
       the flatfields should be dark subtracted as well as bias corrected.

    """
    global lastflats
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if self.comments["HISTORY"].find("BIAS: ") == -1:
      print "Can't flatfield, image not bias corrected and trimmed."
      return 0
    if self.comments["HISTORY"].find("DARK: ") == -1:
      print "Can't flatfield, image not dark subtracted."
      return 0
    if self.comments["HISTORY"].find("FLAT: ") > -1:
      print "Can't flatfield, image already flatfield corrected."
      return 0

    flatimage = None
    if type(flatfile) == str and flatfile <> '':
      flatimage = FITS(flatfile)         #If given a filename, load the image
    elif isinstance(flatfile,FITS):
      flatimage = flatfile               #If given a FITS image, use as-is
    else:                            #Look in our cache for a match
      for flt in lastflats:
        if (os.path.abspath(os.path.dirname(self.filename))==
            os.path.abspath(os.path.dirname(flt.filename))  and
            self.headers['FILTERID'] == flt.headers['FILTERID'] ):
          if ('MODE' not in self.headers.keys()) or ('MODE' not in flt.headers.keys()):
            flatimage = flt   #Always use cached image if there's no mode field in either image
          elif self.headers['MODE'] == flt.headers['MODE']:
            flatimage = lastdark   #If there is a mode field, only use the cached image if the mode matches
    if not flatimage:              #Look for the default filename/s
      filedir = os.path.abspath(os.path.dirname(self.filename))
      try:
        filt = self.headers['FILTERID'][1:-1].split()[0].strip()
      except:
        filt = 'I'   #Default filter is I on Ariel startup
      if not filt[0].isdigit():
        filt = filt[0]  #Use first letter of filter name, unless it's a digit
      if 'MODE' not in self.headers.keys():
        ffile = 'flat%s.fits' % filt.upper()
      else:
        ffile = 'flat%s-%s.fits' % (filt.upper(), self.headers['MODE'][1:-1])

      flatfile = filedir+'/' + ffile
      if not os.path.exists(flatfile):
          print "Default flatfield not found: %s" % flatfile
          return None
      else:
        flatimage=FITS(flatfile,'r')

    self.data = self.data / flatimage.data
    self.histlog("FLAT: "+os.path.abspath(flatimage.filename))

    if flatimage not in lastflats:
      lastflats.append(flatimage)        #Add it to the cache
    if len(lastflats) > 8:
      lastflats = lastflats[1:]            #Discard old images
                                         #when the cache gets large.
  def fwhmsky(self):
    try:
      try:
        os.remove('/tmp/fwhmtmp.fits')
      except OSError:
        pass
      self.save('/tmp/fwhmtmp.fits',bitpix=16)
      os.system('/home/dts/bin/fwhmsky /tmp/fwhmtmp.fits')
      tmpdata = open('input.dophot','r').read().split()
      try:
        os.remove('input.dophot')
        os.remove('/tmp/fwhmtmp.fits')
      except OSError:
        pass
    except (OSError, IOError):
      print "Error with file creation while calculating FWHM, Sky"
      return -1,-1
    try:
      self.headers['FWHM'] = tmpdata[0]
      self.comments['FWHM'] = 'Seeing FWHM, in pixels.'
      self.headers['SKY'] = tmpdata[1]
      self.comments['SKY'] = 'Sky background, in ADU'
      return float(tmpdata[0]), float(tmpdata[1])
    except:
      print "Error calculating FWHM and Sky"
      return -1,-1




#
#Some support functions that might be of use externally:
#


def median(l=[]):
  """Returns a FITS object which is the median of all the provided FITS
     objects (either as a list or a tuple).
  """
  myl = []
  temps = []
  for i in l:
    if not hasattr(i,'data'):
      print "FITS object has no data section to operate on."
      return 0
    myl.append(i.data)
    try:
      temps.append(float(i.headers['CCDTEMP']))
    except KeyError:
      pass   #No CCDTEMP in header
  out = FITS()
  out.headers = l[0].headers
  out.comments = l[0].comments
  out.data = _ndmedian(num.array(myl))
  if temps:
    out.headers['CCDTEMP'] = `_ndmedian(num.array(temps))`

  return out



def med10(files='', bias=False):
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
  tempfile.tmpdir='/tmp'       #Set up temp file name structure
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
        if bias:
          tenlist[-1].bias()
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
          if bias:
            tenlist[-1].bias()
          allfiles=allfiles[1:]
      tmp=median(tenlist)      #Find the median of those ten files
      tmpname=tempfile.mktemp()     #Save the median of ten in a temp file
      tmp.save(tmpname)
      tmplist.append(tmpname)

    tenlist=[]                         #free up all that memory
    tmp=med10(tmplist, bias=False)  #recursivly call med10 on all of the temp files
    for n in tmplist:
      os.remove(n)            #remove all the temporary files
    return tmp


def reduce(fpat=''):
  """bias, dark, and flatfield a set of image, leave in subdirectory 'reduced'.
     If the 'reduced' directory doesn't exist, it will be created.

     The return value will be a list of names and paths of the reduced images
     if successful. This return value can be passed to other commands, eg
     display(allocate(reduce('/data/M*.fits')))
     
     eg: reduce('/data/myVimg*.fits /data/myIimg*')
  """
  return distribute(fpat,_reducefile)


def dobias(files=[]):
  """Take a list of bias frame filenames and turn them into a median bias image.

     Each image is loaded, and the median of all
     the images is written to the file 'bias.fits' in the same directory as the
     first FITS file.
  """
  nfiles = distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if not nfiles:
    logger.warning("dobias - No images to process.")
    return 0
  im = med10(nfiles, bias=False)    #Signal overscan subtraction only for each image
  firstimage = FITS(nfiles[0],'h')    #Read in just the headers of the first image
  if 'MODE' not in firstimage.headers.keys():
    bfile = 'bias.fits'
  else:
    bfile = 'bias-%s.fits' % firstimage.headers['MODE'][1:-1]
  outfile = os.path.abspath(os.path.dirname(nfiles[0])) + '/' + bfile
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, bitpix=-32)


def dodark(files=[]):
  """Take a list of dark frame filenames and turn them into a median dark image.

     Each image is loaded, bias subtracted and trimmed, and the median of all
     the images is written to the file 'dark.fits' in the same directory as the
     first FITS file.
  """
  nfiles = distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if not nfiles:
    logger.warning("dodark - No images to process.")
    return 0
  im = med10(nfiles, bias=True)   #Signal overscan and bias image subtraction
  firstimage = FITS(nfiles[0],'h')    #Read in just the headers of the first image
  if 'MODE' not in firstimage.headers.keys():
    dfile = 'dark.fits'
  else:
    dfile = 'dark-%s.fits' % firstimage.headers['MODE'][1:-1]
  outfile = os.path.abspath(os.path.dirname(nfiles[0])) + '/' + dfile
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, bitpix=-32)


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
  nfiles = distribute(files, lambda x: x)   #Expand each name for wildcards, etc
  if nfiles and type(nfiles) == str:
    nfiles = [nfiles]
  if len(nfiles)>15:
    logger.warning("doflat - Too many files to median, truncating to first 15 images.")
    nfiles = nfiles[:15]
  if not nfiles:
    logger.warning("doflat - No images to process.")
    return 0
  di=[]
  for d in nfiles:
    im = FITS(d,'r')
    im.bias()
    im.dark()
    num.divide(im.data, num.sum(num.sum(im.data))/num.product(im.data.shape), im.data)
    di.append(im)
  im = median(di)
  if im.headers.has_key('FILTERID'):
    try:
      filt = im.headers['FILTERID'][1:-1].split()[0].strip()
    except:
      filt = 'I'
    if filt[0].isdigit():
      pass  #Use full filter name
    else:
      filt = filt[0]  #Get first letter of filter name
  else:
    filt = 'X'
  if 'MODE' not in im.headers.keys():
    ffile = 'flat%s.fits' % filt.upper()
  else:
    ffile = 'flat%s-%s.fits' % (filt.upper(), im.headers['MODE'][1:-1])

  outfile = os.path.abspath(os.path.dirname(nfiles[0])) + '/' + ffile
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, bitpix=-32)


def gaussian(size=9, sigma=3.0):
  """Return a 2D array of shape (size,size) containing a normalised Gaussian 
     function with stdev of 'sigma', centered on the array. 'size' must be an 
     odd number.
  """
  c,r = divmod(size,2)
  m = 1/(sigma*math.sqrt(2*math.pi))
  if r == 1:  #If size is odd:
    k = num.fromfunction(lambda x,y: m*num.exp(-((x-c)**2+(y-c)**2)/(2*sigma*sigma)), (size,size) )
    k = k/k.sum()
    return k  


def findstar(img=None, n=1):
  """Given a FITS image, return a list of coordinates for the 'n' brightest
     star-like objects. The search is done by convolving the image with a 2D gaussian
     with the appropriate sigma (derived from fwhmsky), normalising to one, and then
     working down from the brightest pixel, calling it the coordinates of a
     'star-like' object if the 8 pixels surrounding it are dimmer than it, and if
     it's at least 4 pixels from any other star-like object already listed.

     Note that the coordinates returned are Numeric array indices into the data, they
     must be swapped and increased by 1 to correspond to ds9 physical image coordinates,
     eg 257,261 returned by findstar actually means (262,258) in the image.
  """
  img.bias()
  fwhm,sky = img.fwhmsky()
  if fwhm < 0:
    return []   #No stars in field
  k = gaussian(size=21, sigma=(fwhm/0.6)/2.3548 )
  xim = convolve(img.data, k, mode='nearest')
  sq = convolve(img.data*img.data, num.ones((21,21)), mode='constant')
  sf = num.sqrt((k*k).sum())
  out = xim/(sf*num.sqrt(sq))
  starlist = []
  rows,cols = out.shape
  sortflat = num.argsort(out.flat)
  i = -1
  offsets = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
  while (len(starlist)<(3*n+3)) and (i>(-rows*cols)):
    x,y = divmod(sortflat[i],cols)
    if x<5 or y<5 or x>(rows-5) or y>(cols-5):
      pass
    else:
      reject = 0
      for ix,iy in offsets:
        if (out[x+ix,y+iy] > out[x,y]):
          reject = 1
      if not reject:
        for val,ox,oy in starlist:
          if (ox-x)*(ox-x) + (oy-y)*(oy-y) < 16:
            reject = 1
      if not reject:
        starlist.append((xim[x,y],x,y))
    i -= 1
  starlist.sort(lambda b,a: cmp(a[0],b[0]))  #Sort by brightness instead of gaussian fit
  slout = []
  for val,x,y in starlist:
    slout.append((x,y))
  return slout


def to8bit(img=None):
  """Return an array of floats in the range 0-255 given a FITS image object. 
     Sorts the data, and uses the 5th and 95th percentile as low and high
     cutoffs.
  """
  sdata = num.sort(num.ravel(img.data))
  lcut = sdata[int(sdata.shape[0]*0.05)]
  hcut = sdata[int(sdata.shape[0]*0.95)]

  return 255 * (num.clip(img.data, lcut, hcut) - lcut) / (hcut - lcut)


#
# Utility functions used internally, probably not useful elsewhere.
#


def _rlog(fname='',filename='?',filterid='?',exptime=0.0,ccdtemp=0.0,pjd=0.0,fwhm=0.0,sky=0.0,secz=0.0):
  """Record an image file reduction in ./reducelog so that it won't be
     reduced again.
  """
  fullfile=os.path.abspath(os.path.expanduser(fname))
  filedir=os.path.dirname(fullfile)
  filename=os.path.basename(fullfile)
  if not os.path.exists(filedir+'/reducelog'):
    empty=1
  else:
    empty=0
  fmt="%-18s %8.5f   %1s  %5.1f   %5.1f  %5.2f %5d  %4.2f\n"
  f=open(filedir+'/reducelog','a')
  if empty:
    f.write("Reduce log for "+filedir+"\n")
    f.write("#Filename          PJD        Filt Exptime CCDTemp FWHM  SKY   SecZ\n")
    try:
      os.remove('/tmp/reducelog')
    except OSError:
      pass
    os.symlink(filedir+'/reducelog', '/tmp/reducelog')
  f.write(fmt % (filename,pjd,filterid,exptime,ccdtemp,fwhm,sky,secz) )
  f.close()


def _reducefile(fname=''):
  """Usage: reducefile(fname)
     Trim, flatfield, bias an image, leave in subdir 'reduced' under the
     current path - if the 'reduced' directory doesn't exist, it will be
     created.

     The return value will be the name and path of the reduced image if
     successful, or '' if the reduction failed.
  """
  fullfile = os.path.abspath(os.path.expanduser(fname))
  filedir = os.path.dirname(fullfile)
  filename = os.path.basename(fullfile)
  outfile = filedir+'/reduced/' + filename

  if not os.path.isdir(filedir + '/reduced'):
    os.mkdir(filedir + '/reduced')

  if not os.path.exists(fullfile):
    logger.error('reducefile - Input image file not found: ' + fullfile)
    return None

  img = FITS(fullfile,'r')    #Load the file
  img.bias()                      #Subtract bias and trim overscan
  img.dark()                      #Subtract scaled dark image
  img.flat()                      #Divide by appropriate flatfield

  exptime = float(img.headers['EXPTIME'])
  filterid = img.headers['FILTERID'][1].strip()
  secz = float(img.headers['SECZ'])
  hjd = float(img.headers['HJD'])
  pjd = hjd-2450000.0
  ccdtemp = float(img.headers['CCDTEMP'])

  fwhm,sky = img.fwhmsky()
  img.save(outfile, bitpix=16)   #Save in Int16 format
  os.system('/home/observer/PyDevel/Prosp/extras/imsex.py ' + outfile)
  _rlog(fname,filename,filterid,exptime,ccdtemp,pjd,fwhm,sky,secz)
  logger.info(filename + ' reduced: FWHM=%4.2f pixels, Sky=%d ADU' % (fwhm,sky))
  return outfile


def _parseregion(im=None, r=''):
  """Returns an array slice from a FITS object given a region string.
     For example, a region string might be '[512,544:1,512]', and the Numeric
     array returned would be im.data[0:512, 511:544].
  """
  if not r:
    return im.data
  else:
    r1,r2 = tuple(r.strip()[2:-2].split(':'))
    xs,xe = tuple(r1.strip().split(','))
    ys,ye = tuple(r2.strip().split(','))
    return im.data[int(ys)-1:int(ye), int(xs)-1:int(xe)]
    

def _msort(m):
  """_msort(m) returns a sort along the first dimension of m as in MATLAB.
  """
  return num.transpose(num.sort(num.transpose(m)))


def _ndmedian(m):
  """median(m) returns a median of m along the first dimension of m. Parameter
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


