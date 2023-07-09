import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import re
from dotenv import load_dotenv 
from config import Config

load_dotenv()
config = Config()

POSTGRES_URL = os.getenv("POSTGRES_URL")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_DB = os.getenv("POSTGRES_DB")

SQLALCHEMY_DATABASE_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PW}@{POSTGRES_URL}/{POSTGRES_DB}'

def preprocess_and_upload_data():
    chunksize = 10 ** 6  # adjust according to your needs 
    first_chunk = True
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    for chunk in pd.read_csv('/Users/christian/Documents/MyDNA Database and Upload/database/variant_summary/variant_summary.txt', delimiter="\t", chunksize=chunksize, dtype=str):
        # Convert all column names to lower case
        chunk.columns = chunk.columns.str.lower()
        # Rename columns
        chunk = chunk.rename(columns={
            'rs# (dbsnp)': 'rs_dbsnp', 
            'nsv/esv (dbvar)': 'nsv_esv_dbvar',
            '#alleleid': 'alleleid'
        })
        integer_columns = ['alleleid', 'geneid', 'clinsigsimple', 'rs_dbsnp', 
                       'chromosome', 'start', 'stop', 'variationid', 'positionvcf']


        # Ensure integer columns contain only integer values
        for col in integer_columns:
            # If the column exists in the chunk
            if col in chunk.columns:
                # Convert to numeric and coerce errors to NaN
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
                # Fill NaN values with a default value
                chunk[col] = chunk[col].fillna(0).astype(int)

        # Clean 'clinicalsignificance' column from integer rows
        chunk['clinicalsignificance'] = chunk['clinicalsignificance'].apply(lambda row: re.sub(r'[^a-zA-Z\s]', '', str(row)))
        # Clean 'GeneID', 'ClinSigSimple', and 'RS_dbsnp' for any text or non-integer rows
        for col in ['geneid', 'clinsigsimple', 'rs_dbsnp']:
            if col in chunk.columns:
                # Convert to numeric and coerce errors to NaN
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
                # Remove any row where col is NaN
                chunk = chunk[np.isfinite(chunk[col])]
                # Convert back to integer
                chunk[col] = chunk[col].astype(int)

        # Remove header rows
        for col in chunk.columns:
            chunk = chunk[chunk[col] != col]

        if first_chunk:
            chunk.to_sql('variant_summary_table', engine, index=False, if_exists='replace')
            first_chunk = False
        else:
            chunk.to_sql('variant_summary_table', engine, index=False, if_exists='append')

def main():
    preprocess_and_upload_data()

if __name__ == "__main__":
    main()
