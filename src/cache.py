def get_cached(cache, key, factory):
    value = cache.get(key)
    if value is None:
        value = factory()
        cache[key] = value
    return value
