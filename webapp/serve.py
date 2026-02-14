from http.server import HTTPServer, SimpleHTTPRequestHandler

server = HTTPServer(("0.0.0.0", 3000), SimpleHTTPRequestHandler)
print("WebApp: http://localhost:3000")
server.serve_forever()
