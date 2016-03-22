#include "metapprox.h"
#include <stdio.h>

int binomial(mpfr_t retval, unsigned long R, unsigned long k)
{
    /* Calculates a binomial using the gamma function to approximate the value 
       of the factorials.
    */
    mpfr_t numerator, denominator, denom1, denom2, temp;
    
    /* init the variables. */
    mpfr_init2 (temp, PRECISION);
    mpfr_init2 (numerator,   PRECISION);
    mpfr_init2 (denominator, PRECISION);
    mpfr_init2 (denom1,      PRECISION);
    mpfr_init2 (denom2,      PRECISION);
    
    /* calculate! */
    mpfr_set_ui (temp, R+1, MPFR_RNDD);
    mpfr_gamma (numerator, temp, MPFR_RNDD);

    mpfr_set_ui (temp, k+1, MPFR_RNDD);
    mpfr_gamma (denom1, temp, MPFR_RNDD);
    
    mpfr_set_ui (temp, R-k+1, MPFR_RNDD);
    mpfr_gamma (denom2, temp, MPFR_RNDD);
    
    mpfr_mul (denominator, denom1, denom2, MPFR_RNDD) ;
    mpfr_div ( retval, numerator, denominator, MPFR_RNDD);
    
    /* clear all the variables */
    mpfr_clear (temp        );
    mpfr_clear (numerator  );
    mpfr_clear (denominator);
    mpfr_clear (denom1     );
    mpfr_clear (denom2     );
    return 0;
}

