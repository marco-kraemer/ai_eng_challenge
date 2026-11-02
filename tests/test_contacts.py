import unittest
from pathlib import Path
from app.contacts import Contacts
from app.chat import Chat
from unittest.mock import Mock

class ContactTests(unittest.TestCase):
    def test_remote_channel_and_conflicting_contacts_have_sources(self):
        result=Contacts(Path('data')).lookup('remote')
        self.assertEqual(result['status'],'found')
        self.assertEqual(result['channels'][0]['phone'],'(67) 3321-4500')
        self.assertEqual(result['channels'][0]['pages'],[6])
        self.assertTrue(result['warnings'])
        self.assertTrue(any('3341-4444' in source['text'] for source in result['items']))
        self.assertTrue(any('3321-4500' in source['text'] for source in result['items']))
        self.assertEqual(Contacts(Path('data')).lookup('invented')['status'],'invalid')

    def test_checkout_tool_is_read_only_and_keeps_provenance(self):
        chat=Chat(Mock(),__import__('app.catalog',fromlist=['Catalog']).Catalog(Path('data')))
        result=chat.dispatch('store_contacts',{'channel':'remote'})
        self.assertEqual(result['status'],'found')
        self.assertIn('3321-4500',str(chat.contacts))
        self.assertTrue(chat.sources)
        self.assertEqual(chat.dispatch('reserve_stock',{'product_id':81})['status'],'invalid')
        self.assertEqual(chat.dispatch('create_order',{})['status'],'invalid')
