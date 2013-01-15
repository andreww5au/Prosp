/********************************************************
	Code to analyse a focus image 

	Written by Ralph Martin
	date 04/05/05 - 
	date 15/03/07 -

	The image is passed to this program as an array maximum size of 1024x1024	


*********************************************************/
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <errno.h>
#include <malloc.h>

#define SWAP(a,b) temp=(a);(a)=(b);(b)=temp;


/*
	 Global variables
*/
	 long            ltime;
	 short		 ReadMode; /* readout mode of the camera */
	 short  	 wide=1024,high=1024,binning=1; /* dimensions of chip */
	 long   	 pixelwide,pixelhigh;
	 int    	 CCDImage[1024][1024]; /* Image array */
/*	 float           raw[512][544]; */
	 float           raw[1024][1024];
	 float           SigmaLimit=12.0;
	 float           FWHMLimit;
	 float           Quality;
	 float		 gain=3.7; 
	 float		 rn=4.2;

	 signed int      MoveLog,Tab,LastMiss,Cycle;
/*
	 Function prototypes
*/
	 int     FindStar (float *, float *, float*, signed int,
			       signed int,signed int, signed int, float,
			       float);
	 int     LocateStar (float *, float *,float *, signed int, 
			         signed int,signed int, signed int, 
			         float, float);
	 int 	Centroide  (float *, float *, float *, signed int, signed int, signed int,
			    signed int, float);
	 int     FindCentre (float *, float *,float *,float , 
			         signed int ,signed int , signed int , 
			         signed int ,float );
	 int     FindThreshold (float *, float *, signed int , 
				        signed int , signed int , signed int, 
			         	signed int);
	 int     FindStarInfo (float *, float *,signed int, signed int, 
			           signed int, signed int, float, 
			           float, float, float);
	 int	 avecnt(float *,int *,int *,int *,int *,float,float,float,float);
	 int 	 integrate
			(float *,float *,int *,int *,int *,int *,
				float, float,float, float,float);
	 int     pxfrac(float *,int *,int *,float, float,float *);
	 int 	 bxlimits(int *, int *, int *, int *, float, float, float, float);
	 int 	 starlimits(int *, int *, int *, int *, float, float, float, float);
	 int     ii,jj,jjj,err;
	 int     Dummy=0;

	 int 	 bstat(float *, float *, int , float *, float *);

	 int 	 subray(float *,float *,float *,int,float *, float *, float *);
	 int     lsq(float *,float *,float *, int ,float *,float *,float * ,float *,
                     float *,float *,float *);
 	 int	 averad(float *, float *,float *,int);

	 double  determinant(double ** ,int );
	 float   median(int , int , float *);


int  main(argc,argv)
	 int argc;
	 char *argv[]; 
{
	 struct stardata {
				  float StarX[32];
				  float StarY[32];
				  float SigmaX[32];
				  float SigmaY[32];
				  float StarCnt[32];
				  float StarErr[32];
				 };
	 struct stardata starplus;
	 struct stardata starminus;
	 struct stardata starall;
	 struct stardata starfit;

	 float            pye=3.141592654;
	 float		  a,b,c,num,offset,small,min,max,vertex,sma,xx;
	 float		  averagecount,total,pxlsum,limit;
	 int		  rtn,numstars,flag,numplus,numminus,numall,allat;
	 int		  startAt,endAt,nrows,ncols,stX,enX,stY,enY;
	 int 		  xdiff,smalldiff,stX_fp,enX_fp,stY_fp,enY_fp;
	 int		  stX_bx,enX_bx,stY_bx,enY_bx;
	 char             *aaa;
	 float            Thresh,Sigma,StarSigmaX,StarSigmaY;
	 float            BoxSize,Sky;
	 float		  x,y,countpixel,cnterr;
	 signed int       StartX,StartY,EndX,EndY,nbytes;
	 signed int       BoxStrX,BoxStrY,BoxEndX,BoxEndY; 
	 float            CovXY,Signal2Noise,SignalNoise;
	 float			  motorpos[64],Spread[64],aa,bb,cc,lgcount;
	 float			  scl;
	 FILE			  *fpr,*fpw;
	 char 			  filenme[64];


	 if (argc<2){
	  printf("Command format is- ./focusat /tmp/junk486.raw \n");
	  printf("Results are written to -/tmp/junk486.dat \n");
	  return(EXIT_FAILURE);
	 }
/*	 Estimate the threshold of the image. */
	 StartX = 0;
	 StartY = 0;
	 EndX = 1023;
	 EndY = 1023;

	 strcpy(filenme,argv[1]);
 	 printf("file =  %s \n",filenme);
	 if ((fpr=fopen(filenme,"rb"))==NULL){
 	 	printf("can not open file \n");
	        return(EXIT_FAILURE);
	 } else {
	 	if(fread(raw,(size_t) sizeof(float),(size_t) 1024*1024, fpr)!=1024*1024) {
		    printf("File read error! \n");
	            return(EXIT_FAILURE);
		}
	 }
	 for (jj=0;jj<=EndY;jj+=1) {
	       for (ii=0;ii<=EndX;ii+=1) {
		 if (raw[ii][jj]<= 0.0) raw[ii][jj]=0.0;
/* 	 	 printf("raw =  %f %i %i \n",raw[ii][jj],ii,jj); */
		 CCDImage[ii][jj]=(int)raw[ii][jj];
	       }
	 }
	 rtn  = FindThreshold(&Thresh,&Sigma,250,10,400,220,(signed int) 2);
	 printf("Sky and sigma = %f %f \n", Thresh,Sigma); 
	 Sky = Thresh + 3*Sigma;
/*       Find a star near to x & y inside the region of the image defined by 
	 BoxStr(X,Y)/BoxStr(X/Y) */
/*	 Find a star starting at the top of the image. Pointing errors mean the 
	 star could be any where. */
	 BoxStrX = 512-70;
	 BoxStrY = 512-70;
	 BoxEndX = 512+70;
	 BoxEndY = 512+70;
	 x=512.0;
	 y=512.0;
/*	 offset=26;   fixed offset between the stars */
         rtn = LocateStar(&x,&y,&Signal2Noise,BoxStrX,BoxStrY,BoxEndX,BoxEndY,Thresh,Sigma);
	 printf("Star located at = %f %f \n", x,y); 

	 rtn = FindStarInfo(&StarSigmaX, &StarSigmaY, StartX, StartY,
				EndX, EndY, Thresh, Sigma, x, y);
	 starplus.SigmaX[0] = StarSigmaX;
	 starplus.SigmaY[0] = StarSigmaY;
	 printf("Star located at = %f %f %f %f \n", x,y,StarSigmaX,StarSigmaY); 

	 rtn = starlimits(&BoxStrX, &BoxStrY, &BoxEndX, &BoxEndY, Thresh, Sigma, x, y);
	 printf("Box stX stY enX enY = %i %i %i %i \n", BoxStrX,BoxStrY,BoxEndX,BoxEndY); 
/*       Calculate centre for the area defined by starlimits */
	 limit=(float)((int)(Thresh+6.0*Sigma)); /* set threshold */
	 rtn = Centroide(&x,&y,&CovXY,BoxStrX,BoxStrY,BoxEndX,BoxEndY,limit);
	 starall.StarX[0] = x;
	 starall.StarY[0] = y;

	 printf("Star found at = %f %f \n", x,y); 
	 total=0.0;

/* 	If a pixel is above the threshold include it in the 
	estimate of the brightness */
	for (jj=BoxStrY;jj<=BoxEndY;++jj) {
	    	for (ii=BoxStrX;ii<=BoxEndX;++ii) {
			if (CCDImage[ii][jj] >= limit) {
				total=total+(float)CCDImage[ii][jj];
			}
	   	}
	}
	averagecount=total;
	printf("Star Count = %f \n", averagecount);
	if (total>=lgcount) lgcount=total;
	rtn = integrate(&countpixel,&cnterr,&BoxStrX,&BoxStrY,&BoxEndX,
			&BoxEndY,Thresh, Sigma,x, y,averagecount);
	starall.StarCnt[0]=countpixel; /* radius  */
	starall.StarErr[0]=cnterr;     /* error */
	scl = 1.0;
	aaa=strstr(filenme,".raw");
	strncpy(aaa,".dat",4);
 	printf("results saved in file =  %s \n",filenme); 
	if ((fpw=fopen(filenme,"wb"))==NULL){
 	 	printf("can not open file \n");
	        return(EXIT_FAILURE);
	} else {
		fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
		starall.StarX[0],starall.StarCnt[0],
		starall.StarErr[0],starall.StarY[0]);
		fclose(fpw);
	}
	return(EXIT_SUCCESS);
}
/*******************************************************************
 Determine the threshold level and Sigma of the image
********************************************************************/
int FindThreshold(float *pThresh, float *pSigma, signed int StartX, 
		  signed int StartY,signed int EndX, signed int EndY,signed int Sample)
{
	int   			ii,jj,cc;
	double          Sum,SumSquare,StandardError;
	double          num,hold;

/*      Calculate the average and standard deviation */
	cc=0;
	num = 0.0;
	Sum = 0.0;
	SumSquare=0.0;
	for (jj=StartY;jj<=EndY;++jj) {
		for (ii=StartX;ii<=EndX;++ii) {
			if(CCDImage[ii][jj] >= 0) {
				num=num+1.0;
				Sum=Sum+(double)CCDImage[ii][jj];
				SumSquare = SumSquare+(double)CCDImage[ii][jj]*(double)CCDImage[ii][jj];
			} else {
				cc=cc+1;
			}
		} /* end for */
	} /* end for */
/*	printf ("num= %i %f %f %f \n",cc,num,Sum,SumSquare); */
	hold = (Sum/num)*(Sum/num);
	StandardError = SumSquare/num - hold;
	if (StandardError < 0.0) StandardError = 0.0;
	StandardError = sqrt(StandardError);
       *pThresh = (float)(Sum/num);
	cc=0;
	num = 0.0;
	Sum = 0.0;
	SumSquare=0.0;
/*	for (jj=StartY;jj<=EndY;jj+=Sample) {
		for (ii=StartX;ii<=EndX;ii+=Sample) { */
	for (jj=StartY;jj<=EndY;++jj) {
		for (ii=StartX;ii<=EndX;++ii) {
			if(CCDImage[ii][jj] >= *pThresh-4.0*StandardError && 
			   CCDImage[ii][jj] <= *pThresh+4.0*StandardError) {
				num=num+1.0;
				Sum=Sum+(double)CCDImage[ii][jj];
				SumSquare = SumSquare+(double)CCDImage[ii][jj]*(double)CCDImage[ii][jj];
			} else {
				cc=cc+1;
			}
		} /* end for */
	} /* end for */
	hold = (Sum/num)*(Sum/num);
	StandardError = SumSquare/num - hold;
	if (StandardError < 0.0) StandardError = 0.0;
	StandardError = sqrt(StandardError);

       *pThresh = (float)(Sum/num);
       *pSigma = (float) StandardError;
/*	printf("mean sigma = %f %f \n", *pThresh,StandardError); */

	return  (0);
}



