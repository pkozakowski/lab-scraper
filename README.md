# lab-scraper

Tool for scraping publications of research labs.

## Quickstart

Install: `pip install -e .`. You'll also need [PhantomJS](https://phantomjs.org/).

Run: `lab_scraper.py output.csv`. `lab_scraper.py --help` for more options.

## Configuration

We support scraping [Arxiv](https://arxiv.org), as well the [DeepMind](https://www.deepmind.com/research) website. Paper streams can be customized via the `lab_scraper.subscriptions` variable.

We plan on supporting more labs in the future. It's easy to add more by subclassing `streams.PaperStream`. Contributions welcome!
