#!/bin/bash

VENVDIR="$HOME/.local/share/ark-broker/venv"
GITREPO="https://github.com/Moustikitos/hbmqtt.git"
GITREQS="https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/requirements.txt"
YAML="https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/ark-broker/ark-broker.yaml"

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
pip install -r $GITREQS
echo "done"

echo
echo configuring service
echo ===================

wget -q -O $HOME/.config/ark-broker.yaml $YAML

cat > $HOME/ark-broker.service << EOF
[Unit]
Description=Ark IOT broker
After=network.target

[Service]
User=$USER
WorkingDirectory=$VENVDIR
ExecStart=$VENVDIR/bin/hbmqtt -c $HOME/.config/ark-broker.yaml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

if [ -f /etc/systemd/system/ark-broker.service ]; then
    sudo systemctl stop ark-broker
fi

sudo mv $HOME/ark-broker.service /etc/systemd/system
sudo systemctl daemon-reload

echo "done"

echo
echo starting broker service
echo =======================

sudo systemctl start ark-broker

echo "done"
