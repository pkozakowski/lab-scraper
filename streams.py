import asyncio

import bs4
import feedparser

import data
import scraping


class PaperStream:
    async def __call__(self):
        """Generates a stream of Papers."""
        raise NotImplementedError


class Arxiv(PaperStream):

    api_url_template = (
        "http://export.arxiv.org/api/query?sortBy=lastUpdatedDate&sortOrder=ascending&"
        "search_query={query}&start={start}&max_results={limit}"
    )
    page_limit = 100

    def __init__(self, categories=(), abstract_contains=()):
        def clause(op, xs):
            return "(" + ("+" + op + "+").join(xs) + ")"

        def query_clause(prefix, xs):
            return clause("OR", [prefix + ':"' + x + '"' for x in xs])

        query_elems = []
        if categories:
            query_elems.append(query_clause("cat", categories))
        if abstract_contains:
            query_elems.append(query_clause("abs", abstract_contains))

        self._query = clause("AND", query_elems)

    async def __call__(self):
        page = 0
        n_pages = None
        while page == 0 or page < n_pages:
            url = self.api_url_template.format(
                query=self._query, start=(page * self.page_limit), limit=self.page_limit
            )
            html = await scraping.fetch_static_page(url)
            feed = feedparser.parse(html)

            for entry in feed.entries:
                yield data.Paper(
                    title=entry.title,
                    year=entry.updated_parsed.tm_year,
                    url=entry.link,
                )

            page += 1
            n_pages = (
                int(feed.feed.opensearch_totalresults)
                // int(feed.feed.opensearch_itemsperpage)
                + 1
            )


class DeepMind(PaperStream):

    url_root = "https://www.deepmind.com"
    publist_url_template = (
        url_root + "/research?sort=oldest_first&"
        'filters={{"tags":{tags}}}&page={page}'
    )

    def __init__(self, category=None):
        self._tags = [category] if category is not None else []

    async def __call__(self):
        titles = set()
        page = 1
        while True:
            url = self.publist_url_template.format(
                tags=str(self._tags), page=page
            ).replace("'", '"')
            html = await scraping.fetch_dynamic_page(url)
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
                        self._fetch_paper(title, self.url_root + link["href"])
                    )
                )
            for task in tasks:
                yield await task

            page += 1

    async def _fetch_paper(self, title, pub_url):
        pub_html = await scraping.fetch_static_page(pub_url)
        pub_soup = bs4.BeautifulSoup(pub_html, "html.parser")
        arxiv_url = None
        for link in pub_soup.find("div", {"class": "publication-links"}).find_all("a"):
            if "arxiv" in link["href"]:
                arxiv_url = scraping.arxiv_abs_url(link["href"])

        year = scraping.arxiv_year(arxiv_url) if arxiv_url is not None else None
        return data.Paper(title=title, year=year, url=arxiv_url)
