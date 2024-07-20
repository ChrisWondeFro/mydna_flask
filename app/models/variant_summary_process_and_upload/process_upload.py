
import dask
dask.config.set({'dataframe.query-planning': True, 'scheduler': 'processes'})
import dask.dataframe as dd
from dask import delayed, compute
import pandas as pd
from sqlalchemy import create_engine
import requests
import gzip
import os

import tempfile

from dotenv import load_dotenv

def download_file(url, file_name):
    response = requests.get(url)
    content = gzip.decompress(response.content)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with open(file_name, 'wb') as f:
        f.write(content)

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_DB = os.getenv("POSTGRES_DB")

SQLALCHEMY_DATABASE_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PW}@{POSTGRES_URL}/{POSTGRES_DB}'

def download_file(url, file_name):
    response = requests.get(url)
    content = gzip.decompress(response.content)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with open(file_name, 'wb') as f:
        f.write(content)

def preprocess_chunk(chunk):
    # Efficient column renaming and conversion to lower case using a dictionary mapping
    rename_mapping = {
        'rs# (dbsnp)': 'rs_dbsnp',
        'nsv/esv (dbvar)': 'nsv_esv_dbvar',
        '#alleleid': 'alleleid'
    }
    chunk = chunk.rename(columns={k.lower(): v.lower() for k, v in rename_mapping.items()})
    
    # Define columns to convert to integers and clean up
    integer_columns = ['alleleid', 'geneid', 'clinsigsimple', 'rs_dbsnp',
                       'chromosome', 'start', 'stop', 'variationid', 'positionvcf']
    
    chunk[integer_columns] = chunk[integer_columns].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

    # Clean 'clinicalsignificance' using vectorized string operations
    chunk['clinicalsignificance'] = chunk['clinicalsignificance'].str.replace(r'[^a-zA-Z\s]', '', regex=True)

    # Remove header rows 
    chunk = chunk[~chunk.isin([chunk.columns]).any(1)]

    return chunk

def upload_chunks(chunks, engine):
    for first_chunk, chunk in chunks:
        if_exists_method = 'replace' if first_chunk else 'append'
        chunk.to_sql('variant_summary_table', con=engine, index=False, if_exists=if_exists_method)


def preprocess_and_upload_data():
    chunksize = 950000 
    engine = create_engine(SQLALCHEMY_DATABASE_URI)

    url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
    file_name = "downloaded_variant_summary.txt"
    download_file(url, file_name)

    ddf = dd.read_csv(
        file_name,
        delimiter="\t",
        dtype=str, 
        blocksize=chunksize)

    # Process chunks in parallel using Dask
    processed_chunks = (ddf.map_partitions(preprocess_chunk, meta=ddf).to_delayed())

    # Prepare chunk upload tasks, marking the first chunk for special handling
    upload_tasks = [(i == 0, chunk) for i, chunk in enumerate(processed_chunks)]

    # Sequentially upload chunks to the database; consider parallelizing if appropriate
    upload_chunks(upload_tasks, engine)


def main():
    preprocess_and_upload_data()

if __name__ == "__main__":
    main()
