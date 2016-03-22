from distutils.core import setup, Extension

#
#  RUN WITH: $ python setup.py build_ext --inplace
#

setup(name = 'Metapprox',
      version = '0.1',
      description = 'Metagenomic probability functions',
      author = 'Martin Norling',
      author_email = 'martin.norling@slu.se',
      url = '',
      long_description = '''
Arbitrary precision C implementation for solving the metagenomic approximation 
of Stevens' Theorem as explained by Wendl et al. in "Coverage theories for 
metagenomic DNA sequencing based on a generalization of Stevens' theorem"
(J. Math. Biol. (2013) 67:1141-1161 DIO 10.1006/s00285-012-0586-x).
The implementation uses the MPFR library for numerical precision.
''',
      ext_modules=[Extension("metapprox", 
                             define_macros   = [('MAJOR_VERSION', '0'),
                                                ('MINOR_VERSION', '1')],
                             include_dirs    = ['/usr/local/include', '../../local_apps/gcc/include'],
                             libraries       = ['mpfr', 'gmp'],
                             library_dirs    = ['/usr/local/lib', '../../local_apps/gcc/lib'],
                             sources         = ["_metapprox.c", "metapprox.c"])
                   ],
)
