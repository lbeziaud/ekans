import argparse
import logging
import pickle
from pathlib import Path

import numpy as np
from tapas.report import MIAttackReport
from joblib import Parallel, delayed

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="/app/input/res", type=Path)
parser.add_argument("--output", default="/app/output", type=Path)

test_size = 20

args = parser.parse_args()

logger.info("Unpickling threat...")

with open(args.input / "threat_model.pkl", "rb") as f:
    threat_model = pickle.load(f)

logger.info("Unpickling trained attack...")

with open(args.input / "attacks.pkl", "rb") as f:
    attacks = pickle.load(f)

logger.info("Testing attacks...")


def test_attack(threat, attack):
    return threat.test(attack, num_samples=test_size)


summaries = Parallel(n_jobs=-1, verbose=10)(
    delayed(test_attack)(threat_model_for_a_target, attack)
    for threat_model_for_a_target, attack in zip(threat_model, attacks)
)

logger.info("Building report...")

with np.errstate(divide="ignore"):
    report = MIAttackReport(summaries)

logger.info("Saving scores...")

metrics = [
    "accuracy",
    "true_positive_rate",
    "false_positive_rate",
    "mia_advantage",
    "privacy_gain",
    "auc",
]

scores = report.attacks_data[metrics].mean()
scores.to_json(args.output / "scores.json", double_precision=4)
