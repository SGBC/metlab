#!/bin/bash

WD="$(pwd)"
APP_PATH="local_apps"
DATABASE="metlab.sqlite3"
KRAKEN_DB="https://ccb.jhu.edu/software/kraken/dl/minikraken.tgz"
VFAM="http://derisilab.ucsf.edu/software/vFam/vFam-A_2014.hmm"
VFAM_ANNOT="http://derisilab.ucsf.edu/software/vFam/annotationFiles_2014.zip"
TABLE_DEF="CREATE TABLE IF NOT EXISTS paths (id INTEGER PRIMARY KEY, name TEXT, path TEXT)"

if [[ "$(uname)" == "Darwin" ]]
then
    GET="curl -L"
    OUT="-o"
else
    GET="wget"
    OUT="-O"
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ----------------------------- Help functions --------------------------------
function print_help
{
    echo "$0"
    echo "-----------------------------------------------------------"
    echo "Installs dependencies for the default metlab pipeline."
    echo "USAGE: $0 [FragGeneScan]"
    echo "          [hmmsearch]"
    echo "          [krona]"
    echo "          [kraken]"
    echo "          [kraken_db]"
    echo "          [vfam]"
    echo "          [spades]"
    echo "          [samtools]"
    echo "          [bowtie2]"
    echo "          [prinseq-lite]"
    echo "          [local]"
    echo "          [metapprox]"
    echo "          [gcc]"
    echo "          [all]"
    echo
    echo "Running the script without arguments will default to 'all'"
}

function insert_into_database
{
    sqlite3 $DATABASE "$TABLE_DEF"
    sqlite3 $DATABASE "INSERT INTO paths (name, path) VALUES ('$1', '$2')"
}

function check_database
{
    sqlite3 $DATABASE "$TABLE_DEF"
    sqlite3 $DATABASE "SELECT path FROM paths WHERE name LIKE '$1%'"
}

function find_exec
{
    printf " - $1\t" >/dev/stderr
    db_path="$(check_database $1)"
    [[ "$db_path" != "" ]] && echo "0" && return
    type $1 >/dev/null 2>&1
    echo "$?"
}

function find_or_install
{
    if [[ "$(find_exec $1)" == "0" ]]
    then
        printf "${GREEN}Found${NC}\n"
    else
        printf "${RED}Not Found${NC}\n"
        eval "install_$1"
    fi
}

