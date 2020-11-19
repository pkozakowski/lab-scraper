import asyncio
from concurrent import futures
import tempfile
import warnings

import aiohttp
import bs4
from selenium import webdriver
import textract
from textract.parsers import pdf_parser


async def fetch_static_page(url):
    async with aiohttp.request("GET", url) as resp:
        assert resp.status == 200, "Status {} when fetching {}.".format(
            resp.status, url
        )
        return await resp.text()


async def fetch_file(url):
    async with aiohttp.request("GET", url) as resp:
        assert resp.status == 200, "Status {} when fetching {}.".format(
            resp.status, url
        )
        return await resp.read()


async def fetch_dynamic_page(url, load_time=3):
    web_driver = webdriver.PhantomJS()
    web_driver.get(url)
    await asyncio.sleep(load_time)
    html = web_driver.page_source
    web_driver.close()
    return html


def is_arxiv_url(url):
    return "arxiv" in url


def arxiv_abs_url(url):
    if "abs" not in url:
        assert "pdf" in url, url
        if url.endswith(".pdf"):
            url = url[: -len(".pdf")]
        url = url.replace("pdf", "abs")
    return url


def arxiv_pdf_url(url):
    if "pdf" not in url:
        assert "abs" in url, url
        url = url.replace("abs", "pdf") + ".pdf"
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


async def arxiv_fetch_citations(abs_url):
    ss_url = arxiv_to_semanticscholar(abs_url)
    ss_html = await fetch_static_page(ss_url)
    ss_soup = bs4.BeautifulSoup(ss_html, "html.parser")
    citation_list_label = ss_soup.find("div", {"class": "citation-list__label"})
    if citation_list_label is not None:
        citation_text = citation_list_label.text
        return semanticscholar_parse_citations(citation_text)
    else:
        return None


pool = futures.ProcessPoolExecutor()


def parse_pdf(pdf):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(pdf)
        return pdf_parser.Parser().extract_pdftotext(f.name, layout=True)


async def arxiv_fetch_content(abs_url):
    pdf_url = arxiv_pdf_url(abs_url)
    pdf = await fetch_file(pdf_url)
    try:
        return await asyncio.wrap_future(pool.submit(parse_pdf, pdf))
    except textract.exceptions.ShellError as e:
        warnings.warn(f'Could not parse PDF {pdf_url}: {e}')
        return None
