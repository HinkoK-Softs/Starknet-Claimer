import json
import typing

from pydantic import BaseModel

class Config(BaseModel):
    threads: int
    max_retries: int
    rpc_url: str
    comission_mode: str

    @classmethod
    def load(cls):
        with open('config.json') as file:
            data = json.load(file)

        return cls.parse_obj(data)
