"""PyTracery

PyTracery is a Python-port of the JavaScript library, by GalaxyKate, that uses grammars
to generate surprising new text.

"""

from __future__ import annotations

import enum
import random
import re
from argparse import Action
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union


class NodeType(enum.IntEnum):
    Raw = -1
    """Needs parsing."""
    PlainText = 0
    """Plain text."""
    Tag = 1
    """('#symbol.mod.mod2.mod3#' or '#[pushTarget:pushRule]symbol.mod')"""
    Action = 2
    """('[pushTarget:pushRule]', '[pushTarget:POP]', more in the future)"""


class Node:
    """A single node in the grammar expansion."""

    __slots__ = (
        "errors",
        "parent",
        "grammar",
        "child_index",
        "node_type",
        "depth",
        "is_expanded",
        "raw",
        "children",
        "finished_text",
        "modifiers",
    )

    errors: List[str]
    """Errors accumulated when evaluating a node."""

    parent: Optional[Node]
    """The parent of a node."""

    grammar: Grammar
    """The grammar a node belongs to."""

    child_index: int
    """The index of a node in it's parent's child list."""

    node_type: NodeType
    """The type of the node."""

    is_expanded: bool
    """Has a node been expanded."""

    depth: int
    """The depth of a node in the tree."""

    raw: str
    """The raw text for of a node."""

    finished_text: str
    """The final expanded text."""

    children: List[Node]
    """The children of a node."""

    modifiers: List[str]
    """Names of modifiers to apply to this node."""

    def __init__(
        self,
        parent: Optional[Node],
        grammar: Grammar,
        child_index: int,
        settings: _ParsedRuleSection,
    ) -> None:
        self.children: List[Node] = []
        self.errors = []
        self.finished_text = ""
        self.grammar = grammar
        self.child_index = child_index
        self.parent = parent
        self.modifiers = []

        if parent is not None:
            self.depth = parent.depth + 1
        else:
            self.depth = 0

        self.raw = settings.raw
        self.node_type = settings.node_type
        self.is_expanded = False

    def expand_children(
        self, child_rule: Optional[str], prevent_recursion: bool = False
    ):
        self.finished_text = ""
        self.children = []

        if child_rule is not None:
            sections, errors = parse(child_rule)
            self.errors.extend(errors)
            for i, section in enumerate(sections):
                node = Node(self, self.grammar, i, section)
                self.children.append(node)
                if not prevent_recursion:
                    node.expand(prevent_recursion)
                self.finished_text += node.finished_text
        else:
            self.errors.append("No child rule provided, can't expand children.")

    def expand(self, prevent_recursion: bool = False) -> None:
        if not self.is_expanded:
            self.is_expanded = True

            if self.node_type == NodeType.Raw:
                self.expand_children(self.raw, prevent_recursion)

            elif self.node_type == NodeType.PlainText:
                self.finished_text = self.raw

            elif self.node_type == NodeType.Tag:
                pre_actions: List[NodeAction] = []
                post_actions: List[NodeAction] = []

                parsed = parse_tag(self.raw)

                for action in parsed.pre_actions:
                    pre_actions.append(NodeAction(self, action.raw))

                for action in pre_actions:
                    if action.action_type == ActionType.Push:
                        undo_action = action.create_undo()
                        if undo_action is not None:
                            post_actions.append(undo_action)

                for action in pre_actions:
                    action.activate()

                self.finished_text = self.raw

                selected_rule = self.grammar.select_rule(
                    parsed.symbol, self, self.errors
                )
                self.expand_children(selected_rule, prevent_recursion)

                # apply modifiers
                for mod_name in parsed.modifiers:
                    mod_params: List[str] = []

                    if mod_name.find("(") > 0:
                        regexp = re.compile(r"\(([^)]+)\)")
                        matches = regexp.findall(mod_name)
                        if len(matches) > 0:
                            mod_params = matches[0].split(",")
                            mod_name = mod_name[: mod_name.find("(")]

                    mod = self.grammar.modifiers.get(mod_name, None)
                    if mod is None:
                        self.errors.append("Missing modifier " + mod_name)
                        self.finished_text += "((." + mod_name + "))"
                    else:
                        self.finished_text = mod(self.finished_text, *mod_params)

            elif self.node_type == NodeType.Action:
                action = NodeAction(self, self.raw)
                action.activate()
                self.finished_text = ""

    def clear_escape_chars(self):
        """Remove all escape characters."""
        self.finished_text = (
            self.finished_text.replace("\\\\", "DOUBLEBACKSLASH")
            .replace("\\", "")
            .replace("DOUBLEBACKSLASH", "\\")
        )