/*********************************************
 Calculate a centroide from a region in x & y
**********************************************/
int Centroide(float *px, float *py, float *CovXY,
		signed int StartX,signed int StartY,signed int EndX,
		signed int EndY,float Sky)
{
	signed int      Imin,Jmin,Imax,Jmax; /* centroide box limits */
	double          XPos,YPos;
	int             ii,jj,interation;
	double          Sum,SumX,SumY,Cnt,ExpXY;      /* centre of mass sums */ 
	double          XNew,YNew,XOld,YOld,DeltaX,DeltaY;
	float           T,U,P1,P2,P3,P4,C1,C2,C3,C4;


	Imin = StartX;
	Jmin = StartY;
	Imax = EndX;
	Jmax = EndY;

	XOld = *px;
	YOld = *py;
	interation = 1;
/*      Find Centroide */
	Sum  = 0.0;
	SumX = 0.0;
	SumY = 0.0;
	for (jj=Jmin;jj<=Jmax;++jj) {
		YPos = (double)jj;
		for (ii=Imin;ii<=Imax;++ii) {
				XPos  = (double)ii;
				Cnt   = (double)CCDImage[ii][jj] - (double)Sky;
				if (Cnt >= 0.0) {
				    Sum   = Sum  + Cnt;
				    SumY  = SumY + Cnt*YPos;
				    SumX  = SumX + Cnt*XPos;
				}
		}
	}
	XNew   = (SumX/Sum);
	YNew   = (SumY/Sum);
	*px = (float)XNew;
	*py = (float)YNew;
	*CovXY = 0.0;

/*      Estimate the covariance */
	for (jj=Jmin;jj<=Jmax;++jj) {
		YPos = (double)jj-YNew;
		for (ii=Imin;ii<=Imax;++ii) {
				XPos = (double)ii-XNew;
				Cnt  = ((double)CCDImage[ii][jj]-(double)Sky);
				 if (Cnt >= 0.0) {
					  Cnt   = Cnt/Sum;
					 *CovXY = *CovXY+(Cnt*XPos*YPos);
				 }
		}
	}
	return (0);
}


/****************************************************************
 Calculate a centroide from an estimated x & y
*****************************************************************/
int FindCentre(float *px, float *py, float *CovXY, float BoxSize,
		signed int StartX,signed int StartY,signed int EndX,
		signed int EndY,float Sky)
{
	signed int      Imin,Jmin,Imax,Jmax; /* centroide box limits */
	double          XPos,YPos;
	int             ii,jj,interation;
	double          Sum,SumX,SumY,Cnt,ExpXY;      /* centre of mass sums */ 
	double          XNew,YNew,XOld,YOld,DeltaX,DeltaY;
	float           T,U,P1,P2,P3,P4,C1,C2,C3,C4;


	Imin = *px - BoxSize;
	Jmin = *py - BoxSize;
	Imax = *px + BoxSize;
	Jmax = *py + BoxSize;
	if( Imin<=StartX || Jmin<=StartY || Imax>=EndX || Jmax>=EndY ) {
	     /* Box is outside of the Image - forget it. */
		return -1;
	}
	XOld = *px;
	YOld = *py;
	interation = 1;
/*      Find Centroide */
	do {
		Sum  = 0.0;
		SumX = 0.0;
		SumY = 0.0;
		for (jj=Jmin;jj<=Jmax;++jj) {
			YPos = (double)jj;
			for (ii=Imin;ii<=Imax;++ii) {
				XPos  = (double)ii;
				Cnt   = (double)CCDImage[ii][jj] - (double)Sky;
				if (Cnt >= 0.0) {
				    Sum   = Sum  + Cnt;
				    SumY  = SumY + Cnt*YPos;
				    SumX  = SumX + Cnt*XPos;
				}
			}
		}
		XNew   = (SumX/Sum);
		YNew   = (SumY/Sum);
		DeltaX = (double)(fabs((float)XNew - (float)XOld));
		DeltaY = (double)(fabs((float)YNew - (float)YOld));
		if(DeltaX <= 0.01 && DeltaY <= 0.01) {
		     /* found centre */
		       *px = (float)XNew;
		       *py = (float)YNew;
		       *CovXY = 0.0;
/*                      Estimate the covariance */
			for (jj=Jmin;jj<=Jmax;++jj) {
				YPos = (double)jj-YNew;
				for (ii=Imin;ii<=Imax;++ii) {
				    XPos = (double)ii-XNew;
				    Cnt  = ((double)CCDImage[ii][jj]-(double)Sky);
				    if (Cnt >= 0.0) {
					  Cnt   = Cnt/Sum;
					 *CovXY = *CovXY+(Cnt*XPos*YPos);
				    }
				}
			}
			return 0;
		}
		else {
			XOld=XNew;
			YOld=YNew;
			interation=interation+1;
			Imin = (signed int)((float)XNew - BoxSize);
			Jmin = (signed int)((float)YNew - BoxSize);
			Imax = (signed int)((float)XNew + BoxSize);
			Jmax = (signed int)((float)YNew + BoxSize);
			if( Imin<=StartX || Jmin<=StartY || Imax>=EndX || Jmax>=EndY ) {
		     /* Box is outside of the Image - forget it. */
			    return -1;
			}
		
		}
	} while (interation <= 7);
/*      centroide calculation did not converge */
	return (-2);
} 

/****************************************************************
 Calculate the average covarence value.
 Use the average coverience to measure the quality of this image
*****************************************************************/
int CheckOut( float CovXY )
{

	
	if ( CovXY >= Quality || CovXY <= -1.0*Quality) {
	       return -1;     /* not a very good image - don't use it */
	}
	return 0;
} 


/**********************************************************************
 Go through part or all of an image and find star nearest to the point
 x an y.
 **********************************************************************/

int LocateStar(float *px, float *py, float *SN,signed int StrX, signed int StrY,
		signed int EnX, signed int EnY, float Thresh, float Sigma)

