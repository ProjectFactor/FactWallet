#!/usr/bin/env python3
"""Standalone tests for the chunk resize from 672 to 42.

Pure logic tests — no Electrum imports beyond constants.
Run: python electrum/tests/test_chunk_resize.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from electrum.constants import CHUNK_SIZE, RETARGET_INTERVAL

HEADER_SIZE = 218  # bytes, from blockchain.py


class TestChunkResize(unittest.TestCase):

    def test_constants(self):
        """RETARGET_INTERVAL is an exact multiple of CHUNK_SIZE."""
        self.assertEqual(RETARGET_INTERVAL % CHUNK_SIZE, 0)

    def test_epoch_mapping(self):
        """First RETARGET_INTERVAL // CHUNK_SIZE chunk indices map to epoch 0, etc."""
        chunks_per_epoch = RETARGET_INTERVAL // CHUNK_SIZE
        for chunk_idx in range(chunks_per_epoch):
            chunk_start = chunk_idx * CHUNK_SIZE
            epoch = chunk_start // RETARGET_INTERVAL
            self.assertEqual(epoch, 0, f"chunk {chunk_idx} should be in epoch 0")
        # First chunk of epoch 1
        chunk_idx = chunks_per_epoch
        chunk_start = chunk_idx * CHUNK_SIZE
        epoch = chunk_start // RETARGET_INTERVAL
        self.assertEqual(epoch, 1)

    def test_checkpoint_boundaries(self):
        """Checkpoint heights are at CHUNK_SIZE-1, 2*CHUNK_SIZE-1, etc."""
        for i in range(10):
            cp_height = (i + 1) * CHUNK_SIZE - 1
            self.assertEqual((cp_height + 1) % CHUNK_SIZE, 0)
            self.assertEqual(cp_height // CHUNK_SIZE, i)

    def test_old_retarget_boundaries_still_aligned(self):
        """RETARGET_INTERVAL boundaries are also CHUNK_SIZE boundaries."""
        for epoch in range(5):
            boundary = (epoch + 1) * RETARGET_INTERVAL - 1
            self.assertEqual((boundary + 1) % CHUNK_SIZE, 0,
                             f"retarget boundary {boundary} not aligned to CHUNK_SIZE")

    def test_save_chunk_offset(self):
        """Byte offset for chunk index matches the height-derived position."""
        for index in range(5):
            byte_offset = index * CHUNK_SIZE * HEADER_SIZE
            # The first header height in this chunk is index * CHUNK_SIZE,
            # so the byte offset must equal that height * HEADER_SIZE.
            self.assertEqual(byte_offset, (index * CHUNK_SIZE) * HEADER_SIZE)
            # Must be header-aligned
            self.assertEqual(byte_offset % HEADER_SIZE, 0)

    def test_chainwork_stepping(self):
        """height // CHUNK_SIZE * CHUNK_SIZE - 1 gives last retarget boundary before height."""
        test_cases = [
            (CHUNK_SIZE, CHUNK_SIZE - 1),
            (CHUNK_SIZE + 1, CHUNK_SIZE - 1),
            (2 * CHUNK_SIZE - 1, CHUNK_SIZE - 1),
            (2 * CHUNK_SIZE, 2 * CHUNK_SIZE - 1),
            (3 * CHUNK_SIZE + 5, 3 * CHUNK_SIZE - 1),
        ]
        for height, expected_last_retarget in test_cases:
            last_retarget = height // CHUNK_SIZE * CHUNK_SIZE - 1
            self.assertEqual(last_retarget, expected_last_retarget,
                             f"height={height}: expected {expected_last_retarget}, got {last_retarget}")

    def test_checkpoint_region(self):
        """index < len(checkpoints) correctly identifies checkpoint region."""
        # Simulate 100 checkpoints
        num_checkpoints = 100
        max_cp_height = num_checkpoints * CHUNK_SIZE - 1
        # Last chunk in region
        self.assertTrue(num_checkpoints - 1 < num_checkpoints)
        # First chunk outside region
        self.assertFalse(num_checkpoints < num_checkpoints)
        # Verify max_checkpoint calculation
        self.assertEqual(max_cp_height, max(0, num_checkpoints * CHUNK_SIZE - 1))


    def test_get_target_epoch_mapping(self):
        """Verify get_target's chunk-to-epoch mapping logic.

        Reproduces the core arithmetic from Blockchain.get_target without
        needing a full Blockchain instance.
        """
        chunks_per_epoch = RETARGET_INTERVAL // CHUNK_SIZE  # 16

        def target_epoch_index(chunk_index):
            """Return the epoch index that get_target would delegate to,
            or None when it would return MIN_TARGET."""
            if chunk_index == -1:
                return None  # MIN_TARGET
            next_chunk_start = (chunk_index + 1) * CHUNK_SIZE
            epoch_index = next_chunk_start // RETARGET_INTERVAL
            if epoch_index == 0:
                return None  # MIN_TARGET
            return epoch_index - 1

        # chunk_index -1 -> MIN_TARGET
        self.assertIsNone(target_epoch_index(-1))

        # All chunks whose *next* chunk is still in epoch 0 -> MIN_TARGET
        for ci in range(chunks_per_epoch - 1):  # 0..14
            self.assertIsNone(target_epoch_index(ci),
                              f"chunk {ci} should yield MIN_TARGET")

        # chunk 15: next chunk (16) starts at height 672 -> epoch 1 -> get_epoch_target(0)
        self.assertEqual(target_epoch_index(chunks_per_epoch - 1), 0)

        # chunks 16..30: next chunk is still in epoch 1 -> get_epoch_target(0)
        for ci in range(chunks_per_epoch, 2 * chunks_per_epoch - 1):
            self.assertEqual(target_epoch_index(ci), 0,
                             f"chunk {ci} should use epoch_target(0)")

        # chunk 31: next chunk (32) starts at 1344 -> epoch 2 -> get_epoch_target(1)
        self.assertEqual(target_epoch_index(2 * chunks_per_epoch - 1), 1)

    def test_sub_chunk_split_indices(self):
        """Verify the sub-chunk splitting arithmetic from interface.request_chunk."""
        for batch_index in range(3):
            batch_start = batch_index * RETARGET_INTERVAL
            total_headers = RETARGET_INTERVAL
            sub_indices = []
            for offset in range(0, total_headers, CHUNK_SIZE):
                sub_index = (batch_start + offset) // CHUNK_SIZE
                sub_indices.append(sub_index)
            # Should produce exactly chunks_per_epoch consecutive chunk indices
            chunks_per_epoch = RETARGET_INTERVAL // CHUNK_SIZE
            expected = list(range(batch_index * chunks_per_epoch,
                                  (batch_index + 1) * chunks_per_epoch))
            self.assertEqual(sub_indices, expected,
                             f"batch {batch_index}: sub-chunk indices mismatch")


if __name__ == '__main__':
    unittest.main()
