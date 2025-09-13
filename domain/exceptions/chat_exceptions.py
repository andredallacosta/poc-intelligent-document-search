class ChatError(Exception):
    pass


class SessionNotFoundError(ChatError):
    pass


class SessionExpiredError(ChatError):
    pass


class InvalidMessageError(ChatError):
    pass


class MessageNotFoundError(ChatError):
    pass


class RateLimitExceededError(ChatError):
    pass


class SearchError(ChatError):
    pass


class LLMError(ChatError):
    pass