{
static  int 		    MaxHeadRoom;
static  int   		    ii,jj;
static  int		    i,j;
static  int   		    Limit,Pixel;
static  int      	    StartX,StartY,EndX,EndY,offst,x,y;
static  float               Signal,Noise,S2N;


	x = (signed int)*px;
	y = (signed int)*py;
	MaxHeadRoom = (int)(Thresh+SigmaLimit*Sigma);
	Limit  = (int)(Thresh+SigmaLimit*Sigma/3.0);
	offst = 0;
	StartX = x;
	StartY = y;
	EndX   = x;
	EndY   = y;

/*      Check that the event has extent */
	*SN = 0.0;
	do {
	    for (ii=StartX;ii<=EndX;++ii) {
		jj=StartY;
		Pixel = (int)CCDImage[ii][jj];
		if (Pixel                >= MaxHeadRoom &&
		    CCDImage[ii+1][jj]   >= Limit &&
		    CCDImage[ii-1][jj]   >= Limit &&
		    CCDImage[ii+1][jj+1] >= Limit &&
		    CCDImage[ii-1][jj-1] >= Limit &&
		    CCDImage[ii+1][jj-1] >= Limit &&
		    CCDImage[ii-1][jj+1] >= Limit &&
		    CCDImage[ii][jj-1]   >= Limit &&
		    CCDImage[ii][jj+1]   >= Limit &&
		    CCDImage[ii+1][jj]   <= Pixel &&
		    CCDImage[ii-1][jj]   <= Pixel &&
		    CCDImage[ii+1][jj+1] <= Pixel &&
		    CCDImage[ii-1][jj-1] <= Pixel &&
		    CCDImage[ii+1][jj-1] <= Pixel &&
		    CCDImage[ii-1][jj+1] <= Pixel &&
		    CCDImage[ii][jj-1]   <= Pixel &&
		    CCDImage[ii][jj+1]   <= Pixel ) {
/*                     Use a 3x3 box to extimate the Signal/Noise ratio. */
			   Signal =  (float)(CCDImage[ii][jj]+CCDImage[ii+1][jj]+
				     CCDImage[ii-1][jj]+CCDImage[ii+1][jj+1]+
				     CCDImage[ii-1][jj-1]+CCDImage[ii+1][jj-1]+
				     CCDImage[ii-1][jj+1]+CCDImage[ii][jj-1]+
				     CCDImage[ii][jj+1]);
			   Signal = Signal - 9.0*Thresh;   /* Subract of the sky */
/*                         Image has been bias subtracted add a constant to approximate the bias level */
			   Noise =  (9*rn*rn+(float)(1300+CCDImage[ii][jj])/gain+
						(float)(1300+CCDImage[ii+1][jj])/gain+
				        (float)(1300+CCDImage[ii-1][jj])/gain+
					    (float)(1300+CCDImage[ii+1][jj+1])/gain+
				        (float)(1300+CCDImage[ii-1][jj-1])/gain+
                                (float)(1300+CCDImage[ii+1][jj-1])/gain+
				        (float)(1300+CCDImage[ii-1][jj+1])/gain+
                                (float)(1300+CCDImage[ii][jj-1])/gain+
				        (float)(1300+CCDImage[ii][jj+1])/gain);
			   Noise  = (float)sqrt((double)(Noise));
/*			   printf(" Noise= %f ",Noise); */
			   S2N = Signal/(Noise);
			   if (S2N >= *SN) {
			     *SN = S2N;
			     *px = (float)ii;
			     *py = (float)jj;
			   }
  
		} /* end if */
		jj=EndY;
		Pixel = CCDImage[ii][jj];
		if (Pixel                >= MaxHeadRoom &&
		    CCDImage[ii+1][jj]   >= Limit && 
		    CCDImage[ii-1][jj]   >= Limit &&
		    CCDImage[ii+1][jj+1] >= Limit &&
		    CCDImage[ii-1][jj-1] >= Limit &&
		    CCDImage[ii+1][jj-1] >= Limit && 
		    CCDImage[ii-1][jj+1] >= Limit &&
		    CCDImage[ii][jj-1]   >= Limit &&
		    CCDImage[ii][jj+1]   >= Limit &&
		    CCDImage[ii+1][jj]   <= Pixel && 
		    CCDImage[ii-1][jj]   <= Pixel &&
		    CCDImage[ii+1][jj+1] <= Pixel &&
		    CCDImage[ii-1][jj-1] <= Pixel &&
		    CCDImage[ii+1][jj-1] <= Pixel && 
		    CCDImage[ii-1][jj+1] <= Pixel &&
		    CCDImage[ii][jj-1]   <= Pixel &&
		    CCDImage[ii][jj+1]   <= Pixel ) {
/*                         Use a 3x3 box to extimate the Signal/Noise ratio. */
			   Signal =  (float)(CCDImage[ii][jj]+CCDImage[ii+1][jj]+
				     CCDImage[ii-1][jj]+CCDImage[ii+1][jj+1]+
				     CCDImage[ii-1][jj-1]+CCDImage[ii+1][jj-1]+
				     CCDImage[ii-1][jj+1]+CCDImage[ii][jj-1]+
				     CCDImage[ii][jj+1]);
			   Signal = Signal - 9.0*Thresh;   /* Subract of the sky */
/*                         Image has been bias subtracted add a constant to approximate the bias level */
			   Noise =  (9*rn*rn+(float)(1300+CCDImage[ii][jj])/gain+
						(float)(1300+CCDImage[ii+1][jj])/gain+
				        (float)(1300+CCDImage[ii-1][jj])/gain+
					    (float)(1300+CCDImage[ii+1][jj+1])/gain+
				        (float)(1300+CCDImage[ii-1][jj-1])/gain+
                                (float)(1300+CCDImage[ii+1][jj-1])/gain+
				        (float)(1300+CCDImage[ii-1][jj+1])/gain+
                                (float)(1300+CCDImage[ii][jj-1])/gain+
				        (float)(1300+CCDImage[ii][jj+1])/gain);
			   Noise  = (float)sqrt((double)(Noise));
			   S2N = Signal/(Noise);
			   if (S2N >= *SN) {
				*SN = S2N;
			        *px = (float)ii;
			        *py = (float)jj;
			   }
		} /* end if */

	    } /* end for */
	    for (jj=StartY;jj<=EndY;++jj) { 
		ii=StartX;
		Pixel = CCDImage[ii][jj];
		if (Pixel                >= MaxHeadRoom &&
		    CCDImage[ii+1][jj]   >= Limit && 
		    CCDImage[ii-1][jj]   >= Limit &&
		    CCDImage[ii+1][jj+1] >= Limit &&
		    CCDImage[ii-1][jj-1] >= Limit &&
		    CCDImage[ii+1][jj-1] >= Limit && 
		    CCDImage[ii-1][jj+1] >= Limit &&
		    CCDImage[ii][jj-1]   >= Limit &&
		    CCDImage[ii][jj+1]   >= Limit &&
		    CCDImage[ii+1][jj]   <= Pixel && 
		    CCDImage[ii-1][jj]   <= Pixel &&
		    CCDImage[ii+1][jj+1] <= Pixel &&
		    CCDImage[ii-1][jj-1] <= Pixel &&
		    CCDImage[ii+1][jj-1] <= Pixel && 
		    CCDImage[ii-1][jj+1] <= Pixel &&
		    CCDImage[ii][jj-1]   <= Pixel &&
		    CCDImage[ii][jj+1]   <= Pixel ) {
/*                         Use a 3x3 box to extimate the Signal/Noise ratio. */
			   Signal =  (float)(CCDImage[ii][jj]+CCDImage[ii+1][jj]+
				     CCDImage[ii-1][jj]+CCDImage[ii+1][jj+1]+
				     CCDImage[ii-1][jj-1]+CCDImage[ii+1][jj-1]+
				     CCDImage[ii-1][jj+1]+CCDImage[ii][jj-1]+
				     CCDImage[ii][jj+1]);
			   Signal = Signal - 9.0*Thresh;   /* Subract of the sky */
/*                         Image has been bias subtracted add a constant to approximate the bias level */
			   Noise =  (9*rn*rn+(float)(1300+CCDImage[ii][jj])/gain+
						(float)(1300+CCDImage[ii+1][jj])/gain+
				        (float)(1300+CCDImage[ii-1][jj])/gain+
					    (float)(1300+CCDImage[ii+1][jj+1])/gain+
				        (float)(1300+CCDImage[ii-1][jj-1])/gain+
                                (float)(1300+CCDImage[ii+1][jj-1])/gain+
				        (float)(1300+CCDImage[ii-1][jj+1])/gain+
                                (float)(1300+CCDImage[ii][jj-1])/gain+
				        (float)(1300+CCDImage[ii][jj+1])/gain);
			   Noise  = (float)sqrt((double)(Noise));
			   S2N = Signal/(Noise);
			   if (S2N >= *SN) {
			      *SN = S2N;
			      *px = (float)ii;
			      *py = (float)jj;
			   }
		} /* end if */
		ii=EndX;
		Pixel = CCDImage[ii][jj];
		if (Pixel                >= MaxHeadRoom &&
		    CCDImage[ii+1][jj]   >= Limit && 
		    CCDImage[ii-1][jj]   >= Limit &&
		    CCDImage[ii+1][jj+1] >= Limit &&
		    CCDImage[ii-1][jj-1] >= Limit &&
		    CCDImage[ii+1][jj-1] >= Limit && 
		    CCDImage[ii-1][jj+1] >= Limit &&
		    CCDImage[ii][jj-1]   >= Limit &&
		    CCDImage[ii][jj+1]   >= Limit &&
		    CCDImage[ii+1][jj]   <= Pixel && 
		    CCDImage[ii-1][jj]   <= Pixel &&
		    CCDImage[ii+1][jj+1] <= Pixel &&
		    CCDImage[ii-1][jj-1] <= Pixel &&
		    CCDImage[ii+1][jj-1] <= Pixel && 
		    CCDImage[ii-1][jj+1] <= Pixel &&
		    CCDImage[ii][jj-1]   <= Pixel &&
		    CCDImage[ii][jj+1]   <= Pixel ) {
/*                        Use a 3x3 box to estimate the Signal/Noise ratio. */
			  Signal =  (float)(CCDImage[ii][jj]+CCDImage[ii+1][jj]+
				     CCDImage[ii-1][jj]+CCDImage[ii+1][jj+1]+
				     CCDImage[ii-1][jj-1]+CCDImage[ii+1][jj-1]+
				     CCDImage[ii-1][jj+1]+CCDImage[ii][jj-1]+
				     CCDImage[ii][jj+1]);
			   Signal = Signal - 9.0*Thresh;   /* Subract of the sky */
/*                         Image has been bias subtracted add a constant to approximate the bias level */
			   Noise =  (9*rn*rn+(float)(1300+CCDImage[ii][jj])/gain+
						(float)(1300+CCDImage[ii+1][jj])/gain+
				        (float)(1300+CCDImage[ii-1][jj])/gain+
					    (float)(1300+CCDImage[ii+1][jj+1])/gain+
				        (float)(1300+CCDImage[ii-1][jj-1])/gain+
                                (float)(1300+CCDImage[ii+1][jj-1])/gain+
				        (float)(1300+CCDImage[ii-1][jj+1])/gain+
                                (float)(1300+CCDImage[ii][jj-1])/gain+
				        (float)(1300+CCDImage[ii][jj+1])/gain);
			   Noise  = (float)sqrt((double)(Noise));
			   S2N = Signal/(Noise);
			   if (S2N >= *SN) {
			      *SN = S2N;
			      *px = (float)ii;
			      *py = (float)jj;
			   }
		} /* end if */
	    } /* end for */

	    offst = offst+1;
	    StartX = x-offst;
	    StartY = y-offst;
	    EndX   = x+offst;
	    EndY   = y+offst;
	} while (StartX >= StrX || StartY >= StrY || 
		 EndX   <= EnX  || EndY   <= EnY);

/*      Largest *SN abd its position */
	if (*SN == 0.0){
            return -1;
	} else {
            return 0;
        }

} /* end of function */



/****************************************************************
 Go through part or all of an image and find the brightest star
 Assumes threshold and sigma already calculated.
******************************************************************/
int FindStar(float *px, float *py, float *ExpTime , signed int StartX, 
	     signed int StartY, signed int EndX, signed int EndY, 
	     float Thresh, float Sigma)

{
	int             MaxHeadRoom;
	int             ii,jj,i,j;
	int             Limit;
	static  int     flag;
	float           Signal,Noise,SN,SNpixel;


	MaxHeadRoom = (int)(Thresh+SigmaLimit*Sigma/3.0);
	Limit = (int)(Thresh+SigmaLimit*Sigma/3.0);
	flag = -1;
/*      Tests require that the search area be trimed by 1 */
	for (jj=StartY+1;jj<=EndY-1;++jj) {
		for (ii=StartX+1;ii<=EndX-1;++ii) {
/*                      Check that the event has extent    */
			if (CCDImage[ii][jj] >  MaxHeadRoom &&
			    CCDImage[ii+1][jj] >= Limit && 
			    CCDImage[ii-1][jj] >= Limit &&
			    CCDImage[ii+1][jj+1] >= Limit &&
			    CCDImage[ii-1][jj-1] >= Limit &&
			    CCDImage[ii+1][jj-1] >= Limit && 
			    CCDImage[ii-1][jj+1] >= Limit &&
			    CCDImage[ii][jj-1] >= Limit &&
			    CCDImage[ii][jj+1] >= Limit ) {
/*                          This is an event that is bright and not 
			    restrict to a single pixel. */
			    MaxHeadRoom = CCDImage[ii][jj];
			    Signal =  (float)(CCDImage[ii][jj]+
					      CCDImage[ii+1][jj]+
					      CCDImage[ii-1][jj]+
					      CCDImage[ii+1][jj+1]+
					      CCDImage[ii-1][jj-1]+
					      CCDImage[ii+1][jj-1]+
					      CCDImage[ii-1][jj+1]+
					      CCDImage[ii][jj-1]+
					      CCDImage[ii][jj+1]);
			    Signal = Signal - 9.0*Thresh;
/*                         Image has been bias subtracted add a constant to approximate the bias level */
			    Noise =  (9*rn*rn+(float)(1300+CCDImage[ii][jj])/gain+
						(float)(1300+CCDImage[ii+1][jj])/gain+
				        (float)(1300+CCDImage[ii-1][jj])/gain+
					    (float)(1300+CCDImage[ii+1][jj+1])/gain+
				        (float)(1300+CCDImage[ii-1][jj-1])/gain+
                                (float)(1300+CCDImage[ii+1][jj-1])/gain+
				        (float)(1300+CCDImage[ii-1][jj+1])/gain+
                                (float)(1300+CCDImage[ii][jj-1])/gain+
				        (float)(1300+CCDImage[ii][jj+1])/gain);
			   Noise  = (float)sqrt((double)(Noise));
			   SN = Signal/(Noise);

			   *px = (float)ii;
			   *py = (float)jj;
			    flag = 0;
			} /* end if */
		}
	}
	if (flag != 0) {
		return -1; /* no stars */
	}
/*      Check the signal strength. */
	SNpixel = SN;       /* Average ratio per pixel. */
/*      If the SN is to low or to high change exposure time */
	if (SNpixel <= SigmaLimit  || SNpixel >= 2.0*SigmaLimit) {
/*               Change the exposure time. */
		*ExpTime = (SigmaLimit*(*ExpTime))/(SNpixel);
	};
	return 0; /* found something */
} /* end of function */