class ActionType(enum.IntEnum):
    Push = 0
    Pop = 1
    Flatten = 2


class NodeAction:
    __slots__ = (
        "node",
        "target",
        "rule",
        "action_type",
    )

    node: Node
    """The node to perform an action on."""

    target: str
    """A section of text to apply the action to."""

    action_type: ActionType
    """The type of action performed."""

    def __init__(self, node: Node, raw: str) -> None:
        self.node = node
        sections = raw.split(":")
        self.target = sections[0]

        if len(sections) == 1:
            self.action_type = ActionType.Flatten
        else:
            self.rule = sections[1]
            if self.rule == "POP":
                self.action_type = ActionType.Pop
            else:
                self.action_type = ActionType.Push

    def create_undo(self) -> Optional[NodeAction]:
        if self.action_type == ActionType.Push:
            return NodeAction(self.node, self.target + ":POP")
        return None

    def activate(self) -> None:
        if self.action_type == ActionType.Push:
            rule_sections: List[str] = self.rule.split(",")
            finished_rules: List[str] = []
            for rule_section in rule_sections:
                n = Node(
                    None,
                    self.node.grammar,
                    0,
                    _ParsedRuleSection(node_type=NodeType.Raw, raw=rule_section),
                )
                n.expand()
                finished_rules.append(n.finished_text)
            self.node.grammar.push_rules(self.target, finished_rules)

        elif self.action_type == ActionType.Pop:
            self.node.grammar.pop_rules(self.target)

        elif self.action_type == ActionType.Flatten:
            self.node.grammar.flatten(self.target, True)

    def to_text(self) -> str:
        raise NotImplementedError()  # FIXME


class RuleSet:
    """A collection of strings that a symbol can expand to."""

    __slots__ = "grammar", "default_uses", "default_rules"

    grammar: Grammar
    """The grammar a rule set belongs to."""

    default_uses: List[Any]
    """Cached records of when this rule was used."""

    default_rules: List[str]
    """Strings that the rule could evaluate to."""

    def __init__(self, grammar: Grammar, raw: Union[str, List[str]]) -> None:
        self.grammar = grammar
        self.default_uses = []
        self.default_rules = []

        if isinstance(raw, list):
            self.default_rules = raw
        else:
            self.default_rules = [raw]

    def select_rule(self) -> str:
        """Randomly select a rule."""
        # in kate's code there's a bunch of stuff for different methods of
        # selecting a rule, none of which seem to be implemented yet! so for
        # now I'm just going to ...
        return self.grammar.rng.choice(self.default_rules)

    def clear_state(self) -> None:
        """Clear all times this rule was used."""
        self.default_uses = []


@dataclass
class _SymbolUseEntry:
    node: Node


