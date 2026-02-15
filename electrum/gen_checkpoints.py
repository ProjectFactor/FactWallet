#!/usr/bin/env python3
"""Generate checkpoints.json at CHUNK_SIZE-block boundaries using factorn-cli.

Usage:
    python electrum/gen_checkpoints.py [--cli PATH] [--output PATH]

Requires a running FACT0RN node accessible via factorn-cli.
"""
import json
import os
import subprocess
import sys
import argparse

# These must match the values in electrum/constants.py.
# Defined here directly to avoid importing the electrum package,
# which triggers __init__.py and pulls in heavy dependencies.
CHUNK_SIZE = 42
RETARGET_INTERVAL = CHUNK_SIZE * 16  # 672

DEFAULT_CLI = os.path.expanduser('~/Tools/factorn-ff5ee5ea61ab/bin/factorn-cli')


def cli_call(cli_path, *args):
    result = subprocess.run(
        [cli_path] + list(args),
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def get_block_count(cli_path):
    return int(cli_call(cli_path, 'getblockcount'))


def get_block_hash(cli_path, height):
    return cli_call(cli_path, 'getblockhash', str(height))


def get_block_header(cli_path, block_hash):
    header_json = cli_call(cli_path, 'getblockheader', block_hash)
    return json.loads(header_json)


def main():
    parser = argparse.ArgumentParser(description='Generate FACT0RN checkpoints')
    parser.add_argument('--cli', default=DEFAULT_CLI,
                        help=f'Path to factorn-cli (default: {DEFAULT_CLI})')
    parser.add_argument('--output', default=os.path.join(os.path.dirname(__file__), 'checkpoints.json'),
                        help='Output file path (default: electrum/checkpoints.json)')
    args = parser.parse_args()

    cli_path = args.cli
    if not os.path.exists(cli_path):
        print(f"Error: factorn-cli not found at {cli_path}", file=sys.stderr)
        sys.exit(1)

    chain_height = min(168672 + 1344, get_block_count(cli_path))
    num_chunks = chain_height // CHUNK_SIZE
    # We need at least one complete chunk beyond the checkpoint to verify against
    num_checkpoints = num_chunks - 1
    if num_checkpoints <= 0:
        print("Error: chain too short for checkpoints", file=sys.stderr)
        sys.exit(1)

    print(f"Chain height: {chain_height}")
    print(f"CHUNK_SIZE: {CHUNK_SIZE}, RETARGET_INTERVAL: {RETARGET_INTERVAL}")
    print(f"Generating {num_checkpoints} checkpoints...")

    checkpoints = []
    for i in range(num_checkpoints):
        boundary_height = (i + 1) * CHUNK_SIZE - 1  # last block in chunk i
        next_height = (i + 1) * CHUNK_SIZE           # first block of next chunk

        block_hash = get_block_hash(cli_path, boundary_height)
        next_block_hash = get_block_hash(cli_path, next_height)
        next_header = get_block_header(cli_path, next_block_hash)
        target = int(next_header['bits'])

        checkpoints.append([block_hash, target])

        if (i + 1) % 500 == 0 or i == num_checkpoints - 1:
            print(f"  {i + 1}/{num_checkpoints} checkpoints generated")

    with open(args.output, 'w') as f:
        json.dump(checkpoints, f)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"Wrote {len(checkpoints)} checkpoints to {args.output} ({size_kb:.1f} KB)")


if __name__ == '__main__':
    main()
