"""Cache Utils for Video Block"""

import itertools

import wrapt
from django.utils.encoding import force_str
from edx_django_utils.cache import RequestCache


def request_cached(namespace=None, arg_map_function=None, request_cache_getter=None):
    """
    A function decorator that automatically handles caching its return value for
    the duration of the request. It returns the cached value for subsequent
    calls to the same function, with the same parameters, within a given request.

    Notes:
        - We convert arguments and keyword arguments to their string form to build the cache key. So if you have
          args/kwargs that can't be converted to strings, you're gonna have a bad time (don't do it).
        - Cache key cardinality depends on the args/kwargs. So if you're caching a function that takes five arguments,
          you might have deceptively low cache efficiency.  Prefer functions with fewer arguments.
        - WATCH OUT: Don't use this decorator for instance methods that take in a "self" argument that changes each
          time the method is called. This will result in constant cache misses and not provide the performance benefit
          you are looking for. Rather, change your instance method to a class method.
        - Benchmark, benchmark, benchmark! If you never measure, how will you know you've improved? or regressed?

    Arguments:
        namespace (string): An optional namespace to use for the cache. By default, we use the default request cache,
            not a namespaced request cache. Since the code automatically creates a unique cache key with the module and
            function's name, storing the cached value in the default cache, you won't usually need to specify a
            namespace value.
            But you can specify a namespace value here if you need to use your own namespaced cache - for example,
            if you want to clear out your own cache by calling RequestCache(namespace=NAMESPACE).clear().
            NOTE: This argument is ignored if you supply a ``request_cache_getter``.
        arg_map_function (function: arg->string): Function to use for mapping the wrapped function's arguments to
            strings to use in the cache key. If not provided, defaults to force_text, which converts the given
            argument to a string.
        request_cache_getter (function: args, kwargs->RequestCache): Function that returns the RequestCache to use.
            If not provided, defaults to edx_django_utils.cache.RequestCache.  If ``request_cache_getter`` returns None,
            the function's return values are not cached.

    Returns:
        func: a wrapper function which will call the wrapped function, passing in the same args/kwargs,
              cache the value it returns, and return that cached value for subsequent calls with the
              same args/kwargs within a single request.
    """

    @wrapt.decorator
    def decorator(wrapped, instance, args, kwargs):
        """
        Arguments:
            args, kwargs: values passed into the wrapped function
        """
        # Check to see if we have a result in cache.  If not, invoke our wrapped
        # function.  Cache and return the result to the caller.
        if request_cache_getter:
            request_cache = request_cache_getter(args if instance is None else (instance,) + args, kwargs)
        else:
            request_cache = RequestCache(namespace)

        if request_cache:
            cache_key = _func_call_cache_key(wrapped, arg_map_function, *args, **kwargs)
            cached_response = request_cache.get_cached_response(cache_key)
            if cached_response.is_found:
                return cached_response.value

        result = wrapped(*args, **kwargs)

        if request_cache:
            request_cache.set(cache_key, result)

        return result

    return decorator


def _func_call_cache_key(func, arg_map_function, *args, **kwargs):
    """
    Returns a cache key based on the function's module,
    the function's name, a stringified list of arguments
    and a stringified list of keyword arguments.
    """
    arg_map_function = arg_map_function or force_str

    converted_args = list(map(arg_map_function, args))
    converted_kwargs = list(map(arg_map_function, _sorted_kwargs_list(kwargs)))

    cache_keys = [func.__module__, func.__name__] + converted_args + converted_kwargs
    return ".".join(cache_keys)


def _sorted_kwargs_list(kwargs):
    """
    Returns a unique and deterministic ordered list from the given kwargs.
    """
    sorted_kwargs = sorted(kwargs.items())
    sorted_kwargs_list = list(itertools.chain(*sorted_kwargs))
    return sorted_kwargs_list
