from typing import Dict, List, Tuple, Union
import toml
import re
import jack
import atexit
import logging
logger = logging.getLogger(__name__)

from nodes import *


class PatchBayState:
    jack_client = jack.Client("selectrator")

    all_nodes: Dict[str, Dict[str, Node]] = {}
    all_links: List[Tuple[LinkPort, LinkPort]] = []

    _ctx: PatchBayContext

    def __init__(self):
        self._ctx = PatchBayContext(self)
        atexit.register(self.cleanup)

    def cleanup(self):
        for instances in self.all_nodes.values():
            for instance in instances.values():
                instance.reconcile_links([])
                instance.shutdown()

    def load_state_from_toml(self, file_path: str):
        data = toml.load(file_path)

        new_instances: List[Node] = []
        for typename in data.keys():
            if typename == "links":
                continue
            klass = globals()[typename]

            for id_part, cfg in data[typename].items():
                self.all_nodes.setdefault(typename, {})

                if id_part not in self.all_nodes[typename]:
                    instance = klass(id_part, cfg)
                    instance._jack = self.jack_client
                    instance._ctx = self._ctx
                    self.all_nodes[typename][id_part] = instance
                    new_instances.append(instance)

        logger.debug("load_state_from_toml: starting")
        for instance in new_instances:
            logger.debug(f"load_state_from_toml: starting {instance}")
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

            src = self.all_nodes[src_type][src_id]
            src_port = [port for port in src.OUTPUTS if port.id == src_port_id][0]
            tgt = self.all_nodes[tgt_type][tgt_id]
            tgt_port = [port for port in tgt.INPUTS if port.id == tgt_port_id][0]

            logger.debug(f"load_state_from_toml: loaded link {src_port}->{tgt_port}")

            self.all_links.append((src_port, tgt_port))
            src_port.links_as_src.append(tgt_port)
            tgt_port.links_as_tgt.append(src_port)

        logger.debug("load_state_from_toml: reconciling")
        self.reconcile_all_links()

        for instance in new_instances:
            logger.debug(f"load_state_from_toml: late-starting {instance}")
            instance.late_start()

    def write_state_to_toml(self, file_path: str):
        result = {}
        for typename, nodes in self.all_nodes.items():
            result[typename] = {}
            for id_part, node in nodes.items():
                result[typename][id_part] = node._props

        result["links"] = []
        for src, tgt in self.all_links:
            from_str = f"{src.node.id}[{src.id}]"
            to_str = f"{tgt.node.id}[{tgt.id}]"
            result["links"].append({"from": from_str, "to": to_str})

        with open(file_path, "w") as fd:
            toml.dump(result, fd)

    def reconcile_all_links(self):
        logger.debug("Reconciling all links")
        # we set up this temporary dict to avoid needing a quadratic loop over all_links
        links_by_source: Dict[Tuple[str, str], List[Tuple[LinkPort, LinkPort]]] = {}

        for src_port, tgt_port in self.all_links:
            src_type = src_port.node.__class__.__name__
            src_id = src_port.node._id
            links_by_source.setdefault((src_type, src_id), [])
            links_by_source[(src_type, src_id)].append((src_port, tgt_port))

        for node_type, node_id in links_by_source.keys():
            node = self.all_nodes[node_type][node_id]
            node.reconcile_links(links_by_source[(node_type, node_id)])

    def reconcile_node(self, node: Union[Node, str]):
        self._ctx._ignore_reconciles = True
        logger.debug(f"Reconciling {node}")
        if not isinstance(node, Node):
            typename, id = node.split(".")
            node = self.all_nodes[typename][id]

        links: List[Tuple[LinkPort, LinkPort]] = []

        for src, tgt in self.all_links:
            if src.node.id == node.id:
                links.append((src, tgt))

        node.reconcile_links(links)
        logger.debug(f"reconcile of {node} done")
        self._ctx._ignore_reconciles = False

    def init(self):
        self.load_state_from_toml("init.toml")
        self.write_state_to_toml("state.toml")

    def link(self, source: LinkPort, target: LinkPort):
        if (source, target) in self.all_links:
            return
        self.all_links.append((source, target))
        source.links_as_src.append(target)
        target.links_as_src.remove(source)
        self.reconcile_all_links()

    def unlink(self, source: LinkPort, target: LinkPort):
        if (source, target) not in self.all_links:
            return
        self.all_links.remove((source, target))
        source.links_as_src.remove(target)
        target.links_as_tgt.remove(source)
        self.reconcile_all_links()
