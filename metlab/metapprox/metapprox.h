#ifndef __METAPPROX_H__
#define __METAPPROX_H__

#define PRECISION 128

#include <gmp.h>
#include <mpfr.h>

/******************************************************************************
* FUNCTION DEFINITIONS                                                        *
******************************************************************************/

int gap_consensus(mpfr_t          result,
                  unsigned long   L, 
                  unsigned int    l, 
                  unsigned long   R, 
                           double a, 
                  unsigned int    k);
int full_coverage(mpfr_t          result,
                  unsigned long   L, 
                  unsigned int    l, 
                  unsigned long   R, 
                           double a);

#endif
