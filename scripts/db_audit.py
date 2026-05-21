#!/usr/bin/env python3
"""Quick DB audit for embedding status"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.db.session import SessionLocal
from app.domains.inventory.model import Product

db = SessionLocal()
total = db.query(Product).count()
null_emb = db.query(Product).filter(Product.embedding == None).count()
has_emb = total - null_emb
print(f'Total products: {total}')
print(f'Embedding NULL: {null_emb}')
print(f'Embedding OK:   {has_emb}')
print(f'NULL ratio:     {null_emb/total*100:.1f}%')
db.close()
