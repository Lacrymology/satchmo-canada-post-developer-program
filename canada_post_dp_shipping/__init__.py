from livesettings.functions import config_choice_values
import shipper

def get_methods():
    return [shipper.Shipper(service_type=value)
            for value in config_choice_values('canada_post_dp_shipping',
                                              'SHIPPING_CHOICES')]

