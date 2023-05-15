import argparse
import importlib.util
import json
import logging
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.neighbors import KernelDensity
from tapas.attacks import ProbabilityEstimationAttack
from tapas.datasets import TabularDataset, DataDescription
from tapas.generators import Raw
from tapas.threat_models import AuxiliaryDataKnowledge, BlackBoxKnowledge, TargetedMIA

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="/app/input_data", type=Path)
parser.add_argument("--output", default="/app/output", type=Path)
parser.add_argument("--submission", default="/app/ingested_program", type=Path)

n_records = 10000
n_samples = 1000
train_size = 10
n_targets = 100

args = parser.parse_args()

logger.info("Loading dataset...")

with open(args.input / "data.json") as f:
    schema = json.load(f)
description = DataDescription(schema)

df = pd.read_feather(args.input / "data.feather")
df = df.sample(n=n_records, replace=False).reset_index(drop=True)  # downsampling

data = TabularDataset(df, description)

logger.info("Loading submission...")

spec = importlib.util.spec_from_file_location(
    "taskmaster", args.submission / "taskmaster.py"
)
taskmaster = importlib.util.module_from_spec(spec)
sys.modules["taskmaster"] = taskmaster
spec.loader.exec_module(taskmaster)

logger.info("Calling submission...")

targets = taskmaster.sample_targets(df, n_targets)

logger.info("Validating targets...")

assert all(0 <= t < n_records for t in targets), "target index out of range"

unique = set()
assert not any(t in unique or unique.add(t) for t in targets), "duplicate target"

targets = data.get_records(targets)

logger.info("Preparing threat...")

generator = Raw()

data_knowledge = AuxiliaryDataKnowledge(
    data, auxiliary_split=0.5, num_training_records=n_samples
)

sdg_knowledge = BlackBoxKnowledge(generator, num_synthetic_records=n_samples)

threat_model = TargetedMIA(
    attacker_knowledge_data=data_knowledge,
    target_record=targets,
    attacker_knowledge_generator=sdg_knowledge,
    generate_pairs=False,
    replace_target=True,
)

logger.info("Pickling threat...")

with open(args.output / "threat_model.pkl", "wb") as f:
    pickle.dump(threat_model, f)

logger.info("Training attacks...")

attacks = []
for threat_model_for_a_target in threat_model:
    # noinspection PyTypeChecker
    attack = ProbabilityEstimationAttack(KernelDensity(), criterion="accuracy")
    attack.train(threat_model_for_a_target, num_samples=train_size)
    attacks.append(attack)

logger.info("Pickling trained attacks...")

with open(args.output / "attacks.pkl", "wb") as f:
    pickle.dump(attacks, f)
