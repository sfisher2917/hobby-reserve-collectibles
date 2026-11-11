import importlib.util
import unittest
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
spec=importlib.util.spec_from_file_location('sync','scripts/sync_inventory.py'); sync=importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
def xml(content): return ET.fromstring('<Response xmlns="urn:ebay:apis:eBLBaseComponents">'+content+'</Response>')
class Fake:
    def call(self,name,fields):
        if name=='GetUser': return xml('<User><UserID>hobbyreservecollectibles</UserID></User>')
        if name=='GetMyeBaySelling':
            page=fields['ActiveList']['Pagination']['PageNumber']
            return xml(f'<ActiveList><PaginationResult><TotalNumberOfPages>2</TotalNumberOfPages><TotalNumberOfEntries>2</TotalNumberOfEntries></PaginationResult><ItemArray><Item><ItemID>{page}</ItemID><Title>Football {page}</Title><SellingStatus><CurrentPrice currencyID="USD">9.99</CurrentPrice></SellingStatus></Item></ItemArray></ActiveList>')
        return xml('<Item><Seller><UserID>hobbyreservecollectibles</UserID></Seller><Description>&lt;p&gt;Clean card&lt;/p&gt;</Description><PrimaryCategory><CategoryName>Football Cards</CategoryName></PrimaryCategory><PictureDetails><PictureURL>https://i.ebayimg.com/photo.jpg</PictureURL></PictureDetails></Item>')
class Tests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(sync.classify('Pokémon booster box',''),['Sealed Products','Pokémon'])
        self.assertEqual(sync.classify('Topps','Sports:Basketball Cards'),['Basketball'])
        self.assertEqual(sync.classify('Lorcana',''),['Other TCG'])
        self.assertEqual(sync.classify('Collectible coin',''),['Other Collectibles'])
    def test_plain(self): self.assertNotIn('bad',sync.plain('<script>bad()</script><p>Good</p>'))
    def test_pages_and_removal(self):
        result=sync.export(Fake(),{'products':[{'id':'999'}]},datetime.now(timezone.utc))
        self.assertEqual([p['id'] for p in result['products']],['1','2'])
        self.assertTrue(all(p['description']=='Clean card' for p in result['products']))
    def test_wrong_seller(self):
        class Wrong(Fake):
            def call(self,name,fields): return xml('<User><UserID>someone_else</UserID></User>')
        with self.assertRaises(RuntimeError): sync.export(Wrong(),{},datetime.now(timezone.utc))
if __name__=='__main__':unittest.main()
