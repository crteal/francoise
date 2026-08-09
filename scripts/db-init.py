#!/usr/bin/env python3

import argparse
import os

if __name__ == '__main__' and __package__ is None:
    import sys
    # __file__ should be defined in this case
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(PARENT_DIR)

from dotenv import load_dotenv
from françoise.migrate import upgrade_to_head

load_dotenv()

parser = argparse.ArgumentParser(
        description="Initializes a database with the necessary schema.")

parser.add_argument("-db", "--database", type=str, default=os.environ.get('DATABASE_URL', 'data.db'))

args = parser.parse_args()

upgrade_to_head(args.database)