/*************************************************************************
  The stars seeing (FWHM in pixels) 
**************************************************************************/

int FindStarInfo(float  *pStarSigmaX, float *pStarSigmaY,signed int StartX, 
	     signed int StartY, signed int EndX, signed int EndY, 
	     float Thresh, float Sigma, float x, float y)
{        
	int             ii,jj,interation;
	int    RC[4],MidBrightness,TestBrightness;
	int    CentreX,CentreY;
	float           pye=3.141592654;
	float           countpixel;


/*      Make a rough estimate of sigma X and sigma Y */
	CentreX = (signed int)(floor((double) x));
	CentreY = (signed int)(floor((double) y));
	MidBrightness = CCDImage[CentreX][CentreY] - (int)Thresh;
	ii = 0;
	do {
		ii=ii+1;
		if (CentreX+ii >=wide){
			ii=wide-CentreX;
			break;
		}
		TestBrightness = CCDImage[CentreX+ii][CentreY] - (int)Thresh;
	} while(MidBrightness-TestBrightness <= MidBrightness/2 && ii<=15);
	RC[0] = ii;
	ii = 0;
	do {
		ii=ii-1;
		if (CentreX+ii <=0){
			ii=-CentreX;
			break;
		}
		TestBrightness = CCDImage[CentreX+ii][CentreY] - (int)Thresh;
	} while(MidBrightness-TestBrightness <= MidBrightness/2 && ii<=-15);
	RC[1] = (ii);
	*pStarSigmaX = (float)(RC[0]-RC[1]+1);
	jj=0;
	do {
		jj=jj+1;
		if (CentreY+jj >=high){
			jj=high-CentreY;
			break;
		}
		TestBrightness = CCDImage[CentreX][CentreY+jj] - (int)Thresh;
	} while(MidBrightness-TestBrightness <= MidBrightness/2 && jj<=15);
	RC[2] = (jj);
	jj=0;
	do {
		jj=jj-1;
		if (CentreY+jj <=0){
			jj=-CentreY;
			break;
		}
		TestBrightness = CCDImage[CentreX][CentreY+jj] - (int)Thresh;
	} while(MidBrightness-TestBrightness <= MidBrightness/2 && jj<=15);
	RC[3] = (jj);
       *pStarSigmaY = (float)(RC[2]-RC[3]+1);
	return(0);	
 
 }


/*************************************************************************
  box limits

**************************************************************************/
int starlimits(int  *stX, int *stY, int *enX, int *enY, float Thresh, 
	       float Sigma, float x, float y)

{
	int             ii,jj,off,limit;
	int		offx1,offy1,offx2,offy2;
	int		StartX,StartY,EndX,EndY;
	int  		tstlimit,jjlimit,iilimit;
	float           total,pxlsum,sn,sg,MI,RD;
	float			sig,sigtotal,sd;


/*      Start at each edge of the box and move in until limit is reached. */
/*      Threshold limit is threshold plus sigma   */
	limit=(int)(Thresh+8.0*Sigma);
	tstlimit =0;

/*      Calculate a box size for the star   */

	ii=(int)x;
        jjlimit=(int)y;
	for (jj= (int)y;jj<=jjlimit;--jj) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii][jj-1] <= limit && 
			CCDImage[ii][jj-2] <= limit) {
				offy1=jj+1;
				break;
		}
	}
	*stY=(int)offy1;

	jjlimit = (int)y;
	for (jj= (int)y; jj>=jjlimit;++jj) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii][jj+1] <= limit && 
			CCDImage[ii][jj+2] <= limit) {
				offy2=jj-1;
				break;
		}
	}
	*enY=(int)offy2;

	jj=(int)y;
        iilimit = (int)x;
	for (ii = (int)x; ii<=iilimit;--ii) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii-1][jj] <= limit && 
			CCDImage[ii-2][jj] <= limit) {
				offx1=ii+1;
				break;
		}
	}
	*stX=(int)offx1;

	iilimit = (int)x;
	for (ii= (int)x;ii>=iilimit;++ii) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii+1][jj] <= limit && 
			CCDImage[ii+2][jj] <= limit) {
				offx2=ii-1;
				break;
		}
	}
	*enX=(int)offx2;

	if (*stX >= *enX) *stX=*enX-3;
	if (*stY >= *enY) *stY=*enY-3;
	if (*enX <= *stX) *enX=*stX+3;
	if (*enY <= *stY) *enY=*stY+3;

	return(0);
/*		printf("CCDImage = %i %i %i \n",jj,ii,CCDImage[ii][jj] ); */
/*	printf("offy1, offy2 = %i %i \n",offy1,offy2); */
/*	printf("offx2 = %i \n",offx2); */
/*	printf("offx2 = %i \n",offx2); */
/*	printf("stX enX stY, enY = %i %i %i %i \n",*stX, *enX, *stY, *enY); */
/*			    printf("offy2 = %i \n",offy2 );  */
/*			    printf("offy1 = %i \n",offy1 );   */

/*	printf("limit,x,y = %i %f %f \n",limit,x,y );  */
}




/*************************************************************************
  box limits
**************************************************************************/
int bxlimits(int  *stX, int *stY, int *enX, int *enY, float Thresh, 
		float Sigma, float x, float y)
{
	int             ii,jj,off;
	int			offx1,offy1,offx2,offy2;
	int			StartX,StartY,EndX,EndY;
	int  		    limit,tstlimit;
	float           total,pxlsum,sn,sg,MI,RD;
	float			sig,sigtotal,sd;

/*      Threshold limit is threshold plus sigma   */
	limit=(int)(Thresh+20.0*Sigma);
	tstlimit =0;

/*      Calculate a box size for the star   */
	StartY = (int)(y);
	if (y -(float)StartY >= 0.5) StartY=StartY+1;
	ii=(int)x;
	for (jj= StartY;jj<=510;++jj) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii+1][jj] <= limit && 
			CCDImage[ii-1][jj] <= limit) {
				offy1=jj;
				break;
		}
	}
	for (jj= StartY;jj>=1;--jj) {
		if (CCDImage[ii][jj] <= limit && 
			CCDImage[ii+1][jj] <= limit && 
			CCDImage[ii-1][jj] <= limit) {
				offy2=jj;
				break;
		}
	}
	offx2=(offy1-offy2)/2;
	if (offx2 >= 12) offx2=24-offx2;
	*stY=(int)y-offy2;
	*stX=offx2;  /* use a fixed size in x direction */
	*enY=offy1-(int)y;
	*enX=offx2;
	return(0);
/*		printf("CCDImage = %i %i %i \n",jj,ii,CCDImage[ii][jj] ); */
/*	printf("offy1, offy2 = %i %i \n",offy1,offy2); */
/*	printf("offx2 = %i \n",offx2); */
/*	printf("offx2 = %i \n",offx2); */
/*	printf("stX enX stY, enY = %i %i %i %i \n",*stX, *enX, *stY, *enY); */
/*			    printf("offy2 = %i \n",offy2 );  */
/*			    printf("offy1 = %i \n",offy1 );   */
/*	printf("limit,x,y = %i %f %f \n",limit,x,y );  */
}
/*************************************************************************
  Integrate star counts
**************************************************************************/
int integrate(float *radius,float *rderr, int *StartX,int *StartY,int *EndX,int *EndY,
	      float Thresh, float Sigma, float x, float y, float average)
{
	int             ii,jj,kk,StX,StY,EnX,EnY,interation,stoploop,rtn,stp;
	int   			limit;
	float           total,pxlsum,sn,sg,snr,mx_snr,mx2,mx3,tstrd,step;
	float			sig,sigtotal,sigrd,halfsum,rds,bxtl,area;
	float			residual,loop,halftotal,frac,diffsum,lasthalfsum,subpxl;
	float			aveint,annulus,radiuserr,snrprt,sgpxl,sigrdsum,tlterror;
	float           errorhalftotal,errorhalfsum,errorrd;

/*      set high threshold because of star overlap */
	limit=(int)(Thresh+6.0*Sigma);
	total=0.0;
	pxlsum=0.0;
	sigtotal=0.0;
	sn=0.0;
	sg=0.0;
	mx_snr=0;

/*      If a pixel is above the threshold include it in the estimate of the brightness */
	for (jj=*StartY;jj<=*EndY;++jj) {
	    for (ii=*StartX;ii<=*EndX;++ii) {
		if (CCDImage[ii][jj] >= limit) {
			sg=(float)CCDImage[ii][jj];
			total=total+sg;
/*                      statitical error in the count */
			sig=rn*rn+((float)CCDImage[ii][jj])/gain;
		        sigtotal=sigtotal+(float)sqrt((double)sig);
/*			printf("ii,jj = %i %i %i \n",ii,jj,CCDImage[ii][jj] ); */
/*			printf("noise,signal,snr = %f %f %f \n",sig,sg,mx3); */
			pxlsum=pxlsum+1.0;
		}
	   }
	}
/*	Calculate the radius of half intensity */
	stoploop=0;
	StX=(int)x-1; /* start at the centroide and work out */
	StY=(int)y-1;
	EnX=(int)x+1;
	EnY=(int)y+1;
	interation=1+(*EndY-*StartY)/2;
/*	printf("Interations = %i %i %i  \n",interation,*EndY, *StartY); */

	interation=12;
	loop=1.0;
/*	halftotal=average*0.683; */
	halftotal=total*0.683; 
	errorhalftotal=(average-sigtotal)*0.683;
	halfsum=0.0;
	tstrd=0.0;
	step=0.001;
	stp=(int)((1.0/step)-1);
        errorrd=100.0;


/*	intergrate unit sized radii until the halftotal is exceded    */
	do{
/*	    Increasing radius(rds) size by "step" */
	    for (kk=1;kk<=stp;++kk){  /* calculate radius increases of  "step"   */
	     tstrd=tstrd+step;
	     lasthalfsum=halfsum;
	     halfsum=0.0;
	     errorhalfsum=0.0;
	     sigrd=0.0;
	     sigrdsum=0.0;
	     snrprt=0.0;
	     for (ii=StX;ii<=EnX;++ii) {
	        for (jj=StY;jj<=EnY;++jj) {
/*    			  Calculate the radius from the star's centroide to the pixel's centroide (ii,jj)   */
			  rds=((float)ii-x)*((float)ii-x)+
				  ((float)jj-y)*((float)jj-y);
			  rds=(float)sqrt((double)rds);
/*                        Pixel spacial limits are ii+-0.5 by jj+-0.5 spacial units   */
			  if (rds <= tstrd){ /* add part or all of the pixel's count   */
			    if ((tstrd-rds)<= 0.49) { /* add a fraction of the pixel's count */
				  rtn=pxfrac(&tstrd,&ii,&jj,x,y,&frac);
				  sgpxl=frac*(float)CCDImage[ii][jj];
			    } else { /* add all of the pixel's count */
				  sgpxl=(float)CCDImage[ii][jj];
			    }
		        halfsum=halfsum+sgpxl;
			    sigrd=rn*rn+sgpxl/gain;
			    snrprt=snrprt+(float)sqrt((double)sigrd);
			  } else if ((rds-tstrd)<=0.49) { /* add a fraction of the count   */
				rtn=pxfrac(&tstrd,&ii,&jj,x,y,&frac);
				sgpxl=frac*(float)CCDImage[ii][jj];
		        halfsum=halfsum+sgpxl;
			    sigrd=rn*rn+sgpxl/gain;
			    snrprt=snrprt+(float)sqrt((double)sigrd);
			  } /* otherwise ignore the pixel */
			  errorhalfsum=halfsum+snrprt;
			  if (errorhalfsum>=errorhalftotal){
				if(tstrd<=errorrd) {
					errorrd=tstrd;
				}
			  }
		      if (halfsum >= halftotal) {
		        residual=halftotal-lasthalfsum;
				annulus= 3.141593*((tstrd*tstrd)-(tstrd-step)*(tstrd-step));
			    aveint = (halfsum-lasthalfsum);
				tstrd=tstrd+step*(residual/aveint);
/*	printf("annulus aveint residual = %f %f %f \n",annulus,aveint,residual);  */
/*	  	        finished -- stop looping  */
				stoploop=1;
				break;
		      }
		   } /*ii*/
		   if(stoploop == 1) break;
	        } /*jj*/
		if(stoploop == 1) break;
	    } /*kk*/
	    if(stoploop == 1) break;
/*	    Half sum for this test radius was less that the halftotal   */
	    loop=loop+1;
	    StX= StX-1;
	    if (StX <= *StartX) StX=*StartX;
	    StY= StY-1;
	    if (StY <= *StartY) StY=*StartY;
	    EnX= EnX+1;
	    if (EnX >= *EndX) EnX=*EndX;
	    EnY= EnY+1;
	    if (EnY >= *EndY) EnY=*EndY;
 	} while (loop <= interation);
	tstrd=tstrd-step;
	errorrd=errorrd-step;
	sigrdsum=snrprt;
	tlterror=(float)sqrt((double)(sigrdsum*sigrdsum+sigtotal*sigtotal));
	tlterror=sigrdsum+sigtotal;
	radiuserr = step*(tlterror)/aveint;
	radiuserr = tstrd-errorrd;
/* printf("tstrd,errorrd,errorhalftotal = %f %f %f \n",tstrd,errorrd,errorhalftotal); */
/*	printf("err total error sigrd residual = %f %f %f\n",sigtotal,sigrdsum,aveint); 
	printf("radius counts = %f %f %f \n",halftotal,lasthalfsum,residual);  */
/*	printf("radius = %5.1f %5.1f %f %5.2f +/- %5.4f \n",x,y,total,tstrd,radiuserr); */
	*radius=tstrd;
	*rderr=radiuserr;
	return(0);
}

