from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms.array import SimpleArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from dcim.choices import *
from dcim.constants import *
from dcim.models import *
from extras.models import ConfigTemplate
from ipam.models import VRF, IPAddress
from netbox.choices import *
from netbox.forms import NetBoxModelImportForm
from tenancy.models import Tenant
from utilities.forms.fields import (
    CSVChoiceField, CSVContentTypeField, CSVModelChoiceField, CSVModelMultipleChoiceField, CSVTypedChoiceField,
    SlugField,
)
from virtualization.models import Cluster, VMInterface, VirtualMachine
from wireless.choices import WirelessRoleChoices
from .common import ModuleCommonForm

__all__ = (
    'CableImportForm',
    'ConsolePortImportForm',
    'ConsoleServerPortImportForm',
    'DeviceBayImportForm',
    'DeviceImportForm',
    'DeviceRoleImportForm',
    'DeviceTypeImportForm',
    'FrontPortImportForm',
    'InterfaceImportForm',
    'InventoryItemImportForm',
    'InventoryItemRoleImportForm',
    'LocationImportForm',
    'MACAddressImportForm',
    'ManufacturerImportForm',
    'ModuleImportForm',
    'ModuleBayImportForm',
    'ModuleTypeImportForm',
    'ModuleTypeProfileImportForm',
    'PlatformImportForm',
    'PowerFeedImportForm',
    'PowerOutletImportForm',
    'PowerPanelImportForm',
    'PowerPortImportForm',
    'RackImportForm',
    'RackReservationImportForm',
    'RackRoleImportForm',
    'RackTypeImportForm',
    'RearPortImportForm',
    'RegionImportForm',
    'SiteImportForm',
    'SiteGroupImportForm',
    'VirtualChassisImportForm',
    'VirtualDeviceContextImportForm'
)


class RegionImportForm(NetBoxModelImportForm):
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=Region.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Name of parent region')
    )

    class Meta:
        model = Region
        fields = ('name', 'slug', 'parent', 'description', 'tags', 'comments')


class SiteGroupImportForm(NetBoxModelImportForm):
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=SiteGroup.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Name of parent site group')
    )

    class Meta:
        model = SiteGroup
        fields = ('name', 'slug', 'parent', 'description', 'comments', 'tags')


