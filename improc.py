#Fits image image processing in Python. (C) Andrew Williams, 2000, 2001
#  andrew@physics.uwa.edu.au
#
# or
#
#  andrew@longtable.org
#
import os
import fits
import dircache
import cPickle
from globals import *



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
  if len(nfiles)>8:
    swrite("dodark - Too many files to median, truncating to first 8 images.")
    nfiles=nfiles[:8]
  di=[]
  for d in nfiles:
    im=fits.FITS(d,'r')
    im.bias()
    di.append(im)
  im=fits.median(di)
  outfile=os.path.abspath(os.path.dirname(di[0].filename))+'/dark.fits'
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, fits.Float32)


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
    im=fits.FITS(d,'r')
    im.bias()
    im.dark()
    fits.divide(im.data, fits.sum(fits.sum(im.data))/fits.product(im.data.shape), im.data)
    di.append(im)
  im=fits.median(di)
  if im.headers.has_key('FILTERID'):
    filt=im.headers['FILTERID'][1]          #First letter of filter name
  outfile=os.path.abspath(os.path.dirname(di[0].filename))+'/flat'+filt+'.fits'
  if os.path.exists(outfile):
    os.remove(outfile)
  im.save(outfile, fits.Float32)


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
  swrite('logged reduction of '+filename)


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

  img=fits.FITS(fullfile,'r')    #Load the file
  img.bias()                      #Subtract bias and trim overscan
  img.dark()                      #Subtract scaled dark image
  img.flat()                      #Divide by appropriate flatfield
  img.save(outfile,fits.Int16)   #Save in Int16 format
  _rlog(fname)
  return outfile

