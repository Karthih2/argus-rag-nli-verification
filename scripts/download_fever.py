"""One-time setup: download FEVER-NLI dev and create the fixed 600-pair sample.

Run from the repo root: python -m scripts.download_fever
"""

from eval.fever_data import SAMPLE_FILE, load_dev, make_sample


def main() -> None:
    dev = load_dev()
    if SAMPLE_FILE.exists():
        status = "kept existing"  # reuse it so results stay comparable across runs
    else:
        status = f"created ({len(make_sample(dev))} rows)"
    print(f"dev rows: {len(dev)} | sample {SAMPLE_FILE}: {status}")


if __name__ == "__main__":
    main()
