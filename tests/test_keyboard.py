import ctypes
import unittest
from unittest.mock import patch
from ivt import keyboard
from ivt.keyboard import normalize_ascii, split_message, stroke, press, INPUT, KEYEVENTF_SCANCODE, KEYEVENTF_KEYUP, KEYEVENTF_EXTENDEDKEY

class TextTests(unittest.TestCase):
    def test_normalize(self):
        cases={'\u2019':"'",'\u201cquoted\u201d':'"quoted"','a \u2014 b':'a - b','wait\u2026':'wait...',
            'Łódź, żółć, ą ę ś':'Lodz, zolc, a e s','tab\there\nnew':'tab here new','emoji \U0001F600 gone':'emoji gone',
            'non\u00a0breaking':'non breaking'}
        for source,expected in cases.items():self.assertEqual(normalize_ascii(source),expected)
        self.assertTrue(all(' '<=c<='~' for c in normalize_ascii('Zażółć gęślą jaźń \u20ac \u00e9\u00e8')))
    def test_split_prefers_sentences(self):
        self.assertEqual(split_message('One two. Three four.',100),['One two. Three four.'])
        self.assertEqual(split_message('First sentence here. Second one. Third.',22),['First sentence here.','Second one. Third.'])
    def test_split_long_sentence_at_words(self):
        parts=split_message('alpha beta gamma delta epsilon zeta',12)
        self.assertTrue(all(len(p)<=12 for p in parts));self.assertEqual(' '.join(parts),'alpha beta gamma delta epsilon zeta')
        self.assertLessEqual(len(parts),3)
    def test_split_limit(self):
        with self.assertRaises(ValueError):split_message('x '*50,10)

class ScanCodeTests(unittest.TestCase):
    def setUp(self):self.hkl=keyboard.user32.GetKeyboardLayout(0)
    def test_input_struct_size(self):self.assertEqual(ctypes.sizeof(INPUT),40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)
    def test_letters_digits_shift(self):
        self.assertEqual(stroke('a',self.hkl),((),0x1E))
        self.assertEqual(stroke('A',self.hkl),((0x2A,),0x1E))
        self.assertEqual(stroke('1',self.hkl),((),0x02))
        self.assertEqual(stroke(' ',self.hkl),((),0x39))
        self.assertEqual(stroke('!',self.hkl),((0x2A,),0x02))
    def test_all_printable_ascii_mappable(self):
        for code in range(0x20,0x7f):stroke(chr(code),self.hkl)
    def test_unmappable(self):
        with self.assertRaises(ValueError):stroke('\u2603',self.hkl)
    def test_press_events(self):
        sent=[]
        with patch('ivt.keyboard.send',side_effect=sent.extend):press(((0x2A,),0x1E))
        flags=[(e.u.ki.wScan,e.u.ki.dwFlags,e.u.ki.wVk) for e in sent]
        S,U=KEYEVENTF_SCANCODE,KEYEVENTF_KEYUP
        self.assertEqual(flags,[(0x2A,S,0),(0x1E,S,0),(0x1E,S|U,0),(0x2A,S|U,0)])
    def test_extended_key(self):
        sent=[]
        with patch('ivt.keyboard.send',side_effect=sent.extend):press(((),0x11C))
        self.assertEqual((sent[0].u.ki.wScan,sent[0].u.ki.dwFlags),(0x1C,KEYEVENTF_SCANCODE|KEYEVENTF_EXTENDEDKEY))

if __name__=='__main__':unittest.main()
