

def sexstring(value=0,sp=':'):
  """Usage: sexstring(value=0,sp=':')
     Convert the floating point 'value' into a sexagecimal string, using
     'sp' as a spacer between components
  """
  aval=abs(value)
  if value<0:
    outs='-'
  else:
    outs=''
  D=int(aval)
  M=int((aval-float(D))*60)
  S=float(int((aval-float(D)-float(M)/60)*36000))/10
  outs=outs+`D`+sp+`M`+sp+`S`
  return outs


def dosname(uname):
  "Return shortened filename for DOS 8.3 restrictions"
  dname=uname[:-1]   #strip .fits to .fit
  dname=dname[:-7]+dname[-5:]  #strip leading digits from filectr
  return dname


