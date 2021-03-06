import asyncio


class BaseTopicPlugin:
    def __init__(self, context):
        self.context = context
        try:
            self.topic_config = self.context.config['topic-check']
        except KeyError:
            self.context.logger.warning("'topic-check' section not found in context configuration")

    def topic_filtering(self, *args, **kwargs):
        if not self.topic_config:
            # auth config section not found
            self.context.logger.warning("'auth' section not found in context configuration")
            return False
        return True


class TopicTabooPlugin(BaseTopicPlugin):
    def __init__(self, context):
        super().__init__(context)
        self._taboo = ['prohibited', 'top-secret', 'data/classified']

    @asyncio.coroutine
    def topic_filtering(self, *args, **kwargs):
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            topic = kwargs.get('topic', None)
            if topic:
                if session.username != 'admin' and topic in self._taboo:
                    return False
                return True
            else:
                return False
        return filter_result


class EcdsaTopicPlugin(BaseTopicPlugin):
    def __init__(self, context):
        super().__init__(context)

    @asyncio.coroutine
    def topic_filtering(self, *args, **kwargs):
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            topic = kwargs.get('topic', None)
            if any([
                topic.startswith(root) for root in
                self.topic_config.get("ecdsa-roots", [])
            ]):
                return True if getattr(session, "_secp256k1", False) else False
            else:
                return None
        return filter_result


class TopicAccessControlListPlugin(BaseTopicPlugin):
    def __init__(self, context):
        super().__init__(context)

    @staticmethod
    def topic_ac(topic_requested, topic_allowed):
        req_split = topic_requested.split('/')
        allowed_split = topic_allowed.split('/')
        ret = True
        for i in range(max(len(req_split), len(allowed_split))):
            try:
                a_aux = req_split[i]
                b_aux = allowed_split[i]
            except IndexError:
                ret = False
                break
            if b_aux == '#':
                break
            elif (b_aux == '+') or (b_aux == a_aux):
                continue
            else:
                ret = False
                break
        return ret

    @asyncio.coroutine
    def topic_filtering(self, *args, **kwargs):
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            req_topic = kwargs.get('topic', None)
            if req_topic:
                username = session.username
                if username is None:
                    username = 'anonymous'
                allowed_topics = self.topic_config['acl'].get(username, None)
                if allowed_topics:
                    for allowed_topic in allowed_topics:
                        if self.topic_ac(req_topic, allowed_topic):
                            return True
                    return False
                else:
                    return False
            else:
                return False
