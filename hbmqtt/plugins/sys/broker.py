# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
from datetime import datetime
from hbmqtt.mqtt.packet import PUBLISH
from hbmqtt.codecs import int_to_bytes_str

import ssl
import sys
import json
import shlex
import random
import asyncio
import traceback
import importlib
import urllib.parse as urlparse
from collections import deque
from urllib.request import Request, urlopen
from hbmqtt.client import MQTTClient, ConnectException


DOLLAR_SYS_ROOT = '$SYS/broker/'
STAT_BYTES_SENT = 'bytes_sent'
STAT_BYTES_RECEIVED = 'bytes_received'
STAT_MSG_SENT = 'messages_sent'
STAT_MSG_RECEIVED = 'messages_received'
STAT_PUBLISH_SENT = 'publish_sent'
STAT_PUBLISH_RECEIVED = 'publish_received'
STAT_START_TIME = 'start_time'
STAT_CLIENTS_MAXIMUM = 'clients_maximum'
STAT_CLIENTS_CONNECTED = 'clients_connected'
STAT_CLIENTS_DISCONNECTED = 'clients_disconnected'


# async def psql(sql):
#     cmd = shlex.split('psql -qtAX -d ark_mainnet -c "%s"' % sql)
#     proc = await asyncio.create_subprocess_shell(
#         cmd,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE
#     )
#     stdout, stderr = await proc.communicate()
#     if proc.returncode == 0:
#         return stdout.decode().strip()
#     else:
#         return None


async def publish(broker, topic, message, qos=1):
    message = \
        message if isinstance(message, bytes) else \
        message.encode("utf-8")
    try:
        client = MQTTClient()
        await client.connect(broker)
        await client.publish(topic, message, qos=qos)
        await client.disconnect()
    except ConnectException as ce:
        return "%r\n%s" % (ce, traceback.format_exc(ce))
    else:
        return "blockchain response relayed : %r" % message


