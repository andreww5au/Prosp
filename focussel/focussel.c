/******************************************************** 
	Code to analyse a focus image 

	Written by Ralph Martin
	date 04/05/05 - 
	date 15/03/07 -
	date 7/3/07 

	Calculate the focus point from the radius and focus points.	


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
	 short		     ReadMode; /* readout mode of the camera */
	 long   		 pixelwide,pixelhigh;
	 float           SigmaLimit=4.0;
	 float           FWHMLimit;
	 float           Quality;
	 float			 gain=4.3;
	 float			 rn=15/4.3;

	 signed int      MoveLog,Tab,LastMiss,Cycle;
/*
	 Function prototypes
*/
	 int     Dummy=0;

	 int 	 bstat(float *, float *, int , float *, float *);

	 int 	 subray(float *,float *,float *,int,float *, float *, float *);
	 int     lsq(float *,float *,float *, int ,float *,float *,float * ,float *,
                     float *,float *,float *);

	 double  determinant(double ** ,int );
	 float   median(int , int , float *);


int  main(argc,argv)
	 int argc;
	 char *argv[]; 
{
	 struct stardata {
				  float StarX[256];
				  float StarY[256];
				  float SigmaX[256];
				  float SigmaY[256];
				  float StarCnt[256];
				  float StarErr[256];
				 };
	 struct stardata starall;

	 int			  jj,ii,numall,rtn;
	 char             *aaa;
	 float			  file1,file2,file3,file4;
	 float			  x,y,countpixel,cnterr;
	 float			  sclby,sma,vertex;
	 FILE			  *fpr,*fpw;
	 char 			  filenme[64];

	 if (argc<2){
	  printf("Command format is- ./focussel /tmp/junk486.lst \n");
	  printf("Results are written to -/tmp/junk486.fit \n");
	  return(EXIT_FAILURE);
	 }

	 strcpy(filenme,argv[1]);
	 if ((fpr=fopen(filenme,"rb"))==NULL){
 	 	printf("can not open file \n");
	        return(EXIT_FAILURE);
	 } else {
	 	printf("Opened file:  %s \n",filenme);
	        jj=0;
		while (fscanf(fpr,"%f %f %f %f \n",&file1,&file2,&file3,&file4) != EOF)
		{
			starall.StarX[jj]=file1;
			starall.StarCnt[jj]=file2;
			starall.StarErr[jj]=file3;
			starall.StarY[jj]=file4;
			printf("%f %f %f %f\n",
				starall.StarX[jj],starall.StarCnt[jj],
				starall.StarErr[jj],starall.StarY[jj]);
			if (starall.StarX[jj] == starall.StarY[jj]) {   /* this is an LSQ focus point */
				jj=jj-1;
                        }
			jj=jj+1;
		}
		fclose(fpr);
	 }
	 sclby=1.0;	  
	 numall=jj-1;
/*	 numall=numall-1; */
         printf ("number of stars = %i \n", numall );
	 if (numall==0){
 	 		printf("nothing read from the file \n");
	        	return(EXIT_FAILURE);
	 }
 	 rtn=subray(starall.StarX,starall.StarCnt,
				  starall.StarErr,(int)numall,&sclby,&vertex,&sma);
	 for (jj=0;jj<=numall;jj+=1){
	       starall.StarErr[jj]=sclby*starall.StarErr[jj];
	       printf("diameter = %5.2f +/- %5.4f @ %7.2f \n",2.0*starall.StarCnt[jj],
				2.0*starall.StarErr[jj],starall.StarX[jj]);
	 }
	 printf ("best focus is at: %f +/- %f pixels \n",vertex,sma);

	 aaa=strstr(filenme,".lst");
	 strncpy(aaa,".fit",4);
 	 printf("results saved in file =  %s %s \n",filenme,aaa);
	 if ((fpw=fopen(filenme,"w"))==NULL){
 	 		printf("can not open file \n");
	        	return(EXIT_FAILURE);
	 } else {
	 	fprintf(fpw,"%7.2f %5.2f \n",vertex,sma);
		fclose(fpw);
	 }
	 return(EXIT_SUCCESS);
	 exit(0);
}

/*	       	for (jj=0;jj<=numall;jj+=1){
			fprintf(fpw,"%7.2f %5.2f %5.4f %7.2f \n",
			starall.StarX[jj],
			starall.StarCnt[jj],starall.StarErr[jj],starall.StarY[jj]);
		} */



