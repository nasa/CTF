#!/bin/bash

CTF_HOME=$(dirname $(readlink $0):=.)
cd $CTF_HOME/tools/ctf_ui && npm install && npm start