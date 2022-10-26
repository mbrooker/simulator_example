# Simulation of "Nudge: Stochastically Improving upon FCFS" by Grosof et al: https://arxiv.org/pdf/2106.01492.pdf
# 
# From the paper:
# "In this paper, we introduce a new policy, Nudge, which is the first policy to provably stochastically improve upon FCFS.
#   We prove that Nudge simultaneously improves upon FCFS at every point along the tail, for light-tailed job size distributions. "
#
# That sure sounds exciting! Beating FCFS with a simple heuristic across the whole tail is a very interesting thing to do.
#
# The model here is a simple M/G/1, with Poisson arrivals, and Weibull service time.
import random
import heapq
import math
from collections import deque

# We model three "types" of jobs: small, large, and extra large. Each "type" has an associated mean latency, and a probability
#  of each job being that type.

# Probabilities of each type
large_p = 0.1
extra_large_p = 0.01

# Service time (in seconds) for each type
small_t = 1.0
large_t = 10.0
extra_large_t = 100.0

# Shape of the Weibull distribution
weibull_shape = 2.5

def weibull_scale(mean, shape):
    return mean/math.gamma(1.0 + 1.0 / shape)
small_t_scale = weibull_scale(small_t, weibull_shape)
large_t_scale = weibull_scale(large_t, weibull_shape)
extra_large_t_scale = weibull_scale(extra_large_t, weibull_shape)

# Models one Job in the system. In Nudge, each Job can be swapped exactly once, so we track
#  whether the job has been swapped.
class Job(object):
    def __init__(self, t):
        self.size = self.select_size()
        self.swapped = False
        self.created_t = t

    def select_size(self):
        r = random.random()
        if r > (1.0 - extra_large_p):
            return random.weibullvariate(extra_large_t_scale, weibull_shape)
        elif r > (1.0 - extra_large_p - large_p):
            return random.weibullvariate(large_t_scale, weibull_shape)
        else:
            return random.weibullvariate(small_t_scale, weibull_shape)

# First-Come-First-Served Queue
class FCFSQueue(object):
    def __init__(self):
        self.deque = deque()

    def append(self, job):
        self.deque.append(job)

    def pop(self):
        return self.deque.popleft()

    def len(self):
        return len(self.deque)

    def name(self):
        return "FCFS"

# Nudge queue, which has one small additional behavior vs FCFS: when a job is offered to the queue, 
#  and the one in front of it is bigger and has never been swapped, then we swap them.
class NudgeQueue(FCFSQueue):
    def append(self, job):
        if len(self.deque) == 0:
            self.deque.append(job)
        else:
            last = self.deque.pop()
            if last.size > job.size and last.swapped == False:
                # Swap the new job and the last in the queue, and mark this one as already swapped so it doesn't
                #  get swapped twice.
                last.swapped = True
                self.deque.append(job)
                self.deque.append(last)
                
            else:
                # Insert in FCFS order
                self.deque.append(last)
                self.deque.append(job)

    def name(self):
        return "Nudge"

# Last In First Out (LIFO) Queue (aka, a stack)
class LIFOQueue(FCFSQueue):
    def pop(self):
        return self.deque.pop()

    def name(self):
        return "LIFO"

# The single server. All this does is service one request at a time from the queue.
class Server(object):
    def __init__(self, queue, sim_name):
        self.busy = False
        self.queue = queue
        self.in_flight = None
        self.sim_name = sim_name

    def job_done(self, t):
        assert(self.busy)
        print("%f,%f,%f,%s"%(t, t - self.in_flight.created_t, t - self.in_flight.created_t - self.in_flight.size, self.sim_name))

        if self.queue.len() > 0:
            next_job = self.queue.pop()
            self.in_flight = next_job
            return [(t + next_job.size, self.job_done)]
        else:
            self.in_flight = None
            self.busy = False
            return None

    def start(self, job):
        assert(not self.busy)
        self.busy = True
        self.in_flight = job

# Load generation client. Creates an unbounded concurrency
class Client(object):
    def __init__(self, rho, server):
        self.rate_tps = rho / (small_t * (1.0 - extra_large_p - large_p) + large_t * large_p + extra_large_t * extra_large_p)
        self.server = server

    def generate(self, t):
        job = Job(t)
        next_t = t + random.expovariate(self.rate_tps)
        if self.server.busy:
            self.server.queue.append(job)
            return [(next_t, self.generate)]
        else:
            self.server.start(job)
        return [(next_t, self.generate), (t + job.size, self.server.job_done)]

# Run a single simulation.        
def sim_loop(max_t, client):
    t = 0.0
    q = [(t, client.generate)]
    # This is the core simulation loop. Until we've reached the maximum simulation time, pull the next event off
    #  from a heap of events, fire whichever callback is associated with that event, and add any events it generates
    #  back to the heap.
    while len(q) > 0 and t < max_t:
        # Get the next event. Because `q` is a heap, we can just pop this off the front of the heap.
        (t, call) = heapq.heappop(q)
        # Execute the callback associated with this event
        new_events = call(t)
        # If the callback returned any follow-up events, add them to the event queue `q` and make sure its still a valid heap
        if new_events is not None:
            q.extend(new_events)
            heapq.heapify(q)

def run_sims(max_t):
    print("t,service_time,q_time,name")
    for q_type in [LIFOQueue, FCFSQueue, NudgeQueue]:
        for rho in [0.5, 0.8]:
            queue = q_type()
            server = Server(queue, "%s_%.2f"%(queue.name(), rho))
            client = Client(rho, server)
            sim_loop(max_t, client)

#print((small_t * (1.0 - extra_large_p - large_p) + large_t * large_p + extra_large_t * extra_large_p))
run_sims(1000000.0)
