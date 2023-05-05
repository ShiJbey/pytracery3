#!/usr/bin/env python3

"""The Tracery commandline interface."""

import argparse
import json

import tracery
from tracery.modifiers import base_english


def main():
    parser = argparse.ArgumentParser(
        description="Output an example line from a JSON Tracery grammar.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("json", help="Input JSON file")
    parser.add_argument(
        "number", type=int, default=1, nargs="?", help="Number of lines to generate"
    )
    args = parser.parse_args()

    with open(args.json) as data_file:
        rules = json.load(data_file)

    grammar = tracery.Grammar(rules)
    grammar.add_modifiers(base_english)

    for _ in range(args.number):
        print(grammar.flatten("#origin#"))


if __name__ == "__main__":
    main()
