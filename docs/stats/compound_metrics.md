# Compound Metrics

There are metrics in Experimentation Platform, which are compounded, i.e. the nominator does not consist of value or count from a single goal, but it is composed from multiple goals. However, when we combine multiple goals into one, there might occur issues with standard deviation (variance).

In data pipeline we save goals in multiple stages of aggregation:

1. **Tracking table** `tracking`:
Basically raw data, no aggregation applied. Usually one line, one goal.

1. **Aggregated Unit Goals table** `agg_unit_goals`:
Goals are aggregated (grouped by) with respect to `experiment_id`, `variant_id`, `goal` and `guid`.

1. **Aggregated Goals table** `agg_goals`:
Goals are aggregated (grouped by) with respect to `experiment_id`, `variant_id` and `goal`.

In statistical evaluation in EP we use tables `agg_unit_goals` and `agg_goals`, which contain pre-aggregated goals. We do not use table `tracking` with raw goals. This is mainly due to optimality of SQL queries.

## Example

We illustrate differences between tables on the following example. Assume we have two users, Sam and Mike. Sam bought three products for $10, $20 and $50. Than he refunded two of them - the one for $10 and the one for $20. Mike bought two products for $20 and $30. Later he refunded the cheaper one. They are both in A variant of our imaginary experiment.

**Tracking table** `tracking`

| Variant | User                           | Goal                        | Count | Value |
| ------- | ------------------------------ | --------------------------- | ------| ----- |
| A       | :material-account-circle: Sam  | :material-check: purchase   | 1     | $10   |
| A       | :material-account-circle: Sam  | :material-check: purchase   | 1     | $20   |
| A       | :material-account-circle: Sam  | :material-check: purchase   | 1     | $50   |
| A       | :material-account-circle: Sam  | :material-close: refund     | 1     | $10   |
| A       | :material-account-circle: Sam  | :material-close: refund     | 1     | $20   |
| A       | :material-account-circle: Mike | :material-check: purchase   | 1     | $20   |
| A       | :material-account-circle: Mike | :material-check: purchase   | 1     | $30   |
| A       | :material-account-circle: Mike | :material-close: refund     | 1     | $20   |

**Aggregated Unit Goals table** `agg_unit_goals`

| Variant | User                           | Goal                        | Count | Value | Value Squared    |
| ------- | ------------------------------ | --------------------------- | ------| ----- | ---------------- |
| A       | :material-account-circle: Sam  | :material-check: purchase   | 3     | $80   | 6,400 (80 * 80)  |
| A       | :material-account-circle: Sam  | :material-close: refund     | 2     | $30   | 900 (30 * 30)    |
| A       | :material-account-circle: Mike | :material-check: purchase   | 2     | $50   | 2,500 (50 * 50)  |
| A       | :material-account-circle: Mike | :material-close: refund     | 1     | $20   | 400 (20 * 20)    |

**Aggregated Goals table** `agg_goals`

| Variant | Goal                        | Count | Value | Value Squared         |
| ------- | --------------------------- | ------| ----- | --------------------- |
| A       | :material-check: purchase   | 5     | $130  | 8,900 (6,400 + 2,500) |
| A       | :material-close: refund     | 3     | $50   | 1,300 (900 + 400)     |

## Simple vs Compound Metrics

From table `agg_goals` it is easy to compute simple "per User" metrics such as **Bookings per User** or **Refunds per User**.
For example total bookings equals to \$130 (\$80 Sam + \$50 Mike) with sample variance 8,900 (6,400 Sam + 2,500 Mike). Analogously total refunds equals to \$50 (\$30 Sam + \$20 Mike) with sample variance 1,300 (900 Sam + 400 Mike).

The issues might arise when we think about compound metrics. Let assume we are interested in metric **Net Bookings per User**. In this metric we do not want to count purchases which were later refunded.
Ideal situation would be if we had goal `net purchases`. This goal would be defined as `purchases` - `refunds`. If we compute `net purchases` from already aggregated goals, we overestimate the sample variance (`Value Squared`).

**Aggregated Unit Goals table** `agg_unit_goals`
(Overestimating sample variance - the way how we compute it now)

| Variant | User                           | Goal                               | Count | Value | Value Squared       |
| ------- | ------------------------------ | ---------------------------------- | ------| ----- | ------------------- |
| A       | :material-account-circle: Sam  | :material-check-all: net purchases | 1     | $50   | 5,500 (6,400 - 900) |
| A       | :material-account-circle: Mike | :material-check-all: net purchases | 1     | $30   | 2,100 (2,500 - 400) |

