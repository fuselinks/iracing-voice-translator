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

class DeviceRemovalTests(unittest.TestCase):
    WHEEL='03005349d0160000600d000000000000'
    def make(self,recording=True,sources=('wheel',)):
        state=SimpleNamespace(config=SimpleNamespace(joystick=self.WHEEL),joysticks={1:'wheel',2:'pedals'},
                              joystick_guids={1:self.WHEEL,2:'0300358cb73000000310000000000000'},
                              recording=recording,input_sources=set(sources),aborted=0)
        def abort():state.aborted+=1;state.recording=False
        state.abort=abort
        return state
    def test_other_controller_does_not_interrupt(self):
        state=self.make()
        self.assertFalse(App.device_removed(state,2))
        self.assertTrue(state.recording);self.assertEqual(state.aborted,0);self.assertEqual(state.input_sources,{'wheel'})
        self.assertNotIn(2,state.joysticks)
    def test_assigned_controller_cancels_recording(self):
        state=self.make()
        self.assertTrue(App.device_removed(state,1))
        self.assertEqual(state.aborted,1);self.assertFalse(state.input_sources)
    def test_keyboard_recording_survives_wheel_unplug(self):
        state=self.make(sources=('keyboard',))
        self.assertFalse(App.device_removed(state,1))
        self.assertTrue(state.recording);self.assertEqual(state.input_sources,{'keyboard'})
    def test_unknown_instance(self):
        self.assertFalse(App.device_removed(self.make(),99))

if __name__=='__main__':unittest.main()
