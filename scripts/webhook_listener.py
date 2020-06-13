# -*- coding: utf-8 -*-
# © THOORENS Bruno

import os
import sys
import subprocess
import multiprocessing

from uio import srv, loadJson, dumpJson
from optparse import OptionParser

HOME = os.path.normpath(os.environ.get("HOME", os.path.expanduser("~")))
parser = OptionParser(
    usage="usage: %prog [options]",
    version="%prog 1.0"
)
parser.add_option(
    "-p", "--port", action="store", dest="port", default=5000,
    type="int",
    help="port to use  [default: 5000]"
)
parser.add_option(
    "-l", "--log-level", action="store", dest="loglevel", default=20,
    type="int",
    help="set log level from 1 to 50 [default: 20]"
)

(options, args) = parser.parse_args()
app = srv.MicroJsonApp(
    host="0.0.0.0",
    port=options.port,
    loglevel=options.loglevel
)

if "win" not in sys.platform:

    import gunicorn.app.base

    class StandaloneApplication(gunicorn.app.base.BaseApplication):

        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            config = {
                key: value for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    def main():
        StandaloneApplication(app.__call__, {
            'bind': '%s:%s' % ('0.0.0.0', options.port),
            'workers': (multiprocessing.cpu_count() * 2) + 1,
        }).run()

else:
    def main():
        app.run()


def publish(broker, topic, message, qos=1, venv=None):
    """
    Send message on a topic using a specific broker. This function calls
    hbmqtt_pub command in a python subprocess where a virtualenv can be
    specified if needed (folder where `activate` script is localized).

    Args:
        broker (:class:`str`): valid borker url (ie mqtt://127.0.0.1)
        topic (:class:`str`): topic to use
        message (:class:`str`): message to send
        qos (:class:`int`): quality of service [default: 2]
        venv (:class:`str`): virtualenv folder [default: None]
    Returns:
        :class:`str`: subprocess stdout and stderr
    """
    # build hbmqtt_pub command line
    # see ~ https://hbmqtt.readthedocs.io/en/latest/references/hbmqtt_pub.html
    cmd = (
        "hbmqtt_pub --url %(broker)s "
        "-t %(topic)s -m '%(message)s' -q %(qos)s "
        "-i WebhookHandler"
    ) % {
        "broker": broker,
        "topic": topic,
        "message": message,
        "qos": qos
    }

    if venv is not None:
        # check if venv exists and add venv activation in command line
        activate = os.path.expanduser(os.path.join(venv, "activate"))
        if os.path.exists(activate):
            # `.` is used instead of `source`
            cmd = (". %s\n" % activate) + cmd

    # build a python subprocess and send command
    output, errors = subprocess.Popen(
        [],
        executable='/bin/bash',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate(cmd.encode('utf-8'))

    # return stdout and stderr as str
    return (
        output.decode("utf-8") if isinstance(output, bytes) else output,
        errors.decode("utf-8") if isinstance(errors, bytes) else errors
    )


@srv.bind("/webhook/forward", methods=["POST"])
def trigger_webhook(*args, **kwargs):
    data = kwargs["data"]
    webhook = loadJson(
        os.path.join(HOME, ".config", "%s.iot.wh" % data["id"])
    )
    if data["token"] == webhook.get("token", 32 * "?")[:32]:
        publish(
            webhook.get("listener", "mqtt://127.0.0.1"),
            webhook.get("topic", "WEBHOOK/resp"),
            data,
            qos=webhook.get("qos", 1),
            venv=webhook.get("venv", os.path.dirname(sys.executable))
        )


@srv.bind("/webhook/register", methods=["POST", "PUT"])
def register_webhook(*args, **kwargs):
    data = kwargs.get("data", {})
    if data and "127.0.0.1" in kwargs.get("headers", {}).get("host", "?"):
        dumpJson(data, os.path.join(HOME, ".config", "%s.iot.wh" % data["id"]))


@srv.bind("/webhook/delete", methods=["POST"])
def delete_webhook(*args, **kwargs):
    data = kwargs.get("data", {})
    pathfile = os.path.join(HOME, ".config", "%s.iot.wh" % data.get("id", "?"))
    if data["token"] == loadJson(pathfile).get("token", 32 * "?")[:32]:
        os.remove(pathfile)


if __name__ == "__main__":
    main()
