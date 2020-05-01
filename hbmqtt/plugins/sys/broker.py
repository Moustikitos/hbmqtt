# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
from datetime import datetime
from hbmqtt.mqtt.packet import PUBLISH
from hbmqtt.codecs import int_to_bytes_str
import json
import random
import asyncio
import traceback
import urllib.parse as urlparse
from collections import deque
from urllib.request import Request, urlopen


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


class BrokerBlockchainPlugin:
    def __init__(self, context):
        self.context = context
        # config formating
        # 'blockchain': {
        #     "nethash": nethash,
        #     "endpoints": dict([(name, [method, path])...]),
        #     "tasks": dict([(tx_type, func_name)...]),
        #     "peers": ["scheme://ip:port"...],
        # }
        self._blockchain = self.context.config.get("blockchain", {})
        self._endpoints = self._blockchain.get("endpoints", {})
        self._ndpt_headers = {
            "Content-type": "application/json",
            "nethash": self._blockchain.get("nethash", "")
        }
        self.context.logger.debug(
            "blockchain confguration loaded: %s, %s",
            self._blockchain, self._ndpt_headers
        )

    # send http request to blockchain
    async def _rest_req(self, endpoint, data={}, **qs):
        method, path = self._endpoints.get(endpoint, ["GET", endpoint])
        if method not in ["GET"]:
            if isinstance(data, (dict, list, tuple)):
                data = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                # assume data is a valid json string
                data = data.encode("utf-8")
        else:
            data = None
        # build request
        try:
            req = Request(
                urlparse.urlparse(
                    random.choice(self._blockchain["peers"])
                )._replace(
                    path=path,
                    query="&".join(["=".join(item) for item in qs.items()])
                ).geturl(),
                data, self._ndpt_headers
            )
            req.get_method = lambda: method
        except Exception as error:
            self.context.logger.error("%r\n%s", error, traceback.format_exc())
        else:
            self.context.logger.debug(
                "blockchain request prepared: %s %s %s",
                method, req.get_full_url(), data
            )
            try:
                data = urlopen(req).read()
                result = json.loads(data)
            except Exception as error:
                self.context.logger.error(
                    "%r\n%s", error, traceback.format_exc()
                )
            else:
                return result
        return {}

    # function to check if a message sent to specific blockchain topic is
    # genuinely sent from blockchain. If any task linked to transaction type
    # it is executed with the data sent by blockchain.
    async def on_broker_message_received(self, *args, **kwargs):
        truth = False  # truth is true if data comes from blockchain
        message = kwargs["message"]
        if message.topic in self._blockchain.get('topics', []):
            try:
                data = json.loads(message.data)
                truth = any(
                    (
                        await self._rest_req(
                            "/api/transactions", id=data["id"]
                        )
                    ).get("data", [])
                )
            except Exception as error:
                self.context.logger.error(
                    "%r\n%s", error, traceback.format_exc()
                )

        if not truth:
            return False

        func = getattr(
            self,
            self._blockchain.get("tasks", {}).get(data["type"], "?"),
            lambda *a, **k: False
        )

        self.context.logger.debug(
            "genuine data received from blockchain by '%s' on '%s' topic\n",
            kwargs["client_id"], message.topic
        )
        self.context.logger.debug(
            "broker plugin function %s triggered with data: %s",
            func.__name__, data
        )

        return func(self, data)

    def register_device(self, data):
        pass


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
