#!/bin/bash

WD="$(pwd)"
APP_PATH="local_apps"
DATABASE="metlab.sqlite3"
KRAKEN_DB="https://ccb.jhu.edu/software/kraken/dl/minikraken.tgz"
VFAM="http://derisilab.ucsf.edu/software/vFam/vFam-A_2014.hmm"
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

    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH
    mkdir gcc-5.2.0
    cd gcc-5.2.0

    [ ! -e gcc-5.2.0.tar.bz2 ] && $GET ftp://ftp.fu-berlin.de/unix/languages/gcc/releases/gcc-5.2.0/gcc-5.2.0.tar.bz2 $OUT gcc-5.2.0.tar.bz2
    [ ! -e mpc-1.0.3.tar.gz ] && $GET ftp://ftp.gnu.org/gnu/mpc/mpc-1.0.3.tar.gz $OUT mpc-1.0.3.tar.gz
    [ ! -e mpfr-3.1.4.tar.bz2 ] && $GET http://www.mpfr.org/mpfr-current/mpfr-3.1.4.tar.bz2 $OUT mpfr-3.1.4.tar.bz2
    [ ! -e gmp-6.1.0.tar.bz2 ] && $GET https://gmplib.org/download/gmp/gmp-6.1.0.tar.bz2 $OUT gmp-6.1.0.tar.bz2
    [ ! -e isl-0.14.tar.bz2 ] && $GET ftp://gcc.gnu.org/pub/gcc/infrastructure/isl-0.14.tar.bz2 $OUT isl-0.14.tar.bz2

    LDFLAGS="-arch i386"
    tar xf gmp-6.1.0.tar.bz2
    cd gmp-6.1.0
    mkdir build
    cd build
    ../configure --prefix=${wd}/$APP_PATH/gcc --enable-cxx
    make -j4
    make install
    cd ../..

    tar xf mpfr-3.1.4.tar.bz2
    cd mpfr-3.1.4
    mkdir build
    cd build
    ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp=${wd}/$APP_PATH/gcc
    make -j4
    make install
    cd ../..

    tar xf mpc-1.0.3.tar.gz
    cd mpc-1.0.3
    mkdir build
    cd build
    ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp=${wd}/$APP_PATH/gcc --with-mpfr=${wd}/$APP_PATH/gcc
    make -j4
    make install
    cd ../..

    tar xf isl-0.14.tar.bz2
    cd isl-0.14
    mkdir build
    cd build
    ../configure --prefix=${wd}/$APP_PATH/gcc --with-gmp-prefix=${wd}/$APP_PATH/gcc
    make -j4
    make install
    cd ../..

    tar xf gcc-5.2.0.tar.bz2
    cd gcc-5.2.0
    mkdir build
    cd build
    ../configure --prefix=${wd}/$APP_PATH/gcc --enable-checking=release --with-gmp=${wd}/$APP_PATH/gcc --with-mpfr=${wd}/$APP_PATH/gcc --with-mpc=${wd}/$APP_PATH/gcc --enable-languages=c,c++,fortran --with-isl=${wd}/$APP_PATH/gcc
    make -j4
    make install

    cd $wd
}

# ------------------------------ FragGeneScan ---------------------------------

function install_run_FragGeneScan.pl
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "FragGeneScan.tar.gz" ] && rm "FragGeneScan.tar.gzz"
    $GET "https://sourceforge.net/projects/fraggenescan/files/FragGeneScan1.20.tar.gz/download" $OUT "FragGeneScan.tar.gz"

    tar xf "FragGeneScan.tar.gz"
    rm "FragGeneScan.tar.gz"
    cd FragGeneScan*/
    make clean
    if [[ "$(uname)" == "Darwin" ]]
    then
        ln -s /usr/include/sys/malloc.h
        mv util_lib.c util_lib.c.original
        sed "s/#include <malloc.h>/#include \"malloc.h\"/g" util_lib.c.original > util_lib.c
        mv hmm_lib.c hmm_lib.c.original
        sed "s/#include <malloc.h>/#include \"malloc.h\"/g" hmm_lib.c.original > hmm_lib.c.temp
        sed "s/<values.h>/<limits.h>/g" hmm_lib.c.temp > hmm_lib.c
        rm hmm_lib.c.temp
    fi
    make fgs
    path="$(pwd)/run_FragGeneScan.pl"
    cd $wd
    insert_into_database "run_FragGeneScan.pl" "$path"
}

# ------------------------------ Prinseq-lite ---------------------------------

function install_prinseq-lite
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "prinseq-lite-0.20.4.tar.gz" ] && rm "prinseq-lite-0.20.4.tar.gz"
    $GET "https://sourceforge.net/projects/prinseq/files/standalone/prinseq-lite-0.20.4.tar.gz/download" $OUT "prinseq-lite-0.20.4.tar.gz"
    tar xf "prinseq-lite-0.20.4.tar.gz"
    rm "prinseq-lite-0.20.4.tar.gz"
    chmod +x "prinseq-lite-0.20.4/prinseq-lite.pl"
    path="$(pwd)/prinseq-lite-0.20.4/prinseq-lite.pl"
    cd $wd
    insert_into_database "prinseq-lite.pl" "$path"
}

# --------------------------------- Bowtie2 -----------------------------------

