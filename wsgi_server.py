import argparse
import socket
import sys
from io import StringIO


class WsgiServer:

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, server_address):
        self.listen_socket = socket.socket(self.address_family, self.socket_type)
        # Allow to reuse socket
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind and listen
        self.listen_socket.bind(server_address)
        self.listen_socket.listen(self.request_queue_size)\

        host, port = self.listen_socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

        # Return headers set by web framework
        self.headers_set = []

        self.client_connection = None
        self.application = None

    def set_app(self, application):
        self.application = application

    def serve_forever(self):
        while True:
            # New connection
            self.client_connection, client_address = self.listen_socket.accept()
            # Hqndle one request qnd close the client connection.
            # Then loop over to wait for another client connection
            self.handle_one_request()

    def handle_one_request(self):
        request_data = self.client_connection.recv(1024)
        request_data = request_data.decode()
        print(request_data)

        # Construct env dictionary using request data
        env = self.get_environ(request_data)

        # Call our application callable and get back a result
        # then will become HTTP response body
        result = self.application(env, self.start_response)

        self.finish_response(result)

    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')

        # Break down the request line into components
        request_method, path, request_version = request_line.split()
        return request_method, path, request_version

    def get_environ(self, request_data):
        request_method, path, request_version = self.parse_request(request_data)
        return {
            # WSGI
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': StringIO(request_data),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            # CGI
            'REQUEST_METHOD': request_method,
            'PATH_INFO': path,
            'SERVER_NAME': self.server_name,
            'SERVER_PORT': str(self.server_port),
        }

    def start_response(self, status, response_headers, exc_info=None):
        # Necessary server headers
        server_headers = [
            ('Date', '2019-03-10'),
            ('Server', 'WSGIServer v1')

        ]
        self.headers_set = [status, response_headers + server_headers]

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = f"HTTP/1.1 {status}\r\n"
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            response = response.encode()

            for data in result:
                response += data

            print(''.join(
                [f'> {line}\n' for line in response.splitlines()]
            ))

            self.client_connection.sendall(response)

        finally:
            self.client_connection.close()


SERVER_ADDRESS = (HOST, PORT) = '', 8888


def make_server(server_address, application):
    server = WsgiServer(server_address)
    server.set_app(application)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provide a WSGi application object as module:callable'
    )
    parser.add_argument('application')
    args = parser.parse_args()
    app_path = args.application

    module, application = app_path.split(':')
    module = __import__(module)
    application = getattr(module, application)
    httpd = make_server(SERVER_ADDRESS, application)
    print(f'Serving HTTP on port {PORT}')
    httpd.serve_forever()
