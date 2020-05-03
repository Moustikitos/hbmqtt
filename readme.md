
# `ark-broker`

This reposiory is a modification of [hbmqtt](https://hbmqtt.readthedocs.io/en/latest/index.html). It ensures security on subcription or publication and it provides an easy way to bridge the IOT broker with a [powered by Ark](https://ark.io/powered-by-ark) blockchain.

### Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Install

```bash
$ bash <(curl -s https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/ark-broker/install-ark-broker.sh)
```

Installation script will manage dependencies virtual environement needed to install and run `ark-broker`.

## Configure / check

Broker configuration is done in a `yaml` file.

```bash
$ nano $HOME/.config/ark-broker.yaml
```

`ark-broker` is set as a linux service. It responds to `journalctl` and `systemctl` commands.

```bash
# check broker log
$ sudo journalctl -u ark-broker -ef
# restart broker
$ sudo systemctl restart ark-broker
# check broker service
$ sudo systemctl status ark-broker
# activate broker on server startup
$ sudo systemctl enable ark-broker
```

## Bridge

### Sequence

[![](https://mermaid.ink/img/eyJjb2RlIjoic2VxdWVuY2VEaWFncmFtXG4gICAgTmV0d29yay0-PkJyb2tlcjogZGF0YSBzZW50IG9uIGJyaWRnZWQgdG9waWNcbiAgICBhbHQgZGF0YSBzZWVtcyBnb29kIGVub3VnaFxuICAgICAgICBOb3RlIG92ZXIgQnJva2VyOiBkYXRhIGhhcyB0byBiZSBhPGJyLz52YWxpZCBqc29uIHN0cmluZzxici8-YW5kIGNvbnRhaW5zIGlkLDxici8-aGVpZ2h0IG9yIHR5cGVcbiAgICAgICAgQnJva2VyLT4-QmxvY2tjaGFpbjogYXNrIGVsZW1lbnRcbiAgICAgICAgYWx0IGJsb2NrY2hhaW4gc2VuZHMgZWxlbWVudFxuICAgICAgICAgICAgQmxvY2tjaGFpbi0-PkJyb2tlcjogW3R4fGJsb2NrXVxuICAgICAgICAgICAgQnJva2VyLT4-QnJva2VyOiBleGVjdXRlIGNvZGUocGxnLGRhdGFbMF0pXG4gICAgICAgIGVsc2UgYmxvY2tjaGFpbiBzZW5kcyBub3RoaW5nXG4gICAgICAgICAgICBCbG9ja2NoYWluLT4-QnJva2VyOiBbXVxuICAgICAgICBlbmRcbiAgICBlbHNlIGRhdGEgbm90IGdvb2QgZW5vdWdoXG4gICAgICAgIEJyb2tlci0tPj5Ccm9rZXI6IGlnbm9yZVxuICAgIGVuZFxuICAgIEJyb2tlci0-PkJyb2tlcjogZm9yd2FyZCBkYXRhIHRvIHN1YnNjcmliZXJzXG4iLCJtZXJtYWlkIjp7InRoZW1lIjoiZm9yZXN0In0sInVwZGF0ZUVkaXRvciI6ZmFsc2V9)](https://mermaid-js.github.io/mermaid-live-editor/#/edit/eyJjb2RlIjoic2VxdWVuY2VEaWFncmFtXG4gICAgTmV0d29yay0-PkJyb2tlcjogZGF0YSBzZW50IG9uIGJyaWRnZWQgdG9waWNcbiAgICBhbHQgZGF0YSBzZWVtcyBnb29kIGVub3VnaFxuICAgICAgICBOb3RlIG92ZXIgQnJva2VyOiBkYXRhIGhhcyB0byBiZSBhPGJyLz52YWxpZCBqc29uIHN0cmluZzxici8-YW5kIGNvbnRhaW5zIGlkLDxici8-aGVpZ2h0IG9yIHR5cGVcbiAgICAgICAgQnJva2VyLT4-QmxvY2tjaGFpbjogYXNrIGVsZW1lbnRcbiAgICAgICAgYWx0IGJsb2NrY2hhaW4gc2VuZHMgZWxlbWVudFxuICAgICAgICAgICAgQmxvY2tjaGFpbi0-PkJyb2tlcjogW3R4fGJsb2NrXVxuICAgICAgICAgICAgQnJva2VyLT4-QnJva2VyOiBleGVjdXRlIGNvZGUocGxnLGRhdGFbMF0pXG4gICAgICAgIGVsc2UgYmxvY2tjaGFpbiBzZW5kcyBub3RoaW5nXG4gICAgICAgICAgICBCbG9ja2NoYWluLT4-QnJva2VyOiBbXVxuICAgICAgICBlbmRcbiAgICBlbHNlIGRhdGEgbm90IGdvb2QgZW5vdWdoXG4gICAgICAgIEJyb2tlci0tPj5Ccm9rZXI6IGlnbm9yZVxuICAgIGVuZFxuICAgIEJyb2tlci0-PkJyb2tlcjogZm9yd2FyZCBkYXRhIHRvIHN1YnNjcmliZXJzXG4iLCJtZXJtYWlkIjp7InRoZW1lIjoiZm9yZXN0In0sInVwZGF0ZUVkaXRvciI6ZmFsc2V9)