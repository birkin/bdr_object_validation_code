# BDR Object Validation Code

This project validates whether a BDR item is structured the way the front end expects for direct video display.

The current validator is intentionally narrow. It only applies the structure check to items in collection `bdr:cd6rfcmt` (`GCP Curators`), and it focuses on the problem pattern seen in recent examples:

- a working item is itself a top-level `stream` object and displays video inline
- a non-working item is a parent/container object with a stream only in `relations.hasPart`, so the front end does not display the video directly


## Purpose

Given a BDR PID, the script:

- fetches the item JSON from the BDR item API
- determines whether the item is a member of collection `bdr:cd6rfcmt`
- checks whether the root object is structured as a directly playable stream object
- reports whether the item is valid
- reports specific structural problems when it is not valid


## Requirements

- Python 3.12
- `uv`

Project dependencies are defined in [`pyproject.toml`](/Users/birkin/Documents/Brown_Library/bdr_object_validation_stuff/bdr_object_validation_code/pyproject.toml).


## Usage

Run from the project root:

```bash
uv run ./main.py --item-pid bdr:29gw48ug
```

Failing example:

```bash
uv run ./main.py --item-pid bdr:zk9pxwz3
```

You can also pass a full studio item URL:

```bash
uv run ./main.py --item-pid https://repository.library.brown.edu/studio/item/bdr:29gw48ug/
```

To get JSON output:

```bash
uv run ./main.py --item-pid bdr:29gw48ug --json
```

Run tests:

```bash
uv run ./run_tests.py
uv run ./run_tests.py -v
```


## Validation Logic

For items in collection `bdr:cd6rfcmt`, the validator currently expects the root item to look like a directly playable stream object.

It checks for:

- `object_type == 'stream'`
- `'stream'` in `rel_content_models_ssim`
- presence of `rel_panopto_id_ssi`
- presence of `stream_uri_s`
- presence of `display_inline`
- `display_inline_src` pointing to a `/viewers/stream/` URL
- `primary_download_link` pointing to a `/viewers/stream/` URL

It also inspects `relations.hasPart` and reports child parts for debugging context.

If the root item fails the direct-stream checks but contains stream children in `relations.hasPart`, the script reports that the object appears to be a container object with stream descendants rather than a directly playable stream root.


## Example Outcome

These two items motivated the validator:

- `bdr:29gw48ug`
  - valid
  - root object is a `stream`
  - includes stream-specific root fields such as `rel_panopto_id_ssi`, `stream_uri_s`, and inline viewer links

- `bdr:zk9pxwz3`
  - invalid
  - root object is `undetermined`
  - root lacks stream-specific fields
  - a stream exists only as a child in `relations.hasPart`


## Notes

- Some items or datastreams may not be visible in the public API.
- This validator does not attempt to validate all possible BDR object structures.
- The current logic is based on the documented BDR item API and the observed working/non-working examples for the `GCP Curators` collection.


## References

- BDR item API docs: <https://github.com/Brown-University-Library/bdr_api_documentation/wiki/Item-API-examples>
- BDR search API docs: <https://github.com/Brown-University-Library/bdr_api_documentation/wiki/Search-API-examples>
