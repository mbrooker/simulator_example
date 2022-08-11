library(ggplot2)
library(ggpubr)

d = read.table("results.csv", header=TRUE, sep=",")

ggsuccess = ggplot(d, aes(x=100*failure_rate, y=successes, color=name)) + geom_line() + ylab("Successful Operations") + xlab("Server-side failure rate (%)") + guides(color=guide_legend(title="Retry Strategy"))

ggsuccess_rate = ggplot(d, aes(x=100*failure_rate, y=100*successes/unique_calls, color=name)) + geom_line() + ylab("Successful Operations (%)") + xlab("Server-side failure rate (%)") + guides(color=guide_legend(title="Retry Strategy"))

ggload = ggplot(d, aes(x=100*failure_rate, y=100*total_calls/max(unique_calls), color=name)) + geom_line() + ylab("Load (%)") + xlab("Server-side failure rate (%)") + guides(color=guide_legend(title="Retry Strategy"))

g = ggarrange(ggsuccess_rate, ggload, ncol=1, nrow=2)

ggsave("retry_simulation_results.png", dpi=100, width=5.4, height=6)