class Symbol:
    """A replacement symbol in a Grammar"""

    __slots__ = "grammar", "key", "raw_rules", "base_rules", "stack", "uses"

    grammar: Grammar
    """The Grammar a symbol belongs to."""

    key: str
    """The string a symbol is mapped to."""

    raw_rules: Union[str, List[str]]
    """The raw substitution rules."""

    base_rules: RuleSet
    """The default set of substitution rules."""

    stack: List[RuleSet]
    """A stack of RuleSets to evaluate."""

    uses: List[_SymbolUseEntry]
    """Records of nodes a symbol is used in a Grammar."""

    def __init__(
        self, grammar: Grammar, key: str, raw_rules: Union[str, List[str]]
    ) -> None:
        self.grammar = grammar
        self.key = key
        self.raw_rules = raw_rules
        self.base_rules = RuleSet(grammar, raw_rules)
        self.stack = [self.base_rules]
        self.uses = []
        self.clear_state()

    def clear_state(self) -> None:
        """Clear cached symbol state."""
        self.stack = [self.base_rules]
        self.uses = []
        self.base_rules.clear_state()

    def push_rules(self, raw_rules: Union[str, List[str]]) -> None:
        """Add new rules to a symbol."""
        rules = RuleSet(self.grammar, raw_rules)
        self.stack.append(rules)

    def pop_rules(self):
        """Remove the most recently pushed rules."""
        self.stack.pop()

    def select_rule(self, node: Node, errors: List[str]) -> str:
        """Select a rule for a given node."""
        self.uses.append(_SymbolUseEntry(node))
        if len(self.stack) == 0:
            errors.append(
                "The rule stack for '" + self.key + "' is empty, too many pops?"
            )
        return self.stack[-1].select_rule()

    def get_active_rules(self) -> Optional[str]:
        """Get a rule from the top of the rule stack"""
        if len(self.stack) == 0:
            return None
        return self.stack[-1].select_rule()


class Grammar:
    """A Tracery Grammar containing symbols and rules that can be expanded/flattened."""

    __slots__ = (
        "rng",
        "symbols",
        "modifiers",
        "errors",
        "raw",
        "sub_grammars",
        "settings",
    )

    rng: random.Random
    """Random number generator for rule selection."""

    symbols: Dict[str, Symbol]
    """Symbols in loaded in a grammar."""

    modifiers: Dict[str, Modifier]
    """Loaded modifier functions."""

    errors: List[str]
    """Errors accumulated during grammar expansion."""

    raw: Dict[str, Union[str, List[str]]]
    """The raw data used to create the grammar."""

    sub_grammars: List[Grammar]
    """Child grammars."""

    settings: Dict[str, Any]
    """Keyword settings."""

    def __init__(
        self,
        raw: Union[
            Dict[str, Union[str, List[str]]], Dict[str, str], Dict[str, List[str]]
        ],
        settings: Optional[Dict[str, Any]] = None,
        rng: Optional[random.Random] = None,
        modifiers: Optional[Dict[str, Modifier]] = None,
    ) -> None:
        self.raw = {k: v for k, v in raw.items()}
        self.rng = rng if rng is not None else random.Random()
        self.modifiers = modifiers if modifiers is not None else {}
        self.errors = []
        self.symbols = {k: Symbol(self, k, v) for k, v in raw.items()}
        self.sub_grammars = []  # Not Used
        self.settings = settings if settings is not None else {}  # Not Used

    def clear_state(self) -> None:
        """Clear all cached states."""
        for val in self.symbols.values():
            val.clear_state()

    def add_modifiers(self, modifiers: Dict[str, Modifier]) -> None:
        """Load modifier functions."""
        for key, modifier in modifiers.items():
            self.modifiers[key] = modifier

    def create_root(self, rule: str) -> Node:
        return Node(None, self, 0, _ParsedRuleSection(node_type=NodeType.Raw, raw=rule))

    def expand(self, rule: str, allow_escape_chars: bool = False) -> Node:
        root = self.create_root(rule)
        root.expand()
        if not allow_escape_chars:
            root.clear_escape_chars()
        self.errors.extend(root.errors)
        return root

    def flatten(self, rule: str, allow_escape_chars: bool = False) -> str:
        """Expand a rule using the Grammar."""
        root = self.expand(rule, allow_escape_chars)
        return root.finished_text

    def push_rules(self, key: str, raw_rules: Union[str, List[str]]) -> None:
        if key not in self.symbols:
            self.symbols[key] = Symbol(self, key, raw_rules)
        else:
            self.symbols[key].push_rules(raw_rules)

    def pop_rules(self, key: str) -> None:
        if key not in self.symbols:
            self.errors.append("Can't pop: no symbol for key " + key)
        else:
            self.symbols[key].pop_rules()

    def select_rule(self, key: Optional[str], node: Node, errors: List[str]) -> str:
        if key in self.symbols:
            return self.symbols[key].select_rule(node, errors)
        else:
            if key is None:
                key = str(None)
            self.errors.append("No symbol for " + key)
            return "((" + key + "))"


