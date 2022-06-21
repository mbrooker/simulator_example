library(ggplot2)

dpi=100
width=6
height=4

d = read.table("results.csv", header=TRUE, sep=",")

g = ggplot(d, aes(x=time, y=100*rate, color=name)) + geom_line() + geom_point() + xlab("Time (s)") + ylab("Hit Rate %")
ggsave("cache_sim_rate.png", width=width, height=height, dpi=dpi)

gm = ggplot(d, aes(x=time, y=misses, color=name)) + geom_line() + geom_point() + xlab("Time (s)") + ylab("Misses")
ggsave("cache_sim_misses.png", width=width, height=height, dpi=dpi)