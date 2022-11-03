import arcpy
import unittest

from test.test_setup import addressSchema, roadSchema, ng911_db
from ilng911.schemas import DataSchema

class TestFieldCalculations(unittest.TestCase):

    # def test_safe_eval(self):
    #     val = safe_eval('7*4')
    #     self.assertEqual(val, 28)

    def test_concatenated_calc(self):
        pass
        # # expr = '{Add_Number} {St_Name} {St_PosTyp} {Post_Code}'
        # # val = road.create_from_expression(expr)
        # field = 'GC_ADDRESS_wZIP'
        # schema.calculate_custom_fields(ft)
        
        # actual = '142 MAIN STREET 62353'
        # self.assertEqual(ft.get(field), actual)


class TestNG911Database(unittest.TestCase):

    def test_setup_complete(self):
        self.assertTrue(ng911_db.setupComplete, 'the NG911Database setup is complete')

    def test_address_points(self):
        self.assertIsNotNone(ng911_db.addressPoints, 'address points have been located')
    
    def test_road_centerline(self):
        self.assertIsNotNone(ng911_db.addressPoints, 'road centerlines have been located')

    def test_new_nena_ids(self):
        self.assertGreater(len(ng911_db.nena_id_table), 0, 'there are new nena ids')
    
    def test_can_get_shapetype(self):
        self.assertEqual(arcpy.Describe(ng911_db.addressPoints).shapeType, 'Point', 'address points has point shapetype')
    
    def test_road_centerline(self): 
        self.assertEqual(arcpy.Describe(ng911_db.roadCenterlines).shapeType, 'Polyline', 'road centrlines have polyline shapetype')


class Test911DataSchema(unittest.TestCase):
    def test_address_points_name(self):
        self.assertEqual(addressSchema.name, 'ADDRESS_POINTS', 'the address schema has the correct name')
    
    def test_address_points_table(self):
        self.assertEqual(ng911_db.addressPoints, addressSchema.table, 'the address schema can find the table')
    
    def test_road_centerline_name(self):
        self.assertEqual(roadSchema.name, 'ROAD_CENTERLINE', 'the address schema has the correct name')

    def test_road_centerlines_table(self):
        self.assertEqual(ng911_db.roadCenterlines, roadSchema.table, 'the address schema can find the table')

    def test_esb_schemas(self):
        for info in ng911_db.get_911_features():
            if info.FeatureType.startswith('ESB'):
                schema = DataSchema(info.FeatureType)
                print(f'checking schema: "{info.FeatureType}"')
                self.assertEqual(schema.name, info.FeatureType, f'ESB schema has name: "{schema.name}"')
                self.assertEqual(schema.table, info.Path, f'ESB schema has table: "{schema.table}"')
                self.assertEqual(schema.nenaIdentifier, info.GUID_Field, 'the ESB schema has the correct NENA identifier')
                self.assertTrue(schema.isPSAPLike, f'the ESB schema "{schema.name}" is PSAP like')
                