function install_gcc_5.2.0
{
    [[ "$(uname)" == "Darwin" ]] && [[ "$(which gcc)" == "" ]] && xcode-select --install

    GCC_VERSION="gcc-5.2.0"
    MPC_VERSION="mpc-1.0.3"
    MPFR_VERSION="mpfr-3.1.4"
    GMP_VERSION="gmp-6.1.0"
    ISL_VERSION="isl-0.14"

    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1
    mkdir -p $GCC_VERSION
    cd $GCC_VERSION || exit 1

    [ ! -e $GCC_VERSION.tar.bz2 ] && $GET ftp://ftp.fu-berlin.de/unix/languages/gcc/releases/$GCC_VERSION/$GCC_VERSION.tar.bz2 $OUT $GCC_VERSION.tar.bz2
    [ ! -e $MPC_VERSION.tar.gz ] && $GET ftp://ftp.gnu.org/gnu/mpc/$MPC_VERSION.tar.gz $OUT $MPC_VERSION.tar.gz
    [ ! -e $MPFR_VERSION.tar.bz2 ] && $GET http://www.mpfr.org/mpfr-current/$MPFR_VERSION.tar.bz2 $OUT $MPFR_VERSION.tar.bz2
    [ ! -e $GMP_VERSION.tar.bz2 ] && $GET https://gmplib.org/download/gmp/$GMP_VERSION.tar.bz2 $OUT $GMP_VERSION.tar.bz2
    [ ! -e $ISL_VERSION.tar.bz2 ] && $GET ftp://gcc.gnu.org/pub/gcc/infrastructure/$ISL_VERSION.tar.bz2 $OUT $ISL_VERSION.tar.bz2

    [ ! -d "$GMP_VERSION" ] && tar xf $GMP_VERSION.tar.bz2
    cd $GMP_VERSION || exit 1
    mkdir -p build
    cd build || exit 1
    if [ ! -e .complete ]
    then
        ../configure --prefix=${wd}/$APP_PATH/gcc --enable-cxx
        [ "$?" != "0" ] && echo "Could not configure $GMP_VERSION, aborting." && exit 1
        make -j4
        [ "$?" != "0" ] && echo "Could not make $GMP_VERSION, aborting." && exit 1
        make install
        [ "$?" != "0" ] && echo "Could not install $GMP_VERSION, aborting." && exit 1
        touch .complete
    fi
    cd ../.. || exit 1

    [ ! -d "$MPFR_VERSION" ] && tar xf $MPFR_VERSION.tar.bz2
    cd $MPFR_VERSION || exit 1
    mkdir -p build
    cd build || exit 1
    if [ ! -e .complete ]
    then
        ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp=${wd}/$APP_PATH/gcc
        [ "$?" != "0" ] && echo "Could not configure $MPFR_VERSION, aborting." && exit 1
        make -j4
        [ "$?" != "0" ] && echo "Could not make $MPFR_VERSION, aborting." && exit 1
        make install
        [ "$?" != "0" ] && echo "Could not install $MPFR_VERSION, aborting." && exit 1
        touch .complete
    fi
    cd ../.. || exit 1

    [ ! -d "$MPC_VERSION" ] && tar xf $MPC_VERSION.tar.gz
    cd $MPC_VERSION || exit 1
    mkdir -p build
    cd build || exit 1
    if [ ! -e .complete ]
    then
        ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp=${wd}/$APP_PATH/gcc --with-mpfr=${wd}/$APP_PATH/gcc
        [ "$?" != "0" ] && echo "Could not configure $MPC_VERSION, aborting." && exit 1
        make -j4
        [ "$?" != "0" ] && echo "Could not make $MPC_VERSION, aborting." && exit 1
        make install
        [ "$?" != "0" ] && echo "Could not install $MPC_VERSION, aborting." && exit 1
        touch .complete
    fi
    cd ../.. || exit 1

    [ ! -d "$ISL_VERSION" ] && tar xf $ISL_VERSION.tar.bz2
    cd $ISL_VERSION || exit 1
    mkdir -p build
    cd build || exit 1
    if [ ! -e .complete ]
    then
        ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp-prefix=${wd}/$APP_PATH/gcc
        [ "$?" != "0" ] && echo "Could not configure $ISL_VERSION, aborting." && exit 1
        make -j4
        [ "$?" != "0" ] && echo "Could not make $ISL_VERSION, aborting." && exit 1
        make install
        [ "$?" != "0" ] && echo "Could not install $ISL_VERSION, aborting." && exit 1
        touch .complete
    fi
    cd ../.. || exit 1

    [ ! -d "$GCC_VERSION" ] && tar xf $GCC_VERSION.tar.bz2
    cd $GCC_VERSION || exit 1
    mkdir -p build
    cd build || exit 1
    if [ ! -e .complete ]
    then
        ../configure --prefix=${wd}/$APP_PATH/gcc --enable-checking=release --with-gmp=${wd}/$APP_PATH/gcc --with-mpfr=${wd}/$APP_PATH/gcc --with-mpc=${wd}/$APP_PATH/gcc --enable-languages=c,c++,fortran --with-isl=${wd}/$APP_PATH/gcc
        [ "$?" != "0" ] && echo "Could not configure $GCC_VERSION, aborting." && exit 1
        make -j4
        [ "$?" != "0" ] && echo "Could not make $GCC_VERSION, aborting." && exit 1
        make install
        [ "$?" != "0" ] && echo "Could not install $GCC_VERSION, aborting." && exit 1
        touch .complete
    fi
    cd $wd || exit 1
    touch $APP_PATH/gcc/.complete
}

# ------------------------------ FragGeneScan ---------------------------------

