import unittest
from osvimdriver.openstack.heat.template import HeatInputUtil
from ignition.utils.propvaluemap import PropValueMap

class TestHeatInputUtil(unittest.TestCase):

    def test_filter_used_properties(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB:
            type: string
        '''
        orig_props = {'propA': 'testA', 'propB': 'testB', 'propC': 'testC'}
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB': 'testB'})

    def test_filter_used_properties_prop_value_map(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'string', 'value': 'testA'},
          'propB': {'type': 'string', 'value': 'testB'},
          'propC': {'type': 'string', 'value': 'testC'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB': 'testB'})

    def test_filter_used_properties_reference_key_name(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'string', 'value': 'testA'},
          'propB': {'type': 'key', 'keyName': 'keyB', 'privateKey': 'thisIsPrivate', 'publicKey': 'thisIsPublic'},
          'propC': {'type': 'string', 'value': 'testC'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB': 'keyB'})

    def test_filter_used_properties_reference_public(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB_public:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'string', 'value': 'testA'},
          'propB': {'type': 'key', 'keyName': 'keyB', 'privateKey': 'thisIsPrivate', 'publicKey': 'thisIsPublic'},
          'propC': {'type': 'string', 'value': 'testC'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB_public': 'thisIsPublic'})

    def test_filter_used_properties_reference_private(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB_private:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'string', 'value': 'testA'},
          'propB': {'type': 'key', 'keyName': 'keyB', 'privateKey': 'thisIsPrivate', 'publicKey': 'thisIsPublic'},
          'propC': {'type': 'string', 'value': 'testC'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB_private': 'thisIsPrivate'})

    def test_filter_used_properties_reference_all_parts_of_key(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA: 
            type: string
          propB: 
            type: string
          propB_private:
            type: string
          propB_public:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'string', 'value': 'testA'},
          'propB': {'type': 'key', 'keyName': 'keyB', 'privateKey': 'thisIsPrivate', 'publicKey': 'thisIsPublic'},
          'propC': {'type': 'string', 'value': 'testC'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA': 'testA', 'propB': 'keyB', 'propB_public': 'thisIsPublic', 'propB_private': 'thisIsPrivate'})

    def test_filter_used_properties_allows_public_key_suffix_on_non_key_property(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA_public:
            type: string
        '''
        orig_props = PropValueMap({
          'propA_public': {'type': 'string', 'value': 'testA'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA_public': 'testA'})
    
    def test_filter_used_properties_allows_private_key_suffix_on_non_key_property(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA_private:
            type: string
        '''
        orig_props = PropValueMap({
          'propA_private': {'type': 'string', 'value': 'testA'}
        })
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {'propA_private': 'testA'})

    def test_filter_used_properties_supports_no_public_key(self):
        util = HeatInputUtil()
        heat_yml = '''
        parameters: 
          propA_public:
            type: string
        '''
        orig_props = PropValueMap({
          'propA': {'type': 'key', 'keyName': 'keyA', 'privateKey': 'thisIsPrivate'}
        })
        # The property has no public key, so nothing is added to the used properties. Let Heat determine if this parameter is required 
        # (and ultimately throw an error if it is)
        new_props = util.filter_used_properties(heat_yml, orig_props)
        self.assertEqual(new_props, {})


        