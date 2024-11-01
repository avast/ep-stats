# CTR Metric

The goal of this post is to provide complete manual for deriving asymptotic distribution of Click-through rate (CTR). We are aimed at correct theoretical derivations, including verification of all assumptions. Since CTR is one of the primary metrics in A/B testing, we derive asymptotic distribution for absolute and relative difference in CTR between two variants - control and treatment.

## Theory
We will use two core statistical tools - [Central limit theorem](https://en.wikipedia.org/wiki/Central_limit_theorem) and [Delta method](https://en.wikipedia.org/wiki/Delta_method). There exists a great [YouTube video](https://www.youtube.com/watch?v=JNm3M9cqWyc) from the Khan Academy explaining CLT, we greatly recommend it!

### Central limit theorem
Let $X_{1}, \dots, X_{n}$ be a random sample of size $n$ - a sequence of $n$ independent and identically distributed random variables drawn from a distribution of expected value given by $\mu$ and finite variance given by $\sigma^{2}$. Let denote sample average as $\bar{X_{n}} = \frac{1}{n} \sum_{i=1}^{n} X_{i}$. Then holds

$$ \sqrt{n} \, \big( \bar{X_{n}} - \mu \big) \xrightarrow[\text{n $\rightarrow \, \infty$}]{\text{d}} \mathcal{N} (0, \sigma^{2}), $$

$$ \sqrt{n} \, \big( \bar{X_{n}} - \mu \big) \stackrel{d}{\longrightarrow} \mathcal{N} (0, \sigma^{2}), \,\,\, n \rightarrow \, \infty $$

i.e. as $n$ approaches infinity, the random variables $\sqrt{n} \, \big( \bar{X_{n}} - \mu \big)$ converge in distribution to a normal $\mathcal{N} (0, \sigma^{2})$. Another acceptable, but slightly vague formulations are

$$ \bar{X_{n}} \stackrel{as}{\sim} \mathcal{N} (\mu, \frac{\sigma^{2}}{n}), $$

or

$$ \sqrt{n} \, \frac{\bar{X_{n}} - \mu}{\sigma} \stackrel{as}{\sim} \mathcal{N} (0, 1).$$

### Delta Method - Univariate
Let assume any sequence of random variables $\{T_{n}\}_{n=1}^{\infty}$ satisfying

$$ \sqrt{n} \, \big( T_{n} - \mu \big) \xrightarrow[\text{n $\rightarrow \, \infty$}]{\text{d}} \mathcal{N} \big(0, \, \sigma^{2}\big) $$

$$ \sqrt{n} \, \big( T_{n} - \mu \big) \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, \sigma^{2}\big), \,\,\, n \rightarrow \, \infty $$

