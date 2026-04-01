"""
Validates BDR item structure for GCP Curators objects.
"""

import argparse
import json
from dataclasses import asdict
from dataclasses import dataclass

import httpx


TARGET_COLLECTION_PID = 'bdr:cd6rfcmt'
API_ROOT = 'https://repository.library.brown.edu/api/items'


@dataclass
class ValidationResult:
    """
    Stores the validation result for a BDR item.

    Called by: validate_gcp_curators_item()
    """

    pid: str
    title: str
    applicable: bool
    valid: bool
    problems: list[str]
    notes: list[str]


def normalize_pid(raw_pid: str) -> str:
    """
    Normalizes a BDR pid input.

    Called by: fetch_item_data()
    """

    pid = raw_pid.strip()
    if pid.startswith('https://repository.library.brown.edu/studio/item/'):
        pid = pid.rstrip('/').split('/')[-1]
    if pid.startswith('https://repository.library.brown.edu/api/items/'):
        pid = pid.rstrip('/').split('/')[-1]
    return pid


def build_item_url(pid: str) -> str:
    """
    Builds the BDR item API url for a pid.

    Called by: fetch_item_data()
    """

    return f'{API_ROOT}/{pid}/'


def fetch_item_data(client: httpx.Client, raw_pid: str) -> dict:
    """
    Fetches item JSON from the BDR item API.

    Called by: main()
    """

    pid = normalize_pid(raw_pid)
    response = client.get(build_item_url(pid), follow_redirects=True)
    response.raise_for_status()
    return response.json()


def get_title(item_data: dict) -> str:
    """
    Extracts a display title for an item.

    Called by: validate_gcp_curators_item()
    """

    title = item_data.get('primary_title') or item_data.get('title_si') or item_data.get('pid', '')
    return title


def get_collection_pids(item_data: dict) -> list[str]:
    """
    Extracts collection pids from the item payload.

    Called by: validate_gcp_curators_item()
    """

    collection_pids = item_data.get('rel_is_member_of_collection_ssim', [])
    if not isinstance(collection_pids, list):
        collection_pids = []
    return collection_pids


def get_has_part_entries(item_data: dict) -> list[dict]:
    """
    Extracts hasPart relation entries from the item payload.

    Called by: validate_gcp_curators_item()
    """

    relations = item_data.get('relations', {})
    has_part_entries = relations.get('hasPart', [])
    if not isinstance(has_part_entries, list):
        has_part_entries = []
    return has_part_entries


def get_stream_part_entries(item_data: dict) -> list[dict]:
    """
    Extracts stream children from hasPart relations.

    Called by: validate_gcp_curators_item()
    """

    stream_parts: list[dict] = []
    has_part_entries = get_has_part_entries(item_data)
    for entry in has_part_entries:
        content_models = entry.get('rel_content_models_ssim', [])
        object_type = entry.get('object_type')
        if object_type == 'stream' or 'stream' in content_models:
            stream_parts.append(entry)
    return stream_parts


def describe_part(entry: dict) -> str:
    """
    Creates a short description of a hasPart child.

    Called by: summarize_parts()
    """

    pid = entry.get('pid', '<missing-pid>')
    object_type = entry.get('object_type', '<missing-object-type>')
    display_label = entry.get('display_label', '<no-display-label>')
    order = entry.get('order', '<no-order>')
    title = entry.get('primary_title', '<no-title>')
    return f'{pid} ({object_type}, label={display_label}, order={order}, title={title})'


def summarize_parts(item_data: dict) -> list[str]:
    """
    Summarizes child parts for human-readable output.

    Called by: validate_gcp_curators_item()
    """

    summaries: list[str] = []
    for entry in get_has_part_entries(item_data):
        summaries.append(describe_part(entry))
    return summaries


