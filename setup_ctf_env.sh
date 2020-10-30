#!/bin/bash
#replaced \r with \n
updateValue=0
ymlValue=0

while getopts "uy" option
do
 case "${option}"
 in
 y)         ymlValue=1;;
 u)         updateValue=1;;

esac
done

PREFIX=$HOME/anaconda3

export INSTALL_DIR=`pwd`

export ANACONDA_VERSION='anaconda3'

platform='unknown'
unamestr=`uname`
unamemstr=`uname -m`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
   platform='darwin'
else
   platform='windows'
fi
printf "\\n"
printf "%s will now be installed into this location:\\n" "$ANACONDA_VERSION"
printf "%s\\n" "$PREFIX"
printf "\\n"
printf "  - Press ENTER to confirm the location\\n"
printf "  - Press CTRL-C to abort the installation\\n"
printf "  - Or specify a different location below\\n"
printf "\\n"
printf "[%s] >>> " "$PREFIX"
read -r user_prefix
if [ "$user_prefix" != "" ]; then
    case "$user_prefix" in
        *\ * )
            printf "ERROR: Cannot install into directories with spaces\\n" >&2
            exit 1
            ;;
        *)
            eval PREFIX="$user_prefix"
            ;;
    esac
fi


if [ "$updateValue" -eq 1 ]; then
  rm -rf $PREFIX
fi

if [ "$ymlValue" -eq 1 ]; then
echo 'Generating yml file'
if [[ "$platform" == 'darwin' ]]; then
 $PREFIX/bin/conda env export > $INSTALL_DIR/pythonEnvironmentMac3.yml
elif [[ "$platform" == 'linux' ]]; then
 if [[ "$unamemstr" == 'i686' ]]; then
 $PREFIX/bin/conda env export > $INSTALL_DIR/pythonEnvironmentLinuxX86.yml
else
 $PREFIX/bin/conda env export > $INSTALL_DIR/pythonEnvironmentLinux3.yml
fi
else
 $PREFIX/Scripts/conda env export > $INSTALL_DIR/pythonEnvironmentWindows3.yml
fi
else
if [ -d "$PREFIX" ]; then
if [ ! -d "$PREFIX/envs/pythonEnv3" ]; then
if [[ "$platform" == 'darwin' ]]; then
 $PREFIX/bin/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentMac3.yml
elif [[ "$platform" == 'linux' ]]; then
 if [[ "$unamemstr" == 'i686' ]]; then
 $PREFIX/bin/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentLinuxX86.yml
else
 $PREFIX/bin/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentLinux3.yml
fi
else
 $PREFIX/Scripts/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentWindows3.yml
fi
else
echo 'Anaconda3 already installed.'
echo 'execute "source pythonEnvInstall3.sh -u" to update.'
fi
else
if [[ "$platform" == 'darwin' ]]; then
 curl https://repo.anaconda.com/archive/Anaconda3-2018.12-MacOSX-x86_64.sh -o Anaconda3-2018.12-MacOSX-x86_64.sh
 res=$?
 chmod 700 "Anaconda3-2018.12-MacOSX-x86_64.sh"
 ./Anaconda3-2018.12-MacOSX-x86_64.sh -b -p $PREFIX
 rm ./Anaconda3-2018.12-MacOSX-x86_64.sh
elif  [[ "$platform" == 'linux' ]]; then
 if [[ "$unamemstr" == 'i686' ]]; then
 curl https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86.sh -o Anaconda3-2018.12-Linux-x86.sh
 res=$?
 chmod 700 "Anaconda3-2018.12-Linux-x86.sh"
 ./Anaconda3-2018.12-Linux-x86.sh -b -p $PREFIX
 rm ./Anaconda3-2018.12-Linux-x86.sh
else
 curl https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86_64.sh -o Anaconda3-2018.12-Linux-x86_64.sh
 res=$?
 chmod 700 "Anaconda3-2018.12-Linux-x86_64.sh"
 ./Anaconda3-2018.12-Linux-x86_64.sh -b -p $PREFIX
 rm ./Anaconda3-2018.12-Linux-x86_64.sh
fi
else
curl https://repo.anaconda.com/archive/Anaconda3-2018.12-Windows-x86_64.exe -o Anaconda3-2018.12-Windows-x86_64.exe
res=$?
 chmod 700 "Anaconda3-2018.12-Windows-x86_64.exe"
 ./Anaconda3-2018.12-Windows-x86_64.exe /S /D $PREFIX
 rm ./Anaconda3-2018.12-Windows-x86_64.exe
fi
if [[ "$res" == '0' ]]; then

$PREFIX/bin/conda create --name pythonEnv3 -y

$PREFIX/bin/conda update -n base -c defaults conda -y

source $PREFIX/bin/activate pythonEnv3

#conda install --yes --file requirements.txt
conda install -c anaconda bcrypt -y
conda install -c anaconda cffi -y
conda install -c anaconda cryptography -y
conda install -c anaconda fabric -y
conda install -c conda-forge ftputil -y
conda install -c conda-forge invoke -y
conda install -c anaconda paramiko -y
conda install -c anaconda psutil -y
conda install -c conda-forge pycparser -y
conda install -c conda-forge PyNaCl -y
conda install -c anaconda six -y
conda install -c conda-forge pyelftools -y


if  [[ "$platform" == 'linux' ]]; then
conda install -c anaconda nodejs -y
if [[ "$unamemstr" == 'i686' ]]; then
conda install -c anaconda libxscrnsaver-cos6-i686 -y
conda install -c anaconda nodejs -y
else
conda install -c anaconda libxscrnsaver-devel-cos6-x86_64 -y
conda install -c conda-forge nodejs -y
fi
else
conda install -c conda-forge nodejs -y
fi

if [[ "$platform" == 'darwin' ]]; then
conda env export > $INSTALL_DIR/pythonEnvironmentMac3.yml
elif [[ "$platform" == 'linux' ]]; then
 if [[ "$unamemstr" == 'i686' ]]; then
conda env export > $INSTALL_DIR/pythonEnvironmentLinuxX86.yml
else
conda env export > $INSTALL_DIR/pythonEnvironmentLinux3.yml
fi
else
 $PREFIX/Scripts/conda env export > $INSTALL_DIR/pythonEnvironmentWindows3.yml
fi

# See if python2 is already setup on this system
if which python2; then
echo "python2 exist"
elif which python2.7; then
export PYTHON_LOCATION=`which python2.7`
ln -sf "$PYTHON_LOCATION" $PREFIX/envs/pythonEnv3/bin/python2
else
echo "python2.7 does not exist required for npm install"
fi

cd $INSTALL_DIR
else
echo 'Download of Anaconda install script failed:'
echo $res
fi
fi
fi

if which npm; then
  cd tools/ctf_ui
  npm install
  cd $INSTALL_DIR
else
  echo "npm not installed"
fi

ln -sf $INSTALL_DIR/ctf $PREFIX/condabin/ctf
ln -sf $INSTALL_DIR/run_editor.sh $PREFIX/condabin/ctf_editor
