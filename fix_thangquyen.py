import re

def resolve(filename, replacer):
    with open(filename, 'r') as f:
        content = f.read()
    pattern = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> main\n', re.DOTALL)
    new_content = pattern.sub(replacer, content)
    with open(filename, 'w') as f:
        f.write(new_content)

def env_replacer(match):
    h = match.group(1)
    m = match.group(2)
    if "from app.domains.vision import model" in h:
        return h # keep ThangQuyen's imports
    if "include_object" in h and "include_object" not in m:
        return h
    if "include_object" in m and "include_object" not in h:
        return m
    return h # default to ThangQuyen

resolve('backend/app/alembic/env.py', env_replacer)

def model_replacer(match):
    # For model.py, we just use main's store_id: int | None
    return '    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.store_id"), index=True, nullable=True)\n'
resolve('backend/app/domains/inventory/model.py', model_replacer)

def service_replacer(match):
    # For service.py, ThangQuyen didn't have multi-store changes in service, so we can just use main's version for all conflicts
    return match.group(2)
resolve('backend/app/domains/inventory/service.py', service_replacer)