This is exactly what we get if we use `agg_unit_goals` table. Now look closer. Sam bought three items for $10, $20 and $50. He refunded two of them for $10 and $20. In summary, Sam made one valid purchase for $50. Mike bought two items for $20 and $30. He refunded the first one. So do Mike made only one valid purchase for $30. Therefore, the `agg_unit_goals` table for (non-existing) goal `net purchases` should looks like this.

**Aggregated Unit Goals table** `agg_unit_goals`
(True sample variance - the way how we should compute it)

| Variant | User                           | Goal                               | Count | Value | Value Squared   |
| ------- | ------------------------------ | ---------------------------------- | ------| ----- | --------------- |
| A       | :material-account-circle: Sam  | :material-check-all: net purchases | 1     | $50   | 2,500 (50 * 50) |
| A       | :material-account-circle: Mike | :material-check-all: net purchases | 1     | $30   | 900 (30 * 30)   |

Now when we compute metric **Net Bookings per User** from the first table, we end up with two purchases with total value of $80 and **total sample variance 7,600**.

When we compute the same metric from the second table, we end up with two purchases with total value of $80 and **total sample variance 3,400**.

In this specific case **we overestimated sample variance by 4,200 - by 124%**!

## Solutions

There exists three possible solutions of this issue.

### Let it be as it is

We can just let it be as it is now. Actually, there are two scenarios what can happen. We can either overestimate true sample variance or underestimate it.

Overestimating sample variance is not as harmful as underestimating. Overestimating causes we end up with higher p-value and wider confidence intervals. In a nutshell, we are more conservative.
Underestimating is much worse. In this case we have no guarantee our results are trustworthy anymore.

We overestimate the true sample variance if compound metric is subtraction of goals. We underestimate the true sample variance if compound metric is summation of goals. We can both underestimate or overestimate the true sample variance if compound metric is both subtraction and summation of goals.

### Compute Value Squared correctly

We can compute `Value Squared` correctly and avoid all these problems. Unfortunately, this straightforward solution is pretty tricky. It demands non-trivial implementation in EP SQL queries. The interim table `agg_unit_goals` must join itself as many times as many goals compound metric contains.

On the other hand, this is a general solution, and it would solve all problems connected with compound metrics and their sample variances.

### Correct the error

In the next sections we will explicitly derive the error in sample variance. We can adjust the overestimated (underestimated) sample variance using this error. Then we end up with correct value of sample variance. However, this might be messy for compound metrics with more than two goals.

## Error adjustment - subtraction

When the compound metric consists of subtraction of two goals, we overestimate the true sample variance. Firstly, we derive the error for one user. Secondly, we derive the error form multiple users.

### Only one user
Let assume we have only one user. The user made $P$ purchases and $R$ refunds, where $R \leq P$. We denote values of purchases by $p_{i}, \, i = 1, \dots, P$ and values of refunds by $r_{j}, \, j = 1, \dots, R$.

We want to prove that if we compute sample variance of `net purchases` from `agg_unit_goals` table, we will overestimate the true sample variance (right side of inequality). The true sample variance is on the left side of the inequality.

\begin{split}
\big( \sum_{i = 1}^{P} p_{i} - \sum_{j = 1}^{R} r_{j} \big)^{2} & \leq \big( \sum_{i = 1}^{P} p_{i} \big)^{2} - \big( \sum_{j = 1}^{R} r_{j} \big)^{2}, \\
\big( \sum_{i = 1}^{P} p_{i} \big)^{2} + \big( \sum_{j = 1}^{R} r_{j} \big)^{2} - 2 \sum_{i = 1}^{P} p_{i} \sum_{j = 1}^{R} r_{j} & \leq \big( \sum_{i = 1}^{P} p_{i} \big)^{2} - \big( \sum_{j = 1}^{R} r_{j} \big)^{2}, \\
\big( \sum_{j = 1}^{R} r_{j} \big)^{2} - 2 \sum_{i = 1}^{P} p_{i} \sum_{j = 1}^{R} r_{j} & \leq - \big( \sum_{j = 1}^{R} r_{j} \big)^{2}, \\
0 & \leq 2 \sum_{j = 1}^{R} r_{j} \big( \sum_{i = 1}^{P} p_{i} - \sum_{j = 1}^{R} r_{j} \big).
\end{split}

