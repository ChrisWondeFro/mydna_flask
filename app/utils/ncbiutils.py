import asyncio
import httpx
import redis
import json
from Bio import Entrez
from typing import List 
from config import Config
from redis.exceptions import RedisError


config = Config()

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.cache = redis.Redis(connection_pool=self.pool)

    def get(self, key):
        try:
            return self.cache.get(key)
        except RedisError as e:
            print(f"Redis error: {e}")
            return None

    def set(self, key, value):
        try:
            self.cache.set(key, value)
        except RedisError as e:
            print(f"Redis error: {e}")

class HttpClient:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def get(self, url):
        response = await self.client.get(url)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")
        return response.json()            

class NcbiClient:
    def __init__(self):
        Entrez.api_key = config.NCBI_API_KEY
        Entrez.email = config.NCBI_API_EMAIL

    def esearch(self, db, term):
        handle = Entrez.esearch(db=db, term=term)
        record = Entrez.read(handle)
        handle.close()
        return record

    def efetch(self, db, id, retmode):
        handle = Entrez.efetch(db=db, id=id, retmode=retmode)
        record = Entrez.read(handle)
        handle.close()
        return record

    def esummary(self, db, id):
        handle = Entrez.esummary(db=db, id=id)
        record = Entrez.read(handle)
        handle.close()
        return record

class ApiClient:
    def __init__(self):
        self.redis_client = RedisClient()
        self.http_client = HttpClient()
        self.ncbi_client = NcbiClient()

    async def get_data_async(self, url):
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")
        return response.json()

    def cache_key(self, *args, **kwargs):
        return str(args) + str(kwargs)

    def cache_wrapper_sync(self, func):
        def inner(*args, **kwargs):
            key = self.cache_key(*args, **kwargs)
            cached_result = self.cache.get(key)
            if cached_result is not None:
                return json.loads(cached_result.decode('utf-8'))
            result = func(*args, **kwargs)
            self.cache.set(key, json.dumps(result))
            return result
        return inner

    async def cache_wrapper_async(self, func, *args, **kwargs):
        key = self.cache_key(*args, **kwargs)
        cached_result = self.cache.get(key)
        if cached_result is not None:
            return json.loads(cached_result.decode('utf-8'))  # Redis returns bytes, so decode it.
        result = await func(*args, **kwargs)
        self.cache.set(key, json.dumps(result))
        return result

    async def get_refSNP_info(self, rsid):
        url = f"https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/{rsid}"
        return await self.cache_wrapper_async(self.get_data_async, url)

    async def get_gene_info(self, rsid):
        # Query the dbSNP database for the rsID
        handle = Entrez.esearch(db="snp", term=rsid)
        record = Entrez.read(handle)
        handle.close()

        # If the rsID was found in the database, retrieve the associated genes
        if record["Count"] != "0":
            handle = Entrez.efetch(db="snp", id=record["IdList"][0], retmode="xml")
            record = Entrez.read(handle)
            handle.close()

            for item in record[0]['SNP']['SnpTypeAnnot']['Gene']:
                # Query the Gene database for the gene ID
                handle = Entrez.esummary(db="gene", id=item['GeneId'])
                record = Entrez.read(handle)
                handle.close()

                return record[0]['Summary']

        else:
            # If no information from NCBI, return None
            return None

    async def get_clinvar_info(self, rsid):
        """
        Function to get information from ClinVar for a specific rsID.
        """
        # Query the ClinVar database for the rsID
        # The specifics of this operation will depend on the ClinVar API
        # or database you're using. This is just a placeholder.

        handle = Entrez.esearch(db="clinvar", term=rsid)
        record = Entrez.read(handle)
        handle.close()

        # Extract and return the necessary information from the record
        # The specifics of this operation will depend on the structure of
        # the data returned by the ClinVar API or database.
        return record

    async def get_pubmed_info(self, rsid):
        """
        Function to get PubMed articles related to a specific rsID.
        """
        # Query the PubMed database for the rsID
        handle = Entrez.esearch(db="pubmed", term=rsid)
        record = Entrez.read(handle)
        handle.close()

        # Extract and return the necessary information from the record
        # The specifics of this operation will depend on the structure of
        # the data returned by the PubMed API or database.
        return record

    async def get_all_gene_info(self, rsids: List[str]):
        tasks = [self.get_gene_info(rsid) for rsid in rsids]
        return await asyncio.gather(*tasks)
