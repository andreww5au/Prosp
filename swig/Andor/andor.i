
%{
#define SWIG_FILE_WITH_INIT
#include "atmcdLXd.h"
%}

%include "numpy.i"

%init %{
import_array();
%}

%apply (unsigned short * INPLACE_ARRAY1, int DIM1) { (unsigned short * arr, unsigned long size) };
%apply (long * INPLACE_ARRAY1, int DIM1) { (long * arr, unsigned long size) };
%apply (float * INPLACE_ARRAY1, int DIM1) { (float * arr, unsigned long size) };

%include "cpointer.i"
%pointer_class(long, longp);
%pointer_class(unsigned int, uintp);
%pointer_class(int, intp);
%pointer_class(float, floatp);

%ignore GetCameraEventStatus;
%ignore UnMapPhysicalAddress;
%ignore SetPCIMode;
%ignore SetNextAddress16;

%include "atmcdLXd.h"

%extend ANDORCAPS {
	void initsize() {
		self->ulSize = sizeof(AndorCapabilities);
	}
};