class BrokerBlockchainPlugin:

    endpoints = property(lambda cls: cls._endpoints.keys(), None, None, "")
    topics = property(
        lambda cls: cls._blockchain.get('bridged-topics', {}).keys(),
        None, None, ""
    )
    config = property(lambda cls: cls._blockchain, None, None, "")

    def __init__(self, context):
        self.context = context
        self._blockchain = self.context.config.get("broker-blockchain", {})
        self._endpoints = self._blockchain.get("endpoints", {})
        self._ndpt_headers = {
            "Content-type": "application/json",
            "nethash": self._blockchain.get("nethash", "")
        }
        # import python-bindings:
        for t, (m, f) in list(
            self._blockchain.get('bridged-topics', {}).items()
        ):
            if m is not None and m not in sys.modules:
                try:
                    importlib.import_module(m)
                except Exception as error:
                    self.context.logger.debug(
                        "%s python binding not loaded (%r)",
                        m, error
                    )
                    self._blockchain['bridged-topics'].pop(t)

    # send http request to blockchain
    async def bc_request(self, endpoint, method="GET", data={}, **qs):
        method, path = self._endpoints.get(endpoint, [method, endpoint])
        if method in ["POST", "PUT"]:
            if isinstance(data, (dict, list, tuple)):
                data = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                # Assume data is a valid json string
                data = data.encode("utf-8")
        else:
            data = None
        try:
            req = Request(
                urlparse.urlparse(
                    random.choice(self._blockchain["peers"])
                )._replace(
                    path=path,
                    query="&".join(["%s=%s" % (k, v) for k, v in qs.items()])
                ).geturl(),
                data, self._ndpt_headers
            )
            req.add_header("User-agent", "Mozilla/5.0")
            req.get_method = lambda: method
        except Exception as error:
            self.context.logger.error("%r\n%s", error, traceback.format_exc())
        else:
            self.context.logger.debug(
                "blockchain request prepared: %s %s %s",
                method, req.get_full_url(), data
            )
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                result = json.loads(
                    urlopen(req, context=ctx, timeout=5).read()
                )
            except Exception as error:
                return {"status": 500, "error": "http request %s to %s failed" % (method, path)}
                self.context.logger.error(
                    "%r\n%s", error, traceback.format_exc()
                )
            else:
                self.context.logger.debug("blockchain response: %s", result)
                return result
        return {"status": 404, "error": "nothing happen"}

    async def _genuinize(self, data):
        truth = False
        try:
            data = json.loads(data)
            for key, path in zip(
                ["type", "height"],
                ["/api/transactions", "/api/blocks"]
            ):
                if key in data:
                    id_ = data.get("id", False)
                    qs = \
                        {"id": id_, key: data[key]} if id_ else \
                        {key: data[key]}
                    data = (await self.bc_request(path, **qs)).get("data", [])
                    truth = any(data)
                    break
        except Exception as error:
            self.context.logger.error(
                "%r\n%s", error, traceback.format_exc()
            )

        if not truth:
            return False
        else:
            self.context.logger.debug("genuined data: %s", data)
            return data[0] if isinstance(data, list) else data

    def _is_bridged_topic(self, topic):
        return any([
            topic.startswith(t) for t in self._blockchain.get(
                'bridged-topics', []
            )
        ])

    async def on_broker_message_received(self, *args, **kwargs):
        message = kwargs["message"]
        topic = message.topic

        if not self._is_bridged_topic(topic):
            return False

        data = await self._genuinize(message.data)
        if not data:
            return False

        modname, funcname = self._blockchain.get("bridged-topics", {}).get(
            topic, [None, None]
        )
        if modname is not None:
            func = getattr(sys.modules[modname], funcname, None)
        elif funcname is not None:
            func = getattr(self, funcname, None)
        else:
            func = None

        if func is not None:
            self.context.logger.debug(
                "broker plugin function '%s' triggered with data=%s",
                func.__name__, data
            )
            return func(self, data)
        else:
            return None

    @staticmethod
    def dummy(cls, data):
        cls.context.logger.info("dummy function says: %s", data)
        return True


class BlockchainApiPlugin(BrokerBlockchainPlugin):

    def __init__(self, context):
        BrokerBlockchainPlugin.__init__(self, context)
        self.broker_port = self.context.config.get("listeners", {})\
            .get("default", {})\
            .get("bind", "127.0.0.1:1884")\
            .split(":")[-1]

    async def on_broker_message_received(self, *args, **kwargs):
        message = kwargs["message"]
        topic = message.topic.split("/")

        method = topic[0]
        if method not in ["&GET", "&POST", "&PUT", "&DELETE"]:
            self.context.logger.debug("api plugin not triggered")
            return False

        method = method[1:]
        path = "/".join(topic[1:])

        try:
            if method in ["POST", "PUT", "DELETE"]:
                resp = await self.bc_request(path, method, message.data)
            else:
                try:
                    data = json.loads(message.data)
                except Exception:
                    data = {}
                resp = await self.bc_request(path, method, {}, **data)
        except Exception as error:
            msg = "%r\n%s", error, traceback.format_exc()
            resp = {"status": 500, "error": msg}
            self.context.logger.error(msg)
            return None

        # create a message to send to topic
        self.context.logger.info(
            await publish(
                "mqtt://127.0.0.1:%s" % self.broker_port,
                "&RESP/" + kwargs.get('client_id'),
                json.dumps(resp),
                qos=0x02
            )
        )
        return True


# class BlockchainRelayPlugin(BlockchainApiPlugin):

#     def _is_relay_topic(self, topic):
#         return any([
#             topic.startswith(t) for t in self._blockchain.get(
#                 'relay-topics', []
#             )
#         ])

#     async def on_broker_message_received(self, *args, **kwargs):
#         if not self._is_relay_topic(kwargs["message"].topic):
#             return False
#         else:
#             kwargs["message"].topic = "&POST/api/transactions"
#             return await BlockchainApiPlugin.on_broker_message_received(
#                 self, *args, **kwargs
#             )


