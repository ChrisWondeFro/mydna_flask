# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
rather than opening a public issue.

Please do not include real genetic data in a report. Synthetic examples are
enough to demonstrate any parsing or handling bug.

## Threat model

MyDNA is designed to run **locally, for a single user**. It has no accounts, no
sessions, and no authentication, because it is not intended to be exposed to a
network.

Do not deploy this on a public host. If you expose it, you are serving an
unauthenticated endpoint that accepts and analyses genetic data.

## Data handling guarantees

These are enforced in code and covered by tests:

- An uploaded genome file is **never written to disk**. It is parsed from the
  request stream into memory.
- Only the numeric rsIDs are retained during analysis. Genotype calls are
  discarded at parse time and never queried, logged, or rendered.
- Generated charts and PDFs are built in memory and streamed to the response.
  Nothing is written to a shared location.
- No genomic data is written to logs. Errors report counts and categories, not
  variants.
- No third-party requests are made while rendering a report. All CSS, fonts,
  and scripts are self-hosted, so no CDN can observe your report traffic.

The ClinVar index the app queries is public reference data and contains no user
data.

## Supported versions

Fixes are applied to the latest release only.
