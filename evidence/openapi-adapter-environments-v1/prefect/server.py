import json
import os
import httpx2
from fastmcp import FastMCP

with open(os.environ['STUDY_SPEC']) as stream:
    spec = json.load(stream)
client = httpx2.AsyncClient(base_url='http://127.0.0.1:8765', timeout=5)
server = FastMCP.from_openapi(openapi_spec=spec, client=client, name='adapter-study')
server.run(transport='stdio')
