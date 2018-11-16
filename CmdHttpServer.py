#!/usr/bin/env python

import os
import json
import mimetypes
import traceback
import urllib
import StringIO
import gzip
import socket

from threading			import Thread
from urlparse			import urlparse, parse_qs
from BaseHTTPServer		import BaseHTTPRequestHandler
from BaseHTTPServer		import HTTPServer

#-------------------------------------------------------------------
# CmdHttpServerReq

class CmdHttpServerReq(BaseHTTPRequestHandler):

	# Request handlers
	handlers = {}

	# Log file handle
	logFile = 0

	# Size of last response
	sizeResponse = 0

	# Number of requests handled
	requests = 0

	# Context
	ctx = {}

	# Set to non-zero to enable debug mode
	DEBUG = 1

	# Stack trace in response
	STACK = 0

	# Process multiple commands in order, must be numbered from 0, 1, 2, ...
	ORDERED = 1

	# Non-zero to enable compression
	COMPRESS = 0

	# Log requests
	def log_message(self, format, *args):

		if self.logFile:
			self.logFile.write( "%s - - [%s] \"%s\" %s %i\n" %
								(self.client_address[0],
								 self.log_date_time_string(),
								 args[0],
								 args[1],
								 self.sizeResponse))

	# gzip encode string
	def gzip_encode(self, content):
		out = StringIO.StringIO()
		f = gzip.GzipFile(fileobj=out, mode='w', compresslevel=5)
		f.write(content)
		f.close()
		return out.getvalue()

	# Send error to client
	def _send_error(self, code, error):
		self._send_response(code, "html", "<html><body><h1>%i - %s</h1></body></html>" % (code, error))


	# Send response to client
	def _send_response(self, code, type, data, ext={}):

		# Send headers
		self._set_headers(code, type, len(data), ext, data)


	# Set headers
	def _set_headers(self, code, type, sz, ext={}, data=0):

		self.sizeResponse = sz

		# Set response code
		self.send_response(code)

		# Set content type if user didn't specify
		if 'Content-Type' not in ext and type:

			# Get mime type
			mime =	{
						'json': 'application/json'
					}.get(type, mimetypes.MimeTypes().guess_type(type)[0])

			# Default mime type
			if not mime:
				mime = 'application/octet'

			# Set content type
			self.send_header('Content-Type', mime + ';charset=UTF-8')

		# Set extra headers
		if len(ext):
			for k,v in ext.iteritems():
				self.send_header(k, v)
				#self.send_header('Location', loc)
				#self.send_header('Content-Location', loc)

		# Are we compressing the data?
		if self.COMPRESS and data:
			if 'gzip' in self.headers['accept-encoding']:
				self.send_header('Content-Encoding', 'gzip')
				data = self.gzip_encode(data)
				sz = len(data)

		# Set content length
		self.send_header('Content-Length', sz)

		# Send the headers
		self.end_headers()

		# Do we have data to write?
		if data and len(data):
			self.wfile.write(data)


	# Send json data to client
	def sendJSON(self, code, j):

		try:
			self._send_response(code, "json", json.dumps(j))

		except:
			ts = ''
			if self.STACK:
				ts = "\r\n\r\n" + traceback.format_exc()
			self._send_error(500, "Response encoding error" + ts)
			if self.DEBUG:
				raise
			return


	# Process commands
	def processCmd(self, ch, path, qp, pd):

		# Is there post data?
		if pd:
			pl = int(self.headers['Content-Length'])
			pd = self.rfile.read(pl)

		#-----------------------------------------------------------
		# Single command?
		if 1 < len(path):

			if path[1] not in ch:
				return self.sendJSON(200, {"error": "Unsupported"})

			try:
				ret = ch[path[1]](self, path, qp, pd)
			except:
				ts = ''
				if self.STACK:
					ts = traceback.format_exc()
				self.sendJSON(500, {"error": "Server error handling response", "tb": ts})
				if self.DEBUG:
					raise
				return

			self.sendJSON(200, ret)

			return

		#-----------------------------------------------------------
		# Multiple commands
		if 'cmds' not in qp or not isinstance(qp['cmds'], dict):
			return self.sendJSON(200, {"error": "Bad command format, 'cmds' field is missing"})

		# Process each command
		rep = {}

		if self.ORDERED:

			i = 0
			while str(i) in qp['cmds']:

				k = str(i)
				v = qp['cmds'][k]
				i += 1

				if 'c' not in v:
					rep[k] = {"error": "Ordered command missing"}

				elif v['c'] not in ch:
					rep[k] = {"error": "Unsupported"}

				else:

					# Parameters
					p = v
					if '_' in v:
						p = v['_']

					# Call the handler
					try:
						rep[k] = ch[v['c']](self, path, p, pd)
					except:
						ts = ''
						if self.STACK:
							ts = traceback.format_exc()
						rep[k] = {"error": "Server error handling response", "tb": ts}
						if self.DEBUG:
							raise

		else:
			for k,v in qp['cmds'].iteritems():

				if 'c' not in v:
					rep[k] = {"error": "Unordered command missing"}

				elif v['c'] not in ch:
					rep[k] = {"error": "Unsupported"}

				else:

					# Parameters
					p = v
					if '_' in v:
						p = v['_']

					# Call the handler
					try:
						rep[k] = ch[v['c']](self, path, p, pd)
					except:
						ts = ''
						if self.STACK:
							ts = traceback.format_exc()
						rep[k] = {"error": "Server error handling response", "tb": ts}
						if self.DEBUG:
							raise

		# Send combined responses
		self.sendJSON(200, rep)


	def sendFile(self, h, path, qp):

		if 'path' not in h:

			# Redirect?
			if 'default' in h:
				return self._set_headers(301, 0, 0, {'Location': h['default']})

			return self._send_error(404, "File not found")

		# Verify root path exists
		root = h['path']
		if not os.path.exists(root):
			return self._send_error(404, "File not found")

		# Build the name to the file
		fname = os.sep.join(path[1:])
		floc = ''

		# Default redirect?
		if not len(fname):

			# Was a default name specified?
			if 'default' not in h:
				return self._send_error(404, "File not found")

			# We will attempt a redirect
			fname = h['default']
			floc = "/".join([path[0], fname])

		# Don't allow user to move up
		if 0 <= fname.find('..'):
			return self._send_error(404, "File not found")

		# Full path to the file
		fpath = os.path.join(root, fname)

		# Attempt to open file
		try:
			fh = open(fpath, "rb")
		except:
			fh = 0

		# Punt if we didn't get a file
		if not fh:
			return self._send_error(404, "File not found")

		# File length
		flen = os.path.getsize(fpath)

		# Redirect to default?
		if len(floc):
			return self._set_headers(301, fpath, flen, {'Location': floc})

		# Extra headers to send
		hdrs = {}

		# Download only
		if 'download' in h and h['download']:
			hdrs['Content-Disposition'] = "attachment; filename=%s" % fname

		# Send headers
		self._set_headers(200, fpath, flen, hdrs)

		# Send file data
		while True:
			part = fh.read(64 * 1024)
			if not part:
				break
			self.wfile.write(part)

		fh.close()


	def runHandler(self, h, path, qp, pd):

		# Command handler?
		if 'c' in h:
			self.processCmd(h['c'], path, qp, pd)
			return

		# File path?
		if 'f' in h:
			self.sendFile(h['f'], path, qp)
			return

		return self.sendJSON(400, {"error": "Invalid handler"})


	def processRequest(self, pd):

		# Count a request
		self.requests += 1

		# Parse get variables
		url = urlparse(self.path)
		query = url.query
		qp = parse_qs(query)

		# De-array list,
		for k,v in qp.iteritems():
			if isinstance(v, list) and 1 == len(v):
				qp[k] = v[0]

		# Decode json
		for k,v in qp.iteritems():
			if isinstance(v, str):
				try:
					j = json.loads(v)
					qp[k] = j
				except:
					pass


		# Split path
		path = url.path.split('/')

		# Skip if nothing in the first position and second yields a handler
		if not path[0] and 1 < len(path) and path[1] in self.handlers:
			path = path[1:]

		# Is there a handler?
		if path[0] not in self.handlers:
			return self._send_error(400, "Bad Request")

		# Get handler
		h = self.handlers[path[0]]

		# Run the handler
		return self.runHandler(h, path, qp, pd)


	def do_GET(self):
		self.processRequest(0)


	def do_HEAD(self):
		self._set_headers(200, "html", 0)


	def do_POST(self):
		self.processRequest(1)

#-------------------------------------------------------------------
# CmdHttpServer

class CmdHttpServer():

	# Save params
	port = 7788

	# Request handler
	req = CmdHttpServerReq

	# HTTP Server
	httpServer = 0

	# HTTP Server thread
	httpThread = 0

	# Constructor
	def __init__(self, port, ctx={}):
		self.port = port
		if (len(ctx)):
			self.req.ctx = ctx

	# Server main thread function
	def serverThread(self):

		self.httpServer = HTTPServer(('', self.port), self.req)

		try:
			self.httpServer.serve_forever()
		except socket.error:
			pass

	# Start server thread
	def start(self):
		self.httpThread = Thread(target=self.serverThread)
		self.httpThread.start()

	# Stop server thread
	def stop(self):

		if self.httpServer:
			self.httpServer.socket.close()

		if self.httpThread:
			self.httpThread.join()

