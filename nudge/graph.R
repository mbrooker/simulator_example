library(ggplot2)

d = read.table("results.csv", sep=",", header=TRUE)

gg = ggplot(d, aes(service_time, colour=name)) +
	 geom_freqpoly() +
	 scale_y_log10() +
	 ylab("Count") +
	 xlab("Service Time (s)")
ggsave("nudge_poly.png", dpi=100, width=8, height=5)

ggc = ggplot(d, aes(service_time, colour=name)) +
	 stat_ecdf() +
	 coord_cartesian(ylim = c(0.99,1.0)) + 
	 ylab("Cumulative Density") +
	 xlab("Service Time")
ggsave("nudge_ecdf.png", dpi=200, width=5, height=3)
	 