and function $g: \mathbb{R} \rightarrow \mathbb{R}$ which has continuous derivative around a point $\mu$, i.e. $g^{'}(\mu)$ is continuous. Then holds

$$ \sqrt{n} \, \big( g(T_{n}) - g(\mu) \big) \xrightarrow[\text{n $\rightarrow \, \infty$}]{\text{d}} \mathcal{N} \big(0, \, [g^{'}(\mu)]^{2}\sigma^{2}\big).$$

$$ \sqrt{n} \, \big( g(T_{n}) - g(\mu) \big) \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, [g^{'}(\mu)]^{2}\sigma^{2}\big), \,\,\, n \rightarrow \, \infty.$$

### Delta Method - Multivariate

Let assume any sequence of random vectors $\{ \pmb{T}_{n} \}_{n=1}^{\infty}$ satisfying

$$ \sqrt{n} \, \big( \pmb{T}_{n} - \pmb{\mu} \big) \xrightarrow[\text{n $\rightarrow \, \infty$}]{\text{d}} \mathcal{N}_{k} \big(\pmb{0}, \, \Sigma\big) $$

$$ \sqrt{n} \, \big( \pmb{T}_{n} - \pmb{\mu} \big) \stackrel{d}{\longrightarrow} \mathcal{N}_{k} \big(\pmb{0}, \, \Sigma\big), \,\,\, n \rightarrow \, \infty $$

and function $g: \mathbb{R^{k}} \rightarrow \mathbb{R^{p}}$ which is continuously differentiable around point $\pmb{\mu}$. Denote $\mathbb{D}(x) = \frac{\partial \, g(x)}{\partial \, x}$. Then holds

$$ \sqrt{n} \, \big( g(\pmb{T}_{n}) - g(\pmb{\mu}) \big) \xrightarrow[\text{n $\rightarrow \, \infty$}]{\text{d}} \mathcal{N}_{p} \big(\pmb{0}, \, \mathbb{D}(\mu) \, \Sigma \, \mathbb{D}(\mu)^{T} \big). $$

$$ \sqrt{n} \, \big( g(\pmb{T}_{n}) - g(\pmb{\mu}) \big) \stackrel{d}{\longrightarrow} \mathcal{N}_{p} \big(\pmb{0}, \, \mathbb{D}(\mu) \, \Sigma \, \mathbb{D}(\mu)^{T} \big), \,\,\, n \rightarrow \, \infty. $$


## CTR Definition

Without loss of generality, we can only focus on the control group with $K$ users. Every user can see test screen multiple times, denoted by $N_{i}, \, i = 1, \dots, K$. $N_{i} \in \mathbb{N}$ is a discrete random variable with unknown probability distribution and finite variance. Next user can click on the screen. This action is denoted by binomial random variable $Y_{i, j}, \, i = 1, \dots, K, \, j = 1, \dots, N_{i}$

$$
 Y_{i, j}=\begin{cases}
    1, & \text{if $i-th$ user clicks in his $j-th$ view},\\
    0, & \text{otherwise}.
  \end{cases}
$$

Click-through rate (CTR) is then defined as sum of all clicks devided by sum of all views

$$ CTR = \frac{\sum_{i=1}^{K} \sum_{j=1}^{N_{i}} Y_{i, j}}{\sum_{i=1}^{K} N_{i}}.$$

We want to derive asymptotic distribution for CTR. But we can not directly use central limit theorem since assumptions are violated. Random variables $Y_{i, j}$ are not independent, nor identically distributed. We can use a little trick[^1] and simply reformulate CTR definition without any change:

$$ CTR = \frac{\sum_{i=1}^{K} \big( \sum_{j=1}^{N_{i}} Y_{i, j} \big)}{\sum_{i=1}^{K} N_{i}} = \frac{\sum_{i=1}^{K} S_{i}}{\sum_{i=1}^{K} N_{i}} = \frac{\sum_{i=1}^{K} S_{i} \big/ K}{\sum_{i=1}^{K} N_{i} \big/ K} = \frac{\bar{S}}{\bar{N}} = \bar{Y}, $$

where $\bar{S} = \frac{1}{K} \sum_{i=1}^{K} S_{i}$ stands for average clicks per user and $\bar{N} = \frac{1}{K} \sum_{i=1}^{K} N_{i}$ stands for average views per user. Users are independent of each other, random variables $N_{i}, \, i = 1, \dots, K$ are independent and indetically distributed. For simplification we will assume that also random variables $S_{i}, \, i = 1, \dots, K$ are independent and identically distributed, but it is only half true. $S_{i}$ are independent, since users are independent of each other, but they are not identically distributed - $S_{1}$ has some unknown discrete distribution on closed interval $[0, N_{1}]$, $S_{2}$ has some unknown discrete distribution on closed interval $[0, N_{2}]$ and so on. Since $N_{i} \in \mathbb{N}, \, i = 1, \dots, K$ are random variables and so $P \big(N_{i} = N_{j} \big) \neq 1$ for $i \neq j$. There exist other versions of central limit theorem which only assume independence, e.g. [Lyapunov CLT](https://en.wikipedia.org/wiki/Central_limit_theorem#Lyapunov_CLT).

## Asymptotic Distribution of CTR

In this part we will derive asymptotic distributon for CTR. CTR is defined as fraction of two random variables - $\bar{S}$ and $\bar{N}$. We will proceed in three steps:

1. We will use CLT and derive asymptotic distributions for both $\bar{S}$ and $\bar{N}$.
2. We will use **delta method - multivariate** and derive asymptotic distribution for CTR.


### Step 1
Since $S_{1}, \dots, S_{K}$ is a random sample, from CLT we have

$$ \sqrt{K} \, \big( \bar{S} - \mu_{S} \big) \stackrel{d}{\longrightarrow} \mathcal{N} (0, \sigma_{S}^{2}). $$

Since $N_{1}, \dots, N_{K}$ is a random sample, from CLT we similary have

$$ \sqrt{K} \, \big( \bar{N} - \mu_{N} \big) \stackrel{d}{\longrightarrow} \mathcal{N} (0, \sigma_{N}^{2}). $$

We can join both asymptotic normal distributions into two dimensional normal distribution

$$ \sqrt{K} \, \Bigg( \begin{pmatrix} \bar{S} \\ \bar{N} \end{pmatrix} - \begin{pmatrix} \mu_{S} \\ \mu_{N} \end{pmatrix} \Bigg) \stackrel{d}{\longrightarrow} \mathcal{N}_{2} \Bigg( \begin{pmatrix} 0 \\ 0 \end{pmatrix}, \begin{pmatrix} \sigma_{S}^{2} & \sigma_{SN} \\ \sigma_{SN} & \sigma_{N}^2 \end{pmatrix} \Bigg), $$

where $\sigma_{SN}$ is covariance between random variables $S$ and $N$ defined as $\sigma_{SN} = \mathrm{cov}(S,N) = \mathbb{E} \big[(S - \mu_{S})(N - \mu_{n})\big]$. Unknown covariance $\sigma_{SN}$ can be easily estimated using following formula

$$ \hat{\sigma_{SN}} = \sum_{i=1}^{K} (S_{i} - \bar{S}_{n}) (N_{i} - \bar{N}_{n}) = \sum_{i=1}^{K} S_{i} N_{i} - K \bar{S}_{n} \bar{N}_{n}. $$

### Step 2

Now we apply **multivariate delta method** with a link function $g: \mathbb{R}^2 \rightarrow \mathbb{R}$ defined as $g(x, y) = \frac{x}{y}$. Gradient in point $(\mu_{S}, \mu_{N})$ equals to

$$\nabla g (\mu_{S}, \mu_{N}) = (\frac{1}{\mu_{N}}, -\frac{\mu_{S}}{\mu_{N}}).$$

Hence we have

$$ \sqrt{K} \, \Bigg( \frac{\bar{S}}{\bar{N}}  - \frac{\mu_{S}}{\mu_{N}} \Bigg) \stackrel{d}{\longrightarrow} \mathcal{N} \Bigg(0, \, \big(\frac{1}{\mu_{N}}, -\frac{\mu_{S}}{\mu_{N}} \big) \begin{pmatrix} \sigma_{S}^{2} & \sigma_{SN} \\ \sigma_{SN} & \sigma_{N}^2 \end{pmatrix} \begin{pmatrix} \frac{1}{\mu_{N}} \\ -\frac{\mu_{S}}{\mu_{N}} \end{pmatrix} \Bigg) $$

Asymptotic distribution for CTR in treatment group with $K$ observations equals to

$$ \sqrt{K} \, \bigg( \bar{Y} - \mu_{Y} \bigg) \stackrel{d}{\longrightarrow} \mathcal{N} \bigg(0, \, \frac{1}{\mu_{N}^2} \big(\sigma_{S}^2 - 2\frac{\mu_{S}}{\mu_{N}}\sigma_{SN} + \frac{\mu_{S}^2}{\mu_{N}^2} \sigma_{N}^2 \big) \bigg),$$
as $K$ approaches infinity.

## Difference Between Control and Treatment Group

We have derived asymptotic distribution fot control group. Analogously we would have derived asymptotic distribution for treatment group. Let's write them both once again

$$\sqrt{K} \, \big( \bar{Y}_{A} - \mu_{A} \big) \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, \sigma_{A}^2 \big),$$
$$\sqrt{L} \, \big( \bar{Y}_{B} - \mu_{B} \big) \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, \sigma_{B}^2 \big),$$

where $\sigma_{A}^2$ and $\sigma_{B}^2$ follows derivations right above (the complicated fomula) and $K$ and $L$ are number of observations in control and treatment group respectively.

Since we have again two asymptotic normal distributions, we can join them into two dimensional normal distribution

$$\Bigg( \begin{pmatrix} \bar{Y}_{A} \\ \bar{Y}_{B} \end{pmatrix} - \begin{pmatrix} \mu_{A} \\ \mu_{B} \end{pmatrix} \Bigg) \stackrel{as}{\sim} \mathcal{N}_{2} \Bigg( \begin{pmatrix} 0 \\ 0 \end{pmatrix}, \begin{pmatrix} \sigma_{A}^{2} \, / \, K & 0 \\ 0 & \sigma_{B}^2 \, / \, {L} \end{pmatrix} \Bigg).$$

This time we used slightly different notation. We do need to be careful now. In general, we have different sample size ($K \neq L$). But on the other hand, in this case we assume there is no correlation between those two distributions, see zeros in covariance matrix.

In A/B testing we are usually interested in whether the difference between treatment and control group is statistically significant. We derive asymptotic distribution for both absolute and relative difference.

### Absolute Difference

Absolute difference is easier. We will use **multivariate delta method** with simple link function $g: \mathbb{R}^2 \rightarrow \mathbb{R}$ defined as $g(x, y) = y - x$. Be aware of order $x$ and $y$ - it is $y - x$, not $x - y$. Gradient in point $(\mu_{A}, \mu_{B})$ equals to

$$ \nabla g (\mu_{A}, \mu_{B}) = (-1, 1) $$

and hence the result is

$$ \big( (\bar{Y}_{B} - \bar{Y}_{A}) - (\mu_{B} - \mu_{A}) \big) \stackrel{as}{\sim} \mathcal{N} \big(0, \, (\frac{\sigma_{A}^2}{K} + \frac{\sigma_{B}^2}{L}) \big).$$

It can be written in following form

$$ Z_{K, L} = \frac{\bar{Y}_{B} - \bar{Y}_{A} - \delta_{0}}{\sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}}} \xrightarrow{\text{d}} \mathcal{N} \big(0, \, 1 \big), $$

$$ Z_{K, L} = \frac{\bar{Y}_{B} - \bar{Y}_{A} - \delta_{0}}{\sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}}} \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, 1 \big), $$

