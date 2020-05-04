
# `ark-broker`

This reposiory is a modification of [hbmqtt](https://hbmqtt.readthedocs.io/en/latest/index.html). It improves security on subcription or publication and provides an easy way to bridge the IOT broker with a [powered by Ark](https://ark.io/powered-by-ark) blockchain.

### Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Install

### Linux

```bash
$ bash <(curl -s https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/ark-broker/install-ark-broker.sh)
```

This installation script will manage dependencies and virtual environement needed to run `ark-broker`.

### Windows

```cmd
pip install git+https://github.com/Moustikitos/hbmqtt.git
```

## Configure / check

Broker configuration is done in a [`yaml`](https://yaml.org/) file, you can edit it with a simple text editor.

### linux

`yaml` file is stored into user configuration folder.

```bash
$ nano $HOME/.config/ark-broker.yaml
```

On unix system, `ark-broker` is set as a linux service. It responds to `journalctl` and `systemctl` commands:

```bash
# check broker log
$ sudo journalctl -u ark-broker -ef
# start|stop|restart broker
$ sudo systemctl (start|stop|restart) ark-broker
# activate|desactivate broker on server startup
$ sudo systemctl (enable|disable) ark-broker
# check broker service
$ sudo systemctl status ark-broker
```

Configure `ark-broker` unit file:

```bash
$ sudo nano /etc/systemd/system/ark-broker.service
...
$ sudo systemctl daemon-reload
$ sudo systemctl restart ark-broker
```

### Windows

Download `yaml` [configuration file](https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/ark-broker/ark-broker.yaml) and use `hbmqtt` command:

```cmd
hbmqtt -c full\path\to\ark-broker.yaml
```

## Bridge concept

### Sequence

[![](https://mermaid.ink/img/eyJjb2RlIjoic2VxdWVuY2VEaWFncmFtXG5QYXJ0aWNpcGFudCBOZXR3b3JrXG5QYXJ0aWNpcGFudCBCcm9rZXJcbiAgICBOb3RlIGxlZnQgb2YgTmV0d29yazogTmV0d29yayBjb3VsZCBiZTxici8-YSBibG9ja2NoYWluIG5vZGU8YnIvPm9yIHNvbWV0aGluZyBlbHNlXG4gICAgTmV0d29yay0-PkJyb2tlcjogZGF0YSBzZW50IG9uIGJyaWRnZWQgdG9waWNcbiAgICBhbHQgZGF0YSBzZWVtcyBnb29kIGVub3VnaFxuICAgICAgICBOb3RlIG92ZXIgQnJva2VyOiBkYXRhIGhhcyB0byBiZSBhPGJyLz52YWxpZCBqc29uIHN0cmluZzxici8-YW5kIGNvbnRhaW5zIGF0IDxici8-bGVhc3QgaWQgYW5kIGhlaWdodDxici8-b3IgdHlwZSBmaWVsZFxuICAgICAgICBCcm9rZXItPj5CbG9ja2NoYWluOiBhc2sgZWxlbWVudFxuICAgICAgICBhbHQgYmxvY2tjaGFpbiBzZW5kcyBlbGVtZW50XG4gICAgICAgICAgICBCbG9ja2NoYWluLT4-QnJva2VyOiBbdHggb3IgYmxvY2tdXG4gICAgICAgICAgICBCcm9rZXItPj5Ccm9rZXI6IG1vZHVsZS5mdW5jdGlvbihwbGcsIHR4IG9yIGJsb2NrKVxuICAgICAgICBlbHNlIGJsb2NrY2hhaW4gc2VuZHMgbm90aGluZ1xuICAgICAgICAgICAgQmxvY2tjaGFpbi0-PkJyb2tlcjogWyBdXG4gICAgICAgIGVuZFxuICAgIGVsc2UgZGF0YSBub3QgZ29vZCBlbm91Z2hcbiAgICAgICAgQnJva2VyLS0-PkJyb2tlcjogaWdub3JlXG4gICAgZW5kXG4gICAgQnJva2VyLT4-QnJva2VyOiBmb3J3YXJkIGRhdGEgdG8gc3Vic2NyaWJlcnMgKGlmIGFueSlcbiIsIm1lcm1haWQiOnsidGhlbWUiOiJmb3Jlc3QifSwidXBkYXRlRWRpdG9yIjpmYWxzZX0)](https://mermaid-js.github.io/mermaid-live-editor/#/edit/eyJjb2RlIjoic2VxdWVuY2VEaWFncmFtXG5QYXJ0aWNpcGFudCBOZXR3b3JrXG5QYXJ0aWNpcGFudCBCcm9rZXJcbiAgICBOb3RlIGxlZnQgb2YgTmV0d29yazogTmV0d29yayBjb3VsZCBiZTxici8-YSBibG9ja2NoYWluIG5vZGU8YnIvPm9yIHNvbWV0aGluZyBlbHNlXG4gICAgTmV0d29yay0-PkJyb2tlcjogZGF0YSBzZW50IG9uIGJyaWRnZWQgdG9waWNcbiAgICBhbHQgZGF0YSBzZWVtcyBnb29kIGVub3VnaFxuICAgICAgICBOb3RlIG92ZXIgQnJva2VyOiBkYXRhIGhhcyB0byBiZSBhPGJyLz52YWxpZCBqc29uIHN0cmluZzxici8-YW5kIGNvbnRhaW5zIGF0IDxici8-bGVhc3QgaWQgYW5kIGhlaWdodDxici8-b3IgdHlwZSBmaWVsZFxuICAgICAgICBCcm9rZXItPj5CbG9ja2NoYWluOiBhc2sgZWxlbWVudFxuICAgICAgICBhbHQgYmxvY2tjaGFpbiBzZW5kcyBlbGVtZW50XG4gICAgICAgICAgICBCbG9ja2NoYWluLT4-QnJva2VyOiBbdHggb3IgYmxvY2tdXG4gICAgICAgICAgICBCcm9rZXItPj5Ccm9rZXI6IG1vZHVsZS5mdW5jdGlvbihwbGcsIHR4IG9yIGJsb2NrKVxuICAgICAgICBlbHNlIGJsb2NrY2hhaW4gc2VuZHMgbm90aGluZ1xuICAgICAgICAgICAgQmxvY2tjaGFpbi0-PkJyb2tlcjogWyBdXG4gICAgICAgIGVuZFxuICAgIGVsc2UgZGF0YSBub3QgZ29vZCBlbm91Z2hcbiAgICAgICAgQnJva2VyLS0-PkJyb2tlcjogaWdub3JlXG4gICAgZW5kXG4gICAgQnJva2VyLT4-QnJva2VyOiBmb3J3YXJkIGRhdGEgdG8gc3Vic2NyaWJlcnMgKGlmIGFueSlcbiIsIm1lcm1haWQiOnsidGhlbWUiOiJmb3Jlc3QifSwidXBkYXRlRWRpdG9yIjpmYWxzZX0)

Bridging is done with `yaml` configuration:

```yaml
auth:
    ...
    plugins:
    # broker_bc: mandatory plugin to activate the bridge
    - broker_bc
...
broker-blockchain:
    # nethash: not mandatory if only GET requests are sent by broker
    nethash: 6e84d08bd299ed97c212c886c98a57e36545c8f5d645ca7eeae63a8bd62d8988
    # peers: mandatory, at least one valid peer is needed
    peers:
    - https://explorer.ark.io:8443
    # bridget-topics: mandatory
    #   topic: [module=None, function]
    #   if module is None: use plugin instance function
    #   else if module loaded on plugin initialization: use module.function
    bridged-topics:
        blockchain/event: [null, dummy]
    # endoints: not mandatory
    #   name: [method, path]
    endpoints:
        configuration: [GET, /api/node/configuration]
```

Bridged topics are listed in `bridged-topics` field of the `yaml` config. They are stored in an hbmqtt plugin as python dictionary, topic as keys, module-function pair as value. Modules are imported on plugin initialization as the broker starts. if a module is not found, `ImportError` exception is ignored and associated topic is removed.

Once a message is received on a bridged topic, even if there is no subscription, `module.function` is called with plugin itself and genuine data provided by plockchain (when module is `None`, the `function` is found in the plugin). Genuine data is either a transaction (`dict`) or a block (`dict`).

### Python function interface

```python
def function(plg, data):
    pass
```

#### plugin interface
```python
# hbmqtt context
plg.context
# `broker-blockchain` part of yaml conf as python dict
plg.config
# `endpoints` part of yaml conf as key list
plg.endpoints
# awaitable blockchain request
#   - endpoint: either a valid path ('/api/transactions') or a value from plg.endpoints
#   - data: dict or list for HTTP request with body
#   - qs: keyword argument to add a query string to the url
await plg.bc_request(endpoint, data={}, **qs)
```