/*************************************************************************
  Pixel fraction
**************************************************************************/
int	pxfrac(float *tstrd,int *ii,int *jj,float x, float y,float *pfrac)
{
	int    numx,numy,numint;
	double			sd;
	float           lwX,lwY,hiX,hiY,trd,clrd,clx,cly,trx,try,tryX,tryY;
	float			crdX[3],crdY[3],y1,y2,x1,x2,hx,hy,tstX,tstY;
/*	printf("tstrd = %f %i %i %f %f \n", *tstrd,*ii,*jj,x,y); */

	lwX=(float)*ii-0.5;
	hiX=(float)*ii+0.5;
	lwY=(float)*jj-0.5;
	hiY=(float)*jj+0.5;
	crdX[0] =crdX[1] =crdX[2] =crdX[3] = 0.0;
	crdY[0] =crdY[1] =crdY[2] =crdY[3] = 0.0;
/*	printf("box = %f %f %f %f \n", lwX,hiX,lwY,hiY); */
/*      calculate which vertex is closest to the star's centre */
	clrd=1000.0;
	trd = (float)sqrt((double)((x-lwX)*(x-lwX) + (y-lwY)*(y-lwY)));
	if(clrd >= trd) {
		clx=lwX;
		cly=lwY;
		clrd=trd;
	}
	trd=(float)sqrt((double)((x-lwX)*(x-lwX)+(y-hiY)*(y-hiY)));
	if(clrd >= trd) {
		clx=lwX;
		cly=hiY;
		clrd=trd;
	}
	trd=(float)sqrt((double)((x-hiX)*(x-hiX) + (y-lwY)*(y-lwY)));
	if(clrd >= trd) {
		clx=hiX;
		cly=lwY;
		clrd=trd;
	}
	trd=(float)sqrt((double)((x-hiX)*(x-hiX) + (y-hiY)*(y-hiY)));
	if(clrd >= trd) {
		clx=hiX;
		cly=hiY;
		clrd=trd;
	}
/*      calculate the orthoginal coordinates for these four values and see if it
	intersect the pixel's boundaries */
	numint = 0;
	numy = 0;
	numx = 0;
/*      check the four sides of the pixel to see where tstrd interesects the pixel */
	tstY=0.0;
	tstX=0.0;
	sd=(double)((*tstrd)*(*tstrd)-(x-lwX)*(x-lwX));
	if (sd >= 0.0){
	   tstY = (float)sqrt(sd);
	} else {
	   tstY = -100;
	}
	if(tstY > 0) {
	   if (hiY <= y){
		tstY=y-tstY;
	   } else if (lwY >= y) {
		tstY=y+tstY;
	   } else {
		tryY=y+tstY;
		if (tryY > hiY) {
			tstY = y-tryY;
		} else {
			tstY = tryY;
		}
	   }
	}
/*	printf("tstY = %f %f %f \n", tstY,*tstrd,lwX); */
	if (tstY>=lwY && tstY<=hiY) {
	  crdX[numint] = lwX;
	  crdY[numint] = tstY;
	  numy = numy+1;
	  numint=numint+1;
	}
/*      next side */
	tstY=0.0;
	tstX=0.0;
	sd = (double)((*tstrd)*(*tstrd)-(x-hiX)*(x-hiX));
	if (sd >= 0.0){
	   tstY = (float)sqrt(sd);
	} else {
	   tstY = -100.0;
	}
	if(tstY > 0.0) {
	   if (hiY <= y){
		tstY=y-tstY;
	   } else if (lwY >= y) {
		tstY=y+tstY;
	   } else {
		tryY=y+tstY;
		if (tryY > hiY) { 
			tstY = y-tryY;
		} else {
			tstY = tryY;
		}
	   }
	}
/*	printf("tstY = %f %f %f \n", tstY,*tstrd,hiX); */
	if (tstY>=lwY && tstY<=hiY) {
	  crdX[numint] = hiX;
	  crdY[numint] = tstY;
	  numy = numy+1;
	  numint=numint+1;
	}
/*      next side */
	tstY=0.0;
	tstX=0.0;
	sd = (double)((*tstrd)*(*tstrd)-(y-lwY)*(y-lwY));
	if (sd >= 0.0){
	   tstX = (float)sqrt(sd);
	} else {
	   tstX = -100.0;
	}
	if(tstX > 0.0) {
	   if (hiX <= x){
		tstX=x-tstX;
	   } else if (lwX >= x) {
		tstX=x+tstX;
	   } else {
		tryX=x+tstX;
		if (tryX > hiX) {
		    tstX = x-tryX;
		} else {
		    tstX = tryX;
		}
	   }
	}
/*	printf("tstX = %f %f %f \n", tstX,*tstrd,lwY); */
	if (tstX>=lwX && tstX<=hiX) {
	  crdX[numint] = tstX;
	  crdY[numint] = lwY;
	  numx = numx+1;
	  numint = numint+1;
	}
/*      next side */
	tstY=0.0;
	tstX=0.0;
	sd = (double)((*tstrd)*(*tstrd)-(y-hiY)*(y-hiY));
	if (sd >= 0.0){
	   tstX = (float)sqrt(sd);
	} else {
	   tstX = -100.0;
	}
	if(tstX > 0.0) {
	   if (hiX <= x){
		tstX=x-tstX;
	   } else if (lwX >= x) {
		tstX=x+tstX;
	   } else {
		tryX=x+tstX;
		if (tryX > hiX) {
			tstX = x-tstX;
		} else {
			tstX = tryX;
		}
	   }
	}
/*	printf("tstX = %f %f %f \n", tstX,*tstrd,hiY); */
	if (tstX>=lwX && tstX<=hiX) {
	  crdX[numint] = tstX;
	  crdY[numint] = hiY;
	  numx = numx+1;
	  numint = numint+1;
	}
	if (tstX == -100.0 && tstY == -100.0) {
	   printf("Error tstX tstY = -100.0");
	}
/*	printf("numx,numy = %i %i \n", numx,numy); */

/*      calculate the boundaries of the subpixel domain */
	if(numint > 2.0) {
	 	*pfrac = 0.95;
		return;
	} else if(numx==2 || numy==2) {     /* 2 gives a four sided subpixel region */
	  if(numx ==2) {
		hy=fabs(crdY[0]-crdY[1]);
		x1=fabs(clx-crdX[0]);
		x2=fabs(clx-crdX[1]);
		if(x1 <= x2){
			*pfrac = hy*x1+fabs(0.5*hy*(x2-x1));
		} else {
			*pfrac = hy*x2+fabs(0.5*hy*(x1-x2));
		}
/*		printf("pixel fraction = %f \n", *pfrac); */
		return;
	  } else {
		hx=fabs(crdX[0]-crdX[1]);
/*  	if (hx!=1.0) printf("cX0,cx1 %f %f \n",crdX[0],crdX[1]); */
		y1=fabs(cly-crdY[0]);
		y2=fabs(cly-crdY[1]);
		if(y1 <= y2) {
			*pfrac = hx*y1+fabs(0.5*hx*(y2-y1));
		} else {
			*pfrac = hx*y2+fabs(0.5*hx*(y1-y2));
		}
/*		printf("pixel fraction = %f \n", *pfrac); */
		return;
	  }
	  *pfrac=0.5;
	  return;
	} else if (numx == 1 && numy == 1){ /* triangular region */
	  if (crdX[0]==hiX || crdX[1]==hiX){
		trx=hiX;
	  } else if (crdX[0] == lwX || crdX[1] == lwX){
		trx=lwX;
	  }
	  if (crdY[0]==hiY || crdY[1]==hiY){
		try=hiY;
	  } else if (crdY[0]==lwY || crdY[1]==lwY){
		try=lwY;
	  }
/*  	  printf("trx,try,clx,cly = %f %f %f %f \n", trx,try,clx,cly); */
	  if (try == cly && trx == clx) {
		if(trx == crdX[0] && try == crdY[1]) {
			*pfrac = 0.5*fabs(try-crdY[0])*fabs(trx-crdX[1]);
		} else if (try == crdY[0] && trx == crdX[1]){
			*pfrac = 0.5*fabs(try-crdY[1])*fabs(trx-crdX[0]);
		} else {
/*			printf("Error in pxfrac calculating triangle area 1 \n"); */
			*pfrac=0.5;
			return;
		}
		if (*pfrac <= 0.0) *pfrac=-1.0*(*pfrac);
/*		printf("pixel fraction = %f \n", *pfrac); */
		return;
	  } else { /* sort through the vertces until a match is found */
		if(trx == crdX[0] && try == crdY[1]) {
			*pfrac = 1.0-0.5*fabs(try-crdY[0])*fabs(trx-crdX[1]);
		} else if (try == crdY[0]&& trx == crdX[1]){
			*pfrac = 1.0-0.5*fabs(try-crdY[1])*fabs(trx-crdX[0]);
		} else {
/*			printf("Error in pxfrac calculating triangle area 2 \n"); */
/*			printf(" trx try %f %f \n",trx,try); */
			*pfrac=0.5;
			return;
		}
		if (*pfrac <= 0.0) *pfrac=-1.0*(*pfrac);
/*		printf("pixel fraction = %f \n", *pfrac); */
		return;
	  }
	} else { /* error */
/*		printf("Error in pxfrac %i %i %i %f %f %f %f \n",numx,numy,numint,crdX[0],crdY[0],x,y); */
		*pfrac=0.9;
		return;
	}
	
}