def validate_gcp_curators_item(item_data: dict) -> ValidationResult:
    """
    Validates the expected structure for a GCP Curators item.

    Called by: main()
    """

    pid = item_data.get('pid', '<missing-pid>')
    title = get_title(item_data)
    applicable = TARGET_COLLECTION_PID in get_collection_pids(item_data)
    problems: list[str] = []
    notes: list[str] = []

    if not applicable:
        notes.append(f'Item is not a member of target collection {TARGET_COLLECTION_PID}.')
    else:
        object_type = item_data.get('object_type')
        content_models = item_data.get('rel_content_models_ssim', [])
        panopto_id = item_data.get('rel_panopto_id_ssi')
        stream_uri = item_data.get('stream_uri_s')
        inline_src = item_data.get('display_inline_src')
        inline_markup = item_data.get('display_inline')
        primary_download_link = item_data.get('primary_download_link')
        stream_parts = get_stream_part_entries(item_data)

        if object_type != 'stream':
            problems.append(
                f'Root object_type is {object_type!r}; expected "stream" for direct inline video display.'
            )
        if 'stream' not in content_models:
            problems.append(
                f'Root rel_content_models_ssim is {content_models!r}; expected it to include "stream".'
            )
        if not panopto_id:
            problems.append('Root rel_panopto_id_ssi is missing.')
        if not stream_uri:
            problems.append('Root stream_uri_s is missing.')
        if not inline_markup:
            problems.append('Root display_inline is missing or null.')
        if not inline_src or '/viewers/stream/' not in inline_src:
            problems.append(
                f'Root display_inline_src is {inline_src!r}; expected a /viewers/stream/ URL.'
            )
        if not primary_download_link or '/viewers/stream/' not in primary_download_link:
            problems.append(
                f'Root primary_download_link is {primary_download_link!r}; expected a /viewers/stream/ URL.'
            )

        if stream_parts:
            notes.append(
                f'Found {len(stream_parts)} stream child part(s): '
                + '; '.join(entry.get('pid', '<missing-pid>') for entry in stream_parts)
            )
        else:
            notes.append('Found no stream children in relations.hasPart.')

        part_summaries = summarize_parts(item_data)
        if part_summaries:
            notes.append('All hasPart entries: ' + '; '.join(part_summaries))

        if problems and stream_parts:
            notes.append(
                'This looks like a parent/container object with stream descendants, not a directly playable stream root.'
            )

    valid = applicable and not problems
    return ValidationResult(
        pid=pid,
        title=title,
        applicable=applicable,
        valid=valid,
        problems=problems,
        notes=notes,
    )


def format_result(result: ValidationResult) -> str:
    """
    Formats validation output for terminal display.

    Called by: main()
    """

    lines = [
        f'PID: {result.pid}',
        f'Title: {result.title}',
        f'Applicable: {"yes" if result.applicable else "no"}',
        f'Valid: {"yes" if result.valid else "no"}',
    ]

    if result.problems:
        lines.append('Problems:')
        for problem in result.problems:
            lines.append(f'- {problem}')

    if result.notes:
        lines.append('Notes:')
        for note in result.notes:
            lines.append(f'- {note}')

    return '\n'.join(lines)


def parse_args() -> argparse.Namespace:
    """
    Parses CLI arguments.

    Called by: main()
    """

    parser = argparse.ArgumentParser(
        description='Validate whether a BDR item in the GCP Curators collection is structured for direct video display.'
    )
    parser.add_argument(
        'pid',
        nargs='?',
        help='Optional positional BDR pid or item URL to validate.',
    )
    parser.add_argument(
        '--item-pid',
        dest='item_pid',
        help='BDR pid or item URL to validate.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Print the validation result as JSON.',
    )
    return parser.parse_args()


def get_requested_pid(args: argparse.Namespace) -> str:
    """
    Resolves the requested pid from CLI arguments.

    Called by: main()
    """

    requested_pid = args.item_pid or args.pid
    if not requested_pid:
        raise SystemExit('Provide a BDR pid or item URL via --item-pid or as a positional argument.')
    return requested_pid


def main() -> None:
    """
    Runs the BDR object structure validator.

    Called by: __main__
    """

    args = parse_args()
    with httpx.Client(timeout=30.0) as client:
        item_data = fetch_item_data(client, get_requested_pid(args))

    result = validate_gcp_curators_item(item_data)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(format_result(result))


if __name__ == '__main__':
    main()