if $K, L \rightarrow \infty$ and $\frac{K}{L} \rightarrow q \in (0, \infty)$. $S_{A}^2$ and $S_{B}^2$ are sample variances.

Two sided asymptotic confidence interval for absolute difference equals to

$$ \Big( \bar{Y}_{B} - \bar{Y}_{A} - u_{1 - \alpha / 2} \, \sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}} ; \,\, \bar{Y}_{B} - \bar{Y}_{A} + u_{1 - \alpha / 2} \, \sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}} \Big), $$

where $u_{1 - \alpha / 2}$ is $(1 - \alpha / 2)-$quantile of normal distribution $\mathcal{N}(0, 1)$.

P-value equals to

$$ p = 2 \big(1 - \Phi(|z|) \big), $$
where $\Phi$ is distribution function of $\mathcal{N}(0, 1)$ and $z$ is observed value of test statistics $Z_{K,L}$.

In practice is usually used **Welch test**, which uses t-distribution instead of normal distribution, with $f$ degrees of freedom given as

$$ f = \frac{\big( \frac{S_{A}^2}{K} + \frac{S_{B}^2}{L} \big)^2}{\frac{S_{A}^4}{K^2 (K-1)} + \frac{S_{B}^4}{L^2 (L-1)}} .$$

Then two sided asymptotic confidence interval (with t-quantiles) for absolute difference equals to

