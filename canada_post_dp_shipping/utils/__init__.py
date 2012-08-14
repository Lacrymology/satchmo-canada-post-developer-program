from canada_post import PROD, DEV
from canada_post.util.address import Origin, Destination

def get_origin(shop_details):
    return Origin(postal_code=shop_details.postal_code,
                  company=shop_details.store_name, phone=shop_details.phone,
                  address=(shop_details.street1, shop_details.street2),
                  city=shop_details.city, province=shop_details.state)

def get_destination(contact):
    return Destination(postal_code=contact.shipping_address.postal_code,
                       country_code=contact.shipping_address.country.iso2_code,
                       name=u"{last_name}, {first_name}".format(
                           first_name=contact.first_name,
                           last_name=contact.last_name),
                       address=(contact.shipping_address.street1,
                                contact.shipping_address.street2),
                       city=contact.shipping_address.city,
                       province=contact.shipping_address.state)

def canada_post_api_kwargs(settings, production=None):
    cpa_kwargs = {
        'customer_number': settings.CUSTOMER_NUMBER.value
    }
    if production is None:
        production = settings.LIVE.value

    if production:
        cpa_kwargs.update({
            'username': settings.USERNAME.value,
            'password': settings.PASSWORD.value,
            'dev': PROD,
            })
    else:
        cpa_kwargs.update({
            'username': settings.USERNAME_DEBUG.value,
            'password': settings.PASSWORD_DEBUG.value,
            'dev': DEV,
            })
    if settings.CONTRACT_SHIPPING.value:
        cpa_kwargs['contract_number'] = settings.CONTRACT_NUMBER.value
    return cpa_kwargs
