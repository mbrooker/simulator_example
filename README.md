# Small numerical simulator example
This is a small example of the kind of small numerical simulator I often write as I explore the dynamics of different kinds of systems. It's not sophisticated, or advanced, but it is powerful.

## Usage

   python3 ski_sim.py | tee results.png

This type of code runs multiple times faster with [Pypy](https://www.pypy.org/) than it does with standard python.

## Exercises
* (Simple) Replace the normal distributions with distributions with other shapes, especially heavy tails.
* (Simple) Measure queue wait latency directly, calculating percentiles or other statistics.
* (Moderate) Model the effect of breaks in lift service. What happens when a lift is unavailable or stopped for a short period of time?
* (Moderate) Model the effect of people giving up waiting after a period of time. At what capacity does the system become stable?
* (Moderate) Model the effect of different classes of service. How does giving some people priority alter other people's waiting time?
* (Advanced) Extend the simulation to model a network of slopes and lifts, and skiiers of different speed.
