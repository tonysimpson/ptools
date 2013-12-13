from ptools import OperationException
# CTYPES RULEZ!
import ctypes
from ctypes.wintypes import (HANDLE, DWORD, BOOL, WCHAR, POINTER,
                                             USHORT, WCHAR, BYTE, byref)

K32DLL = ctypes.windll.kernel32
NTDLL = ctypes.windll.ntdll

def is_wow64():
    wow64 = BOOL()
    K32DLL.IsWow64Process(K32DLL.GetCurrentProcess(), byref(wow64))
    return True if wow64.value else False

# HACK: I haven't figure wow64 out yet
if is_wow64() and False:
    PTR = ctypes.c_uint64
    NtReadVirtualMemory = NTDLL.NtWow64ReadVirtualMemory64
    NtQueryInformationProcess = NTDLL.NtWow64QueryInformationProcess64
else:
    PTR = ctypes.c_void_p
    NtReadVirtualMemory = NTDLL.NtReadVirtualMemory
    NtQueryInformationProcess = NTDLL.NtQueryInformationProcess


STATUS_SUCCESS = 0x0
PROCESS_TERMINATE = 0x0001
PROCESS_VM_READ  = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000

class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('Reserved1', PTR),
        ('PebBaseAddress', PTR),
        ('Reserved2', PTR*2),
        ('UniqueProcessId', PTR),
        ('Reserved3', PTR)
    ]

class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ('Length', USHORT),
        ('MaximumLength', USHORT),
        ('Buffer', PTR)
    ]

class WindowsOperationException(OperationException):
    def __init__(self, message):
        last_error_mesage = " Last Kernel32 Error: '%s'" % (
                                              get_last_error_message(),)
        OperationException.__init__(self, message +
        last_error_mesage)


def get_last_error_message():
    """Decodes the last error number to its string message

    """
    BUF_LEN = 1 * 1024 # 1k
    error_id = K32DLL.GetLastError()
    message_buf = (WCHAR * BUF_LEN)() # create a c_char array
    K32DLL.FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM, 0, error_id, 0,
                                             message_buf, BUF_LEN, None)
    return message_buf.value.strip()


def read_wchar_string_from_process_vm(handle, address):
    env_wchar = WCHAR()
    chars = []
    while True:
        status = NtReadVirtualMemory(handle,address, byref(env_wchar),
                                         ctypes.sizeof(env_wchar), None)
        if status != STATUS_SUCCESS:
            raise WindowsOperationException('Failed while reading wchar'
                                  ' string from process virtual memory')
        address += ctypes.sizeof(env_wchar)
        if env_wchar.value == u'\x00':
            return address, u''.join(chars)
        chars.append(env_wchar.value)


def read_pointer_from_process_vm(handle, address):
    pointer = PTR()
    num_bytes = ctypes.c_uint32()
    status = NtReadVirtualMemory(handle, address, byref(pointer), ctypes.sizeof(pointer), byref(num_bytes))
    if status != STATUS_SUCCESS:
        raise WindowsOperationException('Could not read process virtual'
                                             ' memory to find pointer.')
    return pointer.value


def read_unicode_string_from_process_vm(handle, address):
    unicode_str_struct = UNICODE_STRING()
    status = NtReadVirtualMemory(handle, address,
                                              byref(unicode_str_struct),
                                ctypes.sizeof(unicode_str_struct), None)
    if status != STATUS_SUCCESS:
        raise WindowsOperationException('Could not read process virtual'
                             ' memory to get unicode string structure.')
    num_char = unicode_str_struct.Length / ctypes.sizeof(WCHAR)
    string = (WCHAR * num_char)()
    address = unicode_str_struct.Buffer
    status = NtReadVirtualMemory(handle, address, byref(string),
                                            ctypes.sizeof(string), None)
    if status != STATUS_SUCCESS:
        raise WindowsOperationException('Could not read process virtual'
                                  ' memory to get unicode string data.')
    return string.value


def read_environ_from_process_vm(handle, address):
    current_address = address
    env = {}
    while True:
        current_address, entry = read_wchar_string_from_process_vm(
                                                handle, current_address)
        if len(entry) == 0:
            break
        name, value = entry.split('=',1)
        env[name] = value
    return env


def get_pid_info(pid):
    """Get a processes command line and environment.

    :raises: ProcessOperationException on error
    :rtype: str command line, dict of environ (str name, str value)
    """
    # open the process so we can read its memory
    K32DLL.OpenProcess.restype = HANDLE
    handle = K32DLL.OpenProcess(PROCESS_QUERY_INFORMATION |
                               PROCESS_VM_READ, BOOL(False), DWORD(pid))
    if not handle:
        raise WindowsOperationException("Could not open process [%d] "
                                    "with memory read access." % (pid,))
    try:
        process_basic_info = PROCESS_BASIC_INFORMATION()
        status = NtQueryInformationProcess(handle, 0,
           byref(process_basic_info), ctypes.sizeof(process_basic_info),
                                                                   None)
        if status != STATUS_SUCCESS:
            raise WindowsOperationException('Could not get process '
                                                           'basic info')
        user_process_parameter_address = read_pointer_from_process_vm(handle, process_basic_info.PebBaseAddress + (4 * ctypes.sizeof(PTR)))
        environ_address = read_pointer_from_process_vm(
                          handle, user_process_parameter_address + 16 + (14 * ctypes.sizeof(PTR)))
        cmd_line = read_unicode_string_from_process_vm(handle,
                                  user_process_parameter_address + 16 + (12 * ctypes.sizeof(PTR)))
        env = read_environ_from_process_vm(handle, environ_address)
        return (cmd_line, env)
    except TypeError as exc:
        raise OperationException(exc.message)
    finally:
        K32DLL.CloseHandle(handle)


def list_pids():
    try:
        EnumProcesses = ctypes.windll.psapi.EnumProcesses
    except AttributeError:
        EnumProcesses = K32DLL.EnumProcesses
    used = DWORD()
    block_size = 8192
    ten_megs = 10*1024*1024
    cur_size = block_size
    while True:
        processes = (DWORD*cur_size)()
        status = EnumProcesses(processes, ctypes.sizeof(processes),
                                                            byref(used))
        if not status:
            raise WindowsOperationException('Could not enumerate proces'
                                                                  'ses')
        if used.value != cur_size:
            return processes[:used.value/ctypes.sizeof(DWORD)]
        cur_size += block_size
        if cur_size > ten_megs:
            raise WindowsOperationException('Unreasonable number of pro'
                                                              'cesses?')

def kill_pid(pid):
    K32DLL.OpenProcess.restype = HANDLE
    handle = K32DLL.OpenProcess(PROCESS_TERMINATE, BOOL(False),
                                                             DWORD(pid))
    try:
        exit_status = ctypes.c_int32()
        K32DLL.TerminateProcess(handle, byref(exit_status))
    finally:
        K32DLL.CloseHandle(handle)

__all__ = ['list_pids', 'get_pid_info', 'kill_pid', 'OperationException']
