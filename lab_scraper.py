import argparse
import asyncio
import csv

import config
import data
import scraping
import streams


def escape_id(id):
    return id.replace("/", "_")


async def postprocess_paper(paper, citations):
    if paper.url is not None and scraping.is_arxiv_url(paper.url):
        if citations:
            n_citations = await scraping.arxiv_fetch_citations(paper.url)
        else:
            n_citations = None

        paper = paper._replace(
            n_citations=n_citations, id=escape_id(scraping.arxiv_pub_id(paper.url))
        )

    return paper


async def stream_all_papers(subscriptions, limit, citations, buffer_size=30):
    count = 0
    tasks = []
    stop = False
    for stream in subscriptions:
        async for paper in stream():
            tasks.append(asyncio.create_task(postprocess_paper(paper, citations)))
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


def write_papers(papers, output):
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(data.Paper._fields)
        writer.writerows(papers)


async def main(subscriptions, output, order_by, limit, citations):
    papers = [
        paper async for paper in stream_all_papers(subscriptions, limit, citations)
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
    kwargs = vars(parser.parse_args())
    asyncio.run(main(config.subscriptions, **kwargs))
