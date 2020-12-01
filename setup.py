from setuptools import setup

setup(
    # setup.cfg files are only available in newer version of setuptools
    # this requirement has to be here to cause an error with older versions
    setup_requires=["setuptools >= 40", "wheel >= 0.32", "pytest-runner >= 5.0, <6.0"],
    # Entry point can't be specified in setup.cfg
    entry_points={"console_scripts": ["epstats = epstats.main:main"]},
)
