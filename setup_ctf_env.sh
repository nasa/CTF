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

if [[ "$platform" == 'linux' ]] && [[ "$unamemstr" == 'i686' ]]; then
    printf "\\n"
    printf "32-bit Linux OS is not supported after CTF v1.5 ! \n\\n"
    return 1
fi

if [[ "$platform" == 'windows' ]] ; then
    printf "\\n"
    printf "Windows OS is not supported ! \n\\n"
    return 1
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
           $PREFIX/bin/conda env export > $INSTALL_DIR/pythonEnvironmentLinux3.yml
      fi
else
    if [ -d "$PREFIX" ]; then
       if [ ! -d "$PREFIX/envs/pythonEnv3" ]; then
          if [[ "$platform" == 'darwin' ]]; then
             $PREFIX/bin/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentMac3.yml
          elif [[ "$platform" == 'linux' ]]; then
             $PREFIX/bin/conda env create -n pythonEnv3 -f=$INSTALL_DIR/pythonEnvironmentLinux3.yml
          fi
       else
          echo 'Anaconda3 already installed.'
          echo 'execute "source pythonEnvInstall3.sh -u" to update.'
      fi
    else
      if [[ "$platform" == 'darwin' ]]; then
        curl https://repo.anaconda.com/archive/Anaconda3-2021.11-MacOSX-x86_64.sh -o Anaconda3-2021.11-MacOSX-x86_64.sh
        res=$?
        chmod 700 "Anaconda3-2021.11-MacOSX-x86_64.sh"
        ./Anaconda3-2021.11-MacOSX-x86_64.sh -b -p $PREFIX
         rm ./Anaconda3-2021.11-MacOSX-x86_64.sh
      elif  [[ "$platform" == 'linux' ]]; then
        curl https://repo.anaconda.com/archive/Anaconda3-2021.11-Linux-x86_64.sh -o Anaconda3-2021.11-Linux-x86_64.sh
        res=$?
        chmod 700 "Anaconda3-2021.11-Linux-x86_64.sh"
        ./Anaconda3-2021.11-Linux-x86_64.sh -b -p $PREFIX
        rm ./Anaconda3-2021.11-Linux-x86_64.sh
      fi

      if [[ "$res" == '0' ]]; then

          $PREFIX/bin/conda create --name pythonEnv3 python=3.8.12 -y

          # $PREFIX/bin/conda update -n base -c defaults conda -y

          source $PREFIX/bin/activate pythonEnv3

          #conda install --yes --file requirements.txt
          conda install -c anaconda bcrypt -y
          conda install -c anaconda cffi -y
          conda install -c anaconda cryptography -y
          conda install -c anaconda fabric -y
          conda install -c conda-forge ftputil -y
          conda install -c anaconda invoke -y
          conda install -c anaconda paramiko -y
          conda install -c anaconda psutil -y
          conda install -c anaconda pycparser -y
          conda install -c anaconda PyNaCl -y
          conda install -c anaconda six -y
          conda install -c conda-forge pyelftools -y
          conda install -c anaconda coverage -y
          conda install -c anaconda pytest'>=6.2.1' -y
          conda install -c anaconda pytest-cov -y
          conda install -c anaconda mock -y
          conda install -c anaconda pylint'=2.6.0' -y
          conda install -c conda-forge demjson -y


          if  [[ "$platform" == 'linux' ]]; then
              # April 2022: if do not specify nodejs version, conda installs nodejs v6.13.1, which is too old for CTF editor
              # April 2022: conda install nodejs v16.13.1, which is compatible. (v15.10.0 also works)
              conda install -c anaconda nodejs'>=14.8.0' -y
              conda install -c anaconda libxscrnsaver-devel-cos6-x86_64 -y
          else
              conda install -c conda-forge nodejs -y
          fi

          if [[ "$platform" == 'darwin' ]]; then
              conda env export > $INSTALL_DIR/pythonEnvironmentMac3.yml
          elif [[ "$platform" == 'linux' ]]; then
              conda env export > $INSTALL_DIR/pythonEnvironmentLinux3.yml
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

conda info
python --version
node -v

ln -sf $INSTALL_DIR/ctf $PREFIX/condabin/ctf
ln -sf $INSTALL_DIR/run_editor.sh $PREFIX/condabin/ctf_editor