class SiteImportForm(NetBoxModelImportForm):
    status = CSVChoiceField(
        label=_('Status'),
        choices=SiteStatusChoices,
        help_text=_('Operational status')
    )
    region = CSVModelChoiceField(
        label=_('Region'),
        queryset=Region.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned region')
    )
    group = CSVModelChoiceField(
        label=_('Group'),
        queryset=SiteGroup.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned group')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )

    class Meta:
        model = Site
        fields = (
            'name', 'slug', 'status', 'region', 'group', 'tenant', 'facility', 'time_zone', 'description',
            'physical_address', 'shipping_address', 'latitude', 'longitude', 'comments', 'tags'
        )
        help_texts = {
            'time_zone': mark_safe(
                '{} (<a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">{}</a>)'.format(
                    _('Time zone'), _('available options')
                )
            )
        }


class LocationImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text=_('Assigned site')
    )
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=Location.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent location'),
        error_messages={
            'invalid_choice': _('Location not found.'),
        }
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=LocationStatusChoices,
        help_text=_('Operational status')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )

    class Meta:
        model = Location
        fields = (
            'site', 'parent', 'name', 'slug', 'status', 'tenant', 'facility', 'description',
            'tags', 'comments',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:
            # Limit location queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['parent'].queryset = self.fields['parent'].queryset.filter(**params)


class RackRoleImportForm(NetBoxModelImportForm):
    slug = SlugField()

    class Meta:
        model = RackRole
        fields = ('name', 'slug', 'color', 'description', 'tags')


class RackTypeImportForm(NetBoxModelImportForm):
    manufacturer = forms.ModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        to_field_name='name',
        help_text=_('The manufacturer of this rack type')
    )
    form_factor = CSVChoiceField(
        label=_('Type'),
        choices=RackFormFactorChoices,
        required=False,
        help_text=_('Form factor')
    )
    starting_unit = forms.IntegerField(
        required=False,
        min_value=1,
        help_text=_('The lowest-numbered position in the rack')
    )
    width = forms.ChoiceField(
        label=_('Width'),
        choices=RackWidthChoices,
        help_text=_('Rail-to-rail width (in inches)')
    )
    outer_unit = CSVChoiceField(
        label=_('Outer unit'),
        choices=RackDimensionUnitChoices,
        required=False,
        help_text=_('Unit for outer dimensions')
    )
    weight_unit = CSVChoiceField(
        label=_('Weight unit'),
        choices=WeightUnitChoices,
        required=False,
        help_text=_('Unit for rack weights')
    )

    class Meta:
        model = RackType
        fields = (
            'manufacturer', 'model', 'slug', 'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units',
            'outer_width', 'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'weight', 'max_weight',
            'weight_unit', 'description', 'comments', 'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)


class RackImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name'
    )
    location = CSVModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        required=False,
        to_field_name='name'
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Name of assigned tenant')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=RackStatusChoices,
        help_text=_('Operational status')
    )
    role = CSVModelChoiceField(
        label=_('Role'),
        queryset=RackRole.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Name of assigned role')
    )
    rack_type = CSVModelChoiceField(
        label=_('Rack type'),
        queryset=RackType.objects.all(),
        to_field_name='model',
        required=False,
        help_text=_('Rack type model')
    )
    form_factor = CSVChoiceField(
        label=_('Type'),
        choices=RackFormFactorChoices,
        required=False,
        help_text=_('Form factor')
    )
    width = forms.ChoiceField(
        label=_('Width'),
        choices=RackWidthChoices,
        required=False,
        help_text=_('Rail-to-rail width (in inches)')
    )
    u_height = forms.IntegerField(
        required=False,
        label=_('Height (U)')
    )
    outer_unit = CSVChoiceField(
        label=_('Outer unit'),
        choices=RackDimensionUnitChoices,
        required=False,
        help_text=_('Unit for outer dimensions')
    )
    airflow = CSVChoiceField(
        label=_('Airflow'),
        choices=RackAirflowChoices,
        required=False,
        help_text=_('Airflow direction')
    )
    weight_unit = CSVChoiceField(
        label=_('Weight unit'),
        choices=WeightUnitChoices,
        required=False,
        help_text=_('Unit for rack weights')
    )

    class Meta:
        model = Rack
        fields = (
            'site', 'location', 'name', 'facility_id', 'tenant', 'status', 'role', 'rack_type', 'form_factor', 'serial',
            'asset_tag', 'width', 'u_height', 'desc_units', 'outer_width', 'outer_height', 'outer_depth', 'outer_unit',
            'mounting_depth', 'airflow', 'weight', 'max_weight', 'weight_unit', 'description', 'comments', 'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit location queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['location'].queryset = self.fields['location'].queryset.filter(**params)

    def clean(self):
        super().clean()

        # width & u_height must be set if not specifying a rack type on import
        if not self.instance.pk:
            if not self.cleaned_data.get('rack_type') and not self.cleaned_data.get('width'):
                raise forms.ValidationError(_("Width must be set if not specifying a rack type."))
            if not self.cleaned_data.get('rack_type') and not self.cleaned_data.get('u_height'):
                raise forms.ValidationError(_("U height must be set if not specifying a rack type."))


class RackReservationImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text=_('Parent site')
    )
    location = CSVModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_("Rack's location (if any)")
    )
    rack = CSVModelChoiceField(
        label=_('Rack'),
        queryset=Rack.objects.all(),
        to_field_name='name',
        help_text=_('Rack')
    )
    units = SimpleArrayField(
        label=_('Units'),
        base_field=forms.IntegerField(),
        required=True,
        help_text=_('Comma-separated list of individual unit numbers')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )

    class Meta:
        model = RackReservation
        fields = ('site', 'location', 'rack', 'units', 'tenant', 'description', 'comments', 'tags')

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit location queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['location'].queryset = self.fields['location'].queryset.filter(**params)

            # Limit rack queryset by assigned site and group
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get('site'),
                f"location__{self.fields['location'].to_field_name}": data.get('location'),
            }
            self.fields['rack'].queryset = self.fields['rack'].queryset.filter(**params)


class ManufacturerImportForm(NetBoxModelImportForm):

    class Meta:
        model = Manufacturer
        fields = ('name', 'slug', 'description', 'tags')


class DeviceTypeImportForm(NetBoxModelImportForm):
    manufacturer = CSVModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        to_field_name='name',
        help_text=_('The manufacturer which produces this device type')
    )
    default_platform = CSVModelChoiceField(
        label=_('Default platform'),
        queryset=Platform.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('The default platform for devices of this type (optional)')
    )
    weight = forms.DecimalField(
        label=_('Weight'),
        required=False,
        help_text=_('Device weight'),
    )
    weight_unit = CSVChoiceField(
        label=_('Weight unit'),
        choices=WeightUnitChoices,
        required=False,
        help_text=_('Unit for device weight')
    )

    class Meta:
        model = DeviceType
        fields = [
            'manufacturer', 'default_platform', 'model', 'slug', 'part_number', 'u_height', 'exclude_from_utilization',
            'is_full_depth', 'subdevice_role', 'airflow', 'description', 'weight', 'weight_unit', 'comments', 'tags',
        ]


class ModuleTypeProfileImportForm(NetBoxModelImportForm):

    class Meta:
        model = ModuleTypeProfile
        fields = [
            'name', 'description', 'schema', 'comments', 'tags',
        ]


