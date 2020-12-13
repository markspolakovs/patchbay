from typing import Dict
from fastapi import FastAPI
from fastapi.params import Body
import logging

logging.basicConfig(level=logging.DEBUG)

import sys
sys.setrecursionlimit(96)

import models
from state import PatchBayState

state = PatchBayState()
state.init()

app = FastAPI()


@app.get("/state", response_model=models.StateModel)
def get_state():
    result = {
        "all_nodes": {
            typename: {id: node._props for id, node in nodes.items()}
            for typename, nodes in state.all_nodes.items()
        },
        "all_links": [
            {"from": f"{src.node.id}[{src.id}]", "to": f"{tgt.node.id}[{tgt.id}]"}
            for src, tgt in state.all_links
        ],
    }
    return result


@app.get("/node/{type}/{id}/props", response_model=Dict[str, str])
def get_props(type: str, id: str):
    node = state.all_nodes[type][id]
    return node._props


@app.put("/node/{type}/{id}/props/{field}")
def set_prop_field(type: str, id: str, field: str, body: str = Body("")):
    node = state.all_nodes[type][id]
    new_props = dict(node._props)
    new_props[field] = body
    node.update(new_props)
