
"""Remote logging interface:

   The site name is hardwired into this module near the top of the file, it
   must be set up for your site by uncommenting the appropriate line.
   If you need to set up an http proxy server, uncomment and edit the
   appropriate line below.

"""

#Standard python modules
import os
import string
import urllib
import threading
import os
import types
import operator
import glob

#My FITS file support module
import fits

##################Customisable lines, set for your site#####################

#Uncomment and edit this string if you need to use a proxy server. We need to
#in Perth because un-proxied web traffic is blocked by the firewall, but if
#you don't _need_ to use one, don't bother, it won't do any caching anyway..
os.environ["http_proxy"]="http://proxy.calm.wa.gov.au:8080"

#Uncomment the correct site= line, comment out the rest
#site="Canopus"
site="Perth"
#site="SAAO"
#site="ESO"

#################End of section that needs customising######################

#URL for the CGI script that receives the data
base="http://www.astro.rug.nl/~planet/cgi-bin/rlogs.cgi"


def ntranslate(name="HB-2K-060"):
  """Localised object name translation. This function should return a 
     name of the form "OB2K026", given the local name (eg OB-2K-026).
     Uses the name of the site to choose how to do the translation.

     Currently no translation is needed at any site.

     The function returns nothing if the name doesn't look like a PLANET
     object, indicating that the object shouldn't be logged.
  """
  name=string.strip(string.upper(name))
  if len(name)==7:
    team,place,year,num=name[0],name[1],name[2:4],name[4:]
    if ( (team=='M' or team=='E' or team=='O' or team=='K') and
         (place=='B' or place=='L' or place=='S') and
         (year=='98' or year=='99' or year=='2K' or year=='01' or year=='02'
          or year=='03') and
         (num[0] in string.digits and num[1] in string.digits and
          num[2] in string.digits)):
      return name    #return (translated?) version of name
  return          #Return nothing, indicating it's not a PLANET name


def senddata( imgs=[('Nothing',0)] ):
  """Build up the CGI form parameters from the (name,date) list and do the 
     encoding to escape invalid characters, etc. Sends data for each image
     as "name0" and "date0", "name1" and "date1", etc, plus a single "Site"
     entry at the beginning. Dates are in PJD's (JD-2450000).
  """
  num=0
  params={}
  params["Site"]=site
  for name,date in imgs:
    n=ntranslate(name)
    if n:     #True if the name appears to be a PLANET object
      params["name"+`num`]=n
      params["date"+`num`]=date
      num=num+1
  data=urllib.urlencode(params)     #Encode spaces as %20, etc
  getpage(base,data)


def getpage(base,data):
  """This function runs in the background to actually download the page.
     It passes the base script URL along with all the form values in a block,
     passing them in the URL fails becuase of the length limit on URL's.
  """
  f=urllib.urlopen(base, data)
  page=f.read()
  f.close()
#  print page
  if not string.find(page,'OK'):
    print "Error logging data:"
    print page    
    

def distribute(fpat='',function=None,args=None):
  """Takes a single string or a list of strings. Calls 'function' on each file
     specified after looping over the list, and expanding each string for
     wildcards using 'glob'.
     eg: distribute('/data/myimg*.fits',display)
  """
  donelist=[]
  if type(fpat)<>types.ListType:
    fpat=[fpat]
  t1=reduce(operator.concat,map(string.split,fpat))
  t2=reduce(operator.concat,map(glob.glob,t1))
  for n in t2:
    if args:
      resn=function(n,args)
    else:
      resn=function(n)
    if resn:
      donelist.append(resn)

  if len(donelist)==0:
    return ''
  elif len(donelist)==1:
    return donelist[0]
  else:
    return donelist


def rlog(filelist=[]):
  """Takes a list of images and/or file wildcards (eg *.fits), and sends the
     object names and PJD's to the PLANET web site. This may need local
     customisation if some sites don't have OBJECT or JD in the FITS header.
  """
  names=distribute(filelist, lambda x: x)
  if type(names)<>type([]):
    names=[names]
  imgs=[]
  for n in names:
    try:
      f=fits.FITS(n,"h")
      if site<>"Canopus":
        imgs.append((f.headers['OBJECT'][1:-1],
                     float(f.headers['JD'])-2450000))
      else:
        imgs.append((f.headers['OBJECT'][1:-1],
                     float(f.headers['MJD'])-49999.5))
    except:
      print "Error parsing FITS cards in file: "+n
            #If one of the files gives an error, just ignore it.
#  print imgs
  senddata(imgs)
  
