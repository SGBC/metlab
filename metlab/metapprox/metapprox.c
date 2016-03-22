/*
 ===============================================================================
 Name        : metapprox.c
 Author      : Martin Norling
 Version     : 0.1.0a
 Copyright   : LGPL
 Description : Arbitrary precision C implementation for solving the metagenomic
               approximation of Stevens' Theorem as explained by Wendl et al. 
               in "Coverage theories for metagenomic DNA sequencing based on a 
                   generalization of Stevens' theorem" 
              (J. Math. Biol. (2013) 67:1141–1161 DOI 10.1007/s00285-012-0586-x)
               The implementation uses the MPFR library for numerical precision.
 ===============================================================================
 */

#include <Python.h>
#include <stdio.h>
#include <string.h>
#include "metapprox.h"

static char module_docstring[] =
    "implementation for solving the metagenomic approximation of Stevens' Theorem as explained by Wendl et al. in 'Coverage theories for metagenomic DNA sequencing based on a generalization of Stevens' theorem'";
static char full_coverage_docstring[] =
    "Calculates the probability of full coverage of a genome of length L, with an abundance of a in a metagenomic community with R reads of length l.";
static char gap_consensus_docstring[] =
    "Calculates the probability of k gaps in a genome of length L, with an abundance of a in a metagenomic community with R reads of length l.";

static PyObject *metapprox_full_coverage(PyObject *self, PyObject *args);
static PyObject *metapprox_gap_consensus(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
    {"full_coverage", metapprox_full_coverage, METH_VARARGS, full_coverage_docstring},
    {"gap_consensus", metapprox_gap_consensus, METH_VARARGS, gap_consensus_docstring},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initmetapprox(void)
{
    PyObject *m = Py_InitModule3("metapprox", module_methods, module_docstring);
    if (m == NULL)
        return;
}

static PyObject *metapprox_full_coverage(PyObject *self, PyObject *args)
{
    /* This function takes the following arguments: 
        unsigned long int L : approximated length of target genome
             unsigned int l : (mean) length of sequenced reads
        unsigned long int R : number of reads in the metagenomic community
                   double a : approximated abundance of target in R
    */
    unsigned long int L, R;
    unsigned int l;
    double a;

    /* Parse the input tuple */
    if (!PyArg_ParseTuple(args, "kIkd", &L, &l, &R, &a))
        return NULL;

    
    /* Call the external C function to compute the probability. */
    mpfr_t result;
    mpfr_init2(result, PRECISION);
    full_coverage(result, L, l, R, a);
    
    /* This doesn't seem to work right... */
    double probability = mpfr_get_d(result, MPFR_RNDD);
    
    /* Build the output double */
    PyObject *ret = Py_BuildValue("d", probability);
    return ret;
}

static PyObject *metapprox_gap_consensus(PyObject *self, PyObject *args)
{
    /* This function takes the following arguments: 
        unsigned long int L : approximated length of target genome
             unsigned int l : (mean) length of sequenced reads
        unsigned long int R : number of reads in the metagenomic community
                   double a : approximated abundance of target in R
             unsigned int k : number of gaps in the assembly
    
    */
    unsigned long int L, R;
    unsigned int l, k;
    double a;
    
    /* Parse the input tuple */
    if (!PyArg_ParseTuple(args, "kIkdI", &L, &l, &R, &a, &k))
        return NULL;
    
    /* Call the external C function to compute the probability. */
    mpfr_t result;
    mpfr_init2(result, PRECISION);
    gap_consensus(result, L, l, R, a, k);
    
    /* This doesn't seem to work right... */
    double probability = mpfr_get_d(result, MPFR_RNDD);
    
    /* Build the output double */
    PyObject *ret = Py_BuildValue("d", probability);
    return ret;
}
