from livesettings.functions import config_choice_values
from satchmo_utils import load_once
import shipper

load_once('canada_post_dp_shipping', 'canada_post_dp_shipping')

def get_methods():
    return [shipper.Shipper(service_type=value)
            for value in config_choice_values('canada_post_dp_shipping',
                                              'SHIPPING_CHOICES')]

