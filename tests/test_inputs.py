import unittest
from types import SimpleNamespace
from ivt.app import App

class InputTests(unittest.TestCase):
    def make(self,mode='ptt'):
        state=SimpleNamespace(config=SimpleNamespace(mode=mode),recording=False,input_sources=set(),calls=[])
        def start():state.calls.append('start');state.recording=True
        def stop():state.calls.append('stop');state.recording=False
        state.start=start;state.stop=stop
        return state
    def test_press_release(self):
        state=self.make()
        App.edge(state,'wheel',True);App.edge(state,'wheel',False)
        self.assertEqual(state.calls,['start','stop'])
    def test_repeat_ignored(self):
        state=self.make()
        App.edge(state,'keyboard',True);App.edge(state,'keyboard',True);App.edge(state,'keyboard',False)
        self.assertEqual(state.calls,['start','stop'])
    def test_toggle(self):
        state=self.make('toggle')
        App.edge(state,'wheel',True);App.edge(state,'wheel',False)
        self.assertTrue(state.recording)
        App.edge(state,'wheel',True);App.edge(state,'wheel',False)
        self.assertEqual(state.calls,['start','stop'])
    def test_overlap(self):
        state=self.make()
        App.edge(state,'wheel',True);App.edge(state,'keyboard',True)
        App.edge(state,'wheel',False);self.assertTrue(state.recording)
        App.edge(state,'keyboard',False)
        self.assertEqual(state.calls,['start','stop'])

if __name__=='__main__':unittest.main()