class ModuleTypeImportForm(NetBoxModelImportForm):
    profile = forms.ModelChoiceField(
        label=_('Profile'),
        queryset=ModuleTypeProfile.objects.all(),
        to_field_name='name',
        required=False
    )
    manufacturer = forms.ModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        to_field_name='name'
    )
    airflow = CSVChoiceField(
        label=_('Airflow'),
        choices=ModuleAirflowChoices,
        required=False,
        help_text=_('Airflow direction')
    )
    weight = forms.DecimalField(
        label=_('Weight'),
        required=False,
        help_text=_('Module weight'),
    )
    weight_unit = CSVChoiceField(
        label=_('Weight unit'),
        choices=WeightUnitChoices,
        required=False,
        help_text=_('Unit for module weight')
    )

    class Meta:
        model = ModuleType
        fields = [
            'manufacturer', 'model', 'part_number', 'description', 'airflow', 'weight', 'weight_unit', 'profile',
            'comments', 'tags'
        ]


class DeviceRoleImportForm(NetBoxModelImportForm):
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=DeviceRole.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent Device Role'),
        error_messages={
            'invalid_choice': _('Device role not found.'),
        }
    )
    config_template = CSVModelChoiceField(
        label=_('Config template'),
        queryset=ConfigTemplate.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Config template')
    )
    slug = SlugField()

    class Meta:
        model = DeviceRole
        fields = (
            'name', 'slug', 'parent', 'color', 'vm_role', 'config_template', 'description', 'comments', 'tags'
        )


class PlatformImportForm(NetBoxModelImportForm):
    slug = SlugField()
    manufacturer = CSVModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Limit platform assignments to this manufacturer')
    )
    config_template = CSVModelChoiceField(
        label=_('Config template'),
        queryset=ConfigTemplate.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Config template')
    )

    class Meta:
        model = Platform
        fields = (
            'name', 'slug', 'manufacturer', 'config_template', 'description', 'tags',
        )


class BaseDeviceImportForm(NetBoxModelImportForm):
    role = CSVModelChoiceField(
        label=_('Device role'),
        queryset=DeviceRole.objects.all(),
        to_field_name='name',
        help_text=_('Assigned role')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )
    manufacturer = CSVModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        to_field_name='name',
        help_text=_('Device type manufacturer')
    )
    device_type = CSVModelChoiceField(
        label=_('Device type'),
        queryset=DeviceType.objects.all(),
        to_field_name='model',
        help_text=_('Device type model')
    )
    platform = CSVModelChoiceField(
        label=_('Platform'),
        queryset=Platform.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned platform')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=DeviceStatusChoices,
        help_text=_('Operational status')
    )
    virtual_chassis = CSVModelChoiceField(
        label=_('Virtual chassis'),
        queryset=VirtualChassis.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Virtual chassis')
    )
    cluster = CSVModelChoiceField(
        label=_('Cluster'),
        queryset=Cluster.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Virtualization cluster')
    )

    class Meta:
        fields = []
        model = Device

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit device type queryset by manufacturer
            params = {f"manufacturer__{self.fields['manufacturer'].to_field_name}": data.get('manufacturer')}
            self.fields['device_type'].queryset = self.fields['device_type'].queryset.filter(**params)


class DeviceImportForm(BaseDeviceImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text=_('Assigned site')
    )
    location = CSVModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_("Assigned location (if any)")
    )
    rack = CSVModelChoiceField(
        label=_('Rack'),
        queryset=Rack.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_("Assigned rack (if any)")
    )
    face = CSVChoiceField(
        label=_('Face'),
        choices=DeviceFaceChoices,
        required=False,
        help_text=_('Mounted rack face')
    )
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Parent device (for child devices)')
    )
    device_bay = CSVModelChoiceField(
        label=_('Device bay'),
        queryset=DeviceBay.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Device bay in which this device is installed (for child devices)')
    )
    airflow = CSVChoiceField(
        label=_('Airflow'),
        choices=DeviceAirflowChoices,
        required=False,
        help_text=_('Airflow direction')
    )
    config_template = CSVModelChoiceField(
        label=_('Config template'),
        queryset=ConfigTemplate.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Config template')
    )

    class Meta(BaseDeviceImportForm.Meta):
        fields = [
            'name', 'role', 'tenant', 'manufacturer', 'device_type', 'platform', 'serial', 'asset_tag', 'status',
            'site', 'location', 'rack', 'position', 'face', 'latitude', 'longitude', 'parent', 'device_bay', 'airflow',
            'virtual_chassis', 'vc_position', 'vc_priority', 'cluster', 'description', 'config_template', 'comments',
            'tags',
        ]

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit location queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['location'].queryset = self.fields['location'].queryset.filter(**params)
            self.fields['parent'].queryset = self.fields['parent'].queryset.filter(**params)

            # Limit rack queryset by assigned site and location
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get('site'),
            }
            if location := data.get('location'):
                params.update({
                    f"location__{self.fields['location'].to_field_name}": location,
                })
            self.fields['rack'].queryset = self.fields['rack'].queryset.filter(**params)

            # Limit device bay queryset by parent device
            if parent := data.get('parent'):
                params = {f"device__{self.fields['parent'].to_field_name}": parent}
                self.fields['device_bay'].queryset = self.fields['device_bay'].queryset.filter(**params)

    def clean(self):
        super().clean()

        # Inherit site and rack from parent device
        if parent := self.cleaned_data.get('parent'):
            self.instance.site = parent.site
            self.instance.rack = parent.rack

        # Set parent_bay reverse relationship
        if device_bay := self.cleaned_data.get('device_bay'):
            self.instance.parent_bay = device_bay


