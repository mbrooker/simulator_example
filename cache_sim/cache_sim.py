# Small simulator to demonstrate the effects of "cold starting" a system with a cache, and a backend
#  that can't handle the entire offered load.
from collections import OrderedDict
from numpy import random

# LRU models a simple least-recently-used cache.
# Puts evict the item from the cache that has been used (get or put) least recently.
class LRU(object):
    def __init__(self, capacity):
        self.capacity = capacity
        self.map = OrderedDict()
        # Here we prime the cache with the items that we know are going to be the most popular (see the Zipf
        #  distribution below). This simulates starting time with a perfectly full cache.
        for i in range(capacity):
            self.map[i+1] = True

    # Put the `v` into the cache for key `k`.
    def put(self, k, v):
        if k in self.map:
            v = self.map.pop(k)
        if len(self.map) == self.capacity:
            self.map.popitem(last=False)
        if v is not None:
            self.map[k] = v
        return v

    # Return `true` if `k` is in the cache
    def is_cached(self, k):
        return self.put(k, None) is not None

    # Remove all items from the cache
    def flush(self):
        self.map = OrderedDict()

# Stats is a convenience class that keeps track of hits and misses, and prints them out once a second.
class Stats(object):
    def __init__(self,name):
        self.last_print = 0
        self.hits = 0
        self.misses = 0
        self.name = name

    def add_stats(self, t, is_hit):
        if t - self.last_print > 1.0: 
            print("%f,%d,%d,%f,%s"%(t, self.hits, self.misses, self.hits/float(self.hits+self.misses), self.name))
            self.hits, self.misses, self.last_print = (0, 0, t)
        if is_hit:
            self.hits += 1
        else:
            self.misses += 1

# Backend simulates a backend service (e.g. a database) that can only respond to `max_per_second` requests.
#  Because we don't care about the sub-second distribution, we brute force this by just counting the number
#  of requests so far this second.
class Backend(object):
    def __init__(self, max_per_second):
        self.max_per_second = max_per_second
        self.last_flush = 0.0
        self.since_last_flush = 0

    # Simulate a `get` from the backend at time `t`. Returns True if the backend can handle the request.
    #  Doesn't return the payload because payloads don't matter to us.
    def get(self, t):
        if t - self.last_flush > 1.0:
            self.since_last_flush, self.last_flush = (0, t)
        self.since_last_flush += 1
        return self.since_last_flush <= self.max_per_second

# Run a simulation.
#  `zipf_alpha` is the alpha parameter of the zipf distribution used to select keys. The higher `alpha` the more
#    traffic is concentrated in the popular keys.
#  `cache_size` is the number of objects we keep in cache
#  `arrival_rate` is the number of requests arriving each second
#  `backend_max_rate` is the maximum number of requests per second the backend can handle (see Backend class)
#
# We loop for 60 simulated seconds, selecting keys from a zipf distribution, and checking if they are in the cache.
# If the keys aren't in the cache, we try fetch them from the backend.
# After 3 seconds of simulated time, we flush the cache, demonstrating the cold start.
def run_sim(zipf_alpha, cache_size, arrival_rate, backend_max_rate, name):
    lru = LRU(cache_size)
    stats = Stats(name)
    backend = Backend(backend_max_rate)
    time = 0.0
    flushed = False

    while time < 60.0:
        time += 1 / arrival_rate
        key = random.zipf(zipf_alpha)
        if lru.is_cached(key):
            stats.add_stats(time, True)
        else:
            stats.add_stats(time, False)
            if backend.get(time):
                lru.put(key, True)
        
        if time >= 4.0 and not flushed:
            flushed = True
            lru.flush()
        
print("time,hits,misses,rate,name")
run_sim(1.3, 1000, 1000.0, 5.0, "backend_0.5%")
run_sim(1.3, 1000, 1000.0, 10.0, "backend_1%")
run_sim(1.3, 1000, 1000.0, 20.0, "backend_2%")
run_sim(1.3, 1000, 1000.0, 100.0, "backend_10%")