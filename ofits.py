import string        #load string handling library
import types
import os
import stat
import time
import fits
from fits import *
from Numeric import *

delchars=''
for i in range(32):
  delchars=delchars+chr(i)
for i in range(127,256):
  delchars=delchars+chr(i)
translatetable=string.maketrans(delchars,' '*len(delchars))


class FITS(fits.FITS):
  def __init__(self, filename='', mode='r'): 
                                  #mode is 'h' (headers) or 'r' (data+headers)
    root,extn=os.path.splitext(os.path.basename(filename))
    flen=os.stat(filename)[stat.ST_SIZE]
    if string.upper(extn)=='.CCD':
      if flen<480100:
        mode='c'
      else:
        mode='v'
    self.filename=filename
    if mode=='h' or mode=='r':  
      fits.FITS.__init__(self,filename,mode)

    if mode=='c':          #Mode h opens file, reads headers and data
      if not filename:
        self.headers={'SIMPLE':'T', 'EXTEND':'T', 'NAXIS':'2', 
                      'NAXIS1':'600', 'NAXIS2':'400'}
        self.comments={'COMMENT':'Empty header & data','HISTORY':''}
        if GotNum:
          self.data=zeros((600,400),Float)
        else:
          print "Numeric library not present, can't create data section."
      else:
        self.file=open(self.filename,'r')
        self.headers={'SIMPLE':'T', 'EXTEND':'T', 'NAXIS':'2',
                      'NAXIS1':'600', 'NAXIS2':'400'}
        self.comments={'COMMENT':'old .CCD format image','HISTORY':''}

        if GotNum:         #If we've got Numeric, load the data section too.
          self.data=fromstring(self.file.read(480000),Int16).astype(Float64)
          self.data.shape=(600,400)

          #Add 65536 if val <0 here
          self.data = self.data + less(self.data,0)*65536

          tail=fromstring(self.file.read(),Int16)
          self.headers['RA']="'"+`tail[0]`+":"+`tail[1]`+":"+`tail[2]`+"'"
          self.headers['DEC']="'"+`tail[3]`+":"+`tail[4]`+":"+`tail[5]`+"'"
          self.headers['TIME-OBS']="'"+`tail[6]`+":"+`tail[7]`+":"+`tail[8]`+ \
                                   "."+`tail[9]`+"'"
          self.headers['DATE-OBS']="'"+`tail[12]`+"-"+`tail[11]`+"-"+ \
                                   `tail[10]`+"'"
          self.headers['EXPTIME']=`tail[13]+tail[14]/1000.0`
          i=15
          filterid=''
          filter=8
          while i<23 and filter==8:
            if tail[i]<8 and i==15:
              filter=tail[i]
            else:
              filterid=filterid+chr(tail[i])
            i=i+1
          if filter<>8:
            self.headers['FILTER']=`filter`
          if filterid<>'':
            self.headers['FILTERID']="'"+filterid+"'"
          objid=''
          while i<tail.shape[0] and tail[i]<>0:
            objid=objid+chr(tail[i])
            i=i+1
          self.headers['OBJECT']="'"+objid+"'"
          self.headers['OBSERVAT']="'Perth'"
          self.headers['TELESCOP']="'Perth-Lowell'"
          self.headers['LATITUDE']="'-32:00:29.1'"
          self.headers['LONGITUD']="'-116:08:06.07'"
          self.headers['INSTRUME']="'PARG Liquid N2 cooled CCD camera'"
          self.headers['DETECTOR']="'Thomson TH7883'"
          self.headers['DATASEC']="'[11,394:2,577]'"
          self.headers['BIASSEC']="'[10,394:579,590]'"

          #Add bias and data section headers here, once I work out 
          #What the dam numbers are...
        else:
          print "Numeric library not present, can't load data section."

        self.file.close()

    if mode=='v':    #Vista format non-byteswapped FITS file
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
          self.line=self.file.read(80)         #Read 80-byte cards
          self.finished=_parseline(self,self.line)
        if not self.comments.has_key('HISTORY'):
          self.comments['HISTORY']=''            #Add a blank HISTORY card

        if GotNum:         #If we've got Numeric, load the data section too.
          # self.file.seek(2880*(self.file.tell()/2880+1))
          self.file.seek(5760)    #All Ralph's pseudo-fits have 5760 byte hdrs
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
          self.data=fromstring(self.file.read(len),type).astype(Float64)
          self.data.shape=tuple(shape)

          if self.headers.has_key('BSCALE') and self.headers.has_key('BZERO'):
            bscale=float(self.headers['BSCALE'])
            bzero=float(self.headers['BZERO'])
            multiply(self.data,bscale,self.data)
            add(self.data,bzero,self.data)
        else:
          print "Numeric library not present, can't load data section."


  def dark(self,darkfile=None):
    return 1                   #Dummy, no dark subtraction needed for CCD


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
       and trimmed) flatfield images.

    """
    if not hasattr(self,'data'):
      print "FITS object has no data section to operate on."
      return 0
    if string.find(self.comments["HISTORY"],"BIAS: ")==-1:
      print "Can't flatfield, image not bias corrected and trimmed."
      return 0
    if string.find(self.comments["HISTORY"],"FLAT: ")>-1:
      print "Can't flatfield, image already flatfield corrected."
      return 0

    flatimage=None
    if type(flatfile)==types.StringType and flatfile<>'':
      flatimage=FITS(flatfile)         #If given a filename, load the image
    elif isinstance(flatfile,fits.FITS):
      flatimage=flatfile               #If given a FITS image, use as-is
    
    if not flatimage:              #Look for the default filename/s
      filedir=os.path.abspath(os.path.dirname(self.filename))
      filt=self.headers['FILTERID'][1]  #Get first letter of filter name
      if filt==' ':
        filt='I'     #Default filter is I on Ariel startup
      names=('flat'+string.lower(filt)+'.ccd',
             'flat'+string.upper(filt)+'.ccd',
             'FLAT'+string.upper(filt)+'.CCD',
             'flat'+string.lower(filt)+'.CCD',
             'flat'+string.lower(filt)+'.fits',
             'flat'+string.upper(filt)+'.fits',
             'flat'+string.lower(filt)+'.fit',
             'flat'+string.upper(filt)+'.fts')
      flatfile=''
      for n in names:
        if os.path.exists(filedir+'/'+n):
          flatfile=filedir+'/'+n
      if flatfile=='':
        print 'Flatfield not found for filter',filt
        return None
      if os.path.exists(flatfile):
        flatimage=FITS(flatfile,'r')
      else:
        print "Flatfield not found in "+filedir+" for filter "+filt
        return 0

    self.data = self.data / flatimage.data
    histlog(self,"FLAT: "+os.path.abspath(flatimage.filename))



def clean(s=''):
  """Clean dirty header values - ensure quotes paired and no non-ascii chars

     Strips nulls from the string, adds a trailing quote if only one quote mark
     is present.
  """
  if string.count(s,'"')==1:
    s=s+'"'
  if string.count(s,"'")==1:
    s=s+"'"
  return string.translate(s,translatetable)



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

  key=clean(string.strip(line[:8]))  #First 8 chars with whitespace stripped
  value=string.strip(line[9:]) #Rest of line with whitespace stripped
  comment=''                   #Empty comment field for now

  if key == 'COMMENT':    #Handle case where comment takes up the whole line
    if ob.comments.has_key('COMMENT'):
      ob.comments['COMMENT']=ob.comments['COMMENT']+'\n'+clean(value)
    else:
      ob.comments['COMMENT']=clean(value)
  elif key == 'HISTORY':  #Handle 'HISTORY' like 'COMMENT'
    if ob.comments.has_key('HISTORY'):
      ob.comments['HISTORY']=ob.comments['HISTORY']+'\n'+clean(value)
    else:
      ob.comments['HISTORY']=clean(value)

#For both HISTORY and COMMENT, build up one value, with newlines seperating
#each line in the FITS file. Otherwise, it's one dictionary entry per line

  elif key == 'END':
    return 1
  else:
    if string.find(value,'/')>-1:    #Strip the comment off
      comment=string.strip(value[string.find(value,'/')+1:])
      value=string.strip(value[:string.find(value,'/')])

#Add dictionary entries for the key value, and key comment if it exists
    ob.headers[key]=clean(value)
    if comment<>'':
      ob.comments[key]=clean(comment)

    return 0

