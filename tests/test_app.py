import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import tkinter as tk
from ivt.config import Config
from ivt.app import App

class FakeJoystick:
    def __init__(self,instance,name,guid,buttons):self.instance,self.name,self.guid,self.buttons=instance,name,guid,buttons
    def get_instance_id(self):return self.instance
    def get_name(self):return self.name
    def get_guid(self):return self.guid
    def get_numbuttons(self):return self.buttons

WHEEL=FakeJoystick(7,'Simucube 2 Pro','03005349d0160000600d000000000000',128)
SHIFTER=FakeJoystick(8,'DS-8X Shifter','03007e21830400003105000000000000',11)

class AppTests(unittest.TestCase):
    """Real Tk window with fake controllers; settings and autostart are never written."""
    def setUp(self):
        patches=[patch.object(Config,'load',classmethod(lambda cls,folder=None:cls())),patch.object(Config,'save'),
                 patch('ivt.app.autostart.enabled',return_value=False),patch('ivt.app.autostart.set_enabled')]
        self.mocks=[p.start() for p in patches]
        for p in patches:self.addCleanup(p.stop)
        Config.load_problem=None
        self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root)
        self.addCleanup(self.app.quit)
        self.app.joysticks={7:WHEEL,8:SHIFTER};self.app.joystick_guids={7:WHEEL.guid,8:SHIFTER.guid}
        self.app.pygame=SimpleNamespace(joystick=SimpleNamespace(get_count=lambda:0),event=SimpleNamespace(get=lambda:[]),quit=lambda:None)
        self.app.refresh_wheels()
    def press(self,joy,button,down):
        self.app.joystick_button(SimpleNamespace(instance_id=joy.instance,button=button),down)
    def test_bind_only_selected_device(self):
        self.app.devices.current(0)  # Simucube
        self.app.bind_wheel()
        self.press(SHIFTER,2,True)
        self.assertTrue(self.app.binding);self.assertEqual(self.app.config.joystick,'')
        self.press(WHEEL,11,True)
        self.assertFalse(self.app.binding)
        self.assertEqual((self.app.config.joystick,self.app.config.button),(WHEEL.guid,11))
        self.assertIn('Simucube 2 Pro, przycisk 12',self.app.wheel_label.get())
    def test_ptt_from_assigned_button_only(self):
        self.app.config.joystick,self.app.config.button=WHEEL.guid,11
        self.app.start=Mock();self.app.stop=Mock()
        self.press(SHIFTER,11,True);self.press(WHEEL,3,True);self.app.start.assert_not_called()
        self.press(WHEEL,11,True);self.app.start.assert_called_once()
        self.press(WHEEL,11,False);self.app.stop.assert_called_once()
    def test_live_button_preview(self):
        self.app.live_buttons.set(True)
        self.press(SHIFTER,4,True);self.press(SHIFTER,4,False)
        lines=self.app.buttons_text.get().splitlines()
        self.assertEqual(len(lines),2);self.assertIn('puszczony',lines[0]);self.assertIn('DS-8X Shifter · przycisk 5 (indeks 4)',lines[1])
        self.assertIn(SHIFTER.guid,lines[1])
    def test_invalid_number_rejected(self):
        self.app.numbers['char_delay'].set('500')
        self.assertFalse(self.app.save());self.assertEqual(self.app.state,'error')
        self.app.numbers['char_delay'].set('abc')
        self.assertFalse(self.app.save())
    def test_save_converts_units_and_vocabulary(self):
        self.app.numbers['char_delay'].set('15');self.app.numbers['open_delay'].set('400')
        self.app.vocabulary.set(' Eau Rouge,, Raidillon ,')
        self.app.vars['hotkey'].set('f17');self.app.autostart.set(True)
        self.assertTrue(self.app.save())
        self.assertAlmostEqual(self.app.config.char_delay,0.015);self.assertAlmostEqual(self.app.config.open_delay,0.4)
        self.assertEqual(self.app.config.vocabulary,'Eau Rouge, Raidillon');self.assertEqual(self.app.config.hotkey,'f17')
        self.mocks[3].assert_called_once_with(True)
        self.assertIs(self.app.sender.config,self.app.config)
    def test_hotkey_edges(self):
        self.app.config.hotkey='f13';self.app.start=Mock();self.app.stop=Mock()
        self.app.events.put(('key',('f13',True)));self.app.events.put(('key',('f13',False)))
        self.app.tick()
        self.app.start.assert_called_once();self.app.stop.assert_called_once()

if __name__=='__main__':unittest.main()
