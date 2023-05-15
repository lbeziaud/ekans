import json

import pandas as pd

sm = snakemake  # noqa

df = pd.read_feather(sm.input[0])

metadata = [
    {
        "name": c,
        "type": (
            "finite/ordered"
            if (not s.dtype == "category") or s.cat.ordered
            else "finite"
        ),
        "representation": (
            s.cat.categories.tolist()
            if s.dtype == "category"
            else list(map(int, range(s.min(), s.max() + 1)))
        ),
    }
    for c, s in df.items()
]

with open(sm.output[0], "w") as f:
    json.dump(metadata, f)
