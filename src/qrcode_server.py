#!/usr/bin/env python
###############################################################################
#
#  ConQR Web Server. Should work on any OS with Python
#
#  Written by: Dave Kennedy (ReL1K)
#  Website: https://www.trustedsec.com
#
#  Forked & Modified by: Jim Gilsinn (@JimGilsinn)
#  Website: http://www.jimgilsinn.com
#
################################################################################

import subprocess
import sys
import socket
import os
import BaseHTTPServer,SimpleHTTPServer,cgi
from SocketServer import BaseServer
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from email.MIMEText import MIMEText
import urlparse
import multiprocessing

# default files
con_file = "database/conference.txt"
reg_file = "database/registered.txt"
types_file = "database/types.txt"

# main dns class
class DNSQuery:
  def __init__(self, data):
    self.data=data
    self.dominio=''

    tipo = (ord(data[2]) >> 3) & 15   # Opcode bits
    if tipo == 0:                     # Standard query
      ini=12
      lon=ord(data[ini])
      while lon != 0:
        self.dominio+=data[ini+1:ini+lon+1]+'.'
        ini+=lon+1
        lon=ord(data[ini])

  def respuesta(self, ip):
    packet=''
    if self.dominio:
      packet+=self.data[:2] + "\x81\x80"
      packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
      packet+=self.data[12:]                                         # Original Domain Name Question
      packet+='\xc0\x0c'                                             # Pointer to domain name
      packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
      packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
    return packet

# grab the ipaddress 
ipaddr = raw_input("Enter the IP address to point machines to the QR Code Web Server: ")

# main dns routine
def dns(ipaddr):
  print "[*] Started DNS Server for ConQR.."
  print "[*] You NEED to configure your wireless AP or network to give DNS to THIS server"
  print "[*] This server will redirect all DNS requests when the QRCode is scanned to the server!"
  udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  udps.bind(('',53))

  try:
    while 1:
      data, addr = udps.recvfrom(1024)
      p=DNSQuery(data)
      udps.sendto(p.respuesta(ipaddr), addr)
      print 'Response: %s -> %s' % (p.dominio, ipaddr)
  except KeyboardInterrupt:
    print "Exiting the DNS Server.."
    udps.close()

# start dns with multiprocessing
p = multiprocessing.Process(target=dns, args=(ipaddr,))
p.start()

# Read the conference file and store the data in a set of lists. This is a major difference from the original conqr
# code. The reason is to allow the conqr code to send the ticket type and email along with the HTML response to the
# QR reader system. This allows the QR reader system to provide feedback to the attendant to provide the correct ticket
# to the attendee.
reg_list = []
email_list = []
ticket_list = []
def ReadConFile(file):
  if not os.path.isfile(file):
    print("File path {} does not exist. Exiting...".format(file))
    sys.exit()

  with open(file, 'r') as cf:
    cnt = 0
    for line in cf:
      field = line.split(',')
      reg_list.append(field[0])
      email_list.append(field[1])
      ticket_list.append(field[2])
      cnt += 1

# Read the badge types file and store the data in a list. This is a major difference from the original conqr code.
# The list allows the QR reader system to provide feedback to teh attendant to provide the correct ticket to the
# attendee.
types_name = []
types_type = []
types_description = []
types_number = []
types_day = []
types_color = []
def ReadTypesFiles(file)
  if not os.path.isfile(file):
    print("File path {} does not exist. Exiting...".format(file))
    sys.exit()
    
  with open(file, 'r') as tf:
    cnt = 0
    for line in tf:
      field = line.split(',')
      types_name.append(field[0])
      types_type.append(field[1])
      types_description.append(field[2])
      types_number.append(field[3])
      types_day.append(field[4])
      types_color.append(field[5])
      cnt += 1

