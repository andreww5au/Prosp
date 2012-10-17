
"""
        Unit DoHGSC;
        interface
        uses XYGlobs;

        {Search the Hubble giude star catalogue}
"""
import math

import xyglobs
import fits

LargeBox = [1,49,96,141,184,224,260,292,
            319,340,355,364,367,415,462,
            507,550,590,626,658,685,706,
            721,730]
DecBandCentre = [3.75,11.25,18.75,26.25,33.75,41.25,48.75,
                 56.25,63.75,71.25,78.75,86.25,
                 -3.75,-11.25,-18.75,-26.25,-33.75,
                 -41.25,-48.75,
                 -56.25,-63.75,-71.25,-78.75,-86.25]
MagLimit = 12.2



def HGSCSearch(RAmin, Decmin, RAmax, Decmax):
  """Procedure HGSCSearch(RAmind,Decmind,RAmaxd,Decmaxd:DMS;var Candidates:ObjArray);
                           {Search Limits} 
     converted to function, return list of Guidestar recs
  """
  sm_reg_x = fits.FITS('/GSC/tables/sm_reg_x.tbl', 'r',tmode='dict')

#       Search limits are in degrees.Order the RA limits in numbered in descending order }
#       Determine the large box number containing  for the search limits
#       Large boxes are 7.5 degree bands of Dec wide. The centre of the band
#       is }
#       Generate the limits of the search area - not done in this version}

  Candidates = []
  
#  print RAmin, Decmin, RAmax, Decmax

  RALimits = [0.0, 0.0, 0.0, 0.0, 0.0]   #Extra item to allow 1..4 instead of 0..3
  DecLimits = [0.0, 0.0, 0.0, 0.0, 0.0]  #Extra item to allow 1..4 instead of 0..3
  Directory = ['', '', '', '', '']
  SmallBoxNumber = [0, 0, 0, 0, 0]

  RALimits[1] = RAmin
  DecLimits[1] = Decmin
  RALimits[2] = RAmax
  DecLimits[2] = Decmax

  RALimits[3] = RALimits[1]
  DecLimits[3] = DecLimits[2]
  RALimits[4] = RALimits[2]
  DecLimits[4] = DecLimits[1]

#       The RA limits are complicated by the}
#       If the difference between the largest and smallest value > 180 then
#        we cross the 0 hour mark}
  ZeroHours = 0
  if abs(RALimits[1]-RALimits[2]) >= 180:
    ZeroHours = 1
  if RALimits[1] > RALimits[2]:
    if not ZeroHours:
      EastSearch = RALimits[1]
      WestSearch = RALimits[2]
    else:
      EastSearch = RALimits[2] + 360.0
      WestSearch = RALimits[1]
  else:
    if not ZeroHours:
       EastSearch = RALimits[2]
       WestSearch = RALimits[1]
    else:
       EastSearch = RALimits[1] + 360.0
       WestSearch = RALimits[2]

  if DecLimits[1] > DecLimits[2]:
    NorthSearch = DecLimits[1]
    SouthSearch = DecLimits[2]
  else:
    NorthSearch = DecLimits[2]
    SouthSearch = DecLimits[1]

# for each pair of RA and Dec calculate the large box number the small box number}
  for i in range(1,5):
    Work = int(abs(DecLimits[i])/7.5)
#    print 'RAlimit=',RALimits[i],' Declimit=',DecLimits[i], 'Work=',Work
    DecBand = int(Work)
    if DecLimits[i] < 0:
      DecBand = DecBand + 12
    # generate the directory name}
    Work = DecBandCentre[DecBand]
#    print 'Work=',Work
    if DecBandCentre[DecBand] < 0:
      # {Southern hemispere object}
      Work = DecBandCentre[DecBand] + 3.75
#      print 'S Work=',Work
      if (Work - int(Work)) == -0.5:
        Work = int(Work) - 0.3
#      print 'S Work=',Work
      Work = round(100 * Work)
#      print 'S Work=',Work
      FileString = '%d' % (-1*int(Work))
      Directory[i] = '/GSC/gsc/s'
#      print FileString
    else:
      Work = DecBandCentre[DecBand] - 3.75
#      print 'N Work=',Work
      if (Work - int(Work)) == 0.5:
        Work = int(Work) + 0.3
#      print 'N Work=',Work
      Work = round(100 * Work)
#      print 'N Work=',Work
      FileString = '%d' % Work
#      print FileString
      Directory[i] = '/GSC/gsc/n'

    FileString = '0'*(4-len(FileString)) + FileString
    Directory[i] = Directory[i] + FileString + '/'     #Directory string
#    print Directory[i]
#   Generate the large box number- Number of large boxes in dec band}
    NumberOfBoxs = 48*math.cos(math.pi*DecBandCentre[DecBand]/180.0)
    NumberOfBoxs = int(round(NumberOfBoxs))
    BoxInterval = 360.0/NumberOfBoxs    #Number of degrees in a large box}
    ThisBox = int(RALimits[i]/BoxInterval)
    SmallBox = ThisBox
    ThisBox = ThisBox + LargeBox[DecBand]
#    print 'NumberOfBoxs=',NumberOfBoxs,' BoxInterval=',BoxInterval,' SmallBox=',SmallBox, 'ThisBox=',ThisBox
    LRN = int(ThisBox)         #Large box number}
#   Large box RA and Dec limits}
    DeltaDec = 7.5/sm_reg_x.table.data[LRN][1]          #Depth
    DeltaRA = BoxInterval/sm_reg_x.table.data[LRN][1]   #Depth
