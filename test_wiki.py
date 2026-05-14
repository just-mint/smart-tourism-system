import requests

def get_wiki_image(title):
    url = f"https://vi.wikipedia.org/w/api.php?action=query&titles={title}&prop=pageimages&format=json&pithumbsize=1000"
    res = requests.get(url).json()
    pages = res.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if "thumbnail" in page_data:
            return page_data["thumbnail"]["source"]
    return None

print("Hạ Long:", get_wiki_image("Vịnh Hạ Long"))
print("Huế:", get_wiki_image("Cố đô Huế"))
print("Bến Thành:", get_wiki_image("Chợ Bến Thành"))
