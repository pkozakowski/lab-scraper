# lab-scraper

Tool for scraping the websites of research labs for publications.

## Quickstart

Install: `pip install -e .`. You'll also need [PhantomJS](https://phantomjs.org/).

Run: `lab_scraper.py output.csv`. `lab_scraper.py --help` for more options.

## Configuration

For now we only support scraping [DeepMind](https://www.deepmind.com/research) papers. By default we scrap just those in the "Reinforcement learning" category on their website, but this can be changed by overriding the `lab_scraper.streams` variable.

We plan on supporting more labs in the future. It's easy to add more by subclassing `lab_scraper.PaperStream`. Contributions welcome!
