import pandas as pd
import numpy as np
import scipy.stats as st
from typing import Optional, Union
from statsmodels.stats.multitest import multipletests
import warnings

DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_POWER = 0.8


class Statistics:
    """
    Various methods needed to evaluate experiment.
    """

    @classmethod
    def ttest_evaluation(cls, stats: np.array, control_variant: str) -> pd.DataFrame:
        """
        Testing statistical significance of relative difference in means of treatment and control variant.

        This is inspired by [scipy.stats.ttest_ind_from_stats](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind_from_stats.html)
        method that returns many more statistics than p-value and test statistic.

        Statistics used:

        1. [Welch's t-test](https://en.wikipedia.org/wiki/Welch%27s_t-test)
        1. [Welch–Satterthwaite equation](https://en.wikipedia.org/wiki/Welch%E2%80%93Satterthwaite_equation)
        approximation of degrees of freedom.

        Arguments:
            stats: array with dimensions (metrics, variants, stats)
            control_variant: string with the name of control variant

        `stats` array values:

        0. `metric_id`
        1. `metric_name`
        1. `exp_variant_id`
        1. `count`
        1. `mean`
        1. `std`
        1. `sum_value`
        1. `sum_sqr_value`

        Returns:
            dataframe containing statistics from the t-test

        Schema of returned dataframe:

        1. `metric_id` - metric id as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `metric_name` - metric name as in [`Experiment`][epstats.toolkit.experiment.Experiment] definition
        1. `exp_variant_id` - variant id
        1. `count` - number of exposures, value of metric denominator
        1. `mean` - `sum_value` / `count`
        1. `std` - sample standard deviation
        1. `sum_value` - value of goals, value of metric nominator
        1. `confidence_level` - current confidence level used to calculate `p_value` and `confidence_interval`
        1. `diff` - relative diff between sample means of this and control variant
        1. `test_stat` - value of test statistic of the relative difference in means
        1. `p_value` - p-value of the test statistic under current `confidence_level`
        1. `confidence_interval` - confidence interval of the `diff` under current `confidence_level`
        1. `standard_error` - standard error of the `diff`
        1. `degrees_of_freedom` - degrees of freedom of this variant mean
        """
        stats = stats.transpose(1, 2, 0)

        stat_res = []  # semiresults
        variants_count = stats.shape[0]  # number of variants

        # get only stats (not metric_id, metric_name, exp_variant_id) from the stats array as floats
        stats_values = stats[:, 3:8, :].astype(float)

        # select stats data for control variant
        for s in stats:
            if s[2][0] == control_variant:
                stats_values_control_variant = s[3:8, :].astype(float)
                break

        # control variant values
        count_cont = stats_values_control_variant[0]  # number of observations
        mean_cont = stats_values_control_variant[1]  # mean
        std_cont = stats_values_control_variant[2]  # standard deviation
        conf_level = stats_values_control_variant[4]  # confidence level

        # this for loop goes over variants and compares one variant values against control variant values for
        # all metrics at once. Similar to scipy.stats.ttest_ind_from_stats
        for i in range(variants_count):
            # treatment variant data
            s = stats_values[i]
            count_treat = s[0]  # number of observations
            mean_treat = s[1]  # mean
            std_treat = s[2]  # standard deviation

            # degrees of freedom
            num = (std_cont ** 2 / count_cont + std_treat ** 2 / count_treat) ** 2
            den = (std_cont ** 4 / (count_cont ** 2 * (count_cont - 1))) + (
                std_treat ** 4 / (count_treat ** 2 * (count_treat - 1))
            )

            with np.errstate(divide="ignore", invalid="ignore"):
                # We fill in zeros, when goal data are missing for some variant.
                # There could be division by zero here which is expected as we return
                # nan or inf values to the caller.
                # np.round() in case of roundoff errors, e.g. f = 9.999999998 => trunc(round(f, 5)) = 10
                f = np.trunc(np.round(num / den, 5))  # (rounded & truncated) degrees of freedom

            # t-quantile
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                t_quantile = st.t.ppf(conf_level + (1 - conf_level) / 2, f)  # right quantile

            # relative difference and test statistics
            with np.errstate(divide="ignore", invalid="ignore"):
                # We fill in zeros, when goal data are missing for some variant.
                # There could be division by zero here which is expected as we return
                # nan or inf values to the caller.
                rel_diff = (mean_treat - mean_cont) / np.abs(mean_cont)
                # standard error for relative difference
                rel_se = (
                    np.sqrt(
                        (mean_treat * std_cont) ** 2 / (mean_cont ** 2 * count_cont) + (std_treat ** 2 / count_treat)
                    )
                    / mean_cont
                )
                test_stat = rel_diff / rel_se

            # p-value
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                pval = 2 * (1 - st.t.cdf(np.abs(test_stat), f))

            # confidence interval
            conf_int = rel_se * t_quantile

            # save results
            stat_res.append((rel_diff, test_stat, pval, conf_int, rel_se, f))

        # Tune up results
        s = np.hstack([stats, stat_res])
        s = s.transpose(2, 0, 1)  # move back to metrics, variants, stats order
        x, y, z = s.shape
        arr = s.reshape(x * y, z)

        # Output dataframe
        col = [
            "metric_id",
            "metric_name",
            "exp_variant_id",
            "count",
            "mean",
            "std",
            "sum_value",
            "confidence_level",
            "diff",
            "test_stat",
            "p_value",
            "confidence_interval",
            "standard_error",
            "degrees_of_freedom",
        ]
        r = pd.DataFrame(arr, columns=col)
        return r

    @classmethod
    def multiple_comparisons_correction(
        cls, df: pd.DataFrame, n_variants: int, metrics: int, confidence_level: float
    ) -> pd.DataFrame:
        """
        [Holm-Bonferroni correction](https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method)
        for multiple comparisons problem. It is applied when we have more than two variants,
        i.e. we have one control variant and at least two treatment variants.

        It adjusts p-value and length of confidence interval - both to be more conservative.
        [Complete manual](../stats/multiple.md)

        Algorithm:

        For each metric, select (unadjusted) p-values and replace them with adjusted ones.
        Based on adjustment ratio, compute new (adjusted) confidence intervals and replace
        old (unadjusted) ones.

        Arguments:
            df: dataframe as output of [`ttest_evaluation`][epstats.toolkit.statistics.Statistics.ttest_evaluation]
            n_variants: number of variants in the experiment
            metrics: number of metrics of experiment
            confidence_level: desired confidence level at the end of the experiment, e.g. 0.95

        Returns:
            dataframe of the same format as input with adjusted p-values and confidence intervals.
        """
        alpha = 1 - confidence_level  # level of significance

        for m in range(metrics):
            # indices of rows with metric m data
            index_from = m * n_variants + 1
            index_to = (m + 1) * n_variants - 1

            # p-value adjustment
            pvals = df.loc[index_from:index_to, "p_value"].to_list()  # select old p-values
            adj_pvals = multipletests(pvals=pvals, alpha=alpha, method="holm")[1]  # compute adjusted p-values

            # confidence interval adjustment
            # we set ratio to 1 when test_stat is so big that pvals are zero, no reason to update ci
            adj_ratio = np.nan_to_num(pvals / adj_pvals, nan=1)  # adjustment ratio
            adj_alpha = adj_ratio * alpha  # adjusted level alpha

            f = df.loc[index_from:index_to, "degrees_of_freedom"].to_list()  # degrees of freedom
            se = df.loc[index_from:index_to, "standard_error"].to_list()  # standard error

            t_quantile = st.t.ppf(np.ones(n_variants - 1) - adj_alpha + adj_alpha / 2, f)  # right t-quantile
            adj_conf_int = se * t_quantile  # adjusted confidence interval

            # replace (unadjusted) p-values and confidence intervals with new adjusted ones
            df.loc[index_from:index_to, "p_value"] = adj_pvals
            df.loc[index_from:index_to, "confidence_interval"] = adj_conf_int
        return df

    @classmethod
    def obf_alpha_spending_function(cls, confidence_level: int, total_length: int, actual_day: int) -> int:
        """
        [O'Brien-Fleming alpha spending function](https://online.stat.psu.edu/stat509/lesson/9/9.6/).
        We adjust confidence level in time in experiment. Confidence level in this setting is
        a decreasing function of experiment time. See [Sequential Analysis](../stats/sequential.md) for details.

        Arguments:
            confidence_level: required confidence level at the end of the test, e.g. 0.95
            total_length: length of the test in days, e.g. 7, 14, 21
            actual_day: actual days in the experiment period, must be between 1 and `total_length`

        Returns:
            adjusted confidence level with respect to actual day of the experiment and total
            length of the experiment.
        """
        alpha = 1 - confidence_level
        t = actual_day / total_length  # t in (0, 1]
        q = st.norm.ppf(1 - alpha / 2)  # quantile of normal distribution
        alpha_adj = 2 - 2 * st.norm.cdf(q / np.sqrt(t))
        return np.round(1 - alpha_adj, decimals=4)

    @staticmethod
    def required_sample_size_per_variant(
        n_variants: int,
        minimum_effect: float,
        mean: float,
        std: float,
        std_2: Optional[float] = None,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        power: float = DEFAULT_POWER,
    ) -> Union[int, float]:
        """
        Computes the sample size required to reach the defined `confidence_level` and `power`.

        Uses the following formula:

        $$
        N = \\frac{(Z_{1-\\alpha/2} + Z_{1-\\beta})^2(s_1^2 + s_2^2)}{\\Delta^2}
        $$

        where $\\Delta = \\mathrm{MEI}\\mu_1$. When `std_2` is unknown,
        we assume equal variance $s_1^2 = s_2^2$:

        $$
        N = \\frac{(Z_{1-\\alpha/2} + Z_{1-\\beta})^2 2s_1^2}{\\Delta^2}
        $$

        For `confidence_level = 0.95` and `power = 0.8`:
        $$
        N = \\frac{7.84 * 2s_1^2}{\\Delta^2} = \\frac{15.7s_1^2}{\\Delta^2}
        $$

        The calculation is using Bonferroni correction when `n_variants > 2`. The initial
        $\\alpha$ defined by the `confidence_level` parameter is adjusted to

        $$
        \\alpha^{*} = \\alpha / m
        $$

        where $m$ is the number of treatment variants. This correction produces
        greater total sample size than Holm-Bonferroni correction because it assigns
        the most conservative $\\alpha^{*}$ to all variants.

        Arguments:
            n_variants: number of variants in the experiment
            minimum_effect: minimum (relative) effect that we find meaningful to detect
            mean: estimate of the current population mean,
            also known as rate in case of Bernoulli distribution
            std: estimate of the current population standard deviation
            std_2: estimate of the treatment population standard deviation
            confidence_level: confidence level of the test
            power: power of the test

        Returns:
            required sample size
        """

        if minimum_effect < 0:
            raise ValueError("minimum_effect must be greater than zero.")

        if n_variants < 2:
            raise ValueError("There must be at least two variants.")

        two_vars = 2 * (std ** 2) if std_2 is None else (std ** 2 + std_2 ** 2)
        delta = np.float64(mean * minimum_effect)

        alpha = 1 - confidence_level
        m = n_variants - 1
        alpha = alpha / m  # Bonferroni correction
        # 7.84 for 80% power and 95% confidence, alpha / 2 for two-sided hypothesis
        confidence_and_power = (st.norm.ppf(1 - alpha / 2) + st.norm.ppf(power)) ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            samples_size_per_variant = confidence_and_power * (two_vars / delta ** 2)
        return np.round(samples_size_per_variant)

    @classmethod
    def required_sample_size_per_variant_bernoulli(
        cls,
        n_variants: int,
        minimum_effect: float,
        mean: float,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        power: float = DEFAULT_POWER,
        **unused_kwargs,
    ) -> Union[int, float]:
        """
        Computes the sample size required to reach the defined `confidence_level`
        and `power` when the data follow Bernoulli distribution.

        Uses `Statistics.required_sample_size_per_variant` with `std_2` defined as

        $$
        p_2 = p_1(1 + \\mathrm{MEI}) \\\\
        s_2^2 = p_2(1 - p_2) \\\\
        $$

        Arguments:
            n_variants: number of variants in the experiment
            minimum_effect: minimum (relative) effect that we find meaningful to detect
            mean: estimate of the current population mean,
                  also known as rate in case of Bernoulli distribution
            confidence_level: confidence level of the test
            power: power of the test

        Returns:
            required sample size
        """

        if mean > 1 or mean < 0:
            raise ValueError(f"mean must be between zero and one, received {mean}.")

        # if we know minimum effect, we know treatment mean and treatment variance
        # see https://github.com/bookingcom/powercalculator/blob/master/src/js/math.js#L113

        def get_std(mean):
            return np.sqrt(mean * (1 - mean))

        mean_2 = mean * (1 + minimum_effect)

        return cls.required_sample_size_per_variant(
            n_variants=n_variants,
            minimum_effect=minimum_effect,
            mean=mean,
            std=get_std(mean),
            std_2=get_std(mean_2),
            confidence_level=confidence_level,
            power=power,
        )

    @staticmethod
    def power_from_required_sample_size_per_variant(
        n_variants: int,
        sample_size_per_variant: Union[int, float],
        required_sample_size_per_variant: Union[int, float],
        required_power: float = DEFAULT_POWER,
        required_confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> float:
        """
        Computes power based on the ratio of `sample_size_per_variant`
        and `required_sample_size_per_variant`.

        How does it work? Consider the formula for computing the sample size $N$
        for a given $\\alpha$ and $1-\\beta$:

        $$
        N = \\frac{(Z_{1-\\alpha/2} + Z_{1-\\beta})^2(s_1^2 + s_2^2)}{\\Delta^2}
        $$

        We can define the required sample size $N_R$ to reach 80% power as

        $$
        N_r = \\frac{(Z_{1-\\alpha/2} + Z_{0.8})^2(s_1^2 + s_2^2)}{\\Delta^2}
        $$

        The ratio $\\frac{N}{N_r}$ simplifies to

        $$
        \\frac{N}{N_r} = \\frac{(Z_{1-\\alpha/2} + Z_{1-\\beta})^2}{(Z_{1-\\alpha/2} + Z_{0.8})^2}
        $$

        This means that the power can be computed as

        $$
        Z_{1-\\beta} = \\sqrt\\frac{N}{N_r}(Z_{1-\\alpha/2}+Z_{0.8})-Z_{1-\\alpha/2} \\\\
        1-\\beta = \\Phi(Z_{1-\\beta})
        $$

        Arguments:
            n_variants: number of variants in the experiment
            sample_size_per_variant: number of samples in one variant
            required_sample_size_per_variant: number of samples required to reach the
                                              `required_power` using the `required_confidence_level`
            required_confidence_level: confidence level used to compute the
                                       `required_sample_size_per_variant`
            required_power: power used to compute the `required_sample_size_per_variant`

        Returns:
            power
        """

        if n_variants < 2:
            return np.nan

        required_sample_size_ratio = sample_size_per_variant / required_sample_size_per_variant
        alpha = (1 - required_confidence_level) / (n_variants - 1)

        return st.norm.cdf(
            np.sqrt(required_sample_size_ratio) * (st.norm.ppf(1 - alpha / 2) + st.norm.ppf(required_power))
            - st.norm.ppf(1 - alpha / 2)
        )
