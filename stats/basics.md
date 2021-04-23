# Statistics

We want to test, whether the difference between treatment and control variant in chosen metric is statistically significant or not. From statistical point of view, we deal with point estimates, confidence intervals and hypothesis testing. Confidence level is set by default to 95%, i.e. we talk about 95%-confidence intervals and hypothesis testing on 5% level of significance.

We also run various data quality checks to guarantee trustworthiness of presented data.

## Point Estimates, Confidence Intervals and Hypothesis Testing
Assume we have one control variant (usually denoted by $A$) and one or more treatment variants (usually denoted by $B$, $C$, $D$, ...). We calculate point estimate for relative difference between treatment and control variant in chosen metric. Next we calculate confidence interval for the relative difference. Finally, we want to test whether estimated relative difference is significantly significant.

Formula for relative difference is straightforward: $(B - A) / A * 100$. To be more precise, point estimate is only the estimate of true relative difference between treatment and control variant. The true relative difference is unknown! The point estimate is the best possible estimate of the true (unknown) relative difference using available data from the experiment.

We implemented Welch's t-test[^1] to test the significance of point estimate in EP Stats engine. Delta method is necessary, since standard Welch's test works well only for absolute differences, i.e. $B - A$. We use quantiles from Student's t-distribution which approximate normal distribution.

## Pitfalls and Corrections
We summarize all corrections implemented next to Welch's t-test in this part. Generally Welch's t-test assumes we have two samples, i.e. we have two sequences of independent and identically distributed random variables with finite variance. The variances between the variants may not be equal.

Unfortunately assumptions above are often violated in practice and appropriate corrections are necessary to guarantee desired level of significance.

### Absolute vs. Relative Difference
Two-sample t-test is only correct when we deal with absolute difference, i.e. $B - A$. But it does not hold any more when we deal with relative difference. In order to be statistically correct, [delta method for relative difference](ctr.md#relative-difference) is necessary.

### Independent and Identically Distributed Observations
Welch's t-test assumes that observations are independent and identically distributed (i.i.d.). Unfortunately this assumption does not hold always.

Let's assume Click-through rate metric (i.e. clicks / views). Since multiple views (and clicks) from the same user (user being randomization unit here) are allowed, the assumption of independence is violated. Multiple observations from the same user are not independent. [Delta method for iid](ctr.md##asymptotic-distribution-of-ctr) is necessary (has not been implemented yet).

### Multiple Comparisons Problem
If we have only one control $A$ and one treatment $B$ variant, we need to run just one Welch's t-test, i.e. relative difference between $B$ and $A$. If we have multiple treatment variants, e.g. $B$, $C$ and $D$, we need to run three Welch's t-tests, i.e. relative difference between $B$ and $A$, $C$ and $A$, $D$ and $A$. If we run every single test on 5% level of significance, the overall level of significance is lower. The probability of false-positive error (i.e. we wrongly reject at least one null hypothesis) is higher than required 5% level.

In ep-stats engine, we implemented [HolmBonferroni p-value correction](multiple.md#holmbonferroni-method). Single tests are more conservative and so overall level of confidence is satisfied.

### Real-time Experiment Evaluation
> Time is Money

One of the main goals in Experimentation Platform was to develop real-time data pipelines. Standard Welch's t-test assumes you evaluate experiment only once, after you collect all data. If you evaluate experiment more than once, than the false-positive error (wrongly rejecting null hypothesis) grows enormously[^2].

We implemented [Sequential testing](sequential.md) procedure to tackle this issue. It allows us to evaluate experiments (hypothesis) real-time during the experiment period without exceeding false-positive errors.

The solution itself is pretty simple. In the beginning (circa first half of the experiment period) the decision rule is very conservative and only great differences can be called statistically significant. As we approach the end of the experiment the decision rule is less and less stringent. If we have enough evidence, the difference can be statistically significant and we can end up the experiment earlier.

Main disadvantage is that the [length of the experiment must be set in advance](../user_guide/protocol.md#set-experiment-duration-before-starting-it) - before starting the experiment. This is very annoying for the experimenters (test owners) but right now this is the only way, how to deal with this issue. If we do not use Sequential testing, our false-positive errors could be somewhere between 20-30%, instead of required below 5%. It means one third of all presented results are wrong and without any chance to fix them. In other words, one third of decisions are wrong.

## Data Quality Checks
Experimentation Platform is very complex. From data collection to statistical evaluation, there are many intermediate steps. All of these steps must be checked regularly in order to guarantee trustworthiness of presented results.

### Sample Ratio Mismatch Check
Sample Ratio Mismatch check[^3] (SRM Check) checks the quality of randomization. Randomization is absolutely crucial. Wrong randomization can have fatal consequences and results might be highly misleading. SRM check checks whether we have the same number of users in each variant. Chi-square[^6] test is implemented.

In this check we require high reliability. Therefore the confidence level is set to 99.9%. If SRM check fails, presented results should not be taken into account and any decisions based on this experiment should not be done!

### Data Quality
We have not implemented any automatic data quality checks yet. The plan is to check all parts of data pipelines.

[^1]: [Welch's t-test](https://en.wikipedia.org/wiki/Welch%27s_t-test)
[^2]: [Ronny Kohavi, Sample Ratio Mismatch](https://twitter.com/ronnyk/status/932798952679776256?lang=cs)
[^3]: [Wikipedia, Chi-square test](https://en.wikipedia.org/wiki/Chi-squared_test)