int gap_consensus(mpfr_t result, unsigned long L, unsigned int l, unsigned long R_in, double a, unsigned int k_in)
{
    mpfr_t f, n, R, k;
    mpfr_t temp, temp2;
    mpfr_t term1;
    long b;
    
    /*
     TODO: We should probably have some checks here... most obviously things 
           like "break if L,l,R_in, or a is 0"
    */
    
    /* we need some variables to store temporary numbers */
    mpfr_init2 (temp, PRECISION);
    mpfr_init2 (temp2, PRECISION);
    
    /* "R" is the size of the metagenomic community */
    mpfr_init2 (R, PRECISION);
    mpfr_set_ui (R, R_in, MPFR_RNDD);
    
    /* "k" is the number of gaps in the alignment */
    mpfr_init2 (k, PRECISION);
    mpfr_set_d (k, k_in, MPFR_RNDD);
    
    /* "f" is the probability of a position being covered */
    mpfr_init2 (f, PRECISION);
    mpfr_set_d (f, ((double)l/(double)L), MPFR_RNDD);
    
    /* "n" is the steven's series delimiter */
    mpfr_init2 (n, PRECISION);
    mpfr_d_div (n, 1.0, f, MPFR_RNDD);
    
    mpfr_round (n, n);
    if ( mpfr_cmp (R, n) < 0.0 )
    {
        mpfr_set (n, R, MPFR_RNDD);
    }
    
    /* Now we have all the variables. Start Calculating! */
    
    /* Term 1: bin(R, k) */
    
    mpfr_init2 (term1, PRECISION);
    binomial(term1, mpfr_get_ui(R, MPFR_RNDD), mpfr_get_ui(k, MPFR_RNDD));
    
    /* The big sum, this is where it get's tricky */
    
    mpfr_init2 (result, PRECISION);
    mpfr_set_d(result, 0.0, MPFR_RNDD);
    
    for (b = k_in; b < mpfr_get_ui(n, MPFR_RNDD); b++)
    {
        /* bin(R-k, b-k) */
        binomial(temp, R_in-k_in, b-k_in);

        /* (-1)^(b-k) */
        mpfr_set_d(temp2, -1.0, MPFR_RNDD);
        mpfr_pow_ui (temp2, temp2, b-k_in, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* a^b */
        mpfr_set_d  (temp2, a, MPFR_RNDD);
        mpfr_pow_ui (temp2, temp2, b, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* (1-b*f)^(b-1) */
        mpfr_mul_ui (temp2, f, b, MPFR_RNDD);
        mpfr_ui_sub (temp2, 1, temp2, MPFR_RNDD);
        mpfr_pow_ui(temp2, temp2, b-1, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* (1-b*f*a)^(R-b) */
        mpfr_mul_ui (temp2, f, b, MPFR_RNDD);
        mpfr_mul_d  (temp2, temp2, a, MPFR_RNDD);
        mpfr_ui_sub (temp2, 1, temp2, MPFR_RNDD);
        mpfr_pow_ui(temp2, temp2, R_in-b, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* Add the iteration result to the final result */
        mpfr_add( result, result, temp, MPFR_RNDD );
    }
    
    /* set the final return value by multiplying the sum with term1 */
    mpfr_mul(result, result, term1, MPFR_RNDD);
    
    /* clear all variables */
    mpfr_clear (f);
    mpfr_clear (n);
    mpfr_clear (R);
    mpfr_clear (k);
    mpfr_clear (term1);
    mpfr_clear (temp);
    mpfr_clear (temp2);
    
    return 0;
}

int full_coverage(mpfr_t result, unsigned long L, unsigned int l, unsigned long R_in, double a)
{
    mpfr_t f, n, R;
    mpfr_t temp, temp2;
    long b;
    
    /*
     TODO: We should probably have some checks here... most obviously things 
           like "break if L,l,R_in, or a is 0"
    */
    
    /* we need some variables to store temporary numbers */
    mpfr_init2 (temp, PRECISION);
    mpfr_init2 (temp2, PRECISION);
    
    /* "R" is the size of the metagenomic community */
    mpfr_init2 (R, PRECISION);
    mpfr_set_ui (R, R_in, MPFR_RNDD);
    
    /* "f" is the probability of a position being covered */
    mpfr_init2 (f, PRECISION);
    mpfr_set_d (f, ((double)l/(double)L), MPFR_RNDD);
    
    /* "n" is the steven's series delimiter */
    mpfr_init2 (n, PRECISION);
    mpfr_d_div (n, 1.0, f, MPFR_RNDD);
    
    mpfr_round (n, n);
    if ( mpfr_cmp (R, n) < 0.0 )
    {
        mpfr_set (n, R, MPFR_RNDD);
    }
    
    /* Now we have all the variables. Start Calculating! */
    /* The big sum, slightly simpler than the gap consensus one */
    
    mpfr_init2 (result, PRECISION);
    mpfr_set_d(result, 0.0, MPFR_RNDD);
    
    for (b = 0; b < mpfr_get_ui(n, MPFR_RNDD); b++)
    {
        /* bin(R-k, b-k) */
        binomial(temp, R_in, b);
        
        /* -a^b */
        mpfr_set_d  (temp2, -a, MPFR_RNDD);
        mpfr_pow_ui (temp2, temp2, b, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* (1-b*f)^(b-1) */
        mpfr_mul_ui (temp2, f, b, MPFR_RNDD);
        mpfr_ui_sub (temp2, 1, temp2, MPFR_RNDD);
        mpfr_pow_ui(temp2, temp2, b-1, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* (1-b*f*a)^(R-b) */
        mpfr_mul_ui (temp2, f, b, MPFR_RNDD);
        mpfr_mul_d  (temp2, temp2, a, MPFR_RNDD);
        mpfr_ui_sub (temp2, 1, temp2, MPFR_RNDD);
        mpfr_pow_ui(temp2, temp2, R_in-b, MPFR_RNDD);
        mpfr_mul (temp, temp, temp2, MPFR_RNDD);
        
        /* Add the iteration result to the final result */
        mpfr_add( result, result, temp, MPFR_RNDD );
    }
    
    /* clear all variables */
    mpfr_clear (f);
    mpfr_clear (n);
    mpfr_clear (R);
    mpfr_clear (temp);
    mpfr_clear (temp2);
    
    return 0;
}

int main(void)
{
    mpfr_t result;
    unsigned long L, R;
    unsigned int l, k;
    double a;
    
    L = 10000000; // 10Mb target species
    l = 250;      // 250bp reads
    R = 45000000; // 10M reads
    a = 0.001;     // 0.1% reads from target species
    k = 10;       // target number of gaps in the sequence
    
    // printf("Running test with:\n");
    // printf("  L = %lu\n", L);
    // printf("  l = %i\n", l);
    // printf("  R = %lu\n", R);
    // printf("  a = %3.2f\n", a);
    // printf("  k = %i\n", k);
    
    
    mpfr_init2 (result, PRECISION);
    // gap_consensus(result, L, l, R, a, k);
    // printf("Gap Consensus, k = %i\n", k);
    // mpfr_printf("Got: %Rf\n\n", result);
    full_coverage(result, L, l, R, a);
	printf("%i, ", PRECISION);
    mpfr_printf("%Rf\n", result);
    mpfr_clear (result);
}