/*****************************************************************************************
******************************************************************************************/
int subray(float *x,float *y,float *dy, int nn,float *scl, float *vt, float *sg)
{
	 float suby[2048],subx[2048],suberr[2048],scl2,allscl[2048];
         float a2,b2,c2,da2,db2,dc2,foc;
	 float aa[2048],bb[2048],cc[2048],vertex[2048],dvert[2048];
	 float xvertex,yvertex,v[2048],dv[2048],ave,sum,smsqu,sd;
	 float x2,y2,err[2048],svescale,mdn;
	 int   rtn,jj,ii,rr,ll,mm,nm[2048],oo,samsize,numfit;

	 samsize=(nn)*40.0; /* number of samples */
 	 numfit=(int)(nn*0.7);  /* sample size */
	 if (numfit >= 10) numfit = 9; 
/*	 numfit=5;   sample size */ 
	 jj=(int)0;
	 srand((unsigned int)time(NULL));
	 do {
	     for (ll=0;ll<samsize;++ll) nm[ll] = 1024;
	     for (ii=0;ii<numfit;++ii) {
		rr = (rand() % nn);
		do {                        /* check the range */
		    rr = (rand() % nn);
		} while(rr < 0 || rr > nn-1);
		do {                        /* check line number has not laready been selected */
		 for (ll=0;ll<ii;++ll) {
		   if (rr == nm[ll]) {
			 ll=0;
			 rr= (rand() % nn);
			 break;
		   }
		 }
		} while(ll < ii);
		nm[ii] = rr;
/*	        printf ("random: %i %i %i \n",rr,ii,nn); */
	        suberr[ii] = dy[rr];
	        suby[ii] = y[rr];
	        subx[ii] = x[rr];
	     }
/*	     printf ("sample number: %i \n",jj);  */
	     scl2=1.0;
 	     rtn=lsq(subx,suby,suberr,(int)numfit,&scl2,&c2,&b2,&a2,&dc2,&db2,&da2);
	     for (mm=0;mm<numfit;++mm) {
	    	err[mm]=suberr[mm]*(scl2);
	     }
	     svescale = scl2;
	     scl2=1.0;
 	     rtn=lsq(subx,suby,err,(int)numfit,&scl2,&c2,&b2,&a2,&dc2,&db2,&da2); 
/*	     rtn=lsq(subx,suby,err,(int)numfit,&scl2,&a2,&b2,&c2,&da2,&db2,&db2); */

/*             printf("parabolla constants and errors:%f %f %f %f %f %f %f  \n",scl2,c2,b2,a2,dc2,db2,da2);  */

	     vertex[jj]=-(b2/(2.0*a2));
	     if(vertex[jj] > 0) {
	     	dvert[jj]= vertex[jj]*(float)sqrt((double)((db2/b2)*(db2/b2)+(da2/a2)*(da2/a2)));
	     } else {
		dvert[jj]=-27.0;
	     }
	     yvertex=(4.0*c2*a2-b2*b2)/(4*a2);
	     x2=vertex[jj];
	     y2=c2-(b2*b2-1.0)/(4.0*a2);

/*           printf("parabolla before: %f %f %f %f %f \n",vertex[jj],dvert[jj],yvertex,y2,svescale);  */

/*	     if(yvertex <= y2 && dvert[jj] && svescale < 3.0 && svescale > 0.333 ){  */
	     if(yvertex <= y2 && dvert[jj] > 0){
/*              printf("parabolla after: %f %f %f %f %f \n",vertex[jj],dvert[jj],yvertex,y2,svescale); */
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
		jj=jj-1;      /* try again !! */
	     }
/* 	     printf ("scale errors by zeroooooo: %f %i \n",allscl[0],jj);  */
	     jj=jj+1; /* test this */
	 } while (jj <= samsize);

	 mdn=median(36,72,vertex);  
	 rtn=bstat(vertex,dvert,samsize,&sd,&ave);
	 ii=0;
	 for (jj=0;jj<samsize;++jj) {
		if (vertex[jj]>=(ave-3.5*sd) && vertex[jj]<=(ave+3.5*sd)) {
			v[ii]=vertex[jj];
			dv[ii]=dvert[jj];
/*	     		printf ("vertex+-err: %f %f \n",v[ii],dv[ii]);  */
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
/*	            printf("best fit: %f %f \n",vertex[jj],dvert[jj]); */
			scl2=scl2+allscl[jj];
			ii=ii+1;
		}
	    }
	    rtn=bstat(v,dv,ii,&sd,&ave);
	    *scl=scl2/ii;
	 } else {
	    *scl=svescale;
	 }
 	 *vt=ave;
/*	 *vt=mdn; */ /* this is a chop to make it a little more reliable */
	 *sg=sd;

/*	 printf ("scale errors by: %f %f %i \n",*scl,scl2,ii); */
	 return;
}

/*******************************************************************************

********************************************************************************/
int bstat(float *vv,float *dv,int nn,float *stand,float *ave)
{
	 double sum,smw,w,sw;
	 int   jj;

	 sum=0.0;
	 smw=0.0;
	 sw=0.0;
	 for (jj=0;jj<nn;++jj) {
/*                printf("average bstat:%f %f %f %f \n",vv[jj],dv[jj],smw,sum); */
		if(dv[jj] > 0.0) {
		    w=1.0/((double)dv[jj]*dv[jj]);
		    sum=sum+w*vv[jj];
		    smw=smw+w;
		    sw=sw+w;
		}
	 }
/*         printf("nn smw sum: %i %f %f \n",nn,smw,sum); */

	 *ave=(float)sum/smw;
	 *stand =(float)sqrt(1.0/sw);
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
	 int	ii,jj;

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


/**********************************************************************
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




/*			fscanf(fpr,"%7.2f %7.2f %5.2f %5.4f \n",
			starall.StarY[jj],starall.StarX[jj],
			starall.StarCnt[jj],starall.StarErr[jj]); */


/*			fscanf(fpr,"%7.2f %7.2f %5.2f %5.4f \n",
			starall.StarY[jj],starall.StarX[jj],
			starall.StarCnt[jj],starall.StarErr[jj]); */


/*	  	if (hy!=1.0) {
			printf("cy0,cy1,numy,numint %f %f %f %i %i \n",crdY[0],crdY[1],crdY[2],numy,numint);
 			printf("box = %f %f %f %f %f %f \n", lwX,hiX,lwY,hiY,x,y);
			printf("cX0,cX1 %f %f %f \n",crdX[0],crdX[1],crdX[2]); 
		} */

