import aiohttp
import asyncio
from typing import List
import json
import aredis 
from aiohttp.client_exceptions import ClientConnectionError, ClientResponseError

class HttpClient:
    def __init__(self, base_url, headers=None, concurrent_limit=15):
        self.base_url = base_url
        self.headers = headers or {}
        self.concurrent_limit = concurrent_limit

    async def fetch(self, session, endpoint):
        url = f"{self.base_url}/{endpoint}"
        try:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()
        except ClientConnectionError as e:
            print(f"Connection error for {url}: {e}")
        except ClientResponseError as e:
            print(f"Response error for {url}: {e.status}, message: {e.message}")
        except Exception as e:
            print(f"An error occurred: {e}")
        return None

    async def request(self, endpoints: List[str]):
        tasks = []
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(self.concurrent_limit)
            for endpoint in endpoints:
                async with sem:
                    task = asyncio.ensure_future(self.fetch(session, endpoint))
                    tasks.append(task)
            return await asyncio.gather(*tasks)

class RedisClient:
    def __init__(self):
        self.redis = aredis.StrictRedis(host='localhost', port=6379, db=0)  # replace with your Redis host and port


    async def get(self, key):
        data = await self.redis.get(key)
        return json.loads(data) if data is not None else None

    async def set(self, key, value):
        await self.redis.set(key, json.dumps(value))

class EnsemblAPI:
    def __init__(self):
        headers = {"Content-Type": "application/json"}
        self.http_client = HttpClient("https://rest.ensembl.org", headers=headers)
        self.redis_client = RedisClient()

    async def cache_wrapper_async(self, func, *args, **kwargs):
        key = json.dumps((func.__name__, args, kwargs))  # a simple way to generate a unique key
        data = await self.redis_client.get(key)
        if data is not None:
            return data  # if the key exists in the cache, return its value

        # otherwise, fetch the data and store it in the cache
        result = await func(*args, **kwargs)
        await self.redis_client.set(key, result)
        return result

    async def get_variants_information(self, rsids: List[str]):
        return await self.cache_wrapper_async(self.http_client.request, [f"vep/human/{rsids}" for rsids in rsids])
    
    async def get_variants_population_data(self, rsids: List[str]):
        return await self.cache_wrapper_async(self.http_client.request, [f"variation/human/{rsids}" for rsids in rsids])
    
    async def get_variant_regions_information(self, rsids: List[str]):
        return await self.cache_wrapper_async(self.http_client.request, [f"vep/human/region/{rsids}" for rsids in rsids])
    
class DataProcessor:
    def __init__(self, api_client: EnsemblAPI): 
        self.api_client = api_client

    async def ensembl_variants_inforamtion(self, species: str, accessions: List[str]):
        return await self.api_client.get_variants_information(species, accessions)
    
    async def variants_population_data(self, species: str, accessions: List[str]):
        return await self.api_client.get_variants_population_data(species, accessions)
    
    async def variant_information_regions(self, species: str, accessions: List[str]):
        return await self.api_client.get_variant_regions_information(species, accessions)
    
    


    
