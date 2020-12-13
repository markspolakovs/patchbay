from typing import Dict, List, Tuple
import toml
import re
import jack
import time
import atexit

from nodes import *

jack_client = jack.Client("selectrator")

all_nodes: Dict[str, Dict[str, Node]] = {}
all_links: List[Tuple[LinkPort, LinkPort]] = []


@atexit.register
def cleanup():
    global all_nodes, all_links
    for source, target in all_links:
        source.node.unlink(source, target)
    for instances in all_nodes.values():
        for instance in instances.values():
            instance.shutdown()


def load_state_from_toml(file_path: str):
    global all_nodes, jack_client, all_links
    data = toml.load(file_path)

    new_instances: List[Node] = []
    for typename in data.keys():
        if typename == "links":
            continue
        klass = globals()[typename]

        for id_part, cfg in data[typename].items():
            id = typename + "." + id_part
            all_nodes.setdefault(typename, {})

            if id_part not in all_nodes[typename]:
                instance = klass(id_part, cfg)
                instance._jack = jack_client
                all_nodes[typename][id_part] = instance
                new_instances.append(instance)

    for instance in new_instances:
        instance.start()

    link_pattern = re.compile(r"([^.]+)\.([^\[]+)\[([^\]]+)\]")

    for link in data["links"]:
        src_match = link_pattern.match(link["from"])
        if not src_match:
            raise Exception(f'Malformed link \'{link["from"]}\'')
        tgt_match = link_pattern.match(link["to"])
        if not tgt_match:
            raise Exception(f'Malformed link \'{link["to"]}\'')

        src_type, src_id, src_port_id = src_match.group(1, 2, 3)
        tgt_type, tgt_id, tgt_port_id = tgt_match.group(1, 2, 3)

        src = all_nodes[src_type][src_id]
        src_port = [port for port in src.OUTPUTS if port.id == src_port_id][0]
        tgt = all_nodes[tgt_type][tgt_id]
        tgt_port = [port for port in tgt.INPUTS if port.id == tgt_port_id][0]

        all_links.append((src_port, tgt_port))


def write_state_to_toml(file_path: str):
    global all_nodes, all_links
    result = {}
    for typename, nodes in all_nodes.items():
        result[typename] = {}
        for id_part, node in nodes.items():
            result[typename][id_part] = node._config
    
    result['links'] = []
    for src, tgt in all_links:
        from_str = f"{src.node.id}[{src.id}]"
        to_str = f"{tgt.node.id}[{tgt.id}]"
        result['links'].append({
            'from': from_str,
            'to': to_str
        })
    
    with open(file_path, 'w') as fd:
        toml.dump(result, fd)


def reconcile_all_links():
    global all_nodes, all_links
    # we set up this temporary dict to avoid needing a quadratic loop over all_links
    links_by_source: Dict[Tuple[str, str], List[Tuple[LinkPort, LinkPort]]] = {}

    for src_port, tgt_port in all_links:
        src_type = src_port.node.__class__.__name__
        src_id = src_port.node._id
        links_by_source.setdefault((src_type, src_id), [])
        links_by_source[(src_type, src_id)].append((src_port, tgt_port))

    for node_type, node_id in links_by_source.keys():
        node = all_nodes[node_type][node_id]
        node.reconcile_links(links_by_source[(node_type, node_id)])


def init():
    load_state_from_toml("init.toml")
    reconcile_all_links()
    write_state_to_toml('state.toml')


def link(source: LinkPort, target: LinkPort):
    global all_links
    if (source, target) in all_links:
        return
    source.node.link_to(source, target)
    all_links.append((source, target))


def unlink(source: LinkPort, target: LinkPort):
    global all_links
    if (source, target) not in all_links:
        return
    source.node.unlink(source, target)
    all_links.remove((source, target))
