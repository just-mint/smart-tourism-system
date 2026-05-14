#!/usr/bin/env python3
"""
=============================================================================
  AEGIS O2O — BATCH VECTOR EMBEDDING PIPELINE
=============================================================================
  Script: sync_product_vectors.py
  
  Chạy CLIP (clip-ViT-B-32) trên TOÀN BỘ products chưa có embedding,
  tải ảnh từ image_url, sinh vector 512D, lưu vào cột `embedding` (pgvector).
  
  Đây là bước BẮT BUỘC để tính năng AI Scan và Mix & Match hoạt động!
  
  Usage:
    cd backend && python3 ../scripts/sync_product_vectors.py
    
  Options (env vars):
    BATCH_SIZE=50         Number of products per commit batch
    MAX_PRODUCTS=0        Max products to process (0 = unlimited)
    SKIP_DOWNLOAD=0       Skip downloading images, use placeholder embedding
=============================================================================
"""

import sys
import os
import io
import time
import logging
import requests
from datetime import datetime, timezone

# ── Setup path ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.session import SessionLocal
from app.domains.inventory.model import Product

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))
MAX_PRODUCTS = int(os.environ.get("MAX_PRODUCTS", "0"))  # 0 = all
REQUEST_TIMEOUT = 10  # seconds per image download
RETRY_LIMIT = 2

# ═══════════════════════════════════════════════════════════════════════════
#  LOAD CLIP MODEL (one-time)
# ═══════════════════════════════════════════════════════════════════════════
def load_clip_model():
    """Load CLIP model into memory."""
    print("=" * 72)
    print("  🧠 AEGIS — CLIP Vector Embedding Pipeline")
    print("=" * 72)
    print("\n⏳ Đang tải model CLIP (clip-ViT-B-32)... (lần đầu sẽ download ~400MB)")
    
    try:
        from sentence_transformers import SentenceTransformer
        from PIL import Image as PILImage
        
        model = SentenceTransformer('clip-ViT-B-32')
        print(f"   ✅ Model loaded! Embedding dimension: {model.get_sentence_embedding_dimension()}")
        return model, PILImage
    except ImportError as e:
        print(f"   ❌ Missing dependency: {e}")
        print("   Run: pip install sentence-transformers Pillow torch")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Model load error: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
#  DOWNLOAD & ENCODE IMAGE
# ═══════════════════════════════════════════════════════════════════════════
def download_and_encode(model, PILImage, image_url: str, product_id: int):
    """Download image from URL and encode with CLIP → 512D vector."""
    if not image_url:
        return None
    
    for attempt in range(RETRY_LIMIT):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "image/*",
                "Referer": "https://shopee.vn/",
            }
            resp = requests.get(image_url, timeout=REQUEST_TIMEOUT, headers=headers)
            resp.raise_for_status()
            
            # Parse image
            img = PILImage.open(io.BytesIO(resp.content)).convert("RGB")
            
            # Resize to reasonable size for CLIP (224x224 is standard input)
            img = img.resize((224, 224))
            
            # Encode with CLIP
            embedding = model.encode(img).tolist()
            
            return embedding
            
        except requests.exceptions.Timeout:
            logger.warning(f"   ⏱ Timeout downloading image for product {product_id} (attempt {attempt+1})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"   🌐 Download error for product {product_id}: {str(e)[:80]} (attempt {attempt+1})")
        except Exception as e:
            logger.warning(f"   ❌ Encode error for product {product_id}: {str(e)[:80]}")
            return None
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
def run_pipeline():
    model, PILImage = load_clip_model()
    
    db = SessionLocal()
    
    try:
        # Count products needing embeddings
        total_null = db.query(Product).filter(Product.embedding == None).count()
        total_all = db.query(Product).count()
        
        print(f"\n📊 Database Status:")
        print(f"   Total products:     {total_all}")
        print(f"   Missing embeddings: {total_null}")
        print(f"   Already embedded:   {total_all - total_null}")
        
        if total_null == 0:
            print("\n✅ All products already have embeddings! Nothing to do.")
            return
        
        # Get products without embeddings
        query = db.query(Product).filter(Product.embedding == None)
        if MAX_PRODUCTS > 0:
            query = query.limit(MAX_PRODUCTS)
            print(f"   ⚠ Limited to {MAX_PRODUCTS} products (MAX_PRODUCTS env var)")
        
        products = query.all()
        total = len(products)
        
        print(f"\n🚀 Starting embedding pipeline for {total} products (batch_size={BATCH_SIZE})...")
        print("-" * 72)
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        start_time = time.time()
        
        for i, product in enumerate(products):
            product_label = f"[{i+1}/{total}] ID:{product.product_id}"
            
            if not product.image_url:
                skip_count += 1
                if i < 5 or i % 100 == 0:
                    logger.info(f"   {product_label} ⏭ No image_url, skipping")
                continue
            
            # Download and encode
            embedding = download_and_encode(model, PILImage, product.image_url, product.product_id)
            
            if embedding is not None:
                product.embedding = embedding
                success_count += 1
                
                if i < 10 or success_count % 50 == 0:
                    name_short = product.name[:45] if product.name else "N/A"
                    logger.info(f"   {product_label} ✅ {name_short}")
            else:
                fail_count += 1
                if i < 10 or fail_count % 20 == 0:
                    logger.info(f"   {product_label} ❌ Failed to encode")
            
            # Batch commit
            if (i + 1) % BATCH_SIZE == 0:
                db.commit()
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (total - i - 1) / rate if rate > 0 else 0
                print(f"   💾 Committed batch {(i+1)//BATCH_SIZE}: {success_count}✅ {fail_count}❌ {skip_count}⏭ | {rate:.1f} img/s | ETA: {eta/60:.1f}min")
        
        # Final commit
        db.commit()
        elapsed = time.time() - start_time
        
        # Verify
        final_null = db.query(Product).filter(Product.embedding == None).count()
        final_ok = total_all - final_null
        
        print("\n" + "=" * 72)
        print("  📊 EMBEDDING PIPELINE REPORT")
        print("=" * 72)
        print(f"  ✅ Successfully embedded: {success_count}")
        print(f"  ❌ Failed to encode:      {fail_count}")
        print(f"  ⏭ Skipped (no URL):      {skip_count}")
        print(f"  ⏱ Total time:            {elapsed:.1f}s ({elapsed/60:.1f}min)")
        print(f"\n  🗃️ DB After Pipeline:")
        print(f"     Embeddings OK:   {final_ok} / {total_all}")
        print(f"     Still NULL:      {final_null}")
        print(f"     Coverage:        {final_ok/total_all*100:.1f}%")
        print("=" * 72)
        
        if final_ok > 0:
            print("  ✅ AI Vision & Mix-Match features are now OPERATIONAL!")
        else:
            print("  ⚠️ No embeddings were generated. Check image URLs and network connectivity.")
        print("=" * 72)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted! Committing partial progress...")
        db.commit()
        print("   Saved. Re-run to continue from where you left off.")
    except Exception as e:
        db.rollback()
        logger.error(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_pipeline()
