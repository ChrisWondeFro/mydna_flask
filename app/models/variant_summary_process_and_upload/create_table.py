import psycopg2
from dotenv import load_dotenv 
import os

load_dotenv()

connection = psycopg2.connect(
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PW"),
    host=os.getenv("POSTGRES_URL"),
)

cursor = connection.cursor()

# first drop the table if it exists
cursor.execute("DROP TABLE IF EXISTS variant_summary_table;")

# then create the table
cursor.execute("""
CREATE TABLE variant_summary_table (
    alleleid INTEGER,
    type TEXT,
    name TEXT,
    geneid INTEGER,
    genesymbol TEXT,
    hgnc_id TEXT,
    clinicalsignificance TEXT,
    clinsigsimple INTEGER,
    lastevaluated TEXT,
    rs_dbsnp INTEGER,
    nsv_esv_dbvar TEXT,
    rcvaccession TEXT,
    phenotypeids TEXT,
    phenotypelist TEXT,
    origin TEXT,
    originsimple TEXT,
    assembly TEXT,
    chromosomeaccession TEXT,
    chromosome INTEGER,
    start INTEGER,
    stop INTEGER,
    referenceallele TEXT,
    alternateallele TEXT,
    cytogenetic TEXT,
    reviewstatus TEXT,
    numbersubmitters INTEGER ,
    guidelines TEXT,
    testedingtr TEXT,
    otherids TEXT,
    submittercategories TEXT,
    variationid INTEGER,
    positionvcf INTEGER,
    referenceallelevcf TEXT,
    alternateallelevcf TEXT   
    );
""")

connection.commit()
cursor.close()
connection.close()