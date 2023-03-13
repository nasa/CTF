#!/bin/bash

# -------------------------------------------------------------------------------
# NOTE: This shell script must run from the "docs" directory.
# -------------------------------------------------------------------------------

SW_DIR=$(git rev-parse --show-toplevel)
SW_REPO=git@js-er-code.jsc.nasa.gov:aes/ctf.git

# -------------------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------------------

echo -e "\nProduct top-level directory: $SW_DIR\n"

echo -e "\n1. Go into the \"docs\" directory\n"
cd $SW_DIR/docs

echo -e "\n2. Make a \"release-artifacts\" directory\n"
mkdir -p ctf-release-artifacts

echo -e "\n3. Build Section 5 of the SDD\n"
./build_dox.sh pdf

echo -e "\n4. Move PDF files into \"release-artifacts\" directory\n"
mv *.pdf ctf-release-artifacts

echo -e "\n5. Copy PDF version of Word documents from \"documentation\" branch to \"release-artifact\"\n"
git clone -b documentation $SW_REPO && \
mv -f ctf/docs/masters/*.pdf ctf-release-artifacts

echo -e "\n6. Create a release-artifacts.tar file\n"
rm -f ctf-release-artifacts.tar && \
tar -zcvf ctf-release-artifacts.tgz ctf-release-artifacts

echo -e "\n7. Remove unwanted files/dirs\n"
rm -rf ctf-release-artifacts ctf

echo -e "\nFinished!\n"

# -------------------------------------------------------------------------------------

