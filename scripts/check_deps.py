#!/usr/bin/env python3
"""Check if CLIP model dependencies are available"""
try:
    from sentence_transformers import SentenceTransformer
    print("sentence_transformers: OK")
except ImportError as e:
    print(f"sentence_transformers: MISSING - {e}")

try:
    from PIL import Image
    print("PIL: OK")
except ImportError as e:
    print(f"PIL: MISSING - {e}")

try:
    import requests
    print("requests: OK")
except ImportError as e:
    print(f"requests: MISSING - {e}")

try:
    import torch
    print(f"torch: OK (CUDA: {torch.cuda.is_available()})")
except ImportError as e:
    print(f"torch: MISSING - {e}")
