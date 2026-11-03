"""Quantized multilingual E5 on CPU, without PyTorch or a remote embedding API."""
from pathlib import Path
import os
import numpy as np
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType
from app.policies import unit

class LocalEncoder:
    model_id = 'intfloat/multilingual-e5-small'

    def __init__(self, cache: str):
        if not any(m['model'] == self.model_id for m in TextEmbedding.list_supported_models()):
            TextEmbedding.add_custom_model(
                model=self.model_id, pooling=PoolingType.MEAN, normalization=True,
                sources=ModelSource(hf='Xenova/multilingual-e5-small'),
                dim=384, model_file='onnx/model_quantized.onnx',
                description='Multilingual E5 small, quantized ONNX, query/passage prefixes applied by app.',
                license='mit', size_in_gb=0.12)
        model_dir = Path(cache) / 'model'
        self.model = TextEmbedding(model_name=self.model_id, cache_dir=str(Path(cache)), threads=2,
                                   local_files_only=os.getenv('VERCEL') == '1',
                                   specific_model_path=str(model_dir) if (model_dir / 'onnx/model_quantized.onnx').is_file() else None)

    def passages(self, texts: list[str]) -> np.ndarray:
        return unit(np.asarray(list(self.model.embed(['passage: ' + t for t in texts], batch_size=8))))

    def query(self, text: str) -> np.ndarray:
        return unit(np.asarray(list(self.model.embed(['query: ' + text])))[0])