$$ \Big( \bar{Y}_{B} - \bar{Y}_{A} - t_{f}(1 - \alpha / 2) \, \sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}} ; \,\, \bar{Y}_{B} - \bar{Y}_{A} + t_{f}(1 - \alpha / 2) \, \sqrt{\frac{S_{A}^2}{K} + \frac{S_{B}^2}{L}} \Big). $$


P-value equals to

$$ p = 2 \big(1 - \text{CDF}_{t, f}(|z|) \big), $$
where $\text{CDF}_{t,f}$ is cumulative distribution function of t-distribution with $f$ degrees of freedom and $z$ is observed value of test statistics $Z_{K,L}$.


### Relative Difference

To derive asymptotic distribution for relative difference we will again use **multivariate delta method** with a link function $g: \mathbb{R}^2 \rightarrow \mathbb{R}$ defined as $g(x, y) = \frac{y - x}{x}$. Be aware of order $x$ and $y$. Gradient in point $(\mu_{A}, \mu_{B})$ equals to

$$ \nabla g (\mu_{A}, \mu_{B}) = \big( -\frac{\mu_{B}}{\mu_{A}^2}, \frac{1}{\mu_{A}} \big).$$

The result is

$$ \Big( \frac{\bar{Y}_{B} - \bar{Y}_{A}}{\bar{Y}_{A}} - \frac{\mu_{B} - \mu_{A}}{\mu_{A}} \Big) \stackrel{as}{\sim} \mathcal{N} \Big(0, \, \frac{1}{\mu_{A}^2} \big(\frac{\mu_{B}^2}{\mu_{A}^2} \frac{\sigma_{A}^2}{K} + \frac{\sigma_{B}^2}{L} \big)\Big).$$

