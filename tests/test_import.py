import sys
import unittest
sys.path.insert(0,'scripts')
from import_inventory import convert
from sync_inventory import details_from_item
import xml.etree.ElementTree as ET
from datetime import datetime,timezone

class ImportTests(unittest.TestCase):
    def row(self):return {'Item number':'137877366789','Item title':'Football rookie','Current price':'$12.00','PicURL':'https://i.ebayimg.com/first.jpg|https://i.ebayimg.com/second.jpg','Description':'<b>Actual description</b><script>bad()</script>','Buyer email':'private@example.com'}
    def test_full_import_excludes_private_fields_and_cleans_description(self):
        data,report=convert([self.row()],{},1,True)
        self.assertEqual(data['products'][0]['description'],'Actual description')
        self.assertEqual(len(data['products'][0]['images']),2)
        self.assertNotIn('Buyer email',data['products'][0])
    def test_wrong_count_and_missing_images_stop_import(self):
        with self.assertRaises(ValueError):convert([self.row()],{},357)
        row=self.row();row.pop('PicURL')
        with self.assertRaises(ValueError):convert([row],{},1)
    def test_details_include_gallery_specifics_and_public_terms(self):
        item=ET.fromstring('<Item xmlns="urn:ebay:apis:eBLBaseComponents"><ConditionDisplayName>Near mint</ConditionDisplayName><PictureDetails><PictureURL>https://i.ebayimg.com/1.jpg</PictureURL><PictureURL>https://i.ebayimg.com/2.jpg</PictureURL></PictureDetails><ItemSpecifics><NameValueList><Name>Player</Name><Value>Example player</Value></NameValueList></ItemSpecifics><ShippingDetails><ShippingServiceOptions><ShippingService>USPS</ShippingService><ShippingServiceCost>4.99</ShippingServiceCost></ShippingServiceOptions></ShippingDetails></Item>')
        data=details_from_item(item,datetime.now(timezone.utc))
        self.assertEqual(len(data['images']),2)
        self.assertEqual(data['itemSpecifics']['Player'],['Example player'])
        self.assertEqual(data['shipping'][0]['cost'],4.99)

if __name__=='__main__':unittest.main()
