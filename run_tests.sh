#!/bin/bash

# This script runs various CTF tests: 
#    - Static Code Analysis (SCA) 
#    - Unit Tests & Coverage (UTC)
#    - Functional Tests (FT)
#    - Verification & Validation Tests (VV)

# -----------------------------------------------------------------------------------

function usage()
{
    echo ""
    echo "USAGE: ./run_tests <arg1>"
    echo ""
    echo "       where arg1 can be [sca|utc|ft|vv]"
    echo "                          sca = static code analysis"
    echo "                          utc = unit tests & code coverage"
    echo "                          ft  = functional tests"
    echo "                          vv  = requirement verification tests"
    echo ""
}

# -----------------------------------------------------------------------------------
#  Main
# -----------------------------------------------------------------------------------

if [ "$#" -ne 1 ]; then
    usage
    exit
fi

# Make a directory to store various test output
OUT_DIR="runtests_output"
mkdir -p $OUT_DIR

if [ "$1" == "sca" ]; then
    # Make a sub-dir for SCA output
    OUT_SUBDIR="$OUT_DIR/sca"
    mkdir -p $OUT_SUBDIR
    # Run static code analysis on the CTF code base
    cd .. && pylint --rcfile=ctf/.pylintrc ctf | tee ctf/$OUT_SUBDIR/ctf_sca.log

elif [ "$1" == "utc" ]; then
    # Make a sub-dir for UTC output
    OUT_SUBDIR="$OUT_DIR/utc"
    mkdir -p $OUT_SUBDIR
    # Run the unit test suite and code coverage 
    pytest -v ./unit_tests/ \
           -W ignore::pytest.PytestCollectionWarning \
           --cov-config=.ctf_coveragerc \
           --cov=plugins --cov=lib \
           --cov-report=html | tee $OUT_SUBDIR/ctf_ut_results.log
    # Convert coverage report in HTML to PDF
    wkhtmltopdf UnitTests_Coverage/index.html $OUT_SUBDIR/ctf_ut_coverage.pdf
    # Move the generated output to UTC sub-dir
    mv -f *.log temp_log mock_sp0_config_cfs-out-file $OUT_SUBDIR
    mv -f UnitTests_Coverage plugin_info_output temp_log_dir local $OUT_SUBDIR
    mv -f CTF_Results/Run* $OUT_SUBDIR/ut_run
    # Remove un-needed files/dirs
    rm -rf CTF_Results

elif [ "$1" == "ft" ]; then
    # Make a sub-dir for FT output
    OUT_SUBDIR="$OUT_DIR/ft"
    mkdir -p $OUT_SUBDIR
    # Run functional tests written in CTF scripts
    ./ctf --config_file configs/default_config.ini \
          functional_tests/plugin_tests \
          functional_tests/cfe_6_7_tests
    # Move the generated output to FT sub-dir
    mv CTF_Results/Run_* $OUT_SUBDIR/ft_run
    # Remove un-needed files/dirs
    rm -rf CTF_Results

elif [ "$1" == "vv" ]; then
    # Make a sub-dir for VV output
    OUT_SUBDIR="$OUT_DIR/vv"
    mkdir -p $OUT_SUBDIR
    # Run requirement verification tests writtent in CTF scripts - set 1
    ./ctf --config_file vv_tests/configs/ctf_vv_config.ini \
          vv_tests/scripts/CTF_VV_start.json \
          vv_tests/scripts/ci_pass &&
    # Move the generated output to VV sub-dir
    mv -f CTF_Results/Run_* $OUT_SUBDIR/vv_run_ci  &&
    # Run requirement verification tests written in CTF scripts - set 2
    ./ctf --config_file vv_tests/configs/ci_vv_lx1_config.ini \
          vv_tests/scripts/CTF_VV_14.json \
          vv_tests/scripts/CTF_VV_15.json \
          vv_tests/scripts/CTF_VV_19.json &&
    # Move the generated output to VV sub-dir
    mv -f CTF_Results/Run_* $OUT_SUBDIR/vv_run_tc
    # Remove un-needed files/dirs
    rm -rf CTF_Results
else
    echo "Bad command line argument - $1"
    exit
fi

# -----------------------------------------------------------------------------------