function install_run_FragGeneScan.pl
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "FragGeneScan.tar.gz" ] && rm "FragGeneScan.tar.gzz"
    $GET "https://sourceforge.net/projects/fraggenescan/files/FragGeneScan1.18.tar.gz/download" $OUT "FragGeneScan.tar.gz"

    tar xf "FragGeneScan.tar.gz"
    rm "FragGeneScan.tar.gz"
    cd FragGeneScan*/ || exit 1
    make clean
    if [[ "$(uname)" == "Darwin" ]]
    then
        ln -s /usr/include/sys/malloc.h
        mv util_lib.c util_lib.c.original
        sed "s/#include <malloc.h>/#include \"malloc.h\"/g" util_lib.c.original > util_lib.c
        [ "$?" != "0" ] && echo "Could not modify util_lib.c, aborting." && exit 1
        mv hmm_lib.c hmm_lib.c.original
        sed "s/#include <malloc.h>/#include \"malloc.h\"/g" hmm_lib.c.original > hmm_lib.c.temp
        [ "$?" != "0" ] && echo "Could not modify hmm_lib.c, aborting." && exit 1
        sed "s/<values.h>/<limits.h>/g" hmm_lib.c.temp > hmm_lib.c
        [ "$?" != "0" ] && echo "Could not modify hmm_lib.c, aborting." && exit 1
        rm hmm_lib.c.temp
    fi
    make fgs
    [ "$?" != "0" ] && echo "make fgs failed, aborting." && exit 1
    path="$(pwd)/run_FragGeneScan.pl"
    cd $wd || exit 1
    insert_into_database "run_FragGeneScan.pl" "$path"
}

# ------------------------------ Prinseq-lite ---------------------------------

function install_prinseq-lite
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "prinseq-lite-0.20.4.tar.gz" ] && rm "prinseq-lite-0.20.4.tar.gz"
    $GET "https://sourceforge.net/projects/prinseq/files/standalone/prinseq-lite-0.20.4.tar.gz/download" $OUT "prinseq-lite-0.20.4.tar.gz"
    tar xf "prinseq-lite-0.20.4.tar.gz"
    rm "prinseq-lite-0.20.4.tar.gz"
    chmod +x "prinseq-lite-0.20.4/prinseq-lite.pl"
    path="$(pwd)/prinseq-lite-0.20.4/prinseq-lite.pl"
    cd $wd || exit 1
    insert_into_database "prinseq-lite.pl" "$path"
}

# --------------------------------- Bowtie2 -----------------------------------

function install_bowtie2
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    link="https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.7/bowtie2-2.2.7-linux-x86_64.zip/download"
    [[ "$(uname)" == "Darwin" ]] && link="https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.7/bowtie2-2.2.7-macos-x86_64.zip/download"

    [ -e "bowtie2-2.2.7.zip" ] && rm "bowtie2-2.2.7.zip"
    $GET $link $OUT "bowtie2-2.2.7.zip"
    unzip "bowtie2-2.2.7.zip"
    [ "$?" != "0" ] && echo "Couldn't unzip Bowtie2, aborting." && exit 1
    rm "bowtie2-2.2.7.zip"

    path="$(pwd)/bowtie2-2.2.7/bowtie2"
    build_path="$(pwd)/bowtie2-2.2.7/bowtie2-build"
    cd $wd || exit 1
    insert_into_database "bowtie2" "$path"
    insert_into_database "bowtie2-build" "$build_path"
}

# -------------------------------- Samtools -----------------------------------

function install_samtools
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "samtools-1.3.tar.bz2" ] && rm "samtools-1.3.tar.bz2"
    $GET "https://sourceforge.net/projects/samtools/files/latest/download?source=files" $OUT "samtools-1.3.tar.bz2"

    mkdir samtools-1.3
    tar xf "samtools-1.3.tar.bz2" -C samtools-1.3 --strip-components=1
    [ "$?" != "0" ] && echo "Couldn't unpack Samtools, aborting." && exit 1
    rm "samtools-1.3.tar.bz2"
    cd samtools-1.3 || exit 1
    ./configure
    [ "$?" != "0" ] && echo "configure samtools failed, aborting." && exit 1
    make
    [ "$?" != "0" ] && echo "make samtools failed, aborting." && exit 1

    path="$(pwd)/samtools"
    cd $wd || exit 1
    insert_into_database "samtools" "$path"
}

# -------------------------------- Spades.py ----------------------------------

function install_spades
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "SPAdes-3.6.2.tar.gz" ] && rm "SPAdes-3.6.2.tar.gz"
    link="http://spades.bioinf.spbau.ru/release3.6.2/SPAdes-3.6.2-Linux.tar.gz"
    [[ "$(uname)" == "Darwin" ]] && link="http://spades.bioinf.spbau.ru/release3.6.2/SPAdes-3.6.2-Darwin.tar.gz"
    $GET $link $OUT "SPAdes-3.6.2.tar.gz"
    tar xf "SPAdes-3.6.2.tar.gz"
    [ "$?" != "0" ] && echo "Couldn't unpack spades, aborting." && exit 1
    rm "SPAdes-3.6.2.tar.gz"

    path="$(pwd)/$(basename ${link/.tar.gz/})/bin/spades.py"
    cd $wd || exit 1

    insert_into_database "spades.py" "$path"
}

