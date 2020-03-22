import argparse
import asyncio
import collections
import csv
import time

import aiohttp
import bs4
from selenium import webdriver


Paper = collections.namedtuple("Paper", ["title", "year", "n_citations", "url"])


async def fetch_static_page(url):
    async with aiohttp.request("GET", url) as resp:
        assert resp.status == 200, "Status {} when fetching {}.".format(
            resp.status, url
        )
        return await resp.text()


async def fetch_dynamic_page(url, load_time=3):
    web_driver = webdriver.PhantomJS()
    web_driver.get(url)
    await asyncio.sleep(load_time)
    html = web_driver.page_source
    web_driver.close()
    return html


def arxiv_abs_url(url):
    if "abs" not in url:
        assert "pdf" in url, url
        if url.endswith(".pdf"):
            url = url[: -len(".pdf")]
        url = url.replace("pdf", "abs")
    return url


def arxiv_pub_id(abs_url):
    index = abs_url.find("/abs/") + len("/abs/")
    return abs_url[index:]


def arxiv_year(abs_url):
    pub_id = arxiv_pub_id(abs_url)
    return 2000 + int(pub_id[:2])


def arxiv_to_semanticscholar(abs_url):
    pub_id = arxiv_pub_id(abs_url)
    if pub_id[-2] == "v":
        pub_id = pub_id[:-2]
    elif pub_id[-3] == "v":
        pub_id = pub_id[:-3]
    return "https://api.semanticscholar.org/arXiv:" + pub_id


def semanticscholar_parse_citations(citation_text):
    # Pattern: SHOWING 1-N OF N CITATIONS
    return int(citation_text.split(" ")[3].replace(",", ""))


class PaperStream:
    async def __call__(self):
        """Generates a stream of Papers."""
        raise NotImplementedError


class DeepMindStream(PaperStream):

    URL_ROOT = "https://www.deepmind.com"
    PUBLIST_URL_TEMPLATE = (
        URL_ROOT + "/research?sort=oldest_first&"
        'filters={{"tags":{tags}}}&page={page}'
    )

    def __init__(self, category=None):
        self._tags = [category] if category is not None else []

    async def __call__(self):
        titles = set()
        page = 1
        while True:
            url = self.PUBLIST_URL_TEMPLATE.format(
                tags=str(self._tags), page=page
            ).replace("'", '"')
            html = await fetch_dynamic_page(url)
            soup = bs4.BeautifulSoup(html, "html.parser")
            pub_cards = soup.find_all("dm-publication-card")
            assert pub_cards

            tasks = []
            for pub_card in pub_cards:
                link = pub_card.find("div", {"class": "body"}).find("a")
                title = link.text.strip()
                if title in titles:
                    return
                titles.add(title)

                tasks.append(
                    asyncio.create_task(
                        self._fetch_paper(title, self.URL_ROOT + link["href"])
                    )
                )
            for task in tasks:
                yield await task

            page += 1

    async def _fetch_paper(self, title, pub_url):
        pub_html = await fetch_static_page(pub_url)
        pub_soup = bs4.BeautifulSoup(pub_html, "html.parser")
        arxiv_url = None
        for link in pub_soup.find("div", {"class": "publication-links"}).find_all("a"):
            if "arxiv" in link["href"]:
                arxiv_url = arxiv_abs_url(link["href"])

        if arxiv_url is not None:
            year = arxiv_year(arxiv_url)
            ss_url = arxiv_to_semanticscholar(arxiv_url)
            ss_html = await fetch_static_page(ss_url)
            ss_soup = bs4.BeautifulSoup(ss_html, "html.parser")
            citation_text = ss_soup.find("div", {"class": "citation-list__label"}).text
            n_citations = semanticscholar_parse_citations(citation_text)
        else:
            year = None
            n_citations = None

        return Paper(title=title, year=year, url=arxiv_url, n_citations=n_citations)


streams = [
    DeepMindStream(category="Reinforcement learning"),
]


async def stream_all_papers(limit):
    count = 0
    for stream in streams:
        async for paper in stream():
            if count == limit:
                return
            yield paper
            count += 1


def parse_order_by(order_by):
    assert order_by[0] in ("+", "-")
    desc = order_by[0] == "-"
    order_by = order_by[1:]
    return {"key": lambda paper: getattr(paper, order_by) or 0, "reverse": desc}


def write_papers(papers, output):
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(Paper._fields)
        writer.writerows(papers)


async def main(output, order_by, limit):
    papers = [paper async for paper in stream_all_papers(limit)]
    papers.sort(**parse_order_by(order_by))
    write_papers(papers, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="path to the output CSV")
    parser.add_argument(
        "--order_by",
        required=False,
        default="-n_citations",
        help=(
            "field to order by, preceded to +/- (ascending/descending); "
            "available fields: " + ", ".join(Paper._fields)
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        required=False,
        default=None,
        help="limit of the number of papers scraped, for debugging",
    )
    kwargs = vars(parser.parse_args())
    asyncio.run(main(**kwargs))