class BrokerSysPlugin:
    def __init__(self, context):
        self.context = context
        # Broker statistics initialization
        self._stats = dict()
        self._sys_handle = None

    def _clear_stats(self):
        """
        Initializes broker statistics data structures
        """
        for stat in (STAT_BYTES_RECEIVED,
                     STAT_BYTES_SENT,
                     STAT_MSG_RECEIVED,
                     STAT_MSG_SENT,
                     STAT_CLIENTS_MAXIMUM,
                     STAT_CLIENTS_CONNECTED,
                     STAT_CLIENTS_DISCONNECTED,
                     STAT_PUBLISH_RECEIVED,
                     STAT_PUBLISH_SENT):
            self._stats[stat] = 0

    @asyncio.coroutine
    def _broadcast_sys_topic(self, topic_basename, data):
        return (yield from self.context.broadcast_message(topic_basename, data))

    def schedule_broadcast_sys_topic(self, topic_basename, data):
        return asyncio.ensure_future(
            self._broadcast_sys_topic(DOLLAR_SYS_ROOT + topic_basename, data),
            loop=self.context.loop
        )

    @asyncio.coroutine
    def on_broker_pre_start(self, *args, **kwargs):
        self._clear_stats()

    @asyncio.coroutine
    def on_broker_post_start(self, *args, **kwargs):
        self._stats[STAT_START_TIME] = datetime.now()
        from hbmqtt.version import get_version
        version = 'HBMQTT version ' + get_version()
        self.context.retain_message(DOLLAR_SYS_ROOT + 'version', version.encode())

        # Start $SYS topics management
        try:
            sys_interval = int(self.context.config.get('sys_interval', 0))
            if sys_interval > 0:
                self.context.logger.debug("Setup $SYS broadcasting every %d secondes" % sys_interval)
                self.sys_handle = self.context.loop.call_later(sys_interval, self.broadcast_dollar_sys_topics)
            else:
                self.context.logger.debug("$SYS disabled")
        except KeyError:
            pass
            # 'sys_internal' config parameter not found

    @asyncio.coroutine
    def on_broker_pre_stop(self, *args, **kwargs):
        # Stop $SYS topics broadcasting
        if self.sys_handle:
            self.sys_handle.cancel()

    def broadcast_dollar_sys_topics(self):
        """
        Broadcast dynamic $SYS topics updates and reschedule next execution depending on 'sys_interval' config
        parameter.
        """

        # Update stats
        uptime = datetime.now() - self._stats[STAT_START_TIME]
        client_connected = self._stats[STAT_CLIENTS_CONNECTED]
        client_disconnected = self._stats[STAT_CLIENTS_DISCONNECTED]
        inflight_in = 0
        inflight_out = 0
        messages_stored = 0
        for session in self.context.sessions:
            inflight_in += session.inflight_in_count
            inflight_out += session.inflight_out_count
            messages_stored += session.retained_messages_count
        messages_stored += len(self.context.retained_messages)
        subscriptions_count = 0
        for topic in self.context.subscriptions:
            subscriptions_count += len(self.context.subscriptions[topic])

        # Broadcast updates
        tasks = deque()
        tasks.append(self.schedule_broadcast_sys_topic('load/bytes/received', int_to_bytes_str(self._stats[STAT_BYTES_RECEIVED])))
        tasks.append(self.schedule_broadcast_sys_topic('load/bytes/sent', int_to_bytes_str(self._stats[STAT_BYTES_SENT])))
        tasks.append(self.schedule_broadcast_sys_topic('messages/received', int_to_bytes_str(self._stats[STAT_MSG_RECEIVED])))
        tasks.append(self.schedule_broadcast_sys_topic('messages/sent', int_to_bytes_str(self._stats[STAT_MSG_SENT])))
        tasks.append(self.schedule_broadcast_sys_topic('time', str(datetime.now()).encode('utf-8')))
        tasks.append(self.schedule_broadcast_sys_topic('uptime', int_to_bytes_str(int(uptime.total_seconds()))))
        tasks.append(self.schedule_broadcast_sys_topic('uptime/formated', str(uptime).encode('utf-8')))
        tasks.append(self.schedule_broadcast_sys_topic('clients/connected', int_to_bytes_str(client_connected)))
        tasks.append(self.schedule_broadcast_sys_topic('clients/disconnected', int_to_bytes_str(client_disconnected)))
        tasks.append(self.schedule_broadcast_sys_topic('clients/maximum', int_to_bytes_str(self._stats[STAT_CLIENTS_MAXIMUM])))
        tasks.append(self.schedule_broadcast_sys_topic('clients/total', int_to_bytes_str(client_connected + client_disconnected)))
        tasks.append(self.schedule_broadcast_sys_topic('messages/inflight', int_to_bytes_str(inflight_in + inflight_out)))
        tasks.append(self.schedule_broadcast_sys_topic('messages/inflight/in', int_to_bytes_str(inflight_in)))
        tasks.append(self.schedule_broadcast_sys_topic('messages/inflight/out', int_to_bytes_str(inflight_out)))
        tasks.append(self.schedule_broadcast_sys_topic('messages/inflight/stored', int_to_bytes_str(messages_stored)))
        tasks.append(self.schedule_broadcast_sys_topic('messages/publish/received', int_to_bytes_str(self._stats[STAT_PUBLISH_RECEIVED])))
        tasks.append(self.schedule_broadcast_sys_topic('messages/publish/sent', int_to_bytes_str(self._stats[STAT_PUBLISH_SENT])))
        tasks.append(self.schedule_broadcast_sys_topic('messages/retained/count', int_to_bytes_str(len(self.context.retained_messages))))
        tasks.append(self.schedule_broadcast_sys_topic('messages/subscriptions/count', int_to_bytes_str(subscriptions_count)))

        # Wait until broadcasting tasks end
        while tasks and tasks[0].done():
            tasks.popleft()
        # Reschedule
        sys_interval = int(self.context.config['sys_interval'])
        self.context.logger.debug("Broadcasting $SYS topics")
        self.sys_handle = self.context.loop.call_later(sys_interval, self.broadcast_dollar_sys_topics)

    @asyncio.coroutine
    def on_mqtt_packet_received(self, *args, **kwargs):
        packet = kwargs.get('packet')
        if packet:
            packet_size = packet.bytes_length
            self._stats[STAT_BYTES_RECEIVED] += packet_size
            self._stats[STAT_MSG_RECEIVED] += 1
            if packet.fixed_header.packet_type == PUBLISH:
                self._stats[STAT_PUBLISH_RECEIVED] += 1

    @asyncio.coroutine
    def on_mqtt_packet_sent(self, *args, **kwargs):
        packet = kwargs.get('packet')
        if packet:
            packet_size = packet.bytes_length
            self._stats[STAT_BYTES_SENT] += packet_size
            self._stats[STAT_MSG_SENT] += 1
            if packet.fixed_header.packet_type == PUBLISH:
                self._stats[STAT_PUBLISH_SENT] += 1

    @asyncio.coroutine
    def on_broker_client_connected(self, *args, **kwargs):
        self._stats[STAT_CLIENTS_CONNECTED] += 1
        self._stats[STAT_CLIENTS_MAXIMUM] = max(self._stats[STAT_CLIENTS_MAXIMUM], self._stats[STAT_CLIENTS_CONNECTED])

    @asyncio.coroutine
    def on_broker_client_disconnected(self, *args, **kwargs):
        self._stats[STAT_CLIENTS_CONNECTED] -= 1
        self._stats[STAT_CLIENTS_DISCONNECTED] += 1
