#!/bin/bash

VENVDIR="$HOME/.local/share/ark-broker/venv"
GITREPO="https://github.com/Moustikitos/hbmqtt.git"

clear

if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "branch selected = $B"

echo
echo installing system dependencies
echo ==============================
sudo apt-get -qq install python3 python3-dev python3-setuptools python3-pip
sudo apt-get -qq install pypy3
sudo apt-get -qq install virtualenv
echo "done"

echo
echo creating virtual environment
echo ============================

if [ -d $VENVDIR ]; then
    read -p "remove previous virtual environement ? [y/N]> " r
    case $r in
    y) rm -rf $VENVDIR;;
    Y) rm -rf $VENVDIR;;
    *) echo -e "previous virtual environement keeped";;
    esac
fi

if [ ! -d $VENVDIR ]; then
    echo -e "select environment:\n  1) python3\n  2) pypy3"
    read -p "[default:python3]> " n
    case $n in
    1) TARGET="$(which python3)";;
    2) TARGET="$(which pypy3)";;
    *) TARGET="$(which python3)";;
    esac
    mkdir $VENVDIR -p
    virtualenv -p $TARGET $VENVDIR -q
fi

echo "done"

echo
echo installing ark-broker
echo =====================
. $VENVDIR/bin/activate
pip install git+$GITREPO --force
echo "done"

echo
echo configuring service
echo ===================

cat > $HOME/ark-broker.service << EOF
[Unit]
Description=Ark IOT broker
After=network.target

[Service]
User=$USER
WorkingDirectory=$VENVDIR/lib/python3.7/site-packages/scripts
ExecStart=$(which python) broker_script.py -c $HOME/.config/ark-broker.yaml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo mv $HOME/ark-broker.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl start ark-broker
