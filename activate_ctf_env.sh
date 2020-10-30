#!/bin/bash


if [[ -d $1 ]]; then
    export INSTALL_DIR=$1
elif [[ -f $1 ]]; then
    export INSTALL_DIR=$(dirname $1)
else
    export INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
fi

echo "INSTALL_DIR=$INSTALL_DIR"

export ANACONDA_VERSION='anaconda3'

platform='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
    platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='darwin'
else
    platform='windows'
fi

PREFIX=`grep 'prefix:' $INSTALL_DIR/pythonEnvironment*.yml | tail -n1 | awk '{print $2}' | sed 's/\/envs\/pythonEnv3//g'`

if [ ! -d "$PREFIX/envs/pythonEnv3" ]; then
    printf "The install location '%s' is not valid from yml file.\\n" "$PREFIX"
    PREFIX=$HOME/anaconda3
    printf "\\n"
    printf "%s install location:\\n" "$ANACONDA_VERSION"
    printf "%s\\n" "$PREFIX"
    printf "\\n"
    printf "  - Press ENTER to confirm %s install location\\n" "$ANACONDA_VERSION"
    printf "  - Press CTRL-C to abort the activation\\n"
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
fi

# See if conda is already setup on this system
if [ `which conda` ]; then
    PYTHONENV=`conda env list | grep pythonEnv3`
    if [ "$PYTHONENV" ]; then
        echo 'activate! 1'
	    if [[ "$platform" == "windows" ]]; then
		source $PREFIX/Scripts/activate pythonEnv3
	    else
		source $PREFIX/bin/activate pythonEnv3
	    fi
    else
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
        echo 'activate! 2'
	if [[ "$platform" == "windows" ]]; then
	    source $PREFIX/Scripts/activate pythonEnv3
	else
	    source $PREFIX/bin/activate pythonEnv3
	fi
    fi
# If not in system, check if it's installed already
elif [ -d "$PREFIX" ]; then
    # Install anaconda
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
    fi
    echo 'activate! 3'
    if [[ "$platform" == "windows" ]]; then
        source $PREFIX/Scripts/activate pythonEnv3
    else
        source $PREFIX/bin/activate pythonEnv3
    fi

# If not installed on the system, install it in the home directory
else
    echo 'Anaconda not installed'
fi