class ModuleImportForm(ModuleCommonForm, NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('The device in which this module is installed')
    )
    module_bay = CSVModelChoiceField(
        label=_('Module bay'),
        queryset=ModuleBay.objects.all(),
        to_field_name='name',
        help_text=_('The module bay in which this module is installed')
    )
    module_type = CSVModelChoiceField(
        label=_('Module type'),
        queryset=ModuleType.objects.all(),
        to_field_name='model',
        help_text=_('The type of module')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=ModuleStatusChoices,
        help_text=_('Operational status')
    )
    replicate_components = forms.BooleanField(
        label=_('Replicate components'),
        required=False,
        help_text=_('Automatically populate components associated with this module type (enabled by default)')
    )
    adopt_components = forms.BooleanField(
        label=_('Adopt components'),
        required=False,
        help_text=_('Adopt already existing components')
    )

    class Meta:
        model = Module
        fields = (
            'device', 'module_bay', 'module_type', 'serial', 'asset_tag', 'status', 'description', 'comments',
            'replicate_components', 'adopt_components', 'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:
            # Limit module_bay queryset by assigned device
            params = {f"device__{self.fields['device'].to_field_name}": data.get('device')}
            self.fields['module_bay'].queryset = self.fields['module_bay'].queryset.filter(**params)

    def clean_replicate_components(self):
        # Make sure replicate_components is True when it's not included in the uploaded data
        if 'replicate_components' not in self.data:
            return True
        else:
            return self.cleaned_data['replicate_components']


#
# Device components
#

class ConsolePortImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=ConsolePortTypeChoices,
        required=False,
        help_text=_('Port type')
    )
    speed = CSVTypedChoiceField(
        label=_('Speed'),
        choices=ConsolePortSpeedChoices,
        coerce=int,
        empty_value=None,
        required=False,
        help_text=_('Port speed in bps')
    )

    class Meta:
        model = ConsolePort
        fields = ('device', 'name', 'label', 'type', 'speed', 'mark_connected', 'description', 'tags')


class ConsoleServerPortImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=ConsolePortTypeChoices,
        required=False,
        help_text=_('Port type')
    )
    speed = CSVTypedChoiceField(
        label=_('Speed'),
        choices=ConsolePortSpeedChoices,
        coerce=int,
        empty_value=None,
        required=False,
        help_text=_('Port speed in bps')
    )

    class Meta:
        model = ConsoleServerPort
        fields = ('device', 'name', 'label', 'type', 'speed', 'mark_connected', 'description', 'tags')


class PowerPortImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=PowerPortTypeChoices,
        required=False,
        help_text=_('Port type')
    )

    class Meta:
        model = PowerPort
        fields = (
            'device', 'name', 'label', 'type', 'mark_connected', 'maximum_draw', 'allocated_draw', 'description', 'tags'
        )


class PowerOutletImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=PowerOutletTypeChoices,
        required=False,
        help_text=_('Outlet type')
    )
    power_port = CSVModelChoiceField(
        label=_('Power port'),
        queryset=PowerPort.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Local power port which feeds this outlet')
    )
    feed_leg = CSVChoiceField(
        label=_('Feed leg'),
        choices=PowerOutletFeedLegChoices,
        required=False,
        help_text=_('Electrical phase (for three-phase circuits)')
    )

    class Meta:
        model = PowerOutlet
        fields = (
            'device', 'name', 'label', 'type', 'color', 'mark_connected', 'power_port', 'feed_leg', 'description',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit PowerPort choices to those belonging to this device (or VC master)
        if self.is_bound and 'device' in self.data:
            try:
                device = self.fields['device'].to_python(self.data['device'])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields['power_port'].queryset = PowerPort.objects.filter(
                device__in=[device, device.get_vc_master()]
            )
        else:
            self.fields['power_port'].queryset = PowerPort.objects.none()


class InterfaceImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=Interface.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent interface')
    )
    bridge = CSVModelChoiceField(
        label=_('Bridge'),
        queryset=Interface.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Bridged interface')
    )
    lag = CSVModelChoiceField(
        label=_('Lag'),
        queryset=Interface.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent LAG interface')
    )
    vdcs = CSVModelMultipleChoiceField(
        label=_('Vdcs'),
        queryset=VirtualDeviceContext.objects.all(),
        required=False,
        to_field_name='name',
        help_text=mark_safe(
            _('VDC names separated by commas, encased with double quotes. Example:') + ' <code>vdc1,vdc2,vdc3</code>'
        )
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=InterfaceTypeChoices,
        help_text=_('Physical medium')
    )
    duplex = CSVChoiceField(
        label=_('Duplex'),
        choices=InterfaceDuplexChoices,
        required=False
    )
    poe_mode = CSVChoiceField(
        label=_('Poe mode'),
        choices=InterfacePoEModeChoices,
        required=False,
        help_text=_('PoE mode')
    )
    poe_type = CSVChoiceField(
        label=_('Poe type'),
        choices=InterfacePoETypeChoices,
        required=False,
        help_text=_('PoE type')
    )
    mode = CSVChoiceField(
        label=_('Mode'),
        choices=InterfaceModeChoices,
        required=False,
        help_text=_('IEEE 802.1Q operational mode (for L2 interfaces)')
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        required=False,
        to_field_name='rd',
        help_text=_('Assigned VRF')
    )
    rf_role = CSVChoiceField(
        label=_('Rf role'),
        choices=WirelessRoleChoices,
        required=False,
        help_text=_('Wireless role (AP/station)')
    )

    class Meta:
        model = Interface
        fields = (
            'device', 'name', 'label', 'parent', 'bridge', 'lag', 'type', 'speed', 'duplex', 'enabled',
            'mark_connected', 'wwn', 'vdcs', 'mtu', 'mgmt_only', 'description', 'poe_mode', 'poe_type', 'mode',
            'vrf', 'rf_role', 'rf_channel', 'rf_channel_frequency', 'rf_channel_width', 'tx_power', 'tags'
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:
            # Limit choices for parent, bridge, and LAG interfaces to the assigned device
            if device := data.get('device'):
                params = {
                    f"device__{self.fields['device'].to_field_name}": device
                }
                self.fields['parent'].queryset = self.fields['parent'].queryset.filter(**params)
                self.fields['bridge'].queryset = self.fields['bridge'].queryset.filter(**params)
                self.fields['lag'].queryset = self.fields['lag'].queryset.filter(**params)
                self.fields['vdcs'].queryset = self.fields['vdcs'].queryset.filter(**params)

    def clean_enabled(self):
        # Make sure enabled is True when it's not included in the uploaded data
        if 'enabled' not in self.data:
            return True
        else:
            return self.cleaned_data['enabled']

    def clean_vdcs(self):
        for vdc in self.cleaned_data['vdcs']:
            if vdc.device != self.cleaned_data['device']:
                raise forms.ValidationError(
                    _("VDC {vdc} is not assigned to device {device}").format(
                        vdc=vdc, device=self.cleaned_data['device']
                    )
                )
        return self.cleaned_data['vdcs']


class FrontPortImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    rear_port = CSVModelChoiceField(
        label=_('Rear port'),
        queryset=RearPort.objects.all(),
        to_field_name='name',
        help_text=_('Corresponding rear port')
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=PortTypeChoices,
        help_text=_('Physical medium classification')
    )

    class Meta:
        model = FrontPort
        fields = (
            'device', 'name', 'label', 'type', 'color', 'mark_connected', 'rear_port', 'rear_port_position',
            'description', 'tags'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit RearPort choices to those belonging to this device (or VC master)
        if self.is_bound and 'device' in self.data:
            try:
                device = self.fields['device'].to_python(self.data['device'])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields['rear_port'].queryset = RearPort.objects.filter(
                device__in=[device, device.get_vc_master()]
            )
        else:
            self.fields['rear_port'].queryset = RearPort.objects.none()


class RearPortImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    type = CSVChoiceField(
        label=_('Type'),
        help_text=_('Physical medium classification'),
        choices=PortTypeChoices,
    )

    class Meta:
        model = RearPort
        fields = ('device', 'name', 'label', 'type', 'color', 'mark_connected', 'positions', 'description', 'tags')


class ModuleBayImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )

    class Meta:
        model = ModuleBay
        fields = ('device', 'name', 'label', 'position', 'description', 'tags')


class DeviceBayImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    installed_device = CSVModelChoiceField(
        label=_('Installed device'),
        queryset=Device.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Child device installed within this bay'),
        error_messages={
            'invalid_choice': _('Child device not found.'),
        }
    )

    class Meta:
        model = DeviceBay
        fields = ('device', 'name', 'label', 'installed_device', 'description', 'tags')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit installed device choices to devices of the correct type and location
        if self.is_bound and 'device' in self.data:
            try:
                device = self.fields['device'].to_python(self.data['device'])
            except forms.ValidationError:
                device = None
        else:
            try:
                device = self.instance.device
            except Device.DoesNotExist:
                device = None

        if device:
            self.fields['installed_device'].queryset = Device.objects.filter(
                site=device.site,
                rack=device.rack,
                parent_bay__isnull=True,
                device_type__u_height=0,
                device_type__subdevice_role=SubdeviceRoleChoices.ROLE_CHILD
            ).exclude(pk=device.pk)
        else:
            self.fields['installed_device'].queryset = Device.objects.none()


class InventoryItemImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name'
    )
    role = CSVModelChoiceField(
        label=_('Role'),
        queryset=InventoryItemRole.objects.all(),
        to_field_name='name',
        required=False
    )
    manufacturer = CSVModelChoiceField(
        label=_('Manufacturer'),
        queryset=Manufacturer.objects.all(),
        to_field_name='name',
        required=False
    )
    parent = CSVModelChoiceField(
        label=_('Parent'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Parent inventory item')
    )
    component_type = CSVContentTypeField(
        label=_('Component type'),
        queryset=ContentType.objects.all(),
        limit_choices_to=MODULAR_COMPONENT_MODELS,
        required=False,
        help_text=_('Component Type')
    )
    component_name = forms.CharField(
        label=_('Compnent name'),
        required=False,
        help_text=_('Component Name')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=InventoryItemStatusChoices,
        help_text=_('Operational status')
    )

    class Meta:
        model = InventoryItem
        fields = (
            'device', 'name', 'label', 'status', 'role', 'manufacturer', 'parent', 'part_id', 'serial', 'asset_tag',
            'discovered', 'description', 'tags', 'component_type', 'component_name',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit parent choices to inventory items belonging to this device
        device = None
        if self.is_bound and 'device' in self.data:
            try:
                device = self.fields['device'].to_python(self.data['device'])
            except forms.ValidationError:
                pass
        if device:
            self.fields['parent'].queryset = InventoryItem.objects.filter(device=device)
        else:
            self.fields['parent'].queryset = InventoryItem.objects.none()

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        component_type = cleaned_data.get('component_type')
        component_name = cleaned_data.get('component_name')
        device = self.cleaned_data.get("device")

        if component_type:
            if device is None:
                cleaned_data.pop('component_type', None)
            if component_name is None:
                cleaned_data.pop('component_type', None)
                raise forms.ValidationError(
                    _("Component name must be specified when component type is specified")
                )
            if all([device, component_name]):
                try:
                    model = component_type.model_class()
                    self.instance.component = model.objects.get(device=device, name=component_name)
                except ObjectDoesNotExist:
                    cleaned_data.pop('component_type', None)
                    cleaned_data.pop('component_name', None)
                    raise forms.ValidationError(
                        _("Component not found: {device} - {component_name}").format(
                            device=device, component_name=component_name
                        )
                    )
            else:
                cleaned_data.pop('component_type', None)
                if not component_name:
                    raise forms.ValidationError(
                        _("Component name must be specified when component type is specified")
                    )
        else:
            if component_name:
                raise forms.ValidationError(
                    _("Component type must be specified when component name is specified")
                )
        return cleaned_data


#
# Device component roles
#

class InventoryItemRoleImportForm(NetBoxModelImportForm):
    slug = SlugField()

    class Meta:
        model = InventoryItemRole
        fields = ('name', 'slug', 'color', 'description')


#
# Addressing
#

class MACAddressImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent device of assigned interface (if any)')
    )
    virtual_machine = CSVModelChoiceField(
        label=_('Virtual machine'),
        queryset=VirtualMachine.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Parent VM of assigned interface (if any)')
    )
    interface = CSVModelChoiceField(
        label=_('Interface'),
        queryset=Interface.objects.none(),  # Can also refer to VMInterface
        required=False,
        to_field_name='name',
        help_text=_('Assigned interface')
    )
    is_primary = forms.BooleanField(
        label=_('Is primary'),
        help_text=_('Make this the primary MAC address for the assigned interface'),
        required=False
    )

    class Meta:
        model = MACAddress
        fields = [
            'mac_address', 'device', 'virtual_machine', 'interface', 'is_primary', 'description', 'comments', 'tags',
        ]

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit interface queryset by assigned device
            if data.get('device'):
                self.fields['interface'].queryset = Interface.objects.filter(
                    **{f"device__{self.fields['device'].to_field_name}": data['device']}
                )

            # Limit interface queryset by assigned device
            elif data.get('virtual_machine'):
                self.fields['interface'].queryset = VMInterface.objects.filter(
                    **{f"virtual_machine__{self.fields['virtual_machine'].to_field_name}": data['virtual_machine']}
                )

    def clean(self):
        super().clean()

        device = self.cleaned_data.get('device')
        virtual_machine = self.cleaned_data.get('virtual_machine')
        interface = self.cleaned_data.get('interface')

        # Validate interface assignment
        if interface and not device and not virtual_machine:
            raise forms.ValidationError({
                "interface": _("Must specify the parent device or VM when assigning an interface")
            })

    def save(self, *args, **kwargs):

        # Set interface assignment
        if interface := self.cleaned_data.get('interface'):
            self.instance.assigned_object = interface

        instance = super().save(*args, **kwargs)

        # Assign the MAC address as primary for its interface, if designated as such
        if interface and self.cleaned_data['is_primary'] and self.instance.pk:
            interface.primary_mac_address = self.instance
            interface.save()

        return instance


#
# Cables
#

class CableImportForm(NetBoxModelImportForm):
    # Termination A
    side_a_site = CSVModelChoiceField(
        label=_('Side A site'),
        queryset=Site.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Site of parent device A (if any)'),
    )
    side_a_device = CSVModelChoiceField(
        label=_('Side A device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Device name')
    )
    side_a_type = CSVContentTypeField(
        label=_('Side A type'),
        queryset=ContentType.objects.all(),
        limit_choices_to=CABLE_TERMINATION_MODELS,
        help_text=_('Termination type')
    )
    side_a_name = forms.CharField(
        label=_('Side A name'),
        help_text=_('Termination name')
    )

    # Termination B
    side_b_site = CSVModelChoiceField(
        label=_('Side B site'),
        queryset=Site.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Site of parent device B (if any)'),
    )
    side_b_device = CSVModelChoiceField(
        label=_('Side B device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Device name')
    )
    side_b_type = CSVContentTypeField(
        label=_('Side B type'),
        queryset=ContentType.objects.all(),
        limit_choices_to=CABLE_TERMINATION_MODELS,
        help_text=_('Termination type')
    )
    side_b_name = forms.CharField(
        label=_('Side B name'),
        help_text=_('Termination name')
    )

    # Cable attributes
    status = CSVChoiceField(
        label=_('Status'),
        choices=LinkStatusChoices,
        required=False,
        help_text=_('Connection status')
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=CableTypeChoices,
        required=False,
        help_text=_('Physical medium classification')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )
    length_unit = CSVChoiceField(
        label=_('Length unit'),
        choices=CableLengthUnitChoices,
        required=False,
        help_text=_('Length unit')
    )
    color = forms.CharField(
        label=_('Color'),
        required=False,
        max_length=16,
        help_text=_('Color name (e.g. "Red") or hex code (e.g. "f44336")')
    )

    class Meta:
        model = Cable
        fields = [
            'side_a_site', 'side_a_device', 'side_a_type', 'side_a_name', 'side_b_site', 'side_b_device', 'side_b_type',
            'side_b_name', 'type', 'status', 'tenant', 'label', 'color', 'length', 'length_unit', 'description',
            'comments', 'tags',
        ]

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:
            # Limit choices for side_a_device to the assigned side_a_site
            if side_a_site := data.get('side_a_site'):
                side_a_device_params = {f'site__{self.fields["side_a_site"].to_field_name}': side_a_site}
                self.fields['side_a_device'].queryset = self.fields['side_a_device'].queryset.filter(
                    **side_a_device_params
                )

            # Limit choices for side_b_device to the assigned side_b_site
            if side_b_site := data.get('side_b_site'):
                side_b_device_params = {f'site__{self.fields["side_b_site"].to_field_name}': side_b_site}
                self.fields['side_b_device'].queryset = self.fields['side_b_device'].queryset.filter(
                    **side_b_device_params
                )

    def _clean_side(self, side):
        """
        Derive a Cable's A/B termination objects.

        :param side: 'a' or 'b'
        """
        assert side in 'ab', f"Invalid side designation: {side}"

        device = self.cleaned_data.get(f'side_{side}_device')
        content_type = self.cleaned_data.get(f'side_{side}_type')
        name = self.cleaned_data.get(f'side_{side}_name')
        if not device or not content_type or not name:
            return None

        model = content_type.model_class()
        try:
            if device.virtual_chassis and device.virtual_chassis.master == device and \
                    model.objects.filter(device=device, name=name).count() == 0:
                termination_object = model.objects.get(device__in=device.virtual_chassis.members.all(), name=name)
            else:
                termination_object = model.objects.get(device=device, name=name)
            if termination_object.cable is not None and termination_object.cable != self.instance:
                raise forms.ValidationError(
                    _("Side {side_upper}: {device} {termination_object} is already connected").format(
                        side_upper=side.upper(), device=device, termination_object=termination_object
                    )
                )
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                _("{side_upper} side termination not found: {device} {name}").format(
                    side_upper=side.upper(), device=device, name=name
                )
            )
        setattr(self.instance, f'{side}_terminations', [termination_object])
        return termination_object

    def _clean_color(self, color):
        """
        Derive a colors hex code

        :param color: color as hex or color name
        """
        color_parsed = color.strip().lower()

        for hex_code, label in ColorChoices.CHOICES:
            if color.lower() == label.lower():
                color_parsed = hex_code

        if len(color_parsed) > 6:
            raise forms.ValidationError(
                _(f"{color} did not match any used color name and was longer than six characters: invalid hex.")
            )
        return color_parsed

    def clean_side_a_name(self):
        return self._clean_side('a')

    def clean_side_b_name(self):
        return self._clean_side('b')

    def clean_length_unit(self):
        # Avoid trying to save as NULL
        length_unit = self.cleaned_data.get('length_unit', None)
        return length_unit if length_unit is not None else ''

    def clean_color(self):
        color = self.cleaned_data.get('color', None)
        return self._clean_color(color) if color is not None else ''
