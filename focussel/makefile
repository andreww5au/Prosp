ORIG  = .			# where the sources lie
DEST  = .			# where to put the executable
CC    = cc 			# the C compiler
COPTS =  -fast         # options for the C compiler
LIBS  =  -lm
STDH  = 

ALL   = focussel.o \


focussel: $(ALL)
	$(CC) -o focussel $(ALL) $(LIBS) $(COPTS)


focussel.o: focussel.c $(STDH)
	$(CC) -c focussel.c

 
