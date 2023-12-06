from dirhash import dirhash


def hash_dataset(dataset_root: str, threads: int = 8, algorithm="sha256"):
    return dirhash(
        dataset_root,
        algorithm=algorithm,
        jobs=threads,
        ignore=["dataset_validator_log.txt"],
    )
