"""Build-only model caches must not become part of the deployed function."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_vercel


class VercelBuildTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root/'data').mkdir()
        (self.root/'data/políticas_da_loja.pdf').write_bytes(b'fake-pdf')
        self.download_cache = None

    def snapshot(self, **kwargs):
        self.download_cache = Path(kwargs['cache_dir'])
        snapshot = self.download_cache/'snapshot'
        snapshot.mkdir(parents=True)
        (snapshot/'onnx').mkdir()
        (snapshot/'onnx/model_quantized.onnx').write_bytes(b'fake-model')
        (snapshot/'tokenizer.json').write_text('{}')
        return str(snapshot)

    def test_download_cache_lives_outside_project_and_is_removed_after_build(self):
        with patch.object(prepare_vercel, 'ROOT', self.root), patch.object(prepare_vercel, 'snapshot_download', side_effect=self.snapshot), patch.object(prepare_vercel, 'LocalEncoder') as encoder, patch.object(prepare_vercel, 'PolicyIndex') as index:
            encoder.return_value.model_id = 'test-model'
            index.return_value.chunks = ['chunk']
            prepare_vercel.prepare()
        self.assertFalse(self.download_cache.is_relative_to(self.root))
        self.assertFalse(self.download_cache.exists())
        self.assertEqual((self.root/'.rag-bundle/embeddings/model/onnx/model_quantized.onnx').read_bytes(), b'fake-model')
        self.assertTrue((self.root/'.rag-bundle/manifest.json').is_file())

    def test_download_cache_is_removed_when_download_fails(self):
        def fail(**kwargs):
            self.snapshot(**kwargs)
            raise RuntimeError('download failed')
        with patch.object(prepare_vercel, 'ROOT', self.root), patch.object(prepare_vercel, 'snapshot_download', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'download failed'):
                prepare_vercel.prepare()
        self.assertFalse(self.download_cache.exists())

    def test_explicit_local_cache_is_reused_and_preserved(self):
        source = self.root/'existing-cache'
        with patch.object(prepare_vercel, 'ROOT', self.root), patch.object(prepare_vercel, 'snapshot_download', side_effect=self.snapshot) as download, patch.object(prepare_vercel, 'LocalEncoder') as encoder, patch.object(prepare_vercel, 'PolicyIndex') as index:
            encoder.return_value.model_id = 'test-model'
            index.return_value.chunks = ['chunk']
            prepare_vercel.prepare(source)
        self.assertEqual(self.download_cache, source/'embeddings')
        self.assertTrue(self.download_cache.exists())
        self.assertTrue(download.call_args.kwargs['local_files_only'])

    def test_rebuild_replaces_old_read_only_model_assets(self):
        model = self.root/'.rag-bundle/embeddings/model'
        (model/'onnx').mkdir(parents=True)
        old_model = model/'onnx/model_quantized.onnx'
        old_model.write_bytes(b'old-model')
        old_model.chmod(0o444)
        (model/'obsolete-weights.bin').write_bytes(b'old-unused-weights')
        with patch.object(prepare_vercel, 'ROOT', self.root), patch.object(prepare_vercel, 'snapshot_download', side_effect=self.snapshot), patch.object(prepare_vercel, 'LocalEncoder') as encoder, patch.object(prepare_vercel, 'PolicyIndex') as index:
            encoder.return_value.model_id = 'test-model'
            index.return_value.chunks = ['chunk']
            prepare_vercel.prepare()
        self.assertEqual(old_model.read_bytes(), b'fake-model')
        self.assertFalse((model/'obsolete-weights.bin').exists())