/*************************************************************************
  average radius values 
**************************************************************************/

int averad(float *x,float *cn, float *er, int nn)
{
	int	jj;
	float	val,dist,wa,weight1,weight2,unst,cnhld[nn+1],erhld[nn+1];
	jj=0;
	     dist = (x[jj]-x[jj+1])/(x[jj+2]-x[jj+1]);
	     val = cn[jj+1]-(cn[jj+1]-cn[jj+2])*dist;
	     weight1 = 1.0/(er[jj+1]*er[jj+1]+er[jj+2]*er[jj+2]);
	     weight2 = 1.0/(er[jj]*er[jj]);
	     wa=(val*weight1+cn[jj]*weight2)/(weight1+weight2);
	     unst=0.707*(float)sqrt((double)(1/weight1+1/weight2));
	     cnhld[jj]=wa;
	     erhld[jj]=unst;
	for (jj=1;jj<=nn-1;++jj) { /* nn = number of entries in x and y. */
	     dist = (x[jj+1]-x[jj])/(x[jj+1]-x[jj-1]);
	     val = cn[jj+1]-(cn[jj+1]-cn[jj-1])*dist;
/*	     weighted average */
	     weight1 = 1.0/(er[jj+1]*er[jj+1]+er[jj-1]*er[jj-1]);
	     weight2 = 1.0/(er[jj]*er[jj]);
	     wa=(val*weight1+cn[jj]*weight2)/(weight1+weight2);
	     unst=0.707*(float)sqrt((double)(1/weight1+1/weight2));
	     cnhld[jj]=wa;
	     erhld[jj]=unst;
/*	     printf("Interpolation values %f %f \n",cnhld[jj],erhld[jj]);  debug */
	}
	jj=nn;
	     dist = (x[jj]-x[jj-1])/(x[jj-1]-x[jj-2]);
	     val = cn[jj-1]-(cn[jj-1]-cn[jj-2])*dist;
	     weight1 = 1.0/(er[jj-1]*er[jj-1]+er[jj-2]*er[jj-2]);
	     weight2 = 1.0/(er[jj]*er[jj]);
	     wa=(val*weight1+cn[jj]*weight2)/(weight1+weight2);
	     unst=0.707*(float)sqrt((double)(1/weight1+1/weight2));
	     cnhld[jj]=wa;
	     erhld[jj]=unst;
	for (jj=0;jj<=nn;++jj) { /* nn = number of entries in x and y. */
	     cn[jj]=cnhld[jj];
	     er[jj]=erhld[jj];
/*	     printf("radius = %5.1f %5.2f +/- %5.4f \n",x[jj],cn[jj],er[jj]);  debug */
	}
	return;
}
/*****************************************************************************************
******************************************************************************************/
int subray(float *x,float *y,float *dy, int nn,float *scl, float *vt, float *sg)
{
	 float suby[1024],subx[1024],suberr[1024],scl2,allscl[1024];
         float a2,b2,c2,da2,db2,dc2,foc;
	 float aa[1024],bb[1024],cc[1024],vertex[1024],dvert[1024];
	 float xvertex,yvertex,v[1024],dv[1024],ave,sum,smsqu,sd;
	 float x2,y2,err[1024],svescale,mdn;
	 int   rtn,kk,jj,ii,rr,ll,mm,nm[10],oo,samsize,numfit,loopcount;


	 samsize=(nn+1)*80.0;
	 numfit=5; 
	 oo=0;
	 jj=(int)0;
	 loopcount=0; 
	 do {
	     for (ll=0;ll<samsize;++ll) nm[ll] = 1024;
	     srand(time(NULL)*rand());
	     if (oo > nn) oo=0;
	     nm[0] = oo;
	     suberr[0] = dy[oo];
	     suby[0] = y[oo];
	     subx[0] = x[oo];
/*	     printf ("random: %i \n",nm[0]); */
	     oo=oo+1; 
	     kk=1;
	     for (ii=1;ii<numfit;++ii) {
		rr = (int)(rand() % nn+1);
		do {
		 for (ll=0;ll<ii;++ll) {
		   if (rr == nm[ll] ) {
			 ll=0;
			 rr=(int)(rand() % nn+1);
			 break;
		   }
		 }
		} while(ll < ii);
		nm[ii] = rr;
/*	        printf ("random: %i \n",rr); */
	        suberr[kk] = dy[rr];
	        suby[kk] = y[rr];
	        subx[kk] = x[rr];
		kk=kk+1;
	     }
	     loopcount=loopcount+1;
	     if(loopcount >= 30*samsize) {  /* poor sample try again */
		return (-1);
             } 
/*	     printf ("sample number: %i %i \n",jj,loopcount); */
	     scl2=1.0;
 	     rtn=lsq(subx,suby,suberr,(int)numfit,&scl2,&c2,&b2,&a2,&dc2,&db2,&da2);
	     for (mm=0;mm<numfit;++mm) {
	    	err[mm]=suberr[mm]*(scl2);
	     }
	     svescale = scl2;
	     scl2=1.0;
 	     rtn=lsq(subx,suby,err,(int)numfit,&scl2,&c2,&b2,&a2,&dc2,&db2,&da2);
	     vertex[jj]=-(b2/(2.0*a2));
	     if(vertex[jj] > 0) {
	     	dvert[jj]= vertex[jj]*(float)sqrt((double)
			((db2/b2)*(db2/b2)+(da2/a2)*(da2/a2)));
	     } else {
		dvert[jj]=-27.0;
	     }
	     yvertex=(4.0*c2*a2-b2*b2)/(4*a2);
	     x2=vertex[jj]+30.0;
	     y2=a2*x2*x2+b2*x2+c2;
/*	     if(yvertex <= y2 && dvert[jj] && svescale < 3.0 && svescale > 0.333 ){ */
/*             printf("parabolla: %f %f %f %f %f \n",vertex[jj],dvert[jj],yvertex,y2,svescale);   debug */
	     if(yvertex <= y2 && dvert[jj] > 0){ 
	        allscl[jj] = svescale;
	     	aa[jj] = a2;
	     	bb[jj] = b2;
	     	cc[jj] = c2;
		jj=jj+1; 
	     } else {
	        allscl[jj] = 0.0;
		dvert[jj] = 0.0;
	     	aa[jj] = 0.0;
	     	bb[jj] = 0.0;
	     	cc[jj] = 0.0;
	     }
/* 	     printf ("scale errors by zeroooooo: %f %i \n",allscl[0],jj);  */
	 } while (jj < samsize);

	 mdn=median(36,72,vertex);
	 rtn=bstat(vertex,dvert,samsize,&sd,&ave);
	 ii=0;
	 for (jj=0;jj<samsize;++jj) {
		if (vertex[jj]>=(ave-3.5*sd) && vertex[jj]<=(ave+3.5*sd)) {
			v[ii]=vertex[jj];
			dv[ii]=dvert[jj];
/*	     		printf ("vertex+-err: %f %f \n",v[ii],dv[ii]); debug */
			ii=ii+1;
		}
	 }
	 if(ii > 0) {
	    rtn=bstat(v,dv,ii,&sd,&ave);
	    ii=0.0;
	    scl2=0.0;
	    for (jj=0;jj<samsize;++jj) {
		if (vertex[jj]>=(ave-3.0*sd) && vertex[jj]<=(ave+3.0*sd)) {
			v[ii]=vertex[jj];
			dv[ii]=dvert[jj];
/*	                printf("best fit: %f %f \n",vertex[jj],dvert[jj]); */
			scl2=scl2+allscl[jj];
			ii=ii+1;
		}
	    }
	    rtn=bstat(v,dv,ii,&sd,&ave);
	    *scl=scl2/ii;
	 } else {
	    *scl=svescale;
	 }
/*	 *vt=ave; */ 
	 *vt=mdn; /* this is a chop to make it a little more reliable */
	 *sg=sd;
	 printf ("scale errors by: %f %f %i \n",*scl,scl2,ii); /* debug */

	 return;
}

/*******************************************************************************

********************************************************************************/
int bstat(float *vv,float *dv,int nn,float *stand,float *ave)
{
	 double sum,smw,w;
	 int   jj;

	 sum=0.0;
	 smw=0.0;
	 for (jj=0;jj<nn;++jj) {
		if(dv[jj] > 0.0) {
		    w=1.0/((double)dv[jj]*dv[jj]);
		    sum=sum+w*vv[jj];
		    smw=smw+w;
		}
	 }
/*         printf("average bstat: %i %f %f \n",nn,smw,sum); */

	 *ave=(float)sum/smw;
	 *stand =(float)sqrt(1.0/smw);
/*         printf("average bstat 2: %f %f %f %f \n",*ave,*stand,smw,sum); */
	 return;
}



