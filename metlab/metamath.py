#!/usr/bin/env python2.7

from __future__ import division
try:
    try:
        from metapprox import metapprox
    except:
        from mpmath import *
        mp.dps = 128
        mp.pretty = True
except:
    raise

def bp_to_int(value, suffix="KMGTP"):
    try:
        exp = (suffix.index(value[-1].upper())+1)*3 if value[-1].upper() in suffix else 1
        return int(float(value[:-1])*(10**exp))
    except:
        return -1

def binomial(n,k):
    return fac(n)/(fac(k)*fac(n-k))

def get_runs(L,l,R,a,max_iterations=10,p_limit=0.1):
    for i in range(max_iterations):
        p = full_coverage(L,l,R*(i+1),a)
        if p >= p_limit:
            break
    return i+1, p

def full_coverage(L,l,R,a):
    """
    Wrapper function around the C-function with the same name. Casts all 
    arguments to the correct type, then calls the C function and returns it's 
    return value. If the C-function isn't available, the value is calculated 
    using mpmath instead.

    Arguments are:
    L : approximated length of target genome
    l : (mean) length of sequenced reads
    R : number of reads in the metagenomic community
    a : approximated abundance of target in R
    """
    # Cast all variables to the right type
    L = int(L)
    l = int(l)
    R = int(R)
    a = float(a)
    
    try:
        from metapprox import metapprox
        return metapprox.full_coverage(L,l,R,a)
    except Exception as e:
        pass
    
    # calculate derived variables
    f = l/L
    n = min(R, int(1.0/f))
    
    # calculate result
    result = 0.0
    steps = n
    for b in range(0, n):
        
        first  = binomial(R,b)
        second = (-a)**(b)
        third  = (1-b*f)**(b-1)
        fourth  = (1-b*f*a)**(R-b) 
        
        result += first * second * third * fourth
    
    return result

def gap_consensus(L,l,R,a,k):
    """
    Wrapper function around the C-function with the same name. Casts all 
    arguments to the correct type, then calls the C function and returns it's 
    return value. If the C-function isn't available, the value is calculated 
    using mpmath instead.
    
    Arguments are:
    L : approximated length of target genome
    l : (mean) length of sequenced reads
    R : number of reads in the metagenomic community
    a : approximated abundance of target in R
    k : target number of assembly gaps
    """
    # Cast all variables to the right type
    L = int(L)
    l = int(l)
    R = int(R)
    a = float(a)
    k = int(k)
    
    try:
        from metapprox import metapprox
        return metapprox.gap_consensus(L,l,R,a,k)
    except Exception as e:
        pass
    
    # calculate derived variables
    f = l/L
    n = min(R, int(1.0/f))
    
    # calculate result
    term1 = binomial(R,k)
    
    term2 = 0.0
    steps = n-k
    for b in range(k, n):
        
        first  = binomial(R-k,b-k)
        second = (-1)**(b-k)
        third  = a**b
        fourth = (1-b*f)**(b-1)
        fifth  = (1-b*f*a)**(R-b) 
        
        term2 += first * second * third * fourth * fifth
    result = term1*term2
    
    return result

if __name__ == '__main__':
    
    import argparse
    
    parser = argparse.ArgumentParser( description = __doc__ )
    
    parser.add_argument("-L", help="approximated target genome size", default="1M")
    parser.add_argument("-l", help="mean read length", default=100, type=float)
    parser.add_argument("-R", help="Reads in the metagenomic community", default="1G")
    parser.add_argument("-a", help="approximated abundance of target in R", default=0.0001, type=float)
    parser.add_argument("-k", help="target number of assembly gaps", default=None)
    parser.add_argument("-m", help="max iterations", default=None, type=int)
    parser.add_argument("-p", help="min probability", default=0.1, type=float)
    
    args = parser.parse_args()
    
    if args.k:
        print gap_consensus(bp_to_int(args.L), args.l, bp_to_int(args.R), args.a, bp_to_int(args.k))
    elif args.m:
        print get_runs(bp_to_int(args.L), args.l, bp_to_int(args.R), args.a, args.m, args.p)
    else:
        print full_coverage(bp_to_int(args.L), args.l, bp_to_int(args.R), args.a)
    