function install_bowtie2
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    link="https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.7/bowtie2-2.2.7-linux-x86_64.zip/download"
    [[ "$(uname)" == "Darwin" ]] && link="https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.2.7/bowtie2-2.2.7-macos-x86_64.zip/download"

    [ -e "bowtie2-2.2.7.zip" ] && rm "bowtie2-2.2.7.zip"
    $GET $link $OUT "bowtie2-2.2.7.zip"
    unzip "bowtie2-2.2.7.zip"
    rm "bowtie2-2.2.7.zip"

    path="$(pwd)/bowtie2-2.2.7/bowtie2"
    build_path="$(pwd)/bowtie2-2.2.7/bowtie2-build"
    cd $wd
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
    rm "samtools-1.3.tar.bz2"
    cd samtools-1.3 || exit 1
    ./configure
    make

    path="$(pwd)/samtools"
    cd $wd || exit 1
    insert_into_database "samtools" "$path"
}

# -------------------------------- Spades.py ----------------------------------

function install_spades
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "SPAdes-3.6.2.tar.gz" ] && rm "SPAdes-3.6.2.tar.gz"
    link="http://spades.bioinf.spbau.ru/release3.6.2/SPAdes-3.6.2-Linux.tar.gz"
    [[ "$(uname)" == "Darwin" ]] && link="http://spades.bioinf.spbau.ru/release3.6.2/SPAdes-3.6.2-Darwin.tar.gz"
    $GET $link $OUT "SPAdes-3.6.2.tar.gz"
    tar xf "SPAdes-3.6.2.tar.gz"
    rm "SPAdes-3.6.2.tar.gz"

    path="$(pwd)/$(basename ${link/.tar.gz/})/bin/spades.py"
    cd $wd

    insert_into_database "spades.py" "$path"
}

# --------------------------------- Kraken ------------------------------------

function install_kraken
{
    if [[ "$(uname)" == "Darwin" ]]
    then
        [ ! -d "$APP_PATH/gcc" ] && install_gcc_5.2.0
        ORG_PATH=$PATH
        PATH=$(pwd)/gcc/bin:$PATH
    fi

    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "kraken-0.10.5-beta.tgz" ] && rm "kraken-0.10.5-beta.tgz"
    $GET "https://ccb.jhu.edu/software/kraken/dl/kraken-0.10.5-beta.tgz" $OUT "kraken-0.10.5-beta.tgz"
    tar xf "kraken-0.10.5-beta.tgz"
    rm "kraken-0.10.5-beta.tgz"
    path="$(pwd)/kraken"
    cd kraken-0.10.5-beta
    ./install_kraken.sh $path

    cd $wd
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
    cd $APP_PATH

    if [ ! -d "kraken_db" ]
    then
        echo " - Downloading kraken database"
        $GET $KRAKEN_DB $OUT $(basename $KRAKEN_DB)
        tar xf $(basename $KRAKEN_DB)
        db_name="$(tar -tf $(basename $KRAKEN_DB) | head -1)"
        rm $(basename $KRAKEN_DB)
        mv $db_name kraken_db
    fi
    cd $wd
}

# --------------------------------- HMMER -------------------------------------

function install_hmmsearch
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "hmmer-3.1b2.tar.gz" ] && rm "hmmer-3.1b2.tar.gz"
    link="http://eddylab.org/software/hmmer3/3.1b2/hmmer-3.1b2-linux-intel-x86_64.tar.gz"
    [[ "$(uname)" == "Darwin" ]] && link="http://eddylab.org/software/hmmer3/3.1b2/hmmer-3.1b2-macosx-intel.tar.gz"
    $GET $link $OUT "hmmer-3.1b2.tar.gz"
    tar xf "hmmer-3.1b2.tar.gz"
    rm "hmmer-3.1b2.tar.gz"
    path="$(pwd)/hmmer-3.1b2"
    source_path=$(basename ${link/.tar.gz/})
    cd $source_path
    ./configure --prefix="$path"
    make
    make install
    cd ..
    rm -rf $source_path
    cd $wd

    insert_into_database "hmmsearch" "$path/bin/hmmsearch"
}

# ---------------------------------- Krona ------------------------------------

function install_ktImportText
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    [ -e "KronaTools-2.6.1.tar" ] && rm "KronaTools-2.6.1.tar"
    $GET "https://github.com/marbl/Krona/releases/download/v2.6.1/KronaTools-2.6.1.tar" $OUT "KronaTools-2.6.1.tar"
    tar xf "KronaTools-2.6.1.tar"
    rm "KronaTools-2.6.1.tar"
    cd "KronaTools-2.6.1"
    ./install.pl --prefix $(pwd)
    ./updateTaxonomy.sh taxonomy/

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
    cd $wd

    insert_into_database "ktImportText" "$path"
}

# ---------------------------------- vFam -------------------------------------

function install_vFam
{
    wd="$(pwd)"
    mkdir -p $APP_PATH
    cd $APP_PATH

    if [ ! -e "$(basename $VFAM)" ]
    then
        echo " - Downloading $(basename $VFAM)"
        $GET $VFAM $OUT $(basename $VFAM)
    fi

    cd $wd
}

# ---------------------- set paths to pipeline scripts ------------------------

function install_local
{
    cd $WD
    sqlite3 $DATABASE "$TABLE_DEF"
    for SCRIPT in "kraken_to_krona.py" "vFam_HmmSearch_parse.py"
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
    cd metlab/metapprox
    ./make.sh
    cd $wd
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