class Modifier(Protocol):
    """A Tracery modifier function."""

    def __call__(self, text: str, *params: str) -> str:
        raise NotImplementedError()


@dataclass
class _ParsedTagOutput:
    symbol: Optional[str] = None
    pre_actions: List[_ParsedRuleSection] = field(default_factory=list)
    post_actions: List[_ParsedRuleSection] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)


def parse_tag(tag_contents: str) -> _ParsedTagOutput:
    """
    returns a dictionary with 'symbol', 'modifiers', 'preactions',
    'postactions'
    """
    parsed: _ParsedTagOutput = _ParsedTagOutput()

    sections, _ = parse(tag_contents)
    symbol_section = None
    for section in sections:
        if section.node_type == NodeType.PlainText:
            if symbol_section is None:
                symbol_section = section.raw
            else:
                raise Exception("multiple main sections in " + tag_contents)
        else:
            parsed.pre_actions.append(section)

    if symbol_section is not None:
        components = symbol_section.split(".")
        parsed.symbol = components[0]
        parsed.modifiers = components[1:]

    return parsed


@dataclass
class _ParsedRuleSection:
    node_type: NodeType = NodeType.Raw
    raw: str = ""
    pre_actions: List[Action] = field(default_factory=list)


def parse(rule: Optional[str]) -> Tuple[List[_ParsedRuleSection], List[str]]:
    depth = 0
    in_tag = False
    sections: List[_ParsedRuleSection] = list()
    escaped = False
    errors: List[str] = []
    start = 0
    escaped_substring = ""
    last_escaped_char = None

    if rule is None:
        return sections, errors

    def create_section(start: int, end: int, type_: NodeType):
        if end - start < 1:
            if type_ == NodeType.Tag:
                errors.append(str(start) + ": empty tag")
            elif type_ == NodeType.Action:
                errors.append(str(start) + ": empty action")
        raw_substring = None
        if last_escaped_char is not None:
            raw_substring = escaped_substring + "\\" + rule[last_escaped_char + 1 : end]
        else:
            raw_substring = rule[start:end]
        sections.append(_ParsedRuleSection(node_type=type_, raw=raw_substring))

    for i, c in enumerate(rule):
        if not escaped:
            if c == "[":
                if depth == 0 and not in_tag:
                    if start < i:
                        create_section(start, i, NodeType.PlainText)
                        last_escaped_char = None
                        escaped_substring = ""
                    start = i + 1
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0 and not in_tag:
                    create_section(start, i, NodeType.Action)
                    last_escaped_char = None
                    escaped_substring = ""
                    start = i + 1
            elif c == "#":
                if depth == 0:
                    if in_tag:
                        create_section(start, i, NodeType.Tag)
                        last_escaped_char = None
                        escaped_substring = ""
                        start = i + 1
                    else:
                        if start < i:
                            create_section(start, i, NodeType.PlainText)
                            last_escaped_char = None
                            escaped_substring = ""
                        start = i + 1
                    in_tag = not in_tag
            elif c == "\\":
                escaped = True
                escaped_substring = escaped_substring + rule[start:i]
                start = i + 1
                last_escaped_char = i
        else:
            escaped = False
    if start < len(rule):
        create_section(start, len(rule), NodeType.PlainText)
        last_escaped_char = None
        escaped_substring = ""

    if in_tag:
        errors.append("unclosed tag")
    if depth > 0:
        errors.append("too many [")
    if depth < 0:
        errors.append("too many ]")

    sections = [
        s
        for s in sections
        if not (s.node_type == NodeType.PlainText and len(s.raw) == 0)
    ]

    return sections, errors
