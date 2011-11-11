ORIG  = .			# where the sources lie
DEST  = .			# where to put the executable
CC    = cc 			# the C compiler
COPTS =  -fast         # options for the C compiler
LIBS  =  -lm
STDH  = 

ALL   = focusat.o \


focusat: $(ALL)
	$(CC) -o focusat $(ALL) $(LIBS) $(COPTS)


focusat.o: focusat.c $(STDH)
	$(CC) -c focusat.c

 
