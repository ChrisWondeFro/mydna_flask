# Contributing to MyDNA

Thanks for your interest in improving MyDNA.

## Ground rule: never commit real genetic data

Test fixtures must be **synthetic**. `tests/fixtures/` contains generated files
with made-up rsIDs and genotypes. Never add a real AncestryDNA, 23andMe, or VCF
export to this repository, not even your own, and not even in a branch you plan
to delete. Git history is forever.

`.gitignore` blocks the common export filenames as a backstop, but it is a
backstop, not a substitute for care.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite, which uses a small fixture index and needs no network:

```bash
pytest
```

Lint and format:

```bash
ruff check .
ruff format .
```

To run the app you need a ClinVar index. Building the real one downloads about
440 MB from NCBI:

```bash
mydna index build
mydna serve
```

## Pull requests

- Keep changes focused. One concern per PR.
- Add tests for behaviour changes, especially in `mydna/core/parser.py`, which
  handles the widest variety of real-world input.
- Run `pytest` and `ruff check .` before pushing. CI runs both.
- If you change how uploaded data is handled, say so explicitly in the PR
  description. The guarantees in [SECURITY.md](SECURITY.md) are the project's
  core promise and are covered by tests in `tests/test_privacy.py`.

## Areas that would help most

- Support for more raw-data export formats (MyHeritage, FamilyTreeDNA, VCF).
- Better clinical-significance grouping. ClinVar's free-text values are messy
  and the current normalisation in `mydna/core/report.py` is deliberately
  conservative.
- Accessibility improvements to the report interface.

## Scope

MyDNA reports what ClinVar already says about variants in your file. It is not
a risk calculator and does not attempt interpretation beyond ClinVar's own
assertions. Proposals that turn it into a diagnostic or predictive tool are out
of scope, for both ethical and regulatory reasons.
