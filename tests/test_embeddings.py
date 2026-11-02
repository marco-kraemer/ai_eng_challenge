import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from app.embeddings import LocalEncoder

class EmbeddingTests(unittest.TestCase):
    def test_e5_prefixes_and_normalization(self):
        with tempfile.TemporaryDirectory() as directory, patch('app.embeddings.TextEmbedding') as embedding:
            embedding.list_supported_models.return_value = [{'model': LocalEncoder.model_id}]
            model = MagicMock()
            model.embed.side_effect = [[np.array([3., 4.])], [np.array([4., 3.])]]
            embedding.return_value = model
            encoder = LocalEncoder(directory)
            self.assertTrue(np.allclose(encoder.passages(['horários']), [[.6, .8]]))
            self.assertTrue(np.allclose(encoder.query('quando abre?'), [.8, .6]))
            self.assertEqual(model.embed.call_args_list[0].args[0], ['passage: horários'])
            self.assertEqual(model.embed.call_args_list[1].args[0], ['query: quando abre?'])
