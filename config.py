import streams


subscriptions = [
    # streams.DeepMind(category="Reinforcement learning"),
    streams.Arxiv(
        categories=["cs.ai", "cs.lg", "cs.sy", "stat.ml"],
        abstract_contains=["reinforcement"],
    ),
]