Since $p_{i} \geq 0$ for $i = 1, \dots, P$ and $r_{j} \geq 0$ for $j = 1, \dots, R$, the right side on the last line is greater or equal to zero. We have proved that the original inequality holds - we overestimate the true sample variance. Next, we have explicitly derived the error term

$$ 2 \sum_{j = 1}^{R} r_{j} \big( \sum_{i = 1}^{P} p_{i} - \sum_{j = 1}^{R} r_{j} \big). $$

### Multiple users

In case of multiple users the problem complicates only slightly. Let assume we have $N$ users. So the inequality is following

$$ \sum_{n = 1}^{N} \Big( \sum_{i = 1}^{P_{n}} p_{i,n} - \sum_{j = 1}^{R_{n}} r_{j,n} \Big)^{2} \leq \sum_{n = 1}^{N} \Big( \big( \sum_{i = 1}^{P_{n}} p_{i,n} \big)^{2} - \big( \sum_{j = 1}^{R_{n}} r_{j,n} \big)^{2} \Big). $$

Since the inequality holds for every single user, it must also holds if we sum them up.

Also the error by how much do we differ is the sum of single errors

$$ \sum_{n = 1}^{N} \Big( 2 \sum_{j = 1}^{R_{n}} r_{j,n} \big( \sum_{i = 1}^{P_{n}} p_{i,n} - \sum_{j = 1}^{R_{n}} r_{j,n} \big) \Big). $$

## Error adjustment - summation

This time we derive error term when we sum two goals. Let assume we want to compute compound metric **All bookings per User** which is defined as purchases plus trial conversions. The compound goal `all purchases` equals to `purchases` + `trails`. In this case we show by how much we underestimate the true sample variance.

### Only one user


Again let assume we have only one user. The user made $P$ purchases and $T$ trial conversions. We denote values of purchases by $p_{i}, \, i = 1, \dots, P$ and values of trial conversions by $t_{k}, \, k = 1, \dots, T$.

We want to prove that if we compute sample variance of `all purchases` from `agg_unit_goals` table, we will underestimate the true sample variance (right side of inequality). The true sample variance is on the left side of the inequality.

\begin{split}
\big( \sum_{i = 1}^{P} p_{i} + \sum_{k = 1}^{T} t_{k} \big)^{2} & \geq \big( \sum_{i = 1}^{P} p_{i} \big)^{2} + \big( \sum_{k = 1}^{T} t_{k} \big)^{2}, \\
\big( \sum_{i = 1}^{P} p_{i} \big)^{2} + \big( \sum_{k = 1}^{T} t_{k} \big)^{2} + 2 \sum_{i = 1}^{P} p_{i} \sum_{k = 1}^{T} t_{k} & \geq \big( \sum_{i = 1}^{P} p_{i} \big)^{2} + \big( \sum_{k = 1}^{T} t_{k} \big)^{2}, \\
2 \sum_{i = 1}^{P} p_{i} \sum_{k = 1}^{T} t_{k} & \geq 0.
\end{split}

Since $p_{i} \geq 0$ for $i = 1, \dots, P$ and $t_{k} \geq 0$ for $k = 1, \dots, T$, the left side on the last line is greater or equal to zero. We have proved that the original inequality holds - we underestimate the true sample variance. Next, we have explicitly derived the error term

$$ 2 \sum_{i = 1}^{P} p_{i} \sum_{k = 1}^{T} t_{k}. $$

### Multiple users

In case of multiple users the problem complicates only slightly. Let assume we have $N$ users. So the inequality is following

$$ \sum_{n = 1}^{N} \Big( \sum_{i = 1}^{P_{n}} p_{i,n} + \sum_{k = 1}^{T_{n}} t_{k,n} \Big)^{2} \geq \sum_{n = 1}^{N} \Big( \big( \sum_{i = 1}^{P_{n}} p_{i,n} \big)^{2} + \big( \sum_{k = 1}^{T_{n}} t_{k, n} \big)^{2} \Big). $$

Since the inequality holds for every single user, it must also holds if we sum them up.

Also the error by how much do we differ is the sum of single errors

$$ \sum_{n = 1}^{N} \Big( 2 \sum_{i = 1}^{P_{n}} p_{i,n} \sum_{k = 1}^{T_{n}} t_{k,n} \Big). $$
