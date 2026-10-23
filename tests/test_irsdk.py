import ctypes
import unittest
import uuid
from ctypes import wintypes
from unittest.mock import patch
from ivt import irsdk
from ivt.irsdk import IRacingSDK, make_long, session_names

kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
kernel32.CreateFileMappingW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.LPCWSTR]
kernel32.CreateFileMappingW.restype=wintypes.HANDLE
INVALID_HANDLE=wintypes.HANDLE(-1).value

class SdkTests(unittest.TestCase):
    def mapping(self,status,yaml=b''):
        # A private mapping with a unique name; never the real iRacing name.
        name='Local\\IVT-test-'+uuid.uuid4().hex
        handle=kernel32.CreateFileMappingW(INVALID_HANDLE,None,0x04,0,4096,name)
        self.assertTrue(handle);self.addCleanup(irsdk.kernel32.CloseHandle,handle)
        view=irsdk.kernel32.MapViewOfFile(handle,0x0002,0,0,4096)
        ctypes.c_int.from_address(view+4).value=status
        if yaml:
            ctypes.c_int.from_address(view+16).value=len(yaml)+16
            ctypes.c_int.from_address(view+20).value=112
            ctypes.memmove(view+112,yaml,len(yaml))
        irsdk.kernel32.UnmapViewOfFile(view)
        return name
    def test_session_names(self):
        yaml=('---\nWeekendInfo:\n TrackName: spa 2024 up\n TrackDisplayName: Circuit de Spa-Francorchamps\n'
              ' TrackDisplayShortName: Spa\nDriverInfo:\n Drivers:\n - CarIdx: 0\n   UserName: Pace Car\n   TeamName: Pace Car\n'
              ' - CarIdx: 1\n   UserName: Igor Wójcik\n   TeamName: Igor Wójcik\n - CarIdx: 2\n   UserName: Lars Eriksson\n'
              '   TeamName: Team Nordic\n...\n').encode('cp1252')
        with patch('ivt.irsdk.MEMMAP_NAME',self.mapping(1,yaml)):
            self.assertEqual(IRacingSDK().session_names(),['Circuit de Spa-Francorchamps','Spa','Igor Wójcik','Lars Eriksson','Team Nordic'])
        with patch('ivt.irsdk.MEMMAP_NAME',self.mapping(0,yaml)):
            self.assertEqual(IRacingSDK().session_names(),[])
        self.assertEqual(session_names(''),[])
        live=('WeekendInfo:\n TrackDisplayName: Nordschleife\nDriverInfo:\n DriverCarIdx: 1\n Drivers:\n'
              ' - CarIdx: 0\n   UserName: Todd Murphy2\n   TeamName: Todd Murphy2\n'
              ' - CarIdx: 1\n   UserName: Igor P Wojtkowiak\n   TeamName: Igor P Wojtkowiak\n'
              ' - CarIdx: 12\n   UserName: Daniel White15\n - CarIdx: 13\n   UserName: ?? King\n - CarIdx: 14\n   UserName: ??\n')
        self.assertEqual(session_names(live),['Nordschleife','Todd Murphy','Daniel White','King'])
    def test_connected_bit(self):
        for status,expected in [(1,True),(3,True),(0,False),(2,False)]:
            with patch('ivt.irsdk.MEMMAP_NAME',self.mapping(status)):
                self.assertIs(IRacingSDK().connected(),expected)
    def test_missing_mapping(self):
        with patch('ivt.irsdk.MEMMAP_NAME','Local\\IVT-missing-'+uuid.uuid4().hex):
            self.assertFalse(IRacingSDK().connected())
    def test_chat_broadcast_parameters(self):
        sent=[]
        with patch.object(irsdk.user32,'RegisterWindowMessageW',return_value=49999),\
             patch.object(irsdk.user32,'SendNotifyMessageW',side_effect=lambda *a:sent.append(a) or 1):
            sdk=IRacingSDK();sdk.cancel_chat();sdk.begin_chat()
        self.assertEqual(sent,[(0xFFFF,49999,make_long(8,3),0),(0xFFFF,49999,make_long(8,1),0)])
        self.assertEqual(make_long(8,1),0x00010008)

if __name__=='__main__':unittest.main()
