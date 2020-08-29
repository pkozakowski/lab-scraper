import pytest

import streams


@pytest.mark.parametrize(
    "stream",
    [
        streams.Arxiv(
            categories=["cs.ai", "stat.ml"], abstract_contains=["reinforcement"],
        ),
        streams.DeepMind(category="Reinforcement learning"),
    ],
)
@pytest.mark.asyncio
async def test_stream(stream):
    it = stream()
    paper1 = await it.__anext__()
    paper2 = await it.__anext__()
    assert paper1 != paper2
