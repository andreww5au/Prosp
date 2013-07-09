
%{
#define SWIG_FILE_WITH_INIT
#include "libfli.h"
%}

%include "cpointer.i"
%pointer_class(long, longp);
%pointer_class(size_t, size_t);
%pointer_class(unsigned long, ulongp);
%pointer_class(unsigned int, uintp);
%pointer_class(int, intp);
%pointer_class(float, floatp);
%pointer_class(double, doublep);

%ignore FLIDebug;

/*
%ignore GetCameraEventStatus;
%ignore UnMapPhysicalAddress;
%ignore SetPCIMode;
%ignore SetNextAddress16;
*/

%include "libfli.h"


/*
%extend ANDORCAPS {
	void initsize() {
		self->ulSize = sizeof(AndorCapabilities);
	}
};
*/
