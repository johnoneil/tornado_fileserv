#!/usr/bin/python
 # vim: set ts=2 expandtab:
"""
Module: fileserver
Desc:
Author: John O'Neil
Email:

"""
#!/usr/bin/python
 
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.iostream
import socket
import string
import json
import time
import datetime
import calendar
import os
import re
import glob
import sys

#tornado command line options support
from tornado.options import define, options
define('port', default=8888)
define('dir',default='.')
define('chunksize',default=16384)

class filedata:
  def __init__(self,filepath,filename):
    self.filename = filename
    self.full_path = filepath + '/' + filename
    self.epoch_time =  time.localtime(os.path.getmtime(self.full_path))
    self.timestamp = time.strftime('%a, %b %d %y', self.epoch_time)
    self.file_type = self.GetFileType(self.full_path)
    self.size = str(os.path.getsize(self.full_path))

  def GetFileType(self, filepath):
    if not os.path.exists(filepath):
      return 'unknown'
    #print 'determining natrue of file ' + filepath
    if os.path.isfile(filepath):
      name,extension = os.path.splitext(filepath)
      extension = extension.lower()
      if(extension == '.mov' or extension == '.avi' or extension == '.mpg'
        or extension == '.mkv' or extension == '.mp4' or extension == '.flv'):
        return 'video'
      if(extension == '.mp3' or extension == '.ogg' or extension == '.flac'):
        return 'audio'
      if extension == '.zip':
        return 'zip'
      return 'file'
    else:
      return 'dir'

class List(tornado.web.RequestHandler):
  def get(self):
    items = os.listdir(options.dir)
    files = []

    for item in items:
      current_file = filedata(options.dir,item)
      files.append(current_file)

    files.sort(key = lambda x: x.epochtime,reverse=True)
    directory_name = os.path.basename(os.path.normpath(options.dir))
    self.render("main.html",title='Contents of '+ directory_name, items=files)

class Download(tornado.web.RequestHandler):
  @tornado.web.asynchronous
  def get(self, filepath):
    #for root URL, filepath is apparently disagreeable
    if not filepath:filepath=''
    print "filepath is " + filepath

    #discern our local system internal path corresponding to the URL
    system_filepath = os.path.normpath(options.dir +'/'+ filepath)
    print 'System local filepath for GET is "' + system_filepath +'"'

    #TODO: Limit paths to children of base path (confine browsing)

    #is this a nonsense URL?
    if not os.path.exists(system_filepath):
      return self.send_error(status_code=404)

    #if this is a file, we'll send the file contents to the user
    #TODO: check user authentication
    if os.path.isfile(system_filepath):
      filesize = str(os.path.getsize(system_filepath))
      filename = os.path.basename(system_filepath)
      print 'file ' + filename + ' requested at ' + system_filepath + ' of size ' + filesize
      self.set_header('Content-type', 'octet/stream')
      self.set_header('Content-Disposition', 'attachment; filename="' + filename+'"')
      self.set_header('Content-Length',filesize)
      
      #TODO: flush the header to client and allow them to "accept" or "cancel"
      #the file transfer before we start to send chunks?

      #send the file as a series of arbitrary chunk sizes
      with open(system_filepath, 'rb') as f:
        chunk_number = 1
        while True:
          data = f.read(options.chunksize)
          if not data: break
          #write binary data into our output buffer and then flush the
          #buffer to the network. This vastly increases download time and
          #decreases the memory requirements on the server as we no longer
          #have to buffer the entire file body in server ram
          self.write(data)
          self.flush()
      self.finish()
    else:#handle directory
      print 'handling directory ' + system_filepath
      items = os.listdir(system_filepath)
      files = []

      for item in items:
        current_file = filedata(system_filepath,item)
        files.append(current_file)
      #sort the files in the directory according to their timestamp
      files.sort(key = lambda x: x.epoch_time,reverse=True)
      
      #form a friendly path to this directory, appending base system directory
      #name to the URL path
      directory_name = os.path.basename(os.path.normpath(options.dir)) + '/'
      if(filepath):
        directory_name = directory_name  + os.path.basename(os.path.normpath(system_filepath))
      
      self.render("main.html",title=directory_name,path=filepath, files=files)



class FileServer(tornado.web.Application):
  def __init__(self, dir_path):
    self.dir_path = dir_path
    handlers = [
      (r"/css/(.*)", tornado.web.StaticFileHandler, {'path': '/home/joneil/code/TornadoFileserv/css'}),
      (r'/(.*)', Download),
    ]
    settings = {}
    super(FileServer,self).__init__(handlers,**settings)

def main():

  tornado.options.parse_command_line()

  application = FileServer(options.dir)
  application.listen(options.port)
  tornado.ioloop.IOLoop.instance().start()
 
if __name__ == "__main__":
  main()