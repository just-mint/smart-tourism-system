from database import init_db, add_to_wishlist, get_wishlist, remove_from_wishlist
from shop_filter import filter_shops_by_keywords, find_shop_by_id, convert_shops_for_member_e


def main():
    print("=== TEST PHAN C ===")
    print()

    print("1. Khoi tao database")
    init_db()
    print("Da tao xong wishlist.db")
    print()

    print("2. Loc shop theo tu khoa")
    keywords = ["non la", "ao so mi"]
    matched_shops = filter_shops_by_keywords(keywords)

    print("Tu khoa:", keywords)
    print("So shop tim duoc:", len(matched_shops))
    for shop in matched_shops:
        print("-", shop["id"], "|", shop["name"], "|", shop["category"])
    print()

    print("3. Them shop_1 vao wishlist")
    shop = find_shop_by_id("shop_1")

    if shop:
        message = add_to_wishlist(shop)
        print(message)
    else:
        print("Khong tim thay shop_1")
    print()

    print("4. Xem wishlist")
    wishlist = get_wishlist()
    print("So shop trong wishlist:", len(wishlist))
    for shop in wishlist:
        print("-", shop["id"], "|", shop["name"], "|", shop["price"])
    print()

    print("5. Chuyen du lieu cho thanh vien E")
    shops_for_member_e = convert_shops_for_member_e(
        wishlist,
        user_lat=10.7769,
        user_lon=106.7009
    )

    for shop in shops_for_member_e:
        print(shop)
    print()

    print("6. Xoa shop_1 khoi wishlist")
    print(remove_from_wishlist("shop_1"))
    print()

    print("7. Xem lai wishlist")
    wishlist = get_wishlist()
    print("So shop con lai:", len(wishlist))


if __name__ == "__main__":
    main()