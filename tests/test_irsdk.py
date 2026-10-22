import ctypes
import unittest
import uuid
from ctypes import wintypes
from unittest.mock import patch
from ivt import irsdk
from ivt.irsdk import IRacingSDK, make_long

kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
kernel32.CreateFileMappingW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.LPCWSTR]
kernel32.CreateFileMappingW.restype=wintypes.HANDLE
INVALID_HANDLE=wintypes.HANDLE(-1).value

class SdkTests(unittest.TestCase):
    def mapping(self,status):
        # A private mapping with a unique name; never the real iRacing name.
        name='Local\\IVT-test-'+uuid.uuid4().hex
        handle=kernel32.CreateFileMappingW(INVALID_HANDLE,None,0x04,0,64,name)
        self.assertTrue(handle);self.addCleanup(irsdk.kernel32.CloseHandle,handle)
        view=irsdk.kernel32.MapViewOfFile(handle,0x0002,0,0,8)
        ctypes.c_int.from_address(view+4).value=status
        irsdk.kernel32.UnmapViewOfFile(view)
        return name
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
