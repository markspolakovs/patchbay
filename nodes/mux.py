from typing import Any, List, Mapping, Tuple
from ._node import Node, LinkPort
import logging

logger = logging.getLogger(__name__)


class Mux(Node):
    PROP_FIELDS = ("inputs", "active")

    active: int = 0

    def __init__(self, id: str, props: Mapping[str, Any]):
        Node.__init__(self, id, props)
        self.INPUTS = [LinkPort(self, str(i)) for i in range(int(props["inputs"]))]
        self.OUTPUTS = [LinkPort(self, "0")]
        self.active = int(props["active"])

    def update(self, props: Mapping[str, Any]):
        super().update(props)
        old_active = self.active
        self.active = int(props["active"])

        if self.active != old_active:
            # logger.debug(f"mux: looping over {self.INPUTS}")
            for in_port in self.INPUTS:
                # logger.debug(f"mux: and in there, {in_port.links_as_tgt}")
    
                for in_link in in_port.links_as_tgt:
                    # logger.debug(f"still looping over {self.INPUTS}, and in there, on {in_port}, {in_port.links_as_tgt}")
                    logger.debug(f"update: requesting reconcile of {in_link.node} for {in_link}")
                    self._ctx.reconcile_node(in_link.node)

    def get_input_ports(self, pseudo: LinkPort):
        if int(pseudo.id) == self.active:

            linked_ports = self.OUTPUTS[0].links_as_src

            linked_port_lists = [
                port.node.get_input_ports(port) for port in linked_ports
            ]

            logger.debug(f"passing on for active {self.active}: {linked_port_lists}")
            return [x for sublist in linked_port_lists for x in sublist]

        return []

    def reconcile_links(self, links: List[Tuple[LinkPort, LinkPort]]) -> None:
        # Mux does nothing here! All the magic happens in get_input_ports
        logger.debug("reconcile_links: doing nothing")

    def late_start(self):
        for in_port in self.INPUTS:
            for in_link in in_port.links_as_tgt:
                logger.debug(f"late_start: requesting reconcile of {in_link.node} for {in_link}")
                self._ctx.reconcile_node(in_link.node)
