#!/bin/bash

CTF_HOME=$(dirname $(readlink $0):=.)

# active pyenv for python
source activate_ctf_env.sh

# activate node for Editor
source ~/.nvm/nvm.sh
node --version

cd $CTF_HOME/tools/ctf_ui && npm install && npm start