#!/usr/bin/env python

import time
import os
import sys
import argparse
import json
import SocketServer
import urllib2
import subprocess

from dateutil			import tz
from datetime			import datetime, timedelta
from threading			import Thread, Event
from CmdHttpServer		import CmdHttpServer
from BaseHTTPServer		import HTTPServer

#-------------------------------------------------------------------
# Globals
p = {}


#-------------------------------------------------------------------
# Web Commands

def cmdGetFiles(req, path, cmd, pd):

	files = []
	dir = req.ctx['folder']
	if not len(dir):
		dir = './'

	sub = ''
	if 'path' in cmd and len(cmd['path']) and 0 > cmd['path'].find('..'):

		s = cmd['path']

		while len(s) and ('/' == s[0] or '\\' == s[0]):
			s = s[1:]

		if len(s) and os.path.exists(os.path.join(dir, s)):
			sub = s
			dir = os.path.join(dir, s)

	for fname in os.listdir(dir):

		path = os.path.join(dir, fname)
		si = os.stat(path)
		isfile = os.path.isfile(path)
		isdir = os.path.isdir(path)

		if isdir:
			link = ''
		elif len(sub):
			link = "/".join(['/files', sub, fname])
		else:
			link = "/".join(['/files', fname])

		fi = {
			'name': fname,
			'isfile': isfile,
			'isdir': isdir,
			'size': si.st_size,
			'atime': si.st_atime,
			'mtime': si.st_mtime,
			'ctime': si.st_ctime,
			'link': link
		}

		files.append(fi)

	return {'ok': 1, 'path': sub, 'files': files, 'root': req.ctx['folder'], 'absroot': os.path.abspath(req.ctx['folder'])}


#-------------------------------------------------------------------
# Main function

def main():
	global p

	print "Los geht's..."

	scriptroot = os.path.dirname(__file__)
	scriptname = os.path.basename(os.path.splitext(__file__)[0])

	# Get user folder
	userroot = os.path.expanduser("~")
	if not os.path.exists(userroot):
		userroot = './'

	# Build a unique web link name
	cachedir = os.path.join(userroot, '.cache', scriptname)
	if not os.path.exists(cachedir):
		os.makedirs(cachedir)

	# Default web log name
	weblog = os.path.join(cachedir, scriptname + '-web.log')

	# Default html root
	htmlroot = os.path.join(scriptroot, 'html')

	# Command line arguments
	ap = argparse.ArgumentParser(description='HTTP Server')
	ap.add_argument('--port', '-p', default=8800, type=int, help='Server Port')
	ap.add_argument('--html', '-m', default=htmlroot, type=str, help='Document root')
	ap.add_argument('--logfile', '-l', default=weblog, type=str, help='Logfile')
	ap.add_argument('--folder', '-f', default='./', type=str, help='Folder to monitor')
	p = vars(ap.parse_args())

	print "Parameters: " + str(p)

	print 'Running at : http://localhost:%i/' % p['port']

	# We must have an html folder
	if not os.path.exists(p['html']):
		print "Bad html path : " + p['html']
		return;

	# Create an exit event
	p['exit'] = Event()

	# Create web server thread
	httpd = CmdHttpServer(p['port'], p)

	# Request handler
	httpd.req.handlers = {
		'_':
		{
			'c':
			{
				'cmdGetFiles': cmdGetFiles
			}
		},
		'html':
		{
			'f':
			{
				'path': p['html'],
				'default': 'index.html'
			}
		},
		'files':
		{
			'f':
			{
				'path': p['folder'],
				'download': True
			}
		},
		'':
		{
			'f':
			{
				'default': 'html/index.html'
			}
		}
	}

	# Log file
	if len(p['logfile']):
		httpd.req.logFile = open(p['logfile'], "a", 0)

	# Start the server
	httpd.start()

	# Local cleanup
	def cleanup():
		p['exit'].set()
		httpd.stop()

	# Run the loop
	try:
		while not p['exit'].is_set():
			p['exit'].wait(1)

	except KeyboardInterrupt:
		print " ~ KeyboardInterrupt ~ "
		pass

	except:
		cleanup()
		raise

	cleanup()

	print "Bye..."


if __name__ == '__main__':
	main()

