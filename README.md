# MyDNA

Look up your DNA variants in a local copy of ClinVar, privately.

Upload the raw data export from AncestryDNA or 23andMe and MyDNA tells you what
the public [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) archive already
records about the variants in your file: the classification, the conditions
they are associated with, how many submitters agree, and how confident ClinVar
is in each record.

It runs entirely on your own machine. Your genome is parsed in memory and never
written to disk.

> [!IMPORTANT]
> **This is not a medical test and not medical advice.** A ClinVar entry means
> someone has submitted an interpretation for a variant, not that you have or
> will develop a condition. Consumer genotyping arrays produce false positives,
> particularly at rare variants. Most people carry variants classified as
> pathogenic for recessive conditions they will never develop. Take anything
> concerning to a clinician or genetic counsellor for proper testing.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/christian/mydna
cd mydna

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

Build the local ClinVar index. This runs once, downloads about 440 MB from
NCBI, and takes a few minutes:

```bash
mydna index build
```

Then start the app and open <http://127.0.0.1:8000>:

```bash
mydna serve
```

That's it. There is no database server to configure, no account to create, and
no configuration file to write.

## How your data is handled

These are the guarantees, and they are enforced by tests in
[`tests/test_privacy.py`](tests/test_privacy.py):

- Your file is **never written to disk**. It is parsed straight from the
  request stream in memory.
- Only the rsIDs are kept. **Your genotype calls are discarded at parse time**
  and are never queried, logged, or displayed.
- **Nothing leaves your machine.** The lookup runs against the local index, and
  the pages load no third-party CSS, fonts, or scripts, so no CDN can observe
  that you generated a report.
- **Nothing is written to logs** beyond counts. No rsIDs, no genotypes.
- Your rendered report is held in memory so the PDF download works, then
  discarded when you clear it, when it expires after 30 minutes, or when you
  stop the app.

The ClinVar index the app queries is public reference data and contains nothing
about you.

## What a report shows

The report groups every matched ClinVar record by classification, ordered from
most to least clinically notable, and within that by variant type.

Each entry gives you the rsID, the gene, the associated conditions, ClinVar's
own classification wording, and a **review confidence rating** of zero to four
stars. That rating matters more than the classification itself: a one-star
"Pathogenic" record from a single submitter with no assertion criteria is a far
weaker signal than a three-star record reviewed by an expert panel. You can
filter the whole report by minimum star rating.

Counts are of ClinVar *records*, not of your variants. A single variant often
holds several records from different submitters who may disagree.

## Commands

| Command | Purpose |
| --- | --- |
| `mydna serve` | Start the web interface on 127.0.0.1:8000 |
| `mydna serve --port 9000` | Use a different port |
| `mydna serve --dev` | Development server with the debugger, loopback only |
| `mydna index build` | Download ClinVar and build the local index |
| `mydna index build --source path/to/variant_summary.txt.gz` | Build from an already-downloaded file |
| `mydna index info` | Show which ClinVar release the index came from |

## Configuration

MyDNA needs no configuration. Every setting is optional and read from the
environment or a `.env` file; see [`.env.example`](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `MYDNA_INDEX_PATH` | `data/clinvar.sqlite` | Where the index lives |
| `MYDNA_DATABASE_URL` | *(unset)* | Use another backend instead of SQLite |
| `MYDNA_HOST` | `127.0.0.1` | Bind address |
| `MYDNA_PORT` | `8000` | Bind port |
| `MYDNA_MAX_UPLOAD_BYTES` | `67108864` | Upload size limit (64 MB) |
| `MYDNA_SECRET_KEY` | *(generated)* | Signs the session cookie used for CSRF |

### Using PostgreSQL

SQLite is the default and is a good fit for a single user. To use Postgres
instead:

```bash
pip install "mydna[postgres]"
export MYDNA_DATABASE_URL="postgresql+psycopg://user:password@localhost/variant_summary"
mydna index build
```

## Supported file formats

AncestryDNA and 23andMe raw data exports, as `.txt`, `.csv`, `.tsv`, or
`.xlsx`. Use the file exactly as downloaded; there is no need to unzip anything
beyond the archive your provider gives you.

Any row whose identifier is not a dbSNP rsID is skipped and counted. That
includes the internal probe identifiers (`i3000001` and similar) that
AncestryDNA includes alongside real rsIDs.

Support for other providers is a welcome contribution; see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Docker

```bash
docker build -t mydna .
docker run --rm -v "$PWD/data:/data" mydna mydna index build
docker run --rm -p 127.0.0.1:8000:8000 -v "$PWD/data:/data" mydna
```

The image runs as an unprivileged user and stores the index on the mounted
volume so it survives rebuilds.

> [!WARNING]
> MyDNA has **no authentication**, by design: it is a local single-user tool.
> Do not publish it to a network or the open internet. Note the
> `127.0.0.1:` prefix on the port mapping above. See [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

The test suite builds its index from a small synthetic fixture, so it needs no
network access and no real genetic data. Please keep it that way.

## Data source and attribution

Variant classifications come from ClinVar, a public archive maintained by the
National Center for Biotechnology Information (NCBI), U.S. National Library of
Medicine. The index is built from
[`variant_summary.txt.gz`](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/),
filtered to GRCh38 rows carrying a dbSNP identifier.

> Landrum MJ, Lee JM, Benson M, et al. ClinVar: improving access to variant
> interpretations and supporting evidence. *Nucleic Acids Research.*
> 2018;46(D1):D1062–D1067.

ClinVar data is not owned by this project, and its contents change as
submitters revise their interpretations. Rebuild your index periodically with
`mydna index build`, and check `mydna index info` to see how old yours is.

## License

MIT. See [LICENSE](LICENSE).
