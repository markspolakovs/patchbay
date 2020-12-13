from typing import Any, List, Mapping, Tuple, Union
import jack
import logging


class LinkPort:
    """
    A port on a node.

    Each LinkPort actually corresponds to _two_ JACK ports (because stereo).

    The ID MUST be unique within the node, but not globally.
    By convention, if a node has only one input or output, its ID should be `"0"`.
    If it has more than one of each, it should give them meaningful names.
    """

    node: "Node"
    id: str

    links_as_src: List["LinkPort"]
    links_as_tgt: List["LinkPort"]

    def __init__(self, node_self: "Node", id: str):
        self.node = node_self
        self.id = id
        self.links_as_src = []
        self.links_as_tgt = []
    
    def __repr__(self):
        return f"<LinkPort {self.node.__class__.__name__}.{self.node._id}[{self.id}]>"


class PatchBayContext:
    state: Any  # importing PatchBayState here causes a circular import
    logger = logging.Logger('PatchBayContext')

    _ignore_reconciles = True

    def __init__(self, state: Any):
        self.state = state

    def reconcile_all_links(self):
        if not self._ignore_reconciles:
            self.state.reconcile_all_links()
    
    def reconcile_node(self, node: Union["Node", str]):
        self.logger.debug(f"requested reconciliation for {node}")
        if not self._ignore_reconciles:
            self.state.reconcile_node(node)
        else:
            self.logger.debug("but it got ignored")


class Node:
    """
    Node is an abstract class for something that can either emit audio into the routing graph,
    take audio out of it, or do both.

    An implementing class should:
    1. Override `__init__`, `update`, `start`, `shutdown`, and one or both of `get_input_ports` and `reconcile_links`
    2. Set `PROP_FIELDS` statically (i.e. not in __init__) to be a list of config fields that can be user-modified
    3. Set `INPUTS` and/or `OUTPUTS` in `__init__`, depending on the values of `props`. It may change them later. (FIXME: there should be a callback for this)

    The general sequence of calls will be:
    1. `__init__`
    2. `start`
    3. `reconcile_links`
    4. possibly `update` and/or `reconcile_links`
    5. `reconcile_links`
    6. `shutdown`

    An implementing class **MUST NOT** itself set any attribute prefixed by an underscore. This will be handled by the engine.

    An implementing class MUST NOT assume that `_jack` will be present in `__init__`. It may assume this at any point from when `start` is called (inclusive).
    """

    INPUTS: List[LinkPort] = []
    OUTPUTS: List[LinkPort] = []
    PROP_FIELDS: Tuple[str, ...] = ()

    _id: str
    _jack: jack.Client
    _ctx: PatchBayContext
    _props: Mapping[str, Any]

    @property
    def id(self):
        """
        The full ID of the node, in the form {class name}.{_id}.
        """
        return self.__class__.__name__ + "." + self._id

    def __init__(self, id: str, props: Mapping[str, Any]) -> None:
        self._id = id
        self._props = props
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self._id}>"

    def get_input_ports(self, pseudo: LinkPort) -> List[Tuple[str, str]]:
        """
        Called by output nodes wishing to connect to this input node.
        Should return the JACK port names for the given LinkPort.
        Output-only nodes need not implement this.
        """
        raise NotImplemented

    def reconcile_links(self, links: List[Tuple[LinkPort, LinkPort]]) -> None:
        """
        Called by the engine when the output connections of this node have changed.
        The `links` list will contain a list of tuples in the form `(output_port, input_port)`.

        The Node should connect every output_port to the given input_port, and
        disconnect any pre-existing links that are not present in the `links` list.

        Input-only nodes need not implement this.
        """
        pass

    def update(self, props: Mapping[str, Any]) -> None:
        """
        Make any changes necessary to the node, based on the new prop values.

        If necessary, call `self._ctx.reconcile_node()` to reconcile another node.
        """
        self._props = props

    def start(self) -> None:
        """
        Start up this node and create its JACK ports.

        `start` should block until the node is ready to produce or consume audio.
        """
        pass
    
    def late_start(self):
        """
        Functions identically to start, except is called after all other nodes have started
        """
        pass

    def shutdown(self) -> None:
        """
        Shut down this node.
        """
        pass
