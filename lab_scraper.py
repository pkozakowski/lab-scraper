import argparse
import asyncio
import csv
import os

import config
import data
import scraping
import streams


def escape_id(id):
    return id.replace("/", "_")


async def postprocess_paper(paper, citations, content_path):
    if paper.url is not None and scraping.is_arxiv_url(paper.url):
        if citations:
            n_citations = await scraping.arxiv_fetch_citations(paper.url)
        else:
            n_citations = None

        paper = paper._replace(
            n_citations=n_citations, id=escape_id(scraping.arxiv_pub_id(paper.url))
        )

        if content_path is not None:
            content = await scraping.arxiv_fetch_content(paper.url)
            with open(os.path.join(content_path, paper.id), "wb") as f:
                f.write(content)

    return paper


async def stream_all_papers(
    subscriptions, limit, citations, content_path, buffer_size=30
):
    count = 0
    tasks = []
    stop = False
    for stream in subscriptions:
        async for paper in stream():
            tasks.append(
                asyncio.create_task(postprocess_paper(paper, citations, content_path))
            )
            count += 1

            if len(tasks) == buffer_size:
                for task in tasks:
                    yield await task
                tasks.clear()

            if count == limit:
                stop = True
                break

        if stop:
            break

    for task in tasks:
        yield await task


def parse_order_by(order_by):
    assert order_by[0] in ("+", "-")
    desc = order_by[0] == "-"
    order_by = order_by[1:]
    return {"key": lambda paper: getattr(paper, order_by) or 0, "reverse": desc}


def write_papers(papers, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(data.Paper._fields)
        writer.writerows(papers)


async def main(
    subscriptions,
    output,
    order_by="-n_citations",
    limit=None,
    citations=True,
    content=None,
):
    if content:
        os.makedirs(content, exist_ok=True)

    papers = [
        paper
        async for paper in stream_all_papers(subscriptions, limit, citations, content)
    ]
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
            "available fields: " + ", ".join(data.Paper._fields)
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        required=False,
        default=None,
        help="limit of the number of papers scraped, for debugging",
    )
    parser.add_argument(
        "--no_citations",
        dest="citations",
        action="store_false",
        help="don't include citation counts",
    )
    parser.add_argument(
        "--content",
        required=False,
        default=None,
        help="path to save the paper contents in",
    )
    kwargs = vars(parser.parse_args())
    asyncio.run(main(config.subscriptions, **kwargs))
