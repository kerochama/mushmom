
class MessageParser:
    def __init__(self, message):
        self.message = message
        self.content = message.content

    def process_prefix(self, prefix):
        """
        Return message with the longest prefix stripped

        :param s:
        :param prefix:
        :return:
        """
        if isinstance(prefix, str):
            prefix = [prefix]

        stripped = [self.content[len(p):] if self.content.startswith(p) else self.content
                    for p in prefix]  # remove prefix
        matches = list(filter(lambda x: x != self.content, stripped))

        if matches:
            return sorted(matches, key=len)[0]
        else:
            return self.content

    def has_prefix(self, prefix):
        """
        Check if message starts with prefix

        :param prefix:
        :return:
        """
        return self.content.startswith(tuple(prefix))

    def parse(self, prefix):
        """
        Return command and prefix. Both prefix only and no prefix will return
        None as command

        :param prefix:
        :return:
        """
        if self.has_prefix(prefix):
            parsed = self.process_prefix(prefix)

            if parsed:
                tokens = parsed.split(' ')
                cmd = tokens.pop(0)
                return cmd, tokens

        return None, None
