import asyncio

import bs4

import data
import scraping


class PaperStream:
    async def __call__(self):
        """Generates a stream of Papers."""
        raise NotImplementedError


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

        year = None
        n_citations = None
        if arxiv_url is not None:
            year = scraping.arxiv_year(arxiv_url)
            ss_url = scraping.arxiv_to_semanticscholar(arxiv_url)
            ss_html = await scraping.fetch_static_page(ss_url)
            ss_soup = bs4.BeautifulSoup(ss_html, "html.parser")
            citation_list_label = ss_soup.find("div", {"class": "citation-list__label"})
            if citation_list_label is not None:
                citation_text = citation_list_label.text
                n_citations = scraping.semanticscholar_parse_citations(citation_text)

        return data.Paper(
            title=title, year=year, url=arxiv_url, n_citations=n_citations
        )