# Handler for handling POST requests and general setup through SSL
class HTTPHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

  # handle basic GET requests
  def do_GET(self):
    # import proper style css files here
    parsed_path = urlparse.urlparse(self.path)

    counter = 0

    path = parsed_path.path
    query = parsed_path.query

    if path == "/qrcode":
      query = query.replace("q=", "")
      self.send_response(200)
      self.send_header('Content_type', 'text/html')
      self.end_headers()
      i = 0
      found = False
      for q in reg_list:
        if q == query:
          found = True
          break
        i += 1

      if found:
        # If the registration file does not exist, touch the file to create it.
        if not os.path.isfile(reg_file, 'r'):
          touchfile = file(reg_file, 'w')
          touchfile.write("")
          touchfile.close()

        # Look for the code in the existing list of codes to see if it's been already registered.
        reg = file(reg_file, 'r')
        reg_data = reg.read()
        if query in reg_data:
          # If the code already exists in the registration file, send back the duplicate response.
          self.wfile.write("<html><head><meta name=\"description\" content=\"duplicate\"></head>")
          self.wfile.write("<body bgcolor=\"#B22222\">User has already registered at the desk. Please check into this.</body></html>")
        else:
          # Code does not exist in the registration file, so append it to the end.
          reg_write = file(reg_file, 'a')
          reg_write.write(query)
          reg_write.close()
          
          # Check for the type of ticket that is being registered
          j = 0
          for q in types_name:
            if q == ticket_list[i]
              break
            j += 1

          # Then, send the correct response to the QR reader system with the correct information included.
          self.wfile.write("<html><head><meta name=\"description\" content=\"registered\">")
          self.wfile.write("<meta name=\"code\" content=\"" + query + "\">")
          self.wfile.write("<meta name=\"email\" content=\"" + email_list[i] + "\">")
          self.wfile.write("<meta name=\"type\" content=\"" + types_type[j] + "\">")
          self.wfile.write("<meta name=\"description\" content=\"" + types_description[j] + "\">")
          self.wfile.write("<meta name=\"number\" content=\"" + types_number[j] + "\">")
          self.wfile.write("<meta name=\"day\" content=\"" + types_day[j] + "\">")
          self.wfile.write("<meta name=\"color\" content\"" + types_color[j] + "\">")
          self.wfile.write("</head>")
          self.wfile.write("<body bgcolor=\"#66ff66\">User has been registered successfully. ")
          self.wfile.write("Refreshing in 10 seconds.<meta HTTP-EQUIV=\"REFRESH\" content=\"10; url=./\">")
          self.wfile.write("</body></html>")
      else:
        self.wfile.write("<html><head><meta name=\"description\" content=\"unknown\"></head>")
        self.wfile.write("<body bgcolor=\"#FFFF66\">[!] User was not found. Try manual methods. :-(</body></html>")

    # Display this message is someone hits the webserver itself from a browser
    if self.path == "/":
      self.send_response(200)
      self.send_header('Content_type', 'text/html')
      self.end_headers()
      self.wfile.write("""
<html><head><title>ConQR Central Registration Web Server</title></head>
<body onload="document.barcodeform.barcode.focus()">
<br />

<p style="text-align:center; font-weight:bold; font-size:larger;">Welcome to the ConQR QRCode and Ticketing Web System.</p>

<table border="0" style="border-spacing:3px; margin-left:auto; margin-right:auto;">
<tr><td><div style="font-style:italic">Written by:</div></td><td>David Kennedy</td></tr>
<tr><td><div style="font-style:italic">Website:</div></td><td><a href="https://www.trustedsec.com" target="_blank">https://www.trustedsec.com</a></td>
<tr><td><div style="font-style:italic">Twitter:</div></td><td><a href="https://twitter.com/HackingDave" target="_blank">HackingDave</a> and <a href="https://twitter.com/trustedsec" target="_blank">TrustedSec</a></td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td><div style="font-style:italic">Forked &amp; Modified by:</div></td><td>Jim Gilsinn</td></tr>
<tr><td><div style="font-style:italic">Website:</div></td><td><a href="http://www.jimgilsinn.com" target="_blank">http://www.jimgilsinn.com</a></td>
<tr><td><div style="font-style:italic">Twitter:</div></td><td><a href="https://twitter.com/JimGilsinn" target="_blank">JimGilsinn</a></td></tr>
</table>

<br />
<p style="text-align:left; font-weight:bold; font-size:larger;">Instructions:</p>
<p>Simply scan a QR code using the PiConReg system. The PiConReg system will display lights and a message on the screen 
according to whether they are already registered or not. If they are registered, the PiConReg system should also 
indicate what type of ticket they registered.</p>
</body></html>
""")

# this ultimately handles the http requests and stuff
def main(server_class=BaseHTTPServer.HTTPServer,handler_class=HTTPHandler):
  try:
    ReadConFile(con_file)
    server_address = ('', int(80))
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

  # handle keyboardinterrupts
  except KeyboardInterrupt:
    print "[!] Exiting the web server...\n"
  # handle the rest
  except Exception, error:
    print "[!] Something went wrong, printing error: " + str(error)
    sys.exit()

#if __name__ == "__main__":
print "{*} The ConQR Server is running on port 80, open a local browser or remote to view... {*}"
main()
