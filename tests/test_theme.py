import unittest
from ivt import theme

class ThemeTests(unittest.TestCase):
    def test_text_contrast_at_least_aa(self):
        for foreground,background in theme.TEXT_PAIRS:
            self.assertGreaterEqual(theme.contrast(foreground,background),4.5,(foreground,background))
    def test_status_dots_visible(self):
        for label,color in theme.STATES.values():
            self.assertGreaterEqual(theme.contrast(color,theme.SURFACE),3.0,label)
    def test_contrast_formula(self):
        self.assertAlmostEqual(theme.contrast('#ffffff','#000000'),21.0,places=3)
        self.assertAlmostEqual(theme.contrast('#777777','#ffffff'),4.48,places=2)
    def test_widget_states_mapped(self):
        import tkinter as tk
        from tkinter import ttk
        root=tk.Tk();root.withdraw()
        try:
            style=ttk.Style(root);theme.apply(root,style)
            pairs=[]
            for name in ('TButton','Primary.TButton'):
                states=[' '.join(map(str,entry[:-1])) for entry in style.map(name,'background')]
                for required in ('disabled','pressed','active'):self.assertTrue(any(required in s for s in states),(name,required))
                for state in ('disabled','pressed','active','!disabled'):
                    pairs.append((style.lookup(name,'foreground',[state]),style.lookup(name,'background',[state])))
            pairs.append((style.lookup('TCombobox','foreground',['readonly']),style.lookup('TCombobox','fieldbackground',['readonly'])))
            pairs.append((style.lookup('TCombobox','selectforeground',['readonly']),style.lookup('TCombobox','selectbackground',['readonly'])))
            pairs.append((style.lookup('TCombobox','foreground',['disabled']),style.lookup('TCombobox','fieldbackground',['disabled'])))
            pairs.append((style.lookup('TCheckbutton','foreground',['active']),style.lookup('TCheckbutton','background',['active'])))
            pairs.append((style.lookup('TCheckbutton','foreground',['disabled']),style.lookup('TCheckbutton','background',['disabled'])))
            pairs.append((style.lookup('TEntry','foreground',['disabled']),style.lookup('TEntry','fieldbackground',['disabled'])))
            for tab_state in (['selected'],['active'],['!selected']):
                pairs.append((style.lookup('TNotebook.Tab','foreground',tab_state),style.lookup('TNotebook.Tab','background',tab_state)))
            pairs.append((root.option_get('foreground','TCombobox.Listbox') or theme.TEXT,theme.FIELD))
            for foreground,background in pairs:
                self.assertTrue(foreground and background,(foreground,background))
                self.assertGreaterEqual(theme.contrast(hexify(root,foreground),hexify(root,background)),4.5,(foreground,background))
        finally:
            root.destroy()

def hexify(root,color):
    r,g,b=root.winfo_rgb(color)
    return '#%02x%02x%02x'%(r//257,g//257,b//257)

if __name__=='__main__':unittest.main()
