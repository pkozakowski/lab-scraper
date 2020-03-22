from setuptools import setup, find_packages

setup(
    name='lab-scraper',
    description='Scraper for publications of AI research labs.',
    version='0.0.1',
    scripts=['lab_scraper.py'],
    install_requires=[
        'aiohttp',
        'bs4',
        'phantomjs',
        'selenium',
    ],
)
