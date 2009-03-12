/*
	PLAT software to control an FLI focuser
	commands:
		home - send the focuser to the home position
		offset - relative offset from the current position
		position - offset from the home position
	Written by:
		Ralph Martin
		April 2005
*/

#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "libfli-mem.h"
#include "libfli-debug.h"
#include "libfli.h"
#include "libfli-filter-focuser.h"


	flidev_t dev[63];  /* FLI handles array */

int main(argc,argv)
	int argc;
	char **argv;
{	int focuserNumber;	
	char focuserCommand[64];
	long numbersteps;
        char **list;
	long error;
	int i,kk,focus;
	long focuserAt;
        char buff[2048];
	size_t len;


	FLISetDebugLevel("localhost", FLIDEBUG_WARN); 

	if (argc<2){
	        printf("	You must enter three parameters: \n");
	        printf("		The number of the focuser - usually 0, \n");
	        printf("		The focuser command (home,offset or position) and \n");
	        printf("		The number of motor steps to move. \n");
	     	return(EXIT_FAILURE);
	} else if (argc == 4) {
		focuserNumber = atoi(argv[1]);
		strcpy(focuserCommand,argv[2]);
		numbersteps = (long) atoi(argv[3]);
        	printf("	focuser number: %i \n", focuserNumber);
        	printf("	focuser command: %s \n",focuserCommand );
        	printf("	number of motor steps to move: %i \n",(int) numbersteps);

	} else {
	        printf("	Too many or too few parameters. \n");
	        printf("	You must enter three parameters: \n");
	        printf("		The number of the focuser - usually 0, \n");
	        printf("		The focuser command (home,offset or position) and \n");
	        printf("		The number of motor steps to move. \n");
	    	return(EXIT_FAILURE);
	}

	if ((error=FLIList(FLIDOMAIN_USB | FLIDEVICE_FOCUSER, &list)))
	{
	  fprintf(stderr,"ErrorFLIList:%s /n",strerror(error));
	  return(EXIT_FAILURE);
	}
	kk=0;
        for (i = 0; list[i] != NULL; i++) {
             int j;
	     kk=kk+1;
             for (j = 0; list[i][j] != '\0'; j++) {
                 if (list[i][j] == ';') {
	            list[i][j] = '\0';  /* replace ; with a null character */
	            break;
                 }
	     }
        }

	if (kk == 0) {
		printf ("	No FLI focus units attached. %i \n",i);
		return(EXIT_FAILURE);
	} else if (focuserNumber >= kk){
		printf ("	The highest FLI focuser number is %i. \n", kk-1);
		return(EXIT_FAILURE);
/*	} else	{
		printf ("	%i FLI focus unit(s) attached. \n", kk); */
	}

/*      for each focuser on the list */
        for (i = 0; list[i] != NULL; i++) {
	   if((error=FLIOpen(&dev[i], list[i], FLIDOMAIN_USB | FLIDEVICE_FOCUSER))) {
	      fprintf(stderr,"ErrorFLIOpen:%s \n",strerror(error));
	      break;
	   }
/*	   if((error=FLIGetModel(dev[i],buff, len ))) { */
	   if((error=FLIGetModel(dev[i],buff, 2048 ))) {
	      fprintf(stderr,"Error FLIGetModel:%s \n",strerror(error));
	      break;
	   }
           printf("	Model: %s \n", buff);
        }
	printf("	Command: %s \n", focuserCommand); 
	if(strcmp(focuserCommand,"home")==0) {
	   if((error=FLIHomeFocuser(dev[focuserNumber]))) {
	      fprintf(stderr,"Error FLIHomeFocuser:%s \n",strerror(error)); 
	   }
	} else if (strcmp(focuserCommand,"offset")==0) {
	   if((error=FLIStepMotor(dev[focuserNumber],numbersteps))) {
	      fprintf(stderr,"Error FLIStepMotor:%s \n",strerror(error)); 
	   }
	} else if(strcmp(focuserCommand,"position")==0) {
	   if((error=FLIGetStepperPosition(dev[focuserNumber],&focuserAt))) {
	      fprintf(stderr,"Error FLIGetStepperPosition:%s \n",strerror(error)); 
	   }
	   focus=(int)focuserAt;
           printf("	focuser position: %i \n", (int)focus);
	   return(focus);
	} else {
           printf("	Unknown focuser command -- %s \n",focuserCommand);
	}

	if((error=FLIFreeList(list))) {
	     fprintf(stderr,"ErrorFLIFreeList:%s \n",strerror(error)); 
	     return(EXIT_FAILURE);
	}
	if((error=FLIClose(dev[focuserNumber]))) {
	     fprintf(stderr,"ErrorFLIClose:%s \n",strerror(error)); 
	     return(EXIT_FAILURE);
	}

	printf("	FLI finished \n"); 

	return(EXIT_SUCCESS);
}