This can be rewritten in following form

$$ Z_{K, L} = \frac{\frac{\bar{Y}_{B} - \bar{Y}_{A}}{\bar{Y}_{A}} - \delta_{0}^{*}}{\frac{1}{\bar{Y}_{A}} \sqrt{ \frac{\bar{Y}_{B}^2}{\bar{Y}_{A}^2} \frac{S_{A}^2}{K} + \frac{S_{B}^2}{L} }} \xrightarrow{\text{d}} \mathcal{N} \big(0, \, 1 \big), $$

$$ Z_{K, L} = \frac{\frac{\bar{Y}_{B} - \bar{Y}_{A}}{\bar{Y}_{A}} - \delta_{0}^{*}}{\frac{1}{\bar{Y}_{A}} \sqrt{ \frac{\bar{Y}_{B}^2}{\bar{Y}_{A}^2} \frac{S_{A}^2}{K} + \frac{S_{B}^2}{L} }} \stackrel{d}{\longrightarrow} \mathcal{N} \big(0, \, 1 \big), $$

if $K, L \rightarrow \infty$ and $\frac{K}{L} \rightarrow q \in (0, \infty)$. $S_{A}^2$ and $S_{B}^2$ are sample variances.

For unknown true relative difference $\frac{\mu_{B} - \mu_{A}}{\mu_{A}}$ we can derive confidence interval. For simplicity let's denote the sample variance as $\tilde{S}^2$, i.e.:

$$\tilde{S}^2 = \frac{1}{\bar{Y}_{A}} \sqrt{ \frac{\bar{Y}_{B}^2}{\bar{Y}_{A}^2} \frac{S_{A}^2}{K} + \frac{S_{B}^2}{L} }. $$

Finaly, the two sided asymptotic confidence interval for relative difference equals to

$$ \Big( \frac{\bar{Y}_{B} - \bar{Y}_{A}}{\bar{Y}_{A}} - \mu_{1 - \alpha / 2} \, \tilde{S}^2 ; \frac{\bar{Y}_{B} - \bar{Y}_{A}}{\bar{Y}_{A}} + \mu_{1 - \alpha / 2} \, \tilde{S}^2 \Big). $$

P-value equals to

$$ p = 2 \big(1 - \Phi(|z|) \big), $$
where $\Phi$ is distribution function of $\mathcal{N}(0, 1)$ and $z$ is observed value of test statistics $Z_{K,L}$.

Since we know, there is no straightforward approximation using t-quantiles, because there is no formula for degrees of freedom. In practise, we have huge amount of observations and both quantiles (normal and t-quantile) are very close to each other for large $n$.

[^1]: [A. Deng et al., Applying the Delta Method in Metrics Analytics: A Practical Guide with Novel Ideas](https://arxiv.org/pdf/1803.06336.pdf)
