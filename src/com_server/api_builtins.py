# /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Contains class with builtin functions that match `Connection` object

Endpoints include:
    - `/send` (POST): Send something through the serial port using `Connection.send()` with parameters in request; equivalent to `Connection.send()`
    - `/receive` (GET, POST): Respond with the most recent received string from the serial port; equivalent to `Connection.receive_str()`
    - `/receive/all` (GET, POST): Returns the entire receive queue; equivalent to `Connection.get_all_rcv_str()`
    - `/get` (GET, POST): Respond with the first string from serial port after request; equivalent to `Connection.get(str)`
    - `/send/get_first` (POST): Responds with the first string response from the serial port after sending data, with data and parameters in request; equivalent to `Connection.get_first_response()`
    - `/get/wait` (POST): Waits until connection receives string data given in request; different response for success and failure; equivalent to `Connection.wait_for_response()`
    - `/send/get` (POST): Continues sending something until connection receives data given in request; different response for success and failure; equivalent to `Connection.send_for_response()`
    - `/list_ports` (GET): Lists all available Serial ports

The above endpoints will not be valid if the class is used
"""

import typing as t

from flask_restful import reqparse
import flask_restful

from . import RestApiHandler, ConnectionResource, Connection

class Builtins:
    """Contains implementations of endpoints that call methods of `Connection` object
    
    Endpoints include:
        - `/send` (POST): Send something through the serial port using `Connection.send()` with parameters in request; equivalent to `Connection.send()`
        - `/receive` (GET, POST): Respond with the most recent received string from the serial port; equivalent to `Connection.receive_str()`
        - `/receive/all` (GET, POST): Returns the entire receive queue; equivalent to `Connection.get_all_rcv_str()`
        - `/get` (GET, POST): Respond with the first string from serial port after request; equivalent to `Connection.get(str)`
        - `/send/get_first` (POST): Responds with the first string response from the serial port after sending data, with data and parameters in request; equivalent to `Connection.get_first_response()`
        - `/get/wait` (POST): Waits until connection receives string data given in request; different response for success and failure; equivalent to `Connection.wait_for_response()`
        - `/send/get` (POST): Continues sending something until connection receives data given in request; different response for success and failure; equivalent to `Connection.send_for_response()`
        - `/list_ports` (GET): Lists all available Serial ports

    The above endpoints will not be valid if the class is used
    """

    def __init__(self, handler: RestApiHandler) -> None:
        """Constructor for class that contains builtin endpoints

        Adds endpoints to given `RestApiHandler` class;
        uses `Connection` object within the class to handle
        serial data.

        Example usage:
        ```
        conn = com_server.Connection(...)
        handler = com_server.RestApiHandler(conn)
        builtins = com_server.Builtins(handler)

        handler.run() # runs the server
        ```

        Parameters:
        - `api`: The `RestApiHandler` class that this class should wrap around
        """

        if (not isinstance(handler.conn, Connection)):
            raise TypeError("The connection object passed into the handler must be a Connection type")

        self.handler = handler

        # add all endpoints
        self._add_all()
    
    def _add_all(self):
        """Adds all endpoints to handler"""
        
        # /send 
        self.handler.add_endpoint("/send")(self.send)
        
        # /receive
        self.handler.add_endpoint("/receive")(self.receive)

        # /get

        # /send/get_first

        # /get/wait

        # /send/get

        # /list_ports
    
    # throwaway variable at beginning because it is part of class, "self" would be passed
    def send(_, conn: Connection) -> t.Type[ConnectionResource]:
        """
        Endpoint to send data to the serial port.
        Calls `Connection.send()` with given arguments in request.

        Method: POST

        Arguments:
        - "data" (str, list): The data to send; can be provided in multiple arguments, which will be concatenated with the `concatenate` variable.
        - "ending" (str) (optional): A character or string that will be appended to `data` after being concatenated before sending to the serial port.
        By default a carraige return + newline.
        - "concatenate" (str) (optional): The character or string that elements of "data" should be concatenated by if its size is greater than 1;
        won't affect "data" if the size of the list is equal to 1. By default a space.

        Responses:
        - `200 OK`: `{"message": "OK"}` if sent through
        - `502 Bad Gateway`: `{"message": "Failed to send"}` if something went wrong with sending (`Connection.send()` returned false)
        """

        class _Sending(ConnectionResource):
            # make parser once when class is declared, don't add arguments each time request is made aka don't put in post()
            parser = reqparse.RequestParser()
            parser.add_argument("data", required=True, action='append', help="Data the serial port should send; is required")
            parser.add_argument("ending", default="\r\n", help="Ending that will be appended to the end of data before sending over serial port; default carriage return + newline")
            parser.add_argument("concatenate", default=' ', help="What the strings in data should be concatenated by if list; by default a space")

            def post(self):
                args = self.parser.parse_args(strict=True)

                # no need for check_type because everything will be parsed as a string
                res = conn.send(*args["data"], ending=args["ending"], concatenate=args["concatenate"])

                if (not res):
                    # abort if failed to send
                    flask_restful.abort(502, message="Failed to send")
                
                return {"message": "OK"}

        return _Sending
    
    def receive(_, conn: Connection) -> t.Type[ConnectionResource]:
        """
        Endpoint to get data that was recently received.
        If POST, calls `Connection.receive_str()` with arguments given in request.
        If GET, calls `Connection.receive_str()` with default arguments (except strip=True). This means
        that it responds with the latest received string with everything included after 
        being stripped of whitespaces and newlines.
        Response is a list containing timestamp and string.

        Method: GET, POST

        Arguments (POST only):
        - "num_before" (int) (optional): How recent the receive object should be.
        If 0, then returns most recent received object. If 1, then returns
        the second most recent received object, etc. By default 0.
        - "read_until" (str, null) (optional): Will return a string that terminates with
        character in "read_until", excluding that character or string. For example,
        if the bytes was `b'123456'` and "read_until" was 6, then it will return
        `'12345'`. If ommitted, then returns the entire string. By default returns entire string.
        - "strip" (bool) (optional): If true, then strips received and processed string of
        whitespaces and newlines and responds with result. Otherwise, returns raw string. 
        By default False.

        Response:
        - `200 OK`:
            - `{"message": "OK", "timestamp": ..., "data": "..."}` where "timestamp"
            is the Unix epoch time that the message was received and "data" is the
            data that was processed. If nothing was received, then "data" and "timestamp"
            would be None/null.
        """

        class _Receiving(ConnectionResource):

            parser = reqparse.RequestParser()
            parser.add_argument("num_before", type=int, default=0, help="Which receive data to return")
            parser.add_argument("read_until", default=None, help="What character the string should read until")
            parser.add_argument("strip", type=bool, default=False, help="If the string should be stripped of whitespaces and newlines before responding")

            def get(self):
                res = conn.receive_str()

                return {
                    "message": "OK",
                    "timestamp": res[0] if isinstance(res, tuple) else None,
                    "data": res[1] if isinstance(res, tuple) else None
                }

            def post(self):
                args = self.parser.parse_args(strict=True)

                res = conn.receive_str(num_before=args["num_before"], read_until=args["read_until"], strip=args["strip"])

                return {
                    "message": "OK",
                    "timestamp": res[0] if isinstance(res, tuple) else None,
                    "data": res[1] if isinstance(res, tuple) else None
                }
        
        return _Receiving
