import threading
import tempfile
import unittest
from pathlib import Path
import numpy as np
from ivt.config import Config
from ivt.chat import Sender, Cancelled, clean_message
from ivt.audio import usable, RATE

class FakeChat:
    """Stateful iRacing chat: SDK BeginChat opens, SDK Cancel clears and closes, Enter submits."""
    def __init__(self):
        self.focus=1;self.connected=True;self.problem='';self.open=False;self.buffer='';self.messages=[];self.events=[];self.lose_after=None
    def target(self):return self.focus
    def sdk_connected(self):return self.connected
    def prepare(self,text,window):return list(text)
    def input_problem(self,window):return self.problem
    def begin_chat(self):self.events.append('begin');self.open=True
    def cancel_chat(self):self.events.append('cancel');self.open=False;self.buffer=''
    def enter(self):
        self.events.append('enter')
        if not self.open:raise AssertionError('Enter outside chat')
        self.messages.append(self.buffer);self.buffer='';self.open=False
    def character(self,char):
        if not self.open:raise AssertionError('Typing outside chat')
        self.buffer+=char
        if self.lose_after and len(self.buffer)>=self.lose_after:self.focus=None

class Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config(open_delay=0,send_delay=0,char_delay=0)
        self.chat=FakeChat();self.sender=Sender(self.chat,self.cfg);self.cancel=threading.Event()
    def test_sequence(self):
        self.sender.send('one','Sorry, my mistake.',self.cancel)
        self.assertEqual(self.chat.messages,['Sorry, my mistake.'])
        self.assertEqual(self.chat.events,['cancel','begin','enter'])
    def test_duplicate(self):
        self.sender.send('one','Hello',self.cancel)
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(len(self.chat.messages),1)
    def test_focus_absent(self):
        self.chat.focus=None
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_sdk_not_connected(self):
        self.chat.connected=False
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_focus_lost_mid_text_cancels_field(self):
        self.chat.lose_after=3
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.events,['cancel','begin','cancel'])
        self.assertFalse(self.chat.open);self.assertEqual(self.chat.buffer,'');self.assertFalse(self.chat.messages)
    def test_cancel_during_typing_cancels_field(self):
        original=self.chat.character
        def typed(char):
            original(char)
            if len(self.chat.buffer)==2:self.cancel.set()
        self.chat.character=typed
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.events[-1],'cancel');self.assertFalse(self.chat.open)
    def test_transport_error_cancels_field(self):
        def broken(char):raise OSError('SendInput failed')
        self.chat.character=broken
        with self.assertRaises(OSError):self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.events,['cancel','begin','cancel'])
    def test_elevated_game_blocks_before_chat(self):
        self.chat.problem='iRacing działa jako administrator'
        with self.assertRaisesRegex(Cancelled,'administrator'):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_cancel_before_start(self):
        self.cancel.set()
        with self.assertRaises(Cancelled):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
    def test_leftover_text_cleared_first(self):
        self.chat.open=True;self.chat.buffer='half typed'
        self.sender.send('one','Hello',self.cancel)
        self.assertEqual(self.chat.messages,['Hello'])
    def test_empty(self):
        with self.assertRaises(ValueError):self.sender.send('one','  \n ',self.cancel)
        self.assertFalse(self.chat.events)
    def test_commands(self):
        for text in ['/12 hello','#clear','!yellow','@mute','$']:
            with self.assertRaises(ValueError):clean_message(text,180)
        with self.assertRaises(ValueError):clean_message('Hello there. /kick me',12)
    def test_long_message_split_and_sent_in_parts(self):
        text='Sorry about that. I did not see you on the inside. My mistake, I will wait for you.'
        self.cfg.max_chars=40
        self.sender.send('one',text,self.cancel)
        self.assertEqual(self.chat.messages,['Sorry about that.','I did not see you on the inside.','My mistake, I will wait for you.'])
        self.assertEqual(self.chat.events,['cancel','begin','enter']*3)
    def test_too_long_even_after_split(self):
        with self.assertRaises(ValueError):clean_message('word '*200,180)
    def test_unicode_normalized_before_typing(self):
        self.sender.send('one','„Mój błąd” — sorry… it’s ok',self.cancel)
        self.assertEqual(self.chat.messages,['"Moj blad" - sorry... it\'s ok'])
    def test_unmappable_character_rejected_before_chat_opens(self):
        def prepare(text,window):raise ValueError('not in layout')
        self.chat.prepare=prepare
        with self.assertRaises(ValueError):self.sender.send('one','Hello',self.cancel)
        self.assertFalse(self.chat.events)
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
