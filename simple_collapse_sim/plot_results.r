library(ggplot2)
library(reshape2)
library(ggthemes)

d <- read.table("results.csv", sep = ",", header = TRUE)

make_graph <- function(run_name) {
    df = d[d$run_name == run_name,]
    dm <- melt(df, id.vars = c("t", "run_name"))
    dmnc <- dm[dm$variable != "concurrency",]
    dmnc <- dmnc[dmnc$variable != "timeouts",]

    gg <- ggplot(dmnc, aes(x = t, y = value, color = variable)) + 
        geom_line() +
        xlab("Simulated time (s)") +
        ylab("Count per second") +
        theme_tufte()

    ggsave(paste0("sim_result_", run_name, ".png"), dpi = 120, w = 6, h = 3)

    return(gg)
}

ggnb <- make_graph("ramp_no_backoff")
ggb <- make_graph("ramp_backoff_and_jitter")
ggnbs <- make_graph("spike_no_backoff")
ggbs <- make_graph("spike_backoff_and_jitter")

gg <- ggplot(d, aes(x = t, y = successes, color = run_name)) +
    geom_line()
ggsave("sim_result_successes.png", dpi=100, w = 8, h = 6)
ggr <- ggplot(d, aes(x = t, y = retries, color = run_name)) +
    geom_line()
ggsave("sim_result_retries.png", dpi=100, w = 8, h = 6)

