from canada_post.util.address import Origin, Destination

def get_origin(shop_details):
    return Origin(postal_code=shop_details.postal_code,
                  company=shop_details.store_name, phone=shop_details.phone,
                  address=(shop_details.street1, shop_details.street2),
                  city=shop_details.city, province=shop_details.state)

