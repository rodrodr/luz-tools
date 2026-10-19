# Shared helpers: read what 00_export.py wrote and build the dyadic data and matrices.
#
# Two specifications:
#   "tool"   the dyads homophily() exported, activity terciles as luz-mcp cut them: reproduces its logit
#   "active" only members who signed at least one measure (a deputy who signed nothing cannot be
#            tied: their dyads are structural zeros), terciles recut by value among them. This is
#            the specification for inference. Since luz-mcp restricts homophily() to the same
#            deputies, both specifications are the same model.

here <- function() {
  a <- commandArgs(FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  if (length(f)) dirname(normalizePath(f)) else getwd()
}
ROOT <- here()
LEGS <- c("1931-1933", "1933-1936", "1936-1939")
COVS <- c("same_party", "same_family", "same_district", "same_region", "ideology_distance")
PAIRS <- c("low-low", "low-mid", "low-high", "mid-mid", "mid-high", "high-high")

read_leg <- function(leg) {
  d <- read.csv(file.path(ROOT, "data", sprintf("dyads_%s.csv", leg)))
  n <- read.csv(file.path(ROOT, "data", sprintf("nodes_%s.csv", leg)), stringsAsFactors = FALSE)
  list(dyads = d, nodes = n)
}

tercile_by_value <- function(a) {
  s <- sort(a); N <- length(a)
  q1 <- s[N %/% 3 + 1]; q2 <- s[(2 * N) %/% 3 + 1]   # as luz-mcp: vals[N // 3], vals[2N // 3]
  factor(ifelse(a <= q1, "low", ifelse(a <= q2, "mid", "high")), levels = c("low", "mid", "high"))
}

pair_class <- function(ti, tj) {
  lv <- c(low = 1, mid = 2, high = 3)
  a <- pmin(lv[as.character(ti)], lv[as.character(tj)]); b <- pmax(lv[as.character(ti)], lv[as.character(tj)])
  p <- paste(names(lv)[a], names(lv)[b], sep = "-")
  factor(p, levels = PAIRS[PAIRS %in% unique(p)])
}

# the dyadic data frame for one legislature and specification
build <- function(leg, spec = c("active", "tool")) {
  spec <- match.arg(spec)
  x <- read_leg(leg)
  nodes <- x$nodes
  if (spec == "active") {
    nodes <- nodes[nodes$activity >= 1, ]
    nodes$tercile <- tercile_by_value(nodes$activity)
  } else {
    nodes$tercile <- factor(nodes$activity_tercile, levels = c("low", "mid", "high"))
  }
  d <- x$dyads[x$dyads$i %in% nodes$id_dip & x$dyads$j %in% nodes$id_dip, ]
  t <- setNames(nodes$tercile, nodes$id_dip)
  d$activity_pair <- pair_class(t[as.character(d$i)], t[as.character(d$j)])
  list(dyads = d, nodes = nodes, spec = spec, leg = leg)
}

# symmetric matrices for MRQAP: y and one slice per predictor (activity pairs as dummies)
matrices <- function(b) {
  ids <- as.character(b$nodes$id_dip); n <- length(ids)
  pos <- setNames(seq_len(n), ids)
  ii <- pos[as.character(b$dyads$i)]; jj <- pos[as.character(b$dyads$j)]
  sym <- function(v) { m <- matrix(0, n, n); m[cbind(ii, jj)] <- v; m[cbind(jj, ii)] <- v; m }
  lv <- levels(b$dyads$activity_pair)
  x <- c(lapply(COVS, function(k) sym(b$dyads[[k]])),
         lapply(lv[-1], function(l) sym(as.numeric(b$dyads$activity_pair == l))))
  names(x) <- c(COVS, paste0("activity ", lv[-1]))
  list(y = sym(b$dyads$tie), x = x)
}

formula_dyadic <- function(b) {
  as.formula(paste("tie ~", paste(c(COVS, if (nlevels(b$dyads$activity_pair) > 1) "activity_pair"), collapse = " + ")))
}
