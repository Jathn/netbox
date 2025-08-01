from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from core.choices import ObjectChangeActionChoices
from core.models import ObjectChange, ObjectType
from dcim.choices import SiteStatusChoices
from dcim.models import Site, CableTermination, Device, DeviceType, DeviceRole, Interface, Cable
from extras.choices import *
from extras.models import CustomField, CustomFieldChoiceSet, Tag
from utilities.testing import APITestCase
from utilities.testing.utils import create_tags, post_data
from utilities.testing.views import ModelViewTestCase
from dcim.models import Manufacturer


class ChangeLogViewTest(ModelViewTestCase):
    model = Site

    @classmethod
    def setUpTestData(cls):
        choice_set = CustomFieldChoiceSet.objects.create(
            name='Choice Set 1',
            extra_choices=(('foo', 'Foo'), ('bar', 'Bar'))
        )

        # Create a custom field on the Site model
        site_type = ObjectType.objects.get_for_model(Site)
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_TEXT,
            name='cf1',
            required=False
        )
        cf.save()
        cf.object_types.set([site_type])

        # Create a select custom field on the Site model
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name='cf2',
            required=False,
            choice_set=choice_set
        )
        cf_select.save()
        cf_select.object_types.set([site_type])

    def test_create_object(self):
        tags = create_tags('Tag 1', 'Tag 2')
        form_data = {
            'name': 'Site 1',
            'slug': 'site-1',
            'status': SiteStatusChoices.STATUS_ACTIVE,
            'cf_cf1': 'ABC',
            'cf_cf2': 'bar',
            'tags': [tag.pk for tag in tags],
        }

        request = {
            'path': self._get_url('add'),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.add_site', 'extras.view_tag')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        site = Site.objects.get(name='Site 1')
        oc = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=site.pk
        )
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.prechange_data, None)
        self.assertEqual(oc.postchange_data['custom_fields']['cf1'], form_data['cf_cf1'])
        self.assertEqual(oc.postchange_data['custom_fields']['cf2'], form_data['cf_cf2'])
        self.assertEqual(oc.postchange_data['tags'], ['Tag 1', 'Tag 2'])

    def test_update_object(self):
        site = Site(name='Site 1', slug='site-1')
        site.save()
        tags = create_tags('Tag 1', 'Tag 2', 'Tag 3')
        site.tags.set(['Tag 1', 'Tag 2'])

        form_data = {
            'name': 'Site X',
            'slug': 'site-x',
            'status': SiteStatusChoices.STATUS_PLANNED,
            'cf_cf1': 'DEF',
            'cf_cf2': 'foo',
            'tags': [tags[2].pk],
        }

        request = {
            'path': self._get_url('edit', instance=site),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.change_site', 'extras.view_tag')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        site.refresh_from_db()
        oc = ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=site.pk
        ).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.prechange_data['name'], 'Site 1')
        self.assertEqual(oc.prechange_data['tags'], ['Tag 1', 'Tag 2'])
        self.assertEqual(oc.postchange_data['custom_fields']['cf1'], form_data['cf_cf1'])
        self.assertEqual(oc.postchange_data['custom_fields']['cf2'], form_data['cf_cf2'])
        self.assertEqual(oc.postchange_data['tags'], ['Tag 3'])

    def test_delete_object(self):
        site = Site(
            name='Site 1',
            slug='site-1',
            custom_field_data={
                'cf1': 'ABC',
                'cf2': 'Bar'
            }
        )
        site.save()
        create_tags('Tag 1', 'Tag 2')
        site.tags.set(['Tag 1', 'Tag 2'])

        request = {
            'path': self._get_url('delete', instance=site),
            'data': post_data({'confirm': True}),
        }
        self.add_permissions('dcim.delete_site')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, site.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.prechange_data['custom_fields']['cf1'], 'ABC')
        self.assertEqual(oc.prechange_data['custom_fields']['cf2'], 'Bar')
        self.assertEqual(oc.prechange_data['tags'], ['Tag 1', 'Tag 2'])
        self.assertEqual(oc.postchange_data, None)

    def test_bulk_update_objects(self):
        sites = (
            Site(name='Site 1', slug='site-1', status=SiteStatusChoices.STATUS_ACTIVE),
            Site(name='Site 2', slug='site-2', status=SiteStatusChoices.STATUS_ACTIVE),
            Site(name='Site 3', slug='site-3', status=SiteStatusChoices.STATUS_ACTIVE),
        )
        Site.objects.bulk_create(sites)

        form_data = {
            'pk': [site.pk for site in sites],
            '_apply': True,
            'status': SiteStatusChoices.STATUS_PLANNED,
            'description': 'New description',
        }

        request = {
            'path': self._get_url('bulk_edit'),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.view_site', 'dcim.change_site')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=sites[0].pk
        )
        self.assertEqual(objectchange.changed_object, sites[0])
        self.assertEqual(objectchange.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(objectchange.prechange_data['status'], SiteStatusChoices.STATUS_ACTIVE)
        self.assertEqual(objectchange.prechange_data['description'], '')
        self.assertEqual(objectchange.postchange_data['status'], form_data['status'])
        self.assertEqual(objectchange.postchange_data['description'], form_data['description'])

    def test_bulk_delete_objects(self):
        sites = (
            Site(name='Site 1', slug='site-1', status=SiteStatusChoices.STATUS_ACTIVE),
            Site(name='Site 2', slug='site-2', status=SiteStatusChoices.STATUS_ACTIVE),
            Site(name='Site 3', slug='site-3', status=SiteStatusChoices.STATUS_ACTIVE),
        )
        Site.objects.bulk_create(sites)

        form_data = {
            'pk': [site.pk for site in sites],
            'confirm': True,
            '_confirm': True,
        }

        request = {
            'path': self._get_url('bulk_delete'),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.delete_site')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=sites[0].pk
        )
        self.assertEqual(objectchange.changed_object_type, ContentType.objects.get_for_model(Site))
        self.assertEqual(objectchange.changed_object_id, sites[0].pk)
        self.assertEqual(objectchange.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(objectchange.prechange_data['name'], sites[0].name)
        self.assertEqual(objectchange.prechange_data['slug'], sites[0].slug)
        self.assertEqual(objectchange.postchange_data, None)

    @override_settings(CHANGELOG_SKIP_EMPTY_CHANGES=False)
    def test_update_object_change(self):
        # Create a Site
        site = Site.objects.create(
            name='Site 1',
            slug='site-1',
            status=SiteStatusChoices.STATUS_PLANNED,
            custom_field_data={
                'cf1': None,
                'cf2': None
            }
        )

        # Update it with the same field values
        form_data = {
            'name': site.name,
            'slug': site.slug,
            'status': SiteStatusChoices.STATUS_PLANNED,
        }
        request = {
            'path': self._get_url('edit', instance=site),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.change_site', 'extras.view_tag')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Check that an ObjectChange record has been created
        self.assertEqual(ObjectChange.objects.count(), 1)

    @override_settings(CHANGELOG_SKIP_EMPTY_CHANGES=True)
    def test_update_object_nochange(self):
        # Create a Site
        site = Site.objects.create(
            name='Site 1',
            slug='site-1',
            status=SiteStatusChoices.STATUS_PLANNED,
            custom_field_data={
                'cf1': None,
                'cf2': None
            }
        )

        # Update it with the same field values
        form_data = {
            'name': site.name,
            'slug': site.slug,
            'status': SiteStatusChoices.STATUS_PLANNED,
        }
        request = {
            'path': self._get_url('edit', instance=site),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.change_site', 'extras.view_tag')
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Check that no ObjectChange records have been created
        self.assertEqual(ObjectChange.objects.count(), 0)

    def test_ordering_genericrelation(self):
        # Create required objects first
        manufacturer = Manufacturer.objects.create(name='Manufacturer 1')
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model='Model 1',
            slug='model-1'
        )
        device_role = DeviceRole.objects.create(
            name='Role 1',
            slug='role-1'
        )
        site = Site.objects.create(
            name='Site 1',
            slug='site-1'
        )

        # Create two devices
        device1 = Device.objects.create(
            name='Device 1',
            device_type=device_type,
            role=device_role,
            site=site
        )
        device2 = Device.objects.create(
            name='Device 2',
            device_type=device_type,
            role=device_role,
            site=site
        )

        # Create interfaces on both devices
        interface1 = Interface.objects.create(
            device=device1,
            name='eth0',
            type='1000base-t'
        )
        interface2 = Interface.objects.create(
            device=device2,
            name='eth0',
            type='1000base-t'
        )

        # Create a cable between the interfaces
        _ = Cable.objects.create(
            a_terminations=[interface1],
            b_terminations=[interface2],
            status='connected'
        )

        # Delete device1
        request = {
            'path': reverse('dcim:device_delete', kwargs={'pk': device1.pk}),
            'data': post_data({'confirm': True}),
        }
        self.add_permissions(
            'dcim.delete_device',
            'dcim.delete_interface',
            'dcim.delete_cable',
            'dcim.delete_cabletermination'
        )
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Get the ObjectChange records for delete actions ordered by time
        changes = ObjectChange.objects.filter(
            action=ObjectChangeActionChoices.ACTION_DELETE
        ).order_by('time')[:3]

        # Verify the order of deletion
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[0].changed_object_type, ContentType.objects.get_for_model(CableTermination))
        self.assertEqual(changes[1].changed_object_type, ContentType.objects.get_for_model(Interface))
        self.assertEqual(changes[2].changed_object_type, ContentType.objects.get_for_model(Device))

    def test_duplicate_deletions(self):
        """
        Check that a cascading deletion event does not generate multiple "deleted" ObjectChange records for
        the same object.
        """
        role1 = DeviceRole(name='Role 1', slug='role-1')
        role1.save()
        role2 = DeviceRole(name='Role 2', slug='role-2', parent=role1)
        role2.save()
        pk_list = [role1.pk, role2.pk]

        # Delete both objects simultaneously
        form_data = {
            'pk': pk_list,
            'confirm': True,
            '_confirm': True,
        }
        request = {
            'path': reverse('dcim:devicerole_bulk_delete'),
            'data': post_data(form_data),
        }
        self.add_permissions('dcim.delete_devicerole')
        self.assertHttpStatus(self.client.post(**request), 302)

        # This should result in exactly one change record per object
        objectchanges = ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(DeviceRole),
            changed_object_id__in=pk_list,
            action=ObjectChangeActionChoices.ACTION_DELETE
        )
        self.assertEqual(objectchanges.count(), 2)


class ChangeLogAPITest(APITestCase):

    @classmethod
    def setUpTestData(cls):

        # Create a custom field on the Site model
        site_type = ObjectType.objects.get_for_model(Site)
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_TEXT,
            name='cf1',
            required=False
        )
        cf.save()
        cf.object_types.set([site_type])

        # Create a select custom field on the Site model
        choice_set = CustomFieldChoiceSet.objects.create(
            name='Choice Set 1',
            extra_choices=(('foo', 'Foo'), ('bar', 'Bar'))
        )
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name='cf2',
            required=False,
            choice_set=choice_set
        )
        cf_select.save()
        cf_select.object_types.set([site_type])

        # Create some tags
        tags = (
            Tag(name='Tag 1', slug='tag-1'),
            Tag(name='Tag 2', slug='tag-2'),
            Tag(name='Tag 3', slug='tag-3'),
        )
        Tag.objects.bulk_create(tags)

    def test_create_object(self):
        data = {
            'name': 'Site 1',
            'slug': 'site-1',
            'custom_fields': {
                'cf1': 'ABC',
                'cf2': 'bar',
            },
            'tags': [
                {'name': 'Tag 1'},
                {'name': 'Tag 2'},
            ]
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse('dcim-api:site-list')
        self.add_permissions('dcim.add_site')

        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        site = Site.objects.get(pk=response.data['id'])
        oc = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=site.pk
        )
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.prechange_data, None)
        self.assertEqual(oc.postchange_data['custom_fields'], data['custom_fields'])
        self.assertEqual(oc.postchange_data['tags'], ['Tag 1', 'Tag 2'])

    def test_update_object(self):
        site = Site(name='Site 1', slug='site-1')
        site.save()

        data = {
            'name': 'Site X',
            'slug': 'site-x',
            'custom_fields': {
                'cf1': 'DEF',
                'cf2': 'foo',
            },
            'tags': [
                {'name': 'Tag 3'}
            ]
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions('dcim.change_site')
        url = reverse('dcim-api:site-detail', kwargs={'pk': site.pk})

        response = self.client.put(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        site = Site.objects.get(pk=response.data['id'])
        oc = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=site.pk
        )
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.postchange_data['custom_fields'], data['custom_fields'])
        self.assertEqual(oc.postchange_data['tags'], ['Tag 3'])

    def test_delete_object(self):
        site = Site(
            name='Site 1',
            slug='site-1',
            custom_field_data={
                'cf1': 'ABC',
                'cf2': 'Bar'
            }
        )
        site.save()
        site.tags.set(Tag.objects.all()[:2])
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions('dcim.delete_site')
        url = reverse('dcim-api:site-detail', kwargs={'pk': site.pk})

        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Site.objects.count(), 0)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, site.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.prechange_data['custom_fields']['cf1'], 'ABC')
        self.assertEqual(oc.prechange_data['custom_fields']['cf2'], 'Bar')
        self.assertEqual(oc.prechange_data['tags'], ['Tag 1', 'Tag 2'])
        self.assertEqual(oc.postchange_data, None)

    def test_bulk_create_objects(self):
        data = (
            {
                'name': 'Site 1',
                'slug': 'site-1',
            },
            {
                'name': 'Site 2',
                'slug': 'site-2',
            },
            {
                'name': 'Site 3',
                'slug': 'site-3',
            },
        )
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse('dcim-api:site-list')
        self.add_permissions('dcim.add_site')

        response = self.client.post(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(ObjectChange.objects.count(), 3)

        site1 = Site.objects.get(pk=response.data[0]['id'])
        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=site1.pk
        )
        self.assertEqual(objectchange.changed_object, site1)
        self.assertEqual(objectchange.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(objectchange.prechange_data, None)
        self.assertEqual(objectchange.postchange_data['name'], data[0]['name'])
        self.assertEqual(objectchange.postchange_data['slug'], data[0]['slug'])

    def test_bulk_edit_objects(self):
        sites = (
            Site(name='Site 1', slug='site-1'),
            Site(name='Site 2', slug='site-2'),
            Site(name='Site 3', slug='site-3'),
        )
        Site.objects.bulk_create(sites)

        data = (
            {
                'id': sites[0].pk,
                'name': 'Site A',
                'slug': 'site-A',
            },
            {
                'id': sites[1].pk,
                'name': 'Site B',
                'slug': 'site-b',
            },
            {
                'id': sites[2].pk,
                'name': 'Site C',
                'slug': 'site-c',
            },
        )
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse('dcim-api:site-list')
        self.add_permissions('dcim.change_site')

        response = self.client.patch(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(ObjectChange.objects.count(), 3)

        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=sites[0].pk
        )
        self.assertEqual(objectchange.changed_object, sites[0])
        self.assertEqual(objectchange.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(objectchange.prechange_data['name'], 'Site 1')
        self.assertEqual(objectchange.prechange_data['slug'], 'site-1')
        self.assertEqual(objectchange.postchange_data['name'], data[0]['name'])
        self.assertEqual(objectchange.postchange_data['slug'], data[0]['slug'])

    def test_bulk_delete_objects(self):
        sites = (
            Site(name='Site 1', slug='site-1'),
            Site(name='Site 2', slug='site-2'),
            Site(name='Site 3', slug='site-3'),
        )
        Site.objects.bulk_create(sites)

        data = (
            {
                'id': sites[0].pk,
            },
            {
                'id': sites[1].pk,
            },
            {
                'id': sites[2].pk,
            },
        )
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse('dcim-api:site-list')
        self.add_permissions('dcim.delete_site')

        response = self.client.delete(url, data, format='json', **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ObjectChange.objects.count(), 3)

        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(Site),
            changed_object_id=sites[0].pk
        )
        self.assertEqual(objectchange.changed_object_type, ContentType.objects.get_for_model(Site))
        self.assertEqual(objectchange.changed_object_id, sites[0].pk)
        self.assertEqual(objectchange.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(objectchange.prechange_data['name'], 'Site 1')
        self.assertEqual(objectchange.prechange_data['slug'], 'site-1')
        self.assertEqual(objectchange.postchange_data, None)
