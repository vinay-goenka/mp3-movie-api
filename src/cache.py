import json
import logging

import fakeredis

logger = logging.getLogger(__name__)


class MovieCache:
    def __init__(self):
        self.client = fakeredis.FakeRedis(decode_responses=True)

    def make_key(self, limit):
        return f"movies:limit:{limit}"

    def get(self, limit):
        """Return the cached response dictionary, or None."""
        # TODO: get the key and log HIT or MISS at DEBUG.
        # Convert a cached JSON string back to a dictionary.
        key = self.make_key(limit)
        cached_text = self.client.get(key)
        if cached_text is None:
            logger.debug(f"Cache MISS for key: {key}")
            return None
        logger.debug(f"Cache HIT for key: {key}")
        response = json.loads(cached_text)
        return response

    def set(self, limit, response):
        """Cache the response dictionary for 90 seconds."""
        # TODO: convert the response to JSON and store it with ex=90.
        key = self.make_key(limit)
        response_text = json.dumps(response)
        self.client.set(key, response_text, ex=90)
        logger.debug(f"Cached response {key}")

    def invalidate(self):
        """Remove all cached movie retrievals."""
        self.client.flushdb()
        logger.debug("Invalidated movie cache")

