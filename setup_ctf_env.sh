# ANSI color codes for terminal output
yellow='\033[0;33m'
reset='\e[0m'

# the following packages need to be installed to compile pyenv
# sudo yum install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel -y

# Introduce --clean option to remove previous setup dirs
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    echo "Removing ~/ctf_env, ~/.pyenv, and ~/.nvm..."
    rm -rf ~/ctf_env
    rm -rf ~/.pyenv
    rm -rf ~/.nvm
    echo "Done."
else
    if [ -e ~/.pyenv ] || [ -e ~/ctf_env ] || [ -e ~/.nvm ]; then
        # -e flag for color coded output
        echo -e "${yellow}Found existing ~/ctf_env, ~/.pyenv and/or ~/.nvm directories."
        echo -e "It is recommended to remove these before re-attempting ctf_env setup. ${reset}"
        read -p "Remove these directories before proceeding? [y/n]: " usr_clean_res
        if [ "$usr_clean_res" = "y" ]; then
            rm -rf ~/ctf_env
            rm -rf ~/.pyenv
            rm -rf ~/.nvm
        fi
    fi
fi

# Determine available package manager: yum or dnf
if command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
else
    echo "Error: Neither 'dnf' nor 'yum' is available on this system."
    return 1
fi

SQLITE_PACKAGE="sqlite-devel"
if ! $PKG_MANAGER list installed "$SQLITE_PACKAGE" >/dev/null 2>&1; then
    echo "Error: Package '$SQLITE_PACKAGE' is not installed."
    return 1
fi


# pyenv will be installed under  ~/.pyenv/
curl https://pyenv.run | bash

# if want to use pyenv for other shell sessions, put the following 3 lines in ~/.bashrc
#export PYENV_ROOT="$HOME/.pyenv"
#command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
#eval "$(pyenv init -)"

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

#python is installed under  ~/.pyenv/versions/
pyenv install -v 3.8.12
pyenv versions
# set python to 3.8.12 only for this shell session
pyenv shell 3.8.12
python -V

# create virtual environment for package management under home directory
python -m venv ~/ctf_env

source ~/ctf_env/bin/activate
# install required ctf packages
python -m pip install pip==22.3.1
pip install -r ./requirements.txt

# install required gateway-ctf packages
gw_ctf_reqs_file="../prj_plugins/requirements.txt"

# Check alternate path
if [ -s "./prj_plugins/requirements.txt" ]; then
    gw_ctf_reqs_file="./prj_plugins/requirements.txt"
fi

if  [ -s "$gw_ctf_reqs_file" ]; then
    echo "installing packages from $gw_ctf_reqs_file.."
    # read each non-empty line in the file
    while IFS= read -r line && [ -n "$line" ]; do
        # extract the package name and version 
        IFS='=' read -r package_name _ package_version <<< "$line"

        # check if we already have the package installed
        installed_version=$(pip show "$package_name" 2>/dev/null | awk '/Version:/ {print $2}')

        # install the package if we don't have it
        if [ -z "$installed_version" ]; then
            pip install "$line"
        elif [ "$installed_version" != "$package_version" ]; then
            echo -e "${yellow}$package_name is already installed, proceeding with installed version $installed_version" ${reset} >&2
        else
            echo "$package_name is already installed with version $installed_version"
        fi
    done < "$gw_ctf_reqs_file"
fi

# if no intention to use CTF editor, the next line could be commented out
source setup_editor.sh

python --version

deactivate
