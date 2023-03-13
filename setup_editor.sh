rm -rf ~/.nvm

# nvm will be installed in home directory ~/.nvm.
# use the option PROFILE="/dev/null" to avoid auto-appending nvm path to .bashrc
#curl https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash
curl https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | PROFILE="/dev/null" bash

source ~/.nvm/nvm.sh

nvm --version

# nvm ls-remote : list available node versions to install
# install node v16.13.1 version
nvm install 16.13.1

# nvm list : list installed node versions
# nvm use v16.13.1: switch node version

