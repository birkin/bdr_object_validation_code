"""
Checks validation logic for BDR object structure.
"""

import unittest
from argparse import Namespace

import main


WORKING_ITEM = {
    'pid': 'bdr:29gw48ug',
    'primary_title': 'Bambi Ceuppens Curatorial Interview',
    'object_type': 'stream',
    'rel_content_models_ssim': ['commonMetadata', 'stream'],
    'rel_is_member_of_collection_ssim': ['bdr:cd6rfcmt'],
    'rel_panopto_id_ssi': '58732d59-f7ab-4d74-98ad-b2a80088defe',
    'stream_uri_s': 'https://brown.hosted.panopto.com/Panopto/Pages/Embed.aspx?id=58732d59-f7ab-4d74-98ad-b2a80088defe',
    'display_inline_src': 'https://repository.library.brown.edu/viewers/stream/bdr:29gw48ug/',
    'display_inline': '<iframe></iframe>',
    'primary_download_link': 'https://repository.library.brown.edu/viewers/stream/bdr:29gw48ug/',
    'relations': {
        'hasPart': [
            {
                'pid': 'bdr:5df85qyh',
                'object_type': 'stream',
                'display_label': 'stream',
                'order': '1',
                'rel_content_models_ssim': ['stream'],
                'primary_title': 'Bambi Ceuppens Curatorial Interview',
            },
            {
                'pid': 'bdr:arfqvvpf',
                'object_type': 'stream',
                'display_label': 'stream',
                'order': '2',
                'rel_content_models_ssim': ['stream'],
                'primary_title': 'Bambi Ceuppens - Interview Video 2',
            },
        ]
    },
}


NON_WORKING_ITEM = {
    'pid': 'bdr:zk9pxwz3',
    'primary_title': 'Bianca Pallo Curatorial Interview',
    'object_type': 'undetermined',
    'rel_content_models_ssim': ['commonMetadata'],
    'rel_is_member_of_collection_ssim': ['bdr:cd6rfcmt'],
    'display_inline_src': 'https://repository.library.brown.edu/studio/item/bdr:zk9pxwz3/',
    'display_inline': None,
    'primary_download_link': 'https://repository.library.brown.edu/studio/item/bdr:zk9pxwz3/',
    'relations': {
        'hasPart': [
            {
                'pid': 'bdr:44f2h2sd',
                'object_type': 'stream',
                'display_label': 'stream',
                'order': '1',
                'rel_content_models_ssim': ['stream'],
                'primary_title': 'Bianca Pallo Curatorial Interview',
            },
            {
                'pid': 'bdr:8a65u7we',
                'object_type': 'pdf',
                'display_label': 'transcript',
                'order': '1a',
                'rel_content_models_ssim': ['pdf', 'commonMetadata'],
                'primary_title': 'Bianca Pallo Transcript',
            },
        ]
    },
}


NON_TARGET_COLLECTION_ITEM = {
    'pid': 'bdr:not-applicable',
    'primary_title': 'Other Item',
    'object_type': 'stream',
    'rel_content_models_ssim': ['commonMetadata', 'stream'],
    'rel_is_member_of_collection_ssim': ['bdr:someothercollection'],
    'relations': {'hasPart': []},
}


class TestMain(unittest.TestCase):
    """
    Checks validator behavior for expected item structures.
    """

    def test_working_item_is_valid(self) -> None:
        """
        Checks that a direct stream root in the target collection validates.
        """

        result = main.validate_gcp_curators_item(WORKING_ITEM)
        self.assertTrue(result.applicable)
        self.assertTrue(result.valid)
        self.assertEqual([], result.problems)

    def test_container_root_with_stream_child_is_invalid(self) -> None:
        """
        Checks that a container-like root with only child streams is flagged.
        """

        result = main.validate_gcp_curators_item(NON_WORKING_ITEM)
        self.assertTrue(result.applicable)
        self.assertFalse(result.valid)
        self.assertTrue(any('object_type' in problem for problem in result.problems))
        self.assertTrue(any('rel_panopto_id_ssi' in problem for problem in result.problems))
        self.assertTrue(any('stream descendants' in note for note in result.notes))

    def test_non_target_collection_item_is_not_applicable(self) -> None:
        """
        Checks that non-target-collection items are marked not applicable.
        """

        result = main.validate_gcp_curators_item(NON_TARGET_COLLECTION_ITEM)
        self.assertFalse(result.applicable)
        self.assertFalse(result.valid)
        self.assertEqual([], result.problems)

    def test_normalize_pid_accepts_item_url(self) -> None:
        """
        Checks that an item URL is normalized to the bare pid.
        """

        pid = main.normalize_pid('https://repository.library.brown.edu/studio/item/bdr:29gw48ug/')
        self.assertEqual('bdr:29gw48ug', pid)

    def test_get_requested_pid_prefers_item_pid_flag(self) -> None:
        """
        Checks that the explicit item-pid flag is accepted.
        """

        args = Namespace(item_pid='bdr:29gw48ug', pid=None, json=False)
        pid = main.get_requested_pid(args)
        self.assertEqual('bdr:29gw48ug', pid)


if __name__ == '__main__':
    unittest.main()
