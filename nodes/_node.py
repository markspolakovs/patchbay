from typing import List, Mapping, Tuple
import jack


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

    def __init__(self, node_self: "Node", id: str):
        self.node = node_self
        self.id = id


class Node:
    """
    Node is an abstract class for something that can either emit audio into the routing graph,
    take audio out of it, or do both.

    An implementing class should:
    1. Override `__init__`, `update`, `start`, `shutdown`, and one or both of `get_input_ports` and `reconcile_links`
    2. Set `CONFIG_FIELDS` statically (i.e. not in __init__) to be a list of config fields that can be user-modified
    3. Set `INPUTS` and/or `OUTPUTS` in `__init__`, depending on the values of `config`. It may change them later. (FIXME: there should be a callback for this)

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
    CONFIG_FIELDS: Tuple[str, ...] = ()

    _id: str
    _jack: jack.Client
    _config: Mapping[str, str]

    @property
    def id(self):
        """
        The full ID of the node, in the form {class name}.{_id}.
        """
        return self.__class__.__name__ + "." + self._id

    def __init__(self, id: str, config: Mapping[str, str]):
        self._id = id
        self._config = config

    def get_input_ports(self, pseudo: LinkPort) -> Tuple[str, str]:
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
        raise NotImplemented

    def update(self, config: Mapping[str, str]):
        self._config = config

    def start(self):
        """
        Start up this node and create its JACK ports.

        `start` should block until the node is ready to produce or consume audio.
        """
        raise NotImplemented

    def shutdown(self):
        """
        Shut down this node.
        """
        raise NotImplemented
