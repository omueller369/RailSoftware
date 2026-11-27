# Vollständige Zugfahrten teilen Seiten; der bisherige Berichtskopf bleibt identisch.
import io,unittest
from pypdf import PdfReader
from lokzeitleiste.documents.archive import pdf_document

def train(marker,rows=1):
    head=[['Zugnr.','StartBf','Abfahrt','ZielBf','Ankunft'],[marker,'AAA','08:00','BBB','10:00']]
    events=[['Grund','Verursacher','Ort/Bf','Von','Bis','Dauer']]+[[marker+'_DETAIL_'+str(i),'DB-InfraGo','CCC','09:00','09:01','0:01'] for i in range(rows)]
    return [(marker+' · Umlaufname TEST-Rotation',head),('Details',events,.12)]

def render(trains,packed=True):
    raw=pdf_document('Arbeitsbericht vom 27.11.2026',[('Name','Fiktiver Tf'),('Dienstbeginn','08:00'),('Dienstende','16:00')],sections=[('Gastfahrten',[['Von','Nach'],['AAA','BBB']],0)],paired_head=True,train_pages=trains,pack_trains=packed)
    return PdfReader(io.BytesIO(raw))

class ReportPagePackingTest(unittest.TestCase):
    def test_first_page_unchanged_and_several_short_trains_share_page(self):
        trains=[train('TRAIN_A'),train('TRAIN_B'),train('TRAIN_C')]
        packed=render(trains);previous=render(trains,False)
        self.assertEqual(packed.pages[0].get_contents().get_data(),previous.pages[0].get_contents().get_data())
        self.assertEqual(len(packed.pages),2);self.assertEqual(len(previous.pages),4)
        text=packed.pages[1].extract_text()
        for marker in ['TRAIN_A','TRAIN_B','TRAIN_C']:self.assertIn(marker+'_DETAIL_0',text)
        for page in packed.pages:self.assertAlmostEqual(float(page.mediabox.width),595.2756,places=2);self.assertAlmostEqual(float(page.mediabox.height),841.8898,places=2)
    def test_long_details_repeat_train_header_and_train_page_counter(self):
        pdf=render([train('SHORT_A'),train('LARGE_B',180),train('SHORT_C')]);texts=[p.extract_text() for p in pdf.pages]
        continued=[text for text in texts if 'LARGE_B_DETAIL_' in text];self.assertGreater(len(continued),1)
        for i,text in enumerate(continued,1):
            compact=' '.join(text.split());self.assertIn(f'Zugnummer LARGE_B: Seite {i} von {len(continued)}',compact)
            for marker in ['Umlaufname TEST-Rotation','AAA','BBB','08:00','10:00']:self.assertIn(marker,compact)
        for i in range(180):self.assertEqual(sum('LARGE_B_DETAIL_'+str(i)+'\n' in text for text in texts),1)
        for marker in ['SHORT_A_DETAIL_0','SHORT_C_DETAIL_0']:self.assertEqual(sum(marker in text for text in texts),1)
    def test_event_and_its_full_width_note_stay_together_on_continuations(self):
        page=train('PAIRED',0);rows=[page[1][1][0]];spans=[]
        for i in range(70):
            rows.append([f'PAIR_{i}_EVENT','DB-InfraGo','CCC','09:00','09:01','0:01'])
            rows.append([f'PAIR_{i}_NOTE','','','','','']);spans.append(len(rows)-1)
        page[1]=('Details',rows,.12,None,spans);pdf=render([page]);texts=[p.extract_text() for p in pdf.pages]
        self.assertGreater(len(pdf.pages),2)
        for i in range(70):
            event=[n for n,text in enumerate(texts) if f'PAIR_{i}_EVENT' in text];note=[n for n,text in enumerate(texts) if f'PAIR_{i}_NOTE' in text]
            self.assertEqual(len(event),1);self.assertEqual(event,note)
    def test_many_trains_have_no_split_details_or_blank_pages(self):
        pdf=render([train('TRAIN_'+str(i)) for i in range(25)]);self.assertLess(len(pdf.pages),26)
        for page in pdf.pages:self.assertTrue(page.extract_text().strip())
        for i in range(25):
            marker='TRAIN_'+str(i)+'_DETAIL_0';self.assertEqual(sum(marker in p.extract_text() for p in pdf.pages),1)
