import unittest

from ilng911.core.parser import safe_eval
from test.test_setup import ft, schema, road

class TestFieldCalculations(unittest.TestCase):

    # def test_safe_eval(self):
    #     val = safe_eval('7*4')
    #     self.assertEqual(val, 28)

    def test_simple_calc(self):
        pass

    def test_complex_calc(self):
        # expr = '{Add_Number} {St_Name} {St_PosTyp} {Post_Code}'
        # val = road.create_from_expression(expr)
        field = 'GC_ADDRESS_wZIP'
        schema.calculate_custom_fields(ft)
        
        actual = '142 MAIN STREET 62353'
        self.assertEqual(ft.get(field), actual)

# "c:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe" -m unittest -v test/test_calculations.py