# --------------------------------- Kraken ------------------------------------

function install_kraken
{
    if [[ "$(uname)" == "Darwin" ]]
    then
        [ ! -e "$APP_PATH/gcc/.complete" ] && install_gcc_5.2.0
        ORG_PATH=$PATH
        PATH=$(pwd)/$APP_PATH/gcc/bin:$PATH
        [[ "$(gcc --version | head -1)" != "gcc (GCC) 5.2.0" ]] && echo "Could not find GCC 5.2.0" && exit 0
    fi

    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    if [ ! -d "kraken-0.10.5-beta" ]
    then
        [ ! -e "kraken-0.10.5-beta.tgz" ] && $GET "https://ccb.jhu.edu/software/kraken/dl/kraken-0.10.5-beta.tgz" $OUT "kraken-0.10.5-beta.tgz"
        tar xf "kraken-0.10.5-beta.tgz"
        rm "kraken-0.10.5-beta.tgz"
    fi
    path="$(pwd)/kraken"
    cd kraken-0.10.5-beta || exit 1
    ./install_kraken.sh $path
    # install_kraken.sh return 1 when successful
    [ "$?" != "1" ] && echo "install_kraken.sh failed, aborting." && exit 1

    cd $wd || exit 1
    insert_into_database "kraken" "$path/kraken"
    insert_into_database "kraken-report" "$path/kraken-report"

    if [[ "$(uname)" == "Darwin" ]] # replace the path only if on osx
    then
        PATH=$ORG_PATH
    fi
}

# -------------------------------- Kraken DB ----------------------------------

function install_kraken_db
{
    # download database
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    if [ ! -d "kraken_db" ]
    then
        echo " - Downloading kraken database"
        $GET $KRAKEN_DB $OUT $(basename $KRAKEN_DB)
        tar xf $(basename $KRAKEN_DB)
        [ "$?" != "0" ] && echo "Couldn't unpack kraken-db, aborting." && exit 1
        db_name="$(tar -tf $(basename $KRAKEN_DB) | head -1)"
        rm $(basename $KRAKEN_DB)
        mv $db_name kraken_db
    fi
    cd $wd || exit 1
}

# --------------------------------- HMMER -------------------------------------

function install_hmmsearch
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "hmmer-3.1b2.tar.gz" ] && rm "hmmer-3.1b2.tar.gz"
    link="http://eddylab.org/software/hmmer3/3.1b2/hmmer-3.1b2-linux-intel-x86_64.tar.gz"
    [[ "$(uname)" == "Darwin" ]] && link="http://eddylab.org/software/hmmer3/3.1b2/hmmer-3.1b2-macosx-intel.tar.gz"
    $GET $link $OUT "hmmer-3.1b2.tar.gz"
    tar xf "hmmer-3.1b2.tar.gz"
    [ "$?" != "0" ] && echo "Couldn't unpack hmmer, aborting." && exit 1
    rm "hmmer-3.1b2.tar.gz"
    path="$(pwd)/hmmer-3.1b2"
    source_path=$(basename ${link/.tar.gz/})
    cd $source_path || exit 1
    ./configure --prefix="$path"
    [ "$?" != "0" ] && echo "make hmmer failed, aborting." && exit 1
    make
    [ "$?" != "0" ] && echo "make hmmer failed, aborting." && exit 1
    make install
    [ "$?" != "0" ] && echo "make install hmmer failed, aborting." && exit 1
    cd ..
    rm -rf $source_path
    cd $wd || exit 1

    insert_into_database "hmmsearch" "$path/bin/hmmsearch"
}

# ---------------------------------- Krona ------------------------------------

function install_ktImportText
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    [ -e "KronaTools-2.6.1.tar" ] && rm "KronaTools-2.6.1.tar"
    $GET "https://github.com/marbl/Krona/releases/download/v2.6.1/KronaTools-2.6.1.tar" $OUT "KronaTools-2.6.1.tar"
    tar xf "KronaTools-2.6.1.tar"
    [ "$?" != "0" ] && echo "Couldn't unpack KronaTools, aborting." && exit 1
    rm "KronaTools-2.6.1.tar"
    cd "KronaTools-2.6.1" || exit 1
    ./install.pl --prefix $(pwd)
    [ "$?" != "0" ] && echo "install KronaTools failed, aborting." && exit 1
    ./updateTaxonomy.sh taxonomy/
    [ "$?" != "0" ] && echo "updateTaxonomy failed, aborting." && exit 1


    cat >ktImportText<<SCRIPT
#!/bin/bash

rel_path="\$(dirname \$(which \$0))"
cwd=\$(pwd)
cd \$rel_path
abs_path="\$(pwd)"
cd \$cwd

export PATH=\$abs_path:\$PATH
export PATH=\$abs_path/bin:\$PATH
export LD_LIBRARY_PATH=\$abs_path/lib:\$LD_LIBRARY_PATH

\$abs_path/bin/ktImportText \$@
SCRIPT
    chmod +x ktImportText

    path="$(pwd)/ktImportText"
    cd $wd || exit 1

    insert_into_database "ktImportText" "$path"
}

# ---------------------------------- vFam -------------------------------------

function install_vFam
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH || exit 1

    if [ ! -e "$(basename $VFAM)" ]
    then
        echo " - Downloading $(basename $VFAM)"
        $GET $VFAM $OUT "$(basename $VFAM)"
    fi

    if [ ! -e "$(basename $VFAM_ANNOT)" ]
    then
        echo " - Downloading $(basename $VFAM_ANNOT)"
        $GET $VFAM_ANNOT $OUT "$(basename $VFAM_ANNOT)"
        unzip "$(basename $VFAM_ANNOT)"
        [ "$?" != "0" ] && echo "Couldn't unzip vFAM annotations, aborting." && exit 1

    fi

    cd $wd || exit 1
}

# ---------------------- set paths to pipeline scripts ------------------------

function install_local
{
    cd $WD || exit 1
    sqlite3 $DATABASE "$TABLE_DEF"
    for SCRIPT in "kraken_to_krona.py" "vFam_HmmSearch_parse.py" "to_fasta.py"
    do
        if [[ $(sqlite3 $DATABASE "SELECT id FROM paths WHERE name = '$SCRIPT'") == "" ]]
        then
            sqlite3 $DATABASE "INSERT INTO paths (name, path) VALUES ('$SCRIPT', '$(pwd)/pipeline_scripts/$SCRIPT')"
        fi
    done
}

function build_metapprox
{
    wd=$(pwd)
    if [[ "$(g++ --version | head -1)" != "g++ (GCC) 5.2.0" ]]
    then
        if [ ! -e "$APP_PATH/gcc/bin/g++" ]
        then
            echo "bungis!" #install_gcc_5.2.0
        fi
        PATH=$APP_PATH/gcc/bin/:$PATH
    fi
    cd metlab/metapprox || exit 1
    ./make.sh
    [ "$?" != "0" ] && echo "make metapprox failed, aborting." && exit 1
    cd $wd || exit 1
}

[[ "$1" == "" ]] && set -- "$@" "all"

while (( $# > 0 ))
do
    [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]] && print_help && exit 0
    [[ "$1" == "FragGeneScan" ]] || [[ "$1" == "all" ]] && find_or_install "run_FragGeneScan.pl"
    [[ "$1" == "hmmsearch" ]] || [[ "$1" == "all" ]] && find_or_install "hmmsearch"
    [[ "$1" == "krona" ]] || [[ "$1" == "all" ]] && find_or_install "ktImportText"
    [[ "$1" == "kraken" ]] || [[ "$1" == "all" ]] && find_or_install "kraken"
    [[ "$1" == "kraken_db" ]] || [[ "$1" == "all" ]] && install_kraken_db
    [[ "$1" == "vfam" ]] || [[ "$1" == "all" ]] && install_vFam
    [[ "$1" == "spades" ]] || [[ "$1" == "all" ]] && find_or_install "spades"
    [[ "$1" == "samtools" ]] || [[ "$1" == "all" ]] && find_or_install "samtools"
    [[ "$1" == "bowtie2" ]] || [[ "$1" == "all" ]] && find_or_install "bowtie2"
    [[ "$1" == "prinseq-lite" ]] || [[ "$1" == "all" ]] && find_or_install "prinseq-lite"
    [[ "$1" == "local" ]] || [[ "$1" == "all" ]] && install_local
	[[ "$1" == "metapprox" ]] || [[ "$1" == "all" ]] && build_metapprox
    [[ "$1" == "gcc" ]] && install_gcc_5.2.0
    shift
done

exit 0
