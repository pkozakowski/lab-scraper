import argparse
import asyncio
import csv

import data
import scraping
import streams


subscriptions = [
    # streams.DeepMind(category="Reinforcement learning"),
    streams.Arxiv(
        categories=["cs.ai", "cs.lg", "cs.sy", "stat.ml"],
        abstract_contains=["reinforcement"],
    )
]


async def postprocess_paper(paper):
    if paper.url is not None and scraping.is_arxiv_url(paper.url):
        n_citations = await scraping.arxiv_fetch_citations(paper.url)
        paper = paper._replace(n_citations=n_citations)
    return paper


async def stream_all_papers(limit, buffer_size=30):
    count = 0
    tasks = []
    for stream in subscriptions:
        async for paper in stream():
            if count == limit or len(tasks) == buffer_size:
                for task in tasks:
                    yield await task
                tasks.clear()

            if count == limit:
                return

            tasks.append(asyncio.create_task(postprocess_paper(paper)))
            count += 1


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
    kwargs = vars(parser.parse_args())
    asyncio.run(main(**kwargs))
