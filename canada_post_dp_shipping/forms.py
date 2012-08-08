from canada_post_dp_shipping.models import ParcelDescription, Shipment
from django import forms

class ParcelDescriptionForm(forms.ModelForm):
    """
    Form for the creation of parcels/shipments. A ModelForm is not used because
    I need to separate the box dimensions from the Box model
    """
    shipment_id = forms.CharField(max_length=32, required=False)
    shipment_status = forms.CharField(max_length=14, required=False)
    shipment_label = forms.FileField(required=False)

    class Meta:
        model = ParcelDescription

    def __init__(self, instance=None, *args, **kwargs):
        shipment_defaults = {}
        if instance:
            try:
                shipment = instance.shipment
                shipment_defaults.update({
                    'shipment_id': shipment.id,
                    'shipment_status': shipment.status,
                    'shipment_label': shipment.label,
                    })
            except Shipment.DoesNotExist:
                pass
        shipment_defaults.update(kwargs.get('initial', {}))
        kwargs['initial'] = shipment_defaults
        super(ParcelDescriptionForm, self).__init__(instance=instance, *args, **kwargs)

    def save(self, commit=True):
        parcel = super(ParcelDescriptionForm, self).save(commit)
        shipment, new = Shipment.objects.get_or_create(id=self.cleaned_data['shipment_id'])
        shipment.status = self.cleaned_data['shipment_status']
        shipment.label = self.cleaned_data['shipment_label']
        if not shipment.label:
            shipment.label = None
        shipment.save()