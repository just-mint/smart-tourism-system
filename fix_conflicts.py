import re

def resolve(filename, head_text, main_text, custom_text=None):
    with open(filename, 'r') as f:
        content = f.read()
    
    # We will find the conflict markers
    # Format: <<<<<<< HEAD\n...\n=======\n...\n>>>>>>> main\n
    pattern = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> main\n', re.DOTALL)
    
    def replacer(match):
        h = match.group(1)
        m = match.group(2)
        if custom_text is not None:
            if callable(custom_text):
                return custom_text(h, m)
            return custom_text
        return h # default to HEAD
        
    new_content = pattern.sub(replacer, content)
    with open(filename, 'w') as f:
        f.write(new_content)

# 1. model.py
def model_replacer(h, m):
    return '    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.store_id"), index=True, nullable=True)\n'

resolve('backend/app/domains/inventory/model.py', '', '', model_replacer)

# 2. schema.py
def schema_replacer(h, m):
    if 'store_id: int\n    quantity: int = 1' in h:
        return '    store_id: int\n    quantity: int = Field(default=1, ge=1)\n'
    if 'store_id: int' in h:
        return '    store_id: int\n'
    if 'lock_id: int' in h:
        return '    store_id: int | None = None\n    lock_id: int\n'
    return h
    
resolve('backend/app/domains/inventory/schema.py', '', '', schema_replacer)

# 3. inventory_tasks.py
def tasks_replacer(h, m):
    if 'SELECT id, product_id, quantity, store_id' in h:
        return h
    if 'quantity = lock_row[2]' in h:
        return h
    if 'WHERE product_id = :pid AND store_id = :sid' in h:
        return m
    return h

resolve('backend/workers/ai_worker/inventory_tasks.py', '', '', tasks_replacer)

