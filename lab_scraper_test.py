import csv
import os

import pytest

import data
import lab_scraper
import streams


test_papers = [
    data.Paper(
        title="Model-Based Reinforcement Learning for Atari",
        year=2019,
        url="https://arxiv.org/abs/1903.00374",
        id="1903.00374",
    ),
    data.Paper(
        title="Attention Is All You Need",
        year=2017,
        url="https://arxiv.org/abs/1706.03762",
        id="1706.03762",
    ),
]


class TestStream(streams.PaperStream):
    async def __call__(self):
        for paper in test_papers:
            yield paper._replace(id=None)


def read_papers(output_path):
    with open(output_path, "r", newline="") as f:
        it = iter(csv.reader(f))
        next(it)  # Skip the header.

        def parse_paper(line):
            paper = data.Paper(*line)
            return paper._replace(
                year=int(paper.year),
                n_citations=(
                    int(paper.n_citations) if paper.n_citations != "" else None
                ),
            )

        return list(map(parse_paper, it))


@pytest.mark.asyncio
async def test_writes_papers_with_citations(tmp_path):
    output_path = os.path.join(tmp_path, "out.csv")
    await lab_scraper.main(
        subscriptions=[TestStream()],
        output=output_path,
        order_by="-year",
        citations=True,
    )

    assert os.path.exists(output_path)
    papers = read_papers(output_path)
    assert len(papers) == len(test_papers)
    for (actual, expected) in zip(papers, test_papers):
        assert actual._replace(n_citations=None) == expected
        assert actual.n_citations > 0


@pytest.mark.asyncio
async def test_writes_papers_without_citations(tmp_path):
    output_path = os.path.join(tmp_path, "out.csv")
    await lab_scraper.main(
        subscriptions=[TestStream()],
        output=output_path,
        order_by="-year",
        citations=False,
    )

    assert read_papers(output_path) == test_papers


@pytest.mark.asyncio
async def test_writes_papers_with_content(tmp_path):
    output_path = os.path.join(tmp_path, "out.csv")
    content_path = os.path.join(tmp_path, "content")
    await lab_scraper.main(
        subscriptions=[TestStream()], output=output_path, content=content_path,
    )

    assert os.path.exists(content_path)
    papers = read_papers(output_path)
    paper_ids = set(paper.id for paper in papers)
    content_filenames = set(os.listdir(content_path))
    assert content_filenames == paper_ids

    for filename in content_filenames:
        path = os.path.join(content_path, filename)
        assert os.path.getsize(path) > 0