#    print 'LRN=',LRN,' DeltaDec=',DeltaDec,' DeltaRA=',DeltaRA
    if DecLimits[i] >= 0:

#     first box occurs in the south west corner - northern hemishere}
      BoxRALimit = SmallBox*BoxInterval
      BoxDecLimit = DecBandCentre[DecBand] - 3.75
#     Which small box does this RA and Dec lie in.}
      DecTest = BoxDecLimit
      DBN = 0
      while DecTest < DecLimits[i]:
        DecTest = DecTest + DeltaDec
        DBN = DBN + 1
        if DBN > sm_reg_x.table.data[LRN][1]:  #Depth
          DecTest = 999
      RATest = BoxRALimit
      RABN = 0
      while RATest < RALimits[i]:
        RATest = RATest + DeltaRA
        RABN = RABN + 1
        if RABN > sm_reg_x.table.data[LRN][1]:  #Depth
          RATest = 999
      Work = sm_reg_x.table.data[LRN][0]   #SRN
      SmallBoxNumber[i] = ( sm_reg_x.table.data[LRN][0] + 
                            (DBN-1)*sm_reg_x.table.data[LRN][1] + RABN - 1 ) 
    else:
#     first box occurs in the nouth west corner - southern hemisphere}
      BoxRALimit = SmallBox*BoxInterval
      BoxDecLimit = DecBandCentre[DecBand] + 3.75
#      print 'BoxRALimit=',BoxRALimit,' BoxDecLimit=',BoxDecLimit
#     Which small box does this RA and Dec lie in.}
      DecTest = BoxDecLimit
      DBN = 0
      while DecTest > DecLimits[i]:
        DecTest = DecTest - DeltaDec
        DBN = DBN + 1
        if DBN > sm_reg_x.table.data[LRN][1]:   #Depth
          DecTest = 999
      RATest = BoxRALimit
      RABN = 0
      while RATest < RALimits[i]:
        RATest = RATest + DeltaRA
        RABN = RABN + 1
        if RABN > sm_reg_x.table.data[LRN][1]:   #Depth
          RATest = 999
      Work = sm_reg_x.table.data[LRN][0]
      SmallBoxNumber[i] = ( sm_reg_x.table.data[LRN][0] + 
                             (DBN-1)*sm_reg_x.table.data[LRN][1] + RABN - 1 ) 
#    print 'DBN=',DBN,' RABN=',RABN,' F0=',sm_reg_x.table.data[LRN][0], ' F1=',sm_reg_x.table.data[LRN][1]
#    print 'SmallBoxNumber=',SmallBoxNumber[i]

    FileString = '%d' % SmallBoxNumber[i]
    FileString = '0'*(4-len(FileString)) + FileString
    Directory[i] = Directory[i] + FileString + '.gsc'      #Directory string}
#    print Directory[i]

  for i in range(1,5):
#   Check to see that the same box is listed more than once}
    AllReadySearched = 0
    nstar = 0
    nbox = 0
    nfound = 0
    for ii in range(1,i):
      if Directory[ii] == Directory[i]:
        AllReadySearched = 1 
    if not AllReadySearched:
      #Read fits table
#      print i, Directory[i],
      ft = fits.FITS(Directory[i], 'r', tmode='list')
      #Columns are GSC_ID, RA_DEG, DEC_DEG, POS_ERR, MAG, MAG_ERR, MAG_BAND, CLASS, PLATE_ID, MULTIPLE
      #              0       1        2        3      4      5        6        7        8        9
      #Reading in list mode, not dict mode, as we never look up based on GSC_ID

      da = ft.table.data

      OldRA = 0
      OldDec = 90.0
      OldMag = 0

      for row in da:
        TableName = row[0]
        TableRA = row[1]
        TableDec = row[2]
        TableMag = row[4]
        TableMagErr = row[5]
        TableMagBand = row[6]
        TableClass = row[7]
#        print TableRA, TableDec

        nstar = nstar + 1
        if (TableRA<180) and ZeroHours:
          AddToTable = 360.0
        else:
          AddToTable = 0.0
        if ( (TableRA+AddToTable >= WestSearch) and 
             (TableRA+AddToTable <= EastSearch) and 
             (TableDec >= SouthSearch) and 
             (TableDec <= NorthSearch) ):
          nbox = nbox + 1
#         This star is in the region of interest
#         Is the star position the same as the last entry?
          if (abs(OldRA-TableRA)<0.00027) and (abs(OldDec-TableDec)<0.00027):
            if ((TableMag>OldMag) and (TableMag+TableMagErr<MagLimit)):
              OldMag = TableMag
              if len(Candidates) > 0:
                Candidates[-1].mag = TableMag + TableMagErr
            TableClass = 4
          else:
            OldMag = TableMag
            OldRA = TableRA
            OldDec = TableDec

          if TableClass == 0:
#           check the class of object - is it a star?}
#           check the Magnitude band and convert to a V magnitude}
            if (TableMag+TableMagErr) < MagLimit:
              nfound = nfound +1
              cand = xyglobs.Guidestar()
              cand.name = TableName
              cand.pos.a = TableRA/15.0
              cand.pos.d = TableDec
              cand.epoch = 2000.0
              cand.mag = TableMag + TableMagErr
              Candidates.append(cand)
    else:
#      print i, Directory[i],' skipped, already done.', 
      pass
#    print 'nstar=',nstar,' nbox=',nbox,' nfound=',nfound
  return Candidates