/*************************************************************************
  Least squares fit 
**************************************************************************/

int lsq(float *x,float *y, float *dy, int nn,float *scl, float *c1, float *b1, float *a1,
        float *dc, float *db, float *da)
{
	 double sy=0,sxy=0,sx2y=0,sx=0,sx2=0,sx3=0,sx4=0,dt=0,dtcoeff=0,ss=0;
	 double Err,me1,jnk;
	 double **work;

	 int i=0;
	 work = malloc(sizeof(double *));
	 if (work == NULL) {
		return(-1);
	 }
	 for (ii=0;ii<3;ii++){
	 	work[ii] = malloc(9*sizeof(double)); /* 3x3 array */
	 	if (work[ii] == NULL) {
	 		printf  ("Error allocating memory ii= %i\n",ii);
			return(-1);
	 	}
	 }
	 me1=(double)(*scl);
	 for (jj=0;jj<nn;++jj) { /* nn = number of entries in x and y. */
	     Err=(double)(1/(dy[jj]*dy[jj]));
	     ss=ss+1.0*Err;
	     sy=sy+(double)y[jj]*Err;
	     sxy=sxy+(double)x[jj]*(double)y[jj]*Err;
	     sx2y=sx2y+(double)x[jj]*(double)x[jj]*(double)y[jj]*Err;
	     sx=sx+(double)x[jj]*Err;
	     sx2=sx2+pow((double)(x[jj]),(int)2)*Err;
	     sx3=sx3+pow((double)(x[jj]),(int)3)*Err;
	     sx4=sx4+pow((double)(x[jj]),(int)4)*Err;
	 }

 	 work[0][0]=ss;
	 work[1][0]=sx;
	 work[2][0]=sx2;
	 work[0][1]=sx;
	 work[1][1]=sx2;
	 work[2][1]=sx3;
	 work[0][2]=sx2;
	 work[1][2]=sx3;
	 work[2][2]=sx4;

/*       get determinant */
	 dt=determinant(work,(int) 3);

/*       calculate coefficient c */
	 work[0][0]=sy;
	 work[1][0]=sxy;
	 work[2][0]=sx2y;
	 dtcoeff=determinant(work,(int) 3);

	 *c1=(float)(dtcoeff/dt);

	 work[0][0]=ss;
	 work[1][0]=sx;
	 work[2][0]=sx2;
	 work[0][1]=sy;
	 work[1][1]=sxy;
	 work[2][1]=sx2y;
	 dtcoeff=determinant(work,(int) 3);

	 *b1=(float)(dtcoeff/dt);

	 work[0][1]=sx;
	 work[1][1]=sx2;
	 work[2][1]=sx3;
	 work[0][2]=sy;
	 work[1][2]=sxy;
	 work[2][2]=sx2y;
	 dtcoeff=determinant(work,(int) 3);

	 *a1=(float)(dtcoeff/dt);
/*	 printf ("c= %f \n",*c1);*/
	 me1=0.0;
	 for (jj=0;jj<nn;++jj) { /* nn = number of entries in x and y. */
	   Err=(double)(1/(dy[jj]*dy[jj]));
	   me1=me1+Err*pow((double)((*c1)+(*b1)*x[jj]+(*a1)*x[jj]*x[jj]-y[jj]),(int)2);
	 }
	 *scl= (float) sqrt(me1/(double)(nn-3));
	 *dc = (*scl)*(float)sqrt((1/dt)*(sx2*sx4-sx3*sx3));
	 *db = (*scl)*(float)sqrt((1/dt)*(ss*sx4-sx2*sx2));
	 *da = (*scl)*(float)sqrt((1/dt)*(ss*sx2-sx*sx));
/*  	 printf ("dc,db,da= %f +- %f ,%f +- %f , %f+- %f \n",*c1,*dc,*b1,*db,*a1,*da); */

	 free(work);
	 return (0);
}


/*************************************************************************
  Least squares fit 
**************************************************************************/

double     determinant(double **a,int n)
{
	int i,j,j1,j2;
	double det;
	double **m=NULL;

/*      calculate coeffic */
	if(n<1){ /* Error */
	} else if (n ==1) {
	    det = a[0][0];
	} else if (n==2) {
	    det = a[0][0]*a[1][1] - a[1][0]*a[0][1];
	} else {
	    det = 0;
	    for (j1=0;j1<n;j1++) {
		m = malloc((n-1)*sizeof(double *));
		for(i=0;i<n-1;i++)
			m[i] = malloc((n-1)*sizeof(double));
		for(i=1;i<n;i++){
			j2 = 0;
			for (j=0;j<n;j++) {
				if(j == j1)
					continue;
				m[i-1][j2] = a[i][j];
				j2++;
			}
		}
		det = det+pow(-1.0,1.0+j1+1.0)*a[0][j1]*determinant(m,n-1);
		for(i=0;i<n-1;i++)
			free(m[i]);
		free(m);
	   }
	}
/*	printf("@ return determinate = %f \n",det); */
	return(det);
}


/*************************************************************************
	median
**************************************************************************/

float     median(int k, int n, float *arr)
{
	int i,ir,j,l,mid;
	float a,temp;


	l=1;
	ir=n;
	for(;;) {
	    if(ir<=l+1){
		if(ir == l+1 && arr[ir]<arr[l]){
			SWAP(arr[l],arr[ir])
		}
		return arr[k];
	    } else {

		 mid=(l+ir)>>1;
		 SWAP(arr[mid],arr[l+1]);
		 if(arr[l]>arr[ir]){
			SWAP(arr[l],arr[ir])
		 }
		 if(arr[l+1]>arr[ir]) {
			SWAP(arr[l+1],arr[ir])
		 }
		 if(arr[l]>arr[ir+1]) {
			SWAP(arr[l],arr[l+1])
		 }
		 i=l+1;
		 j=ir;
		 a=arr[l+1];
		 for (;;) {
			do i++; while(arr[i]<a);
			do j--; while(arr[j]>a);
			if(j<i) break;
			SWAP(arr[i],arr[j])
		 }

		 arr[l+1]=arr[j];
		 arr[j]=a;
		 if(j>=k)ir=j-1;
		 if(j<=k)l=i;
	    }
	}
}




/*	  	if (hy!=1.0) {
			printf("cy0,cy1,numy,numint %f %f %f %i %i \n",crdY[0],crdY[1],crdY[2],numy,numint);
 			printf("box = %f %f %f %f %f %f \n", lwX,hiX,lwY,hiY,x,y);
			printf("cX0,cX1 %f %f %f \n",crdX[0],crdX[1],crdX[2]); 
		} */



/* 	       rtn=subray(starall.StarX,starall.StarCnt,
				  starall.StarErr,(int)numall,&scl,&vertex,&sma);
	       for (jj=0;jj<=numall;jj+=1){
		starall.StarErr[jj]=scl*starall.StarErr[jj];
	        printf("diameter = %5.2f +/- %5.4f @ %7.2f \n",2.0*starall.StarCnt[jj],
				2.0*starall.StarErr[jj],starall.StarX[jj]);
	       } 
	       scl=1.0; */
/*	       printf("calling subray \n"); /* debug */


/* -------------------------------------------------------------------------------------------------
	 flag = rtn;
	 if (flag == 0) {
/*	        Apply the offset in the x direction until all star images are found. 
	 	rtn = FindStarInfo(&StarSigmaX, &StarSigmaY, StartX, StartY,
				           EndX, EndY, Thresh, Sigma, x, y);
		starplus.SigmaX[0] = StarSigmaX;
		starplus.SigmaY[0] = StarSigmaY;
		BoxSize = 1+(int)(sqrt(StarSigmaX+StarSigmaY));
	 	rtn = FindCentre(&x,&y,&CovXY,BoxSize,StartX,StartY,
				         EndX,EndY,Sky);
		if(rtn|= 0) {
 		 printf("Error report(focusat) when trying to find the star's centre. \n");
		}
		starplus.StarX[0]=x;
		starplus.StarY[0]=y;
/*	        Generate the position of the stars either side of this star 
		(offset are in x direction). */
/*		Continue to apply the offset until the chip edge is found or no 
		star is found 
		numplus=1;
		for (jj=0;jj<=7;jj+=1) {
			if (jj>=1 && 
			   (int)starplus.StarX[jj-1]-offset/2<=(int)starplus.StarX[jj] && 
			   (int)starplus.StarX[jj-1]+offset/2>=(int)starplus.StarX[jj] ) break;	
			x=starplus.StarX[jj]+offset;
			y=starplus.StarY[jj];
			if (x >= EndX) break; /* star is off the image 
			BoxStrX=x-(offset*0.45);
			if (BoxStrX <= StartX) BoxStrX <= StartX;
			BoxEndX=x+(offset*0.45);
			if (BoxEndX >= EndX) BoxEndX <= EndX;
			BoxStrY=y-(offset*0.45);
			if (BoxStrY <= StartY) BoxStrY <= StartY;
			BoxEndY=y+(offset*0.45);
			if (BoxEndX >= EndX) BoxEndY <= EndY;
         		rtn  = LocateStar(&x,&y,&Signal2Noise,BoxStrX,BoxStrY,BoxEndX,BoxEndY,
							  Thresh,Sigma);
			if (rtn == 0) { /* found star 
	 			rtn = FindStarInfo(&StarSigmaX, &StarSigmaY, StartX, StartY,
				 		    EndX, EndY, Thresh, Sigma, x, y);
				if (rtn == 0) { /* estimate of x,y 
					BoxSize = 
					1+(int)(sqrt(StarSigmaX*StarSigmaX+
						   StarSigmaY*StarSigmaY));
			 		rtn = FindCentre(&x,&y,&CovXY,BoxSize,StartX,StartY,
				     	    		 EndX,EndY,Sky);
					if(rtn == 0) { /* found a centre
						if (rtn == 0) {
						    starplus.SigmaX[jj+1] = StarSigmaX;
						    starplus.SigmaY[jj+1] = StarSigmaY;
						    starplus.StarX[jj+1]  = x;
						    starplus.StarY[jj+1]  = y;
						    numplus = numplus+1;
						} else {
							printf("Integration failed. \n");
							break;
						}
					} else {
 						printf("Could not find centre. \n");
						break;
					}
				} else { /* couldn't estimate sigmax,sigmay 
				    printf("Could not identify the star. \n");
					break;
				}
			 } else { /* no star found */
