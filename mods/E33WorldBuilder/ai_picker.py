"""Windows file picker runs off the SDK polling thread; it never accesses Unreal."""
def choose_json(directory):
    import ctypes as c
    from ctypes import wintypes as w
    class OPENFILENAME(c.Structure):
        _fields_=[('lStructSize',w.DWORD),('hwndOwner',w.HWND),('hInstance',w.HINSTANCE),
            ('lpstrFilter',w.LPCWSTR),('lpstrCustomFilter',w.LPWSTR),('nMaxCustFilter',w.DWORD),
            ('nFilterIndex',w.DWORD),('lpstrFile',w.LPWSTR),('nMaxFile',w.DWORD),
            ('lpstrFileTitle',w.LPWSTR),('nMaxFileTitle',w.DWORD),('lpstrInitialDir',w.LPCWSTR),
            ('lpstrTitle',w.LPCWSTR),('Flags',w.DWORD),('nFileOffset',w.WORD),('nFileExtension',w.WORD),
            ('lpstrDefExt',w.LPCWSTR),('lCustData',c.c_ssize_t),('lpfnHook',c.c_void_p),
            ('lpTemplateName',w.LPCWSTR),('pvReserved',c.c_void_p),('dwReserved',w.DWORD),('FlagsEx',w.DWORD)]
    buffer=c.create_unicode_buffer(32768);dialog=OPENFILENAME()
    dialog.lStructSize=c.sizeof(dialog);dialog.lpstrFile=c.cast(buffer,w.LPWSTR);dialog.nMaxFile=len(buffer)
    dialog.lpstrFilter='JSON scene\0*.json\0\0';dialog.lpstrTitle='Import AI Scene'
    dialog.lpstrInitialDir=directory;dialog.Flags=0x80000|0x1000|0x800|0x8 # Explorer, existing file/path, no CWD change
    api=c.WinDLL('comdlg32',use_last_error=True);api.GetOpenFileNameW.argtypes=[c.POINTER(OPENFILENAME)];api.GetOpenFileNameW.restype=w.BOOL
    if api.GetOpenFileNameW(c.byref(dialog)):return buffer.value
    error=api.CommDlgExtendedError()
    if error:raise OSError(f'File picker failed ({error})')
    return None
