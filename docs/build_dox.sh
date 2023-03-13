#!/bin/bash

# NOTE: This shell script must run from the tool's "docs" directory.

INFILE=ctf_Doxyfile
OUTFILE=CTF_sdd_s5.pdf

function do_clean()
{
    rm -rf html latex
}

function do_html()
{
    if [ "$1" == "nasa" ]; then
        INFILE=nasa_ctf_Doxyfile
    fi

    do_clean && \
    mkdir -p latex && \
    cp dox_src/customs/*.tex latex && \
    doxygen dox_src/$INFILE && \
    cp *.pdf html

    # Note that the last command is important to get the document links
    # to work properly for HTML.
}

function do_pdf()
{
    if [ "$1" == "nasa" ]; then
        OUTFILE=CTF_sdd_s5-nasa.pdf
    fi

    do_html $1
    cd latex && \
    make && \
    mv refman.pdf ../$OUTFILE && \
    cd ..
}

if [ "$1" == "clean" ]; then
    do_clean
elif [ "$1" == "nasa_pdf" ]; then
    do_pdf nasa && rm -rf html
elif [ "$1" == "nasa_html" ]; then
    do_html nasa && rm -rf latex
elif [ "$1" == "nasa_all" ]; then
    do_pdf nasa
elif [ "$1" == "pdf" ]; then
    do_pdf && rm -rf html
elif [ "$1" == "html" ]; then
    do_html && rm -rf latex
elif [ "$1" == "all" ]; then
    do_pdf
else
    echo ""
    echo "Usage: ./build_dox.sh [clean|html|nasa_html|pdf|nasa_pdf|all|nasa_all]"
    echo ""
fi