/*				Couldn't find a star */
/*				printf("Found %i stars. \n",jj+1); 
				break;
		     }
		}
		starminus.StarX[0]=starplus.StarX[0];
		starminus.StarY[0]=starplus.StarY[0];
/*		printf ("star at %f %f" ,starminus.StarX[0],starminus.StarY[0]); 

		numminus=0;
		for (jj=0;jj<=7;jj+=1) {
			if (jj>=1 && 
			   (int)starminus.StarX[jj-1]-offset/3 <=(int)starminus.StarX[jj] && 
			   (int)starminus.StarX[jj-1]+offset/3 >=(int)starminus.StarX[jj]) break;
			x=starminus.StarX[jj]-offset;
			y=starminus.StarY[jj];
			if (x <= StartX) break; /* star is off the image 
			BoxStrX=x-offset*0.5;
			if (BoxStrX <= StartX) BoxStrX <= StartX;
			BoxEndX=x+offset*0.5;
			if (BoxEndX >= EndX) BoxEndX <= EndX;
			BoxStrY=y-offset*0.5;
			if (BoxStrY <= StartY) BoxStrY <= StartY;
			BoxEndY=y+offset*0.5;
			if (BoxEndX >= EndX) BoxEndY <= EndY;
         		rtn  = LocateStar(&x,&y,&Signal2Noise,BoxStrX,BoxStrY,BoxEndX,BoxEndY,
							  Thresh,Sigma);
			if (rtn == 0) { /* found star 
	 			rtn = FindStarInfo(&StarSigmaX, &StarSigmaY, StartX, StartY,
				 				   EndX, EndY, Thresh, Sigma, x, y);
				if (rtn == 0) { /* estimate of sigmaX,sigmaY 
					BoxSize = 1+(int)(sqrt(StarSigmaX*StarSigmaX+StarSigmaY*StarSigmaY));
			 		rtn = FindCentre(&x,&y,&CovXY,BoxSize,StartX,StartY,
				     	    		 EndX,EndY,Sky);
					if(rtn == 0) { /* found a centre

						if (rtn == 0) {
						    starminus.SigmaX[jj+1] = StarSigmaX;
						    starminus.SigmaY[jj+1] = StarSigmaY;
						    starminus.StarX[jj+1]  = x;
						    starminus.StarY[jj+1]  = y;
						    numminus = numminus+1;
/*		printf("-x,-y,numminus = %f %f %i \n",starminus.StarX[jj+1],starminus.StarY[jj+1],numminus);   

						} else {
							printf("Integration failed. \n");
							break;
						}
					} else {
						printf("Did not find centre. \n");
						break;
					}
				} else { /* couldn't estimate sigmax,sigmay 
					printf("Could not estimate star sigma. \n");
					break;
				}
			} else { /* no star found */
/*				Image is way off centre or doesn't exist */
/*				printf("Found %i stars. \n",jj); 
				break;
			}
		}
/*		Sort the stars found from lowest x to highest x. 
		numall=0;
		numplus=numplus-1;
		for (jj=numminus;jj>=0;jj-=1){
			starall.SigmaX[numall]=starminus.SigmaX[jj];
			starall.SigmaY[numall]=starminus.SigmaY[jj];
			starall.StarX[numall]=starminus.StarX[jj];
			starall.StarY[numall]=starminus.StarY[jj];
			numall = numall+1;
		}

		if(numminus >= 0) {
			if(starminus.StarX[0]-(float)offset/3 <=starplus.StarX[0] && 
			    starminus.StarX[0]+(float)offset/3 >=starplus.StarX[0]) {
			    numall = numall-1;
			}
		}

		for (jj=0;jj<=numplus;jj+=1){
			starall.SigmaX[numall]=starplus.SigmaX[jj];
			starall.SigmaY[numall]=starplus.SigmaY[jj];
			starall.StarX[numall]=starplus.StarX[jj];
			starall.StarY[numall]=starplus.StarY[jj];
			numall = numall+1;
		}
		numall=numall-1;
	        if (numall <= 6) {
/*	 	  printf("Only %i stars found. \n", numall);   debug 
                  return (EXIT_FAILURE);
	        }
/*		go through all of the stars and find the smallest "foot print" 
		smalldiff=256;
		for (jj=0;jj<=numall;jj+=1){
			x=starall.StarX[jj];
			y=starall.StarY[jj];
			rtn = bxlimits(&stX, &stY, &enX, &enY, Thresh, Sigma, x, y);
			xdiff=stX-enX;
			if(xdiff <= smalldiff) {
				smalldiff=xdiff;
				stX_fp=stX;
				stY_fp=stY;
				enX_fp=enX;
				enY_fp=enY;
/*	 		    printf("x = y diff = %i %i %i %i \n", stX, enX,stY,enY);  debug 
			}
		}
		averagecount=0.0;
		pxlsum=0.0;
		lgcount=0;
------------------------------------------------------------- */





/*
	printf ("direct estimate of focus is: %f +/- %f \n",vertex,sma);
	aaa=strstr(filenme,".raw");
	strncpy(aaa,".dat",4);
 	printf("results saved in file =  %s \n",filenme);
	if ((fpw=fopen(filenme,"wb"))==NULL){
 	    printf("can not open file \n");
	    return(EXIT_FAILURE);
	} else {
	    for (jj=0;jj<=numall;jj+=1){
		fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
		starall.StarX[0],starall.StarCnt[0],
		starall.StarErr[0],starall.StarY[0]);
	    }
	    fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
		    vertex,sma,scl,vertex);
	    fclose(fpw);
	    printf ("direct estimate of focus is: %f +/- %f \n",vertex,sma);
	    aaa=strstr(filenme,".raw");
	    strncpy(aaa,".dat",4);
 	    printf("results saved in file =  %s \n",filenme);
	    if ((fpw=fopen(filenme,"wb"))==NULL){
 	 	printf("can not open file \n");
	        return(EXIT_FAILURE);
	    } else {
		fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
		starall.StarX[0],starall.StarCnt[0],
		starall.StarErr[0],starall.StarY[0]);
	    }
	    fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
				vertex,sma,scl,vertex); /* last entry is focus 
	    fclose(fpw); */


/*	printf("diameter = %5.2f +/- %5.4f @ %7.2f \n",2.0*starall.StarCnt[0],
				2.0*starall.StarErr[0],starall.StarX[0]); */

/* 	rtn=subray(starall.StarX,starall.StarCnt,

				  starall.StarErr,(int)numall,&scl,&vertex,&sma);
	if (rtn <= -1) {
              return (EXIT_FAILURE);
	}
	for (jj=0;jj<=numall;jj+=1){

		starall.StarErr[jj]=scl*starall.StarErr[jj];
	        printf("diameter = %5.2f +/- %5.4f @ %7.2f \n",2.0*starall.StarCnt[jj],
				2.0*starall.StarErr[jj],starall.StarX[jj]);
	}

	printf ("direct estimate of focus is: %f +/- %f \n",vertex,sma);*/



/*       Find the star's footprint */
/*	 for (jjj=0;jjj<=numall;jjj+=1){ /* numall is not defined 
		x=starall.StarX[jjj];
		y=starall.StarY[jjj];
		stX_bx=x-BoxStrX;
		stY_bx=y-BoxStrY;
		enX_bx=x+BoxEndX;
		enY_bx=y+BoxEndY;
		total=0.0;
/* 		If a pixel is above the threshold include it in the 
		estimate of the brightness 
		for (jj=stY_bx;jj<=enY_bx;++jj) {
	    		for (ii=stX_bx;ii<=enX_bx;++ii) {
				if (CCDImage[ii][jj] >= limit) {
					total=total+(float)CCDImage[ii][jj];
				}
	   		}
		}
		pxlsum=pxlsum+1.0;
		averagecount = total;
		if (total>=lgcount) lgcount=total;
	}
	averagecount=averagecount/pxlsum;

	for (jj=0;jj<=numall;jj+=1){
			x=starall.StarX[jj];
			y=starall.StarY[jj];
			stX_bx=x-stX_fp;
			stY_bx=y-stY_fp;
			enX_bx=x+enX_fp;
			enY_bx=y+enY_fp;
			rtn = integrate(&countpixel,&cnterr,&stX_bx,&stY_bx,&enX_bx,
							&enY_bx,Thresh, Sigma,x, y,averagecount);
			starall.StarCnt[jj]=countpixel;
			starall.StarErr[jj]=cnterr;
/*	            	printf("count error = %f %f \n",countpixel,cnterr);   debug 

		}
 		rtn=averad(starall.StarX, starall.StarCnt,starall.StarErr,(int)numall);


	       scl=1.0;




/*              integrate this footprint for each star 
/*              find the star with the smallest radius 

		small=100.0;	
		for (jj=0;jj<=numall;jj+=1){
			if(starall.StarCnt[jj]<=small){
				small=starall.StarCnt[jj];
				if (jj == 0) {
					startAt=jj;
					endAt=jj+3;
				} else if (jj == numall){
					startAt=jj-3;
					endAt=jj;
				} else {
					startAt=jj-1;
					endAt=jj+2;
					if(endAt >= numall+1){
						startAt=jj-2;
						endAt=jj+1;
					}
				}

			}
			allat=0;
			for (ii=startAt;ii<=endAt;ii+=1){
				starfit.SigmaY[allat]=starall.SigmaY[ii];
				starfit.SigmaX[allat]=starall.SigmaX[ii];
				starfit.StarY[allat]=starall.StarY[ii];
				starfit.StarX[allat]=starall.StarX[ii];
				starfit.StarCnt[allat]=starall.StarCnt[ii];
				starfit.StarErr[allat]=starall.StarErr[ii];
				allat=allat+1;
			}

		}
	       scl=1.0;
 	       rtn=subray(starall.StarX,starall.StarCnt,
				  starall.StarErr,(int)numall,&scl,&vertex,&sma);
	       if (rtn <= -1) {
                  return (EXIT_FAILURE);
	       }
	       for (jj=0;jj<=numall;jj+=1){

		starall.StarErr[jj]=scl*starall.StarErr[jj];
	        printf("diameter = %5.2f +/- %5.4f @ %7.2f \n",2.0*starall.StarCnt[jj],
				2.0*starall.StarErr[jj],starall.StarX[jj]);
	       }
		printf ("direct estimate of focus is: %f +/- %f \n",vertex,sma);
	 	aaa=strstr(filenme,".raw");
	 	strncpy(aaa,".dat",4);
 	 	printf("results saved in file =  %s \n",filenme);
	 	if ((fpw=fopen(filenme,"wb"))==NULL){
 	 		printf("can not open file \n");
	        	return(EXIT_FAILURE);
	 	} else {
	       		for (jj=0;jj<=numall;jj+=1){
				fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
				starall.StarX[jj],starall.StarCnt[jj],
				starall.StarErr[jj],starall.StarY[jj]);
			}
	 		fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
				vertex,sma,scl,vertex);
			fclose(fpw);
	 	}
		return(EXIT_SUCCESS);
/*       Get a centre for the brightest star 
/*       Look for stars either side of this star
/*	 Test to see if the stars from a line */ 






