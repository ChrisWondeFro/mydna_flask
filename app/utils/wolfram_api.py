import requests
from urllib.parse import urlencode
from config import Config

class WolframAPI:
    def __init__(self):
        self.app_id = Config.WOLFRAM_APP_ID
        self.base_url = "http://api.wolframalpha.com/v2/query"

    def query(self, input_query, include_pod_id=None, format=None):
        params = {
            "input": input_query,
            "appid": self.app_id,
            "output": "JSON",
        }

        # If include_pod_id is specified, add it to the parameters
        if include_pod_id:
            params["includepodid"] = include_pod_id
        
        # If format is specified, add it to the parameters
        if format:
            params["format"] = format

        response = requests.get(self.base_url, params=params)
        data = response.json()
        return data
