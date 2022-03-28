library(ggplot2)

dpi=100

width=4
height=4

d = read.table("results.csv", sep=",", header=TRUE)

gg = ggplot(d, aes(x=skiiers, y=100*skiiers_skiing, color=name)) + geom_line() + xlab("Number of Skiiers") + ylab("% of time spent skiing")
ggsave("ski_percent_time.png", dpi=dpi, width=width, height=height)

ggq = ggplot(d, aes(x=skiiers, y=avg_queue_len, color=name)) + geom_line() + xlab("Number of Skiiers") + ylab("Average Queue Length")
ggsave("ski_queue_len.png", dpi=dpi, width=width, height=height)