"""
Provide an entry point to the fetching routines of the Willa ETL pipeline.
"""

import argparse

from rich.console import Console

from willa.etl.pipeline import fetch_one_from_tind, fetch_all_from_search_query


def main() -> None:
    """The entry point for the document fetcher."""
    console = Console()

    parser = argparse.ArgumentParser(
        prog='willa-fetch',
        description='Downloads documents from the Berkeley Library OHC for textual processing'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-q', '--query', action='store',
                       help='Search the catalogue for the specified terms')
    group.add_argument('-t', '--tind-id', action='store',
                       help='Download a specific item by its TIND ID')
    args = parser.parse_args()

    if args.query:
        with console.status(f'[bold green]Downloading items that match "{args.query}"'):
            fetch_all_from_search_query(args.query)
        console.print('Downloaded.')
    else:
        with console.status(f'[bold green]Downloading item {args.tind_id}'):
            fetch_one_from_tind(args.tind_id)
        console.print(f'{args.tind_id} downloaded.')


if __name__ == "__main__":
    main()