#
# Virtual chassis
#


class VirtualChassisImportForm(NetBoxModelImportForm):
    master = CSVModelChoiceField(
        label=_('Master'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Master device')
    )

    class Meta:
        model = VirtualChassis
        fields = ('name', 'domain', 'master', 'description', 'comments', 'tags')


#
# Power
#

class PowerPanelImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text=_('Name of parent site')
    )
    location = CSVModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        required=False,
        to_field_name='name'
    )

    class Meta:
        model = PowerPanel
        fields = ('site', 'location', 'name', 'description', 'comments', 'tags')

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit group queryset by assigned site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['location'].queryset = self.fields['location'].queryset.filter(**params)


class PowerFeedImportForm(NetBoxModelImportForm):
    site = CSVModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text=_('Assigned site')
    )
    power_panel = CSVModelChoiceField(
        label=_('Power panel'),
        queryset=PowerPanel.objects.all(),
        to_field_name='name',
        help_text=_('Upstream power panel')
    )
    location = CSVModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_("Rack's location (if any)")
    )
    rack = CSVModelChoiceField(
        label=_('Rack'),
        queryset=Rack.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Rack')
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Assigned tenant')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=PowerFeedStatusChoices,
        help_text=_('Operational status')
    )
    type = CSVChoiceField(
        label=_('Type'),
        choices=PowerFeedTypeChoices,
        help_text=_('Primary or redundant')
    )
    supply = CSVChoiceField(
        label=_('Supply'),
        choices=PowerFeedSupplyChoices,
        help_text=_('Supply type (AC/DC)')
    )
    phase = CSVChoiceField(
        label=_('Phase'),
        choices=PowerFeedPhaseChoices,
        help_text=_('Single or three-phase')
    )

    class Meta:
        model = PowerFeed
        fields = (
            'site', 'power_panel', 'location', 'rack', 'name', 'status', 'type', 'mark_connected', 'supply', 'phase',
            'voltage', 'amperage', 'max_utilization', 'tenant', 'description', 'comments', 'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit power_panel queryset by site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['power_panel'].queryset = self.fields['power_panel'].queryset.filter(**params)

            # Limit location queryset by site
            params = {f"site__{self.fields['site'].to_field_name}": data.get('site')}
            self.fields['location'].queryset = self.fields['location'].queryset.filter(**params)

            # Limit rack queryset by site and group
            params = {
                f"site__{self.fields['site'].to_field_name}": data.get('site'),
                f"location__{self.fields['location'].to_field_name}": data.get('location'),
            }
            self.fields['rack'].queryset = self.fields['rack'].queryset.filter(**params)


class VirtualDeviceContextImportForm(NetBoxModelImportForm):

    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Assigned role')
    )
    tenant = CSVModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text=_('Assigned tenant')
    )
    status = CSVChoiceField(
        label=_('Status'),
        choices=VirtualDeviceContextStatusChoices,
    )
    primary_ip4 = CSVModelChoiceField(
        label=_('Primary IPv4'),
        queryset=IPAddress.objects.all(),
        required=False,
        to_field_name='address',
        help_text=_('IPv4 address with mask, e.g. 1.2.3.4/24')
    )
    primary_ip6 = CSVModelChoiceField(
        label=_('Primary IPv6'),
        queryset=IPAddress.objects.all(),
        required=False,
        to_field_name='address',
        help_text=_('IPv6 address with prefix length, e.g. 2001:db8::1/64')
    )

    class Meta:
        fields = [
            'name', 'device', 'status', 'tenant', 'identifier', 'comments', 'primary_ip4', 'primary_ip6',
        ]
        model = VirtualDeviceContext

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if data:

            # Limit primary_ip4/ip6 querysets by assigned device
            params = {f"interface__device__{self.fields['device'].to_field_name}": data.get('device')}
            self.fields['primary_ip4'].queryset = self.fields['primary_ip4'].queryset.filter(**params)
            self.fields['primary_ip6'].queryset = self.fields['primary_ip6'].queryset.filter(**params)
