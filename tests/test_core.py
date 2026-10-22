import threading
import tempfile
import unittest
from pathlib import Path
import numpy as np
from ivt.config import Config
from ivt.chat import Sender, Cancelled, clean_message
from ivt.audio import usable, RATE

class FakeChat:
    """Stateful chat field: T opens, characters append, Enter submits."""
    def __init__(self):
        self.focus=1;self.open=False;self.buffer='';self.messages=[];self.events=[];self.lose_after=None
    def target(self):return self.focus
    def closed(self):return not self.open
    def opened(self):return self.open
    def key(self,key):
        self.events.append(key)
        if key=='t':self.open=True
        elif key=='enter':
            if not self.open:raise AssertionError('Enter outside chat')
            self.messages.append(self.buffer);self.buffer='';self.open=False
    def character(self,char):
        if not self.open:raise AssertionError('Typing outside chat')
        self.buffer+=char
        if self.lose_after and len(self.buffer)>=self.lose_after:self.focus=None

class Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config(open_delay=0,send_delay=0)
        self.chat=FakeChat();self.sender=Sender(self.chat,self.cfg);self.cancel=threading.Event()
    def test_sequence(self):
        self.sender.send('one','Sorry, my mistake.',self.cancel)
        self.assertEqual(self.chat.messages,['Sorry, my mistake.'])
        self.assertEqual(self.chat.events,['t','enter'])
    def test_duplicate(self):
        self.sender.send('one','Hello',self.cancel)
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(len(self.chat.messages),1)
    def test_focus_absent(self):
        self.chat.focus=None
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_focus_lost_mid_text(self):
        self.chat.lose_after=3
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.buffer,'Hel');self.assertFalse(self.chat.messages)
    def test_cancel(self):
        self.cancel.set()
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_chat_already_open(self):
        self.chat.open=True
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_unconfirmed_open(self):
        self.chat.opened=lambda:False
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.events,['t']);self.assertFalse(self.chat.buffer)
    def test_empty(self):
        with self.assertRaises(ValueError):self.sender.send('one','  \n ',self.cancel)
        self.assertFalse(self.chat.events)
    def test_commands(self):
        for text in ['/12 hello','#clear','!yellow','@mute','$']:
            with self.assertRaises(ValueError):clean_message(text,180)
    def test_length(self):
        with self.assertRaises(ValueError):clean_message('a'*181,180)
    def test_silence(self):self.assertFalse(usable(np.zeros(RATE,dtype=np.float32),0.008))
    def test_short_noise(self):self.assertFalse(usable(np.ones(100,dtype=np.float32),0.008))
    def test_signal(self):self.assertTrue(usable(np.ones(RATE,dtype=np.float32)*0.1,0.008))
    def test_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=Config(button=4,joystick='test-device',mode='toggle')
            cfg.save(Path(folder));self.assertEqual(Config.load(Path(folder)),cfg)
    def test_damaged_settings_give_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            (folder/'settings.json').write_bytes(b'\xff\xfe broken')
            with self.assertLogs('ivt.config','WARNING'):self.assertEqual(Config.load(folder),Config())
            for payload in ['{"model": "small",','[1,2]','{"gain": NaN']:
                (folder/'settings.json').write_text(payload,encoding='utf-8')
                with self.assertLogs('ivt.config','WARNING'):self.assertEqual(Config.load(folder),Config())
                self.assertTrue((folder/'settings.json.bad').exists());self.assertIsNotNone(Config.load_problem)
    def test_invalid_field_types_fall_back_per_field(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            (folder/'settings.json').write_text('{"model":"small","gain":"loud","button":true,"auto_send":1,"unknown":5}',encoding='utf-8')
            with self.assertLogs('ivt.config','WARNING'):cfg=Config.load(folder)
            self.assertEqual((cfg.model,cfg.gain,cfg.button,cfg.auto_send),('small',1.0,-1,False))

if __name__=='__main__':unittest.main()
