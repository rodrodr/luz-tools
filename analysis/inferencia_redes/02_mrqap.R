# MRQAP logit (sna::netlogit, Dekker's double semi-partialling, "qapspp") on the inference
# specification: the same covariates as the dyadic logit, so the coefficients are the glm's and only
# the p-values change. Undirected: mode = "graph" (each dyad once).
# Rscript analysis/inferencia_redes/02_mrqap.R <legislature> [reps] [seed]   (one chunk; 04_combine.py pools the seeds)
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))),
                 "common.R"))
suppressMessages(library(sna))

args <- commandArgs(TRUE)
leg <- args[1]
reps <- if (length(args) > 1) as.integer(args[2]) else 500L
seed <- if (length(args) > 2) as.integer(args[3]) else 1L
set.seed(seed)

b <- build(leg, "active")
mx <- matrices(b)
t0 <- Sys.time()
fit <- netlogit(mx$y, mx$x, intercept = TRUE, mode = "graph", diag = FALSE, nullhyp = "qapspp", reps = reps)
secs <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
terms <- c("intercept", names(mx$x))
res <- data.frame(legislature = leg, term = terms, coef = fit$coefficients, se_naive = fit$se,
                  p_mrqap = fit$pgreqabs, p_mrqap_greater = fit$pgreq, p_mrqap_less = fit$pleeq,
                  reps = reps, seed = seed, members = nrow(b$nodes), dyads = nrow(b$dyads), seconds = round(secs))
saveRDS(fit, file.path(ROOT, "results", sprintf("mrqap_%s_s%d.rds", leg, seed)))
write.csv(res, file.path(ROOT, "results", sprintf("mrqap_%s_s%d.csv", leg, seed)), row.names = FALSE)
print(res[, c("term", "coef", "se_naive", "p_mrqap")], digits = 4)
cat("seconds:", round(secs), "\n")
