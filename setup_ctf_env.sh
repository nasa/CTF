# the following packages need to be installed to compile pyenv
# sudo yum install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel -y

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
python -m pip install --upgrade pip
pip install -r ./requirements.txt

# if no intention to use CTF editor, the next line could be commented out
source setup_editor.sh

deactivate
