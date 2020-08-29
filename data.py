import collections


Paper = collections.namedtuple(
    "Paper", ["title", "year", "url", "n_citations", "id"], defaults=[None, None]
)
