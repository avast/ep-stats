# Multiple Comparison Correction
Multiple comparisons problem is a problem, when we perform instead of one statistical test (i.e. difference between A and B variant) multiple statistical tests (i.e. difference between A and B, A and C, A and D). Some of them may have p-values less than 0.05 purely by chance, even if all our null hypotheses are really true.

There exist various solutions. They differ mainly in power and implementation difficulty. We present one-by-one Bonferroni correction, HolmBonferroni method and Sidak correction. We summarize pros and cons of methods and provide step-by-step algorithms. Finally we present simple example in order to compare suggested methods.

Generally HolmBonferroni method and the idk correction are universally more powerful procedures than the Bonferroni correction. Bonferroni correction is the most conservative one and suitable for independent tests.

## Summary
After taking into account computational difficulty and results from a simple, but quite real example, we suggest to use Holm-Bonferroni method.

## Multiple Comparisons Problem

Source [Multiple comparisons problem (Wikipedia)](https://en.wikipedia.org/wiki/Multiple_comparisons_problem).

Let assume we want to test $m$ null hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$. Let denote by $\alpha$ our overall level of significance. Typically we set $\alpha = 0.05$. For each hull hypotheses we calculate p-values $p_{1}, \dots, p_{m}$. We need to adjust these p-values for individual hypotheses $H_{0}^{i}$, $i = 1, \dots, m$ in order to satisfy overall level of significance $\alpha$.

## Bonferroni correction
Source [Bonferroni correction (Wikipedia)](https://en.wikipedia.org/wiki/Bonferroni_correction).

This is the simplest way how to deal with Multiple comparisons problem. It is easy to implement, on the other hand, it is too conservative and tests loose too much power. This correction works in the worst-case scenario that all tests are independent. Since we test difference between A and B, A and C, A and D variant, these tests are dependent and therefore this correction is too stringent.

### Algorithm

1. Compute p-values $p_{1}, \dots, p_{m}$ for all $m$ hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$.
2. Compute adjusted p-values using formula

$$\tilde{p}_{i} = \min \big\{ m \, p_{i}, 1 \big\}, \,\,\, i = 1, \dots, m$$

3. Reject null hypothesis $H_{0}^{i}$ if and only if $\tilde{p}_{i} \leq \alpha$.

### Example

```python
import statsmodels.stats.multitest
pvals=[0.01, 0.04, 0.03]

decision, adj_pvals, sidak_aplha, bonf_alpha = statsmodels.stats.multitest.multipletests(pvals=pvals, alpha=0.05, method='bonferroni')

print(f'Original p-values: \t {pvals}')
print(f'Adjusted p-values: \t {adj_pvals}')
```

    Original p-values: 	 [0.01, 0.04, 0.03]
    Adjusted p-values: 	 [0.03 0.12 0.09]

## HolmBonferroni method
Source [HolmBonferroni method (Wikipedia)](https://en.wikipedia.org/wiki/HolmBonferroni_method).

Holm-Bonferroni method is more powerful than Bonferroni and it is valid under the same assumptions.

### Algorithm

1. Compute p-values $p_{1}, \dots, p_{m}$ for all $m$ hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$.
2. Order p-values from lowest to highest $p_{(1)} \leq \dots \leq p_{(m)}$
3. Let $k$ be the minimal index such that $p_{k} (m + 1 - k) > \alpha$.
4. Reject the null hypotheses $H_{0}^{(1)}, \dots, H_{0}^{(k-1)}$ and do not reject $H_{0}^{(k)}, \dots, H_{0}^{(m)}$.
5. If $k = 1$ then do not reject any of the null hypotheses and if no such $k$ index exist then reject all of the null hypotheses.

### Example



```python
decision, adj_pvals, sidak_aplha, bonf_alpha = statsmodels.stats.multitest.multipletests(pvals=pvals, alpha=0.05, method='holm')

print(f'Original p-values: \t {pvals}')
print(f'Adjusted p-values: \t {adj_pvals}')
```
    Original p-values: 	 [0.01, 0.04, 0.03]
    Adjusted p-values: 	 [0.03 0.06 0.06]


## idk correction
Source [idk correction (Wikipedia)](https://en.wikipedia.org/wiki/idk_correction).

idk correction keeps Type I error rate of exactly $\alpha$ when the tests are independent from each other and all null hypotheses are true. It is less stringent than the Bonferroni correction, but only slightly.

### Algorithm (for $\alpha$)

1. Compute p-values $p_{1}, \dots, p_{m}$ for all $m$ hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$.
2. Reject null hypothesis $H_{0}^{i}$ if and only if associated p-value $p_{i}$ is lower or equal than $\alpha_{SID} = 1 - (1 - \alpha)^{\frac{1}{m}}$.

### Algorithm (for p-values)

1. Compute p-values $p_{1}, \dots, p_{m}$ for all $m$ hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$.
2. Order p-values from lowest to highest $p_{(1)} \leq \dots \leq p_{(m)}$
3. Calculate adjusted p-values $\tilde{p}_{(i)}$ using formula
$$
 \tilde{p}_{(i)}=
     \begin{cases}
        1 - (1 - p_{(i)})^{m} & \text{for $i = 1$},\\
        \max \big\{ \tilde{p}_{(i-1)}, 1 - (1 - p_{(i)})^{m-i+1} \big\} & \text{for $i = 2, \dots, m$}.
     \end{cases}
$$

### Example

```python
decision, adj_pvals, sidak_aplha, bonf_alpha = statsmodels.stats.multitest.multipletests(pvals=pvals, alpha=0.05, method='sidak')

print(f'Original p-values: \t {pvals}')
print(f'Adjusted p-values: \t {adj_pvals}')
```
    Original p-values: 	 [0.01, 0.04, 0.03]
    Adjusted p-values: 	 [0.029701 0.115264 0.087327]


## Confidence Interval Adjustment

After p-values adjustment for Multiple comparisons problem it is also necessary to appropriately adjust confidence intervals. Fortunately this is an easy problem and it does not depend on chosen method. We use duality between p-values and confidence intervals.

### Algorithm

1. Compute (original) p-values $p_{1}, \dots, p_{m}$ for all $m$ hypotheses $H_{0}^{1}, \dots, H_{0}^{m}$.
2. Based on chosen method compute adjusted p-values $\tilde{p}_{1}, \dots, \tilde{p}_{m}$.
3. Compute adjustment ratios $r_{1}, \dots, r_{m}$ such that

$$r_{i} = \frac{p_{i}}{\tilde{p}_{i}}, \,\,\, i = 1, \dots, m.$$

4. Let denote desired confidence level(s) as usual by $\alpha$, e.g. $\alpha = 0.05$. More precisely let assume $\alpha_{1}, \dots, \alpha_{m}$.
5. Compute adjusted confidence levels $\tilde{\alpha}_{1}, \dots, \tilde{\alpha}_{m}$ such that

$$\tilde{\alpha_{i}} = r \, \alpha_{i}.$$

6. Compute $(1 - \alpha_{i})$-confidence intervals such that you use $\tilde{\alpha}_{i}$ instead of $\alpha_{i}$.

!!!note
    Computed confidence intervals using $\tilde{\alpha}_{i}$ instead of $\alpha_{i}$ are actually $(1 - \alpha_{i})$-confidence intervals. Levels of significance DO NOT change, they are still $1 - \alpha_{i}$, not $1 - \tilde{\alpha}_{i}$.

### Example

Unadjusted p-value is $p_{i} = 0.01$. Adjusted p-value is $\tilde{p}_{i} = 0.03$. Adjustment ratio is $r = 1/3$. Desired level of significance is $\alpha = 0.05$. Adjusted level of significance is $\tilde{\alpha} = 0.05 \cdot 1/3 = 0.01667$. So we need to compute $1 - 0.01667 = 0.983 = 98.3\%$-confidence interval in order to get $95\%$-confidence interval.

## Python package

Link to documentation of [Statsmodels package](https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html).
