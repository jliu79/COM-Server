# COM-Server Library API

## Functions

### com_server.all_ports()

```py
def all_ports(**kwargs)
```

Gets all ports from serial interface.

Gets ports from Serial interface by calling `serial.tools.list_ports.comports()`.
See [here](https://pyserial.readthedocs.io/en/latest/tools.html#module-serial.tools.list_ports) for more info.

---

## Classes

### com_server.BaseConnection
A base connection object with a serial or COM port.

If you want to communicate via serial, it is recommended to
either directly use `pyserial` directly or use the `Connection` class.

How this works is that it creates a pyserial object given the parameters, which opens the connection. 
The user can manually open and close the connection. It is closed by default when the initializer is called.
It spawns a thread that continuously looks for serial data and puts it in a buffer. 
When the user wants to send something, it will pass the send data to a queue,
and the thread will process the queue and will continuously send the contents in the queue
until it is empty, or it has reached 0.5 seconds. This thread is referred as the "IO thread".

All data will be encoded and decoded using `utf-8`.

If used in a `while(true)` loop, it is highly recommended to put a `time.sleep()` within the loop,
so the main thread won't use up so many resources and slow down the IO thread.

This class contains the four basic methods needed to talk with the serial port:

- `connect()`: opens a connection with the serial port
- `disconnect()`: closes the connection with the serial port
- `send()`: sends data to the serial port
- `read()`: reads data from the serial port

It also contains the property `connected` to indicate if it is currently connected to the serial port.

If the USB port is disconnected while the program is running, then it will automatically detect the exception
thrown by `pyserial`, and then it will reset the IO variables and then label itself as disconnected. Then,
it will send a `SIGTERM` signal to the main thread if the port was disconnected.

**Warning**: Before making this object go out of scope, make sure to call `disconnect()` in order to avoid thread leaks. 
If this does not happen, then the IO thread will still be running for an object that has already been deleted.

#### BaseConnection.\_\_init\_\_()

```py
def __init__(baud, port, exception=True, timeout=1, queue_size=256, exit_on_disconnect=True, **kwargs)
```

Initializes the Base Connection class. 

`baud`, `port`, `timeout`, and `kwargs` will be passed to pyserial.  
For more information, see [here](https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial).

Parameters:

- `baud` (int): The baud rate of the serial connection 
- `port` (str): The serial port
- `timeout` (float) (optional): How long the program should wait, in seconds, for serial data before exiting. By default 1.
- `exception` (bool) (optional): Raise an exception when there is a user error in the methods rather than just returning. By default True.
- `send_interval` (int) (optional): Indicates how much time, in seconds, the program should wait before sending another message. 
Note that this does NOT mean that it will be able to send every `send_interval` seconds. It means that the `send()` method will 
exit if the interval has not reached `send_interval` seconds. NOT recommended to set to small values. By default 1.
- `queue_size` (int) (optional): The number of previous data that was received that the program should keep. Must be nonnegative. By default 256.
- `exit_on_disconnect` (bool) (optional): If True, sends `SIGTERM` signal to the main thread if the serial port is disconnected. Does NOT work on Windows. By default False.
- `kwargs`: Will be passed to pyserial.

Returns: nothing

May raise:

- `ValueError` if the values given could not be converted to the types they should be.

#### BaseConnection.\_\_enter\_\_()

```py
def __enter__()
```

A context manager for the `BaseConnection` object. 

When in a context manager, it will automatically connect itself
to its serial port and returns itself. 

May raise:

- `ValueError` if the values given could not be converted to the types they should be.
- `com_server.ConnectException` if the user calls this function while it is already connected and `exception` is True.
- `serial.serialutil.SerialException` if the port given in `__init__` does not exist.
- `EnvironmentError` if `exit_on_disconnect` is True and the user is on Windows (_not tested_).

#### BaseConnection.\_\_exit\_\_()

```py
def __exit__(exc_type, exc_value, exc_tb)
```

A context manager for the `BaseConnection` object. 

When exiting from the context manager, it automatically closes itself and exits from the threads it had created.


#### BaseConnection.connect()

```py
def connect()
```

Begins connection to the serial port.

When called, initializes a serial instance if not initialized already. Also starts the IO thread.

Parameters: None

Returns: None

May raise:

- `com_server.ConnectException` if the user calls this function while it is already connected and `exception` is True.
- `serial.serialutil.SerialException` if the port given in `__init__` does not exist.
- `EnvironmentError` if `exit_on_disconnect` is True and the user is on Windows (_not tested_).

#### BaseConnection.disconnect()

```py
def disconnect()
```

Closes connection to the serial port.

When called, calls `Serial.close()` then makes the connection `None`. If it is currently closed then just returns.

**NOTE**: This method should be called if the object will not be used anymore
or before the object goes out of scope, as deleting the object without calling 
this will lead to stray threads.

Parameters: None

Returns: None

#### BaseConnection.send()

```py
def send(*args, check_type=True, ending='\r\n', concatenate=' ')
```

Sends data to the port

If the connection is open and the interval between sending is large enough, 
then concatenates args with a space (or what was given in `concatenate`) in between them, 
encodes to an `utf-8` `bytes` object, adds a carriage return and a newline to the end (i.e. "\\r\\n") (or what was given as `ending`), then sends to the serial port.

Note that the data does not send immediately and instead will be added to a queue. 
The queue size limit is 65536 byte objects. Anything more that is trying to be sent will not be added to the queue.
Sending data too rapidly (e.g. making `send_interval` too small, varies from computer to computer) is not recommended,
as the queue will get too large and the send data will get backed up and will be delayed,
since it takes a considerable amount of time for data to be sent through the serial port.
Additionally, parts of the send queue will be all sent together until it reaches 0.5 seconds,
which may end up with unexpected behavior in some programs.
To prevent these problems, either make the value of `send_interval` larger,
or add a delay within the main thread. 

If the program has not waited long enough before sending, then the method will return `false`.

If `check_type` is True, then it will process each argument, then concatenate, encode, and send.

- If the argument is `bytes` then decodes to `str`
- If argument is `list` or `dict` then passes through `json.dumps`
- If argument is `set` or `tuple` then converts to list and passes through `json.dumps`
- Otherwise, directly convert to `str` and strip
Otherwise, converts each argument directly to `str` and then concatenates, encodes, and sends.

Parameters:

- `*args`: Everything that is to be sent, each as a separate parameter. Must have at least one parameter.
- `check_type` (bool) (optional): If types in *args should be checked. By default True.
- `ending` (str) (optional): The ending of the bytes object to be sent through the serial port. By default a carraige return + newline ("\\r\\n")
- `concatenate` (str) (optional): What the strings in args should be concatenated by. By default a space `' '`

Returns:

- `true` on success (everything has been sent through)
- `false` on failure (not open, not waited long enough before sending, did not fully send through, etc.)

May raise:
- `com_server.ConnectException` if the user tries to send while it is disconnected and `exception` is True.

#### BaseConnection.receive()

```py
def receive(num_before=0)
```

Returns the most recent receive object

The IO thread will continuously detect receive data and put the `bytes` objects in the `rcv_queue`. 
If there are no parameters, the method will return the most recent received data.
If `num_before` is greater than 0, then will return `num_before`th previous data.

- Note: Must be less than the current size of the queue and greater or equal to 0 
    - If not, returns None (no data)
- Example:
    - 0 will return the most recent received data
    - 1 will return the 2nd most recent received data
    - ...

Note that the data will be read as ALL the data available in the serial port,
or `Serial.read_all()`.

Parameters:

- `num_before` (int) (optional): Which receive object to return. Must be nonnegative. By default None.

Returns:

- A `tuple` representing the `(timestamp received, data in bytes)`
- `None` if no data was found or port not open

May raise:

- `com_server.ConnectException` if a user calls this method when the object has not been connected and `exception` is True.
- `ValueError` if `num_before` is nonnegative and `exception` is True.

#### BaseConnection.connected

Getter:  
A property to determine if the connection object is currently connected to a serial port or not.
This also can determine if the IO thread for this object
is currently running or not.

#### BaseConnection.timeout

A property to determine the timeout of this object.

Getter:

- Gets the timeout of this object.

Setter:

- Sets the timeout of this object after checking if convertible to nonnegative float. 
Then, sets the timeout to the same value on the `pyserial` object of this class.
If the value is `float('inf')`, then sets the value of the `pyserial` object to None.

#### BaseConnection.send_interval

A property to determine the send interval of this object.

Getter:

- Gets the send interval of this object.

Setter:

- Sets the send interval of this object after checking if convertible to nonnegative float.

---

### com_server.Connection
A more user-friendly interface with the serial port.

In addition to the four basic methods (see `BaseConnection`),
it makes other methods that may also be useful to the user
when communicating with the classes.

Some of the methods include:

- `get()`: Gets first response after the time that the method was called
- `get_all_rcv()`: Returns the entire receive queue
- `get_all_rcv_str()`: Returns the entire receive queue, converted to strings
- `receive_str()`: Receives as a string rather than bytes object
- `get_first_response()`: Gets the first response from the serial port after sending something (breaks when timeout reached)
- `send_for_response()`: Continues sending something until the connection receives a given response (breaks when timeout reached)
- `wait_for_response()`: Waits until the connection receives a given response (breaks when timeout reached)
- `reconnect()`: Attempts to reconnect given a new port

Other methods can generally help the user with interacting with the classes:

- `all_ports()`: Lists all available COM ports.

**Warning**: Before making this object go out of scope, make sure to call `disconnect()` in order to avoid thread leaks. 
If this does not happen, then the IO thread will still be running for an object that has already been deleted.

#### Connection.\_\_init\_\_()

```py
def __init__(baud, port, exception=True, timeout=1, queue_size=256, exit_on_disconnect=True, **kwargs)
```

See [BaseConnection.\_\_init\_\_()](#baseconnection__init__)

#### Connection.\_\_enter\_\_()

```py
def __enter__()
```

Same as [BaseConnection.\_\_enter\_\_()](#baseconnection__enter__) but returns a `Connection` object rather than a `BaseConnection` object.

#### Connection.\_\_exit\_\_()

```py
def __exit__(exc_type, exc_value, exc_tb)
```

See [BaseConnection.\_\_exit\_\_()](#baseconnection__exit__)

#### Connection.connect()

```py
def connect()
```

See [BaseConnection.connect()](#baseconnectionconnect)

#### Connection.disconnect()

```py
def disconnect()
```

See [BaseConnection.disconnect()](#baseconnectiondisconnect)

#### Connection.send()

```py
def send(*args, check_type=True, ending='\r\n', concatenate=' ')
```

See [BaseConnection.send()](#baseconnectionsend)

#### Connection.receive()

```py
def receive(num_before=0)
```

See [BaseConnection.receive()](#baseconnectionreceive)

#### Connection.connected

See [BaseConnection.connected](#baseconnectionconnected)

#### Connection.timeout
See [BaseConnection.timeout](#baseconnectiontimeout)

#### Connection.send_interval
See [BaseConnection.send_interval](#baseconnectionsend_interval)

#### Connection.conv_bytes_to_str()

```py
def conv_bytes_to_str(rcv, read_until=None, strip=True)
```

Convert bytes receive object to a string.

Parameters:

- `rcv` (bytes): A bytes object. If None, then the method will return None.
- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\\n"`, and `read_until` was `\\n`, then it will return `"abcdefg123456"`.
If there are multiple occurrences of `read_until`, then it will return the string that terminates with the first one.
If `read_until` is None or it doesn't exist, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips spaces and newlines from either side of the processed string before returning.
If False, returns the processed string in its entirety. By default True.

Returns:

- A `str` representing the data
- None if `rcv` is None

May raise:

- `UnicodeDecodeError` if there was trouble decoding the bytes object from `utf-8`.


#### Connection.get()

```py
def get(given_type, read_until=None, strip=True)
```

Gets first response after this method is called.

This method differs from `receive()` because `receive()` returns
the last element of the receive buffer, which could contain objects
that were received before this function was called. This function
waits for something to be received after it is called until it either
gets the object or until the timeout is reached.

Parameters:

- `given_type` (type): either `bytes` or `str`, indicating which one to return. 
Will raise exception if type is invalid, REGARDLESS of `self.exception`. Example: `get(str)` or `get(bytes)`.
- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\n"`, and `read_until` was `\n`, then it will return `"abcdefg123456"`.
If there are multiple occurrences of `read_until`, then it will return the string that terminates with the first one.
If `read_until` is None or it doesn't exist, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips spaces and newlines from either side of the processed string before returning.
If False, returns the processed string in its entirety. By default True.

Returns:

- None if no data received (timeout reached)
- A `bytes` object indicating the data received if `type` is `bytes`

May raise:

- `com_server.ConnectException` if a user calls this method when the object has not been connected and `exception` is True.
- `TypeError` if not given literals `str` or `bytes` in `given_type`

#### Connection.get_all_rcv()

```py
def get_all_rcv()
```

Returns the entire receive queue

The queue will be a `queue_size`-sized list that contains
tuples (timestamp received, received bytes).

Returns:

- A list of tuples indicating the timestamp received and the bytes object received

#### Connection.get_all_rcv_str()

```py
def get_all_rcv_str(read_until=None, strip=True)
```

Returns entire receive queue as string.

Each bytes object will be passed into `conv_bytes_to_str()`.
This means that `read_until` and `strip` will apply to 
EVERY element in the receive queue before returning.

Parameters:

- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\\n"`, and `read_until` was `\\n`, then it will return `"abcdefg123456"`.
If there are multiple occurrences of `read_until`, then it will return the string that terminates with the first one.
If `read_until` is None or it doesn't exist, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips spaces and newlines from either side of the processed string before returning.
If False, returns the processed string in its entirety. By default True.

Returns:

- A list of tuples indicating the timestamp received and the converted string from bytes 

#### Connection.get_first_response()

```py
def get_first_response(*args, is_bytes=True, check_type=True, ending='\r\n', concatenate=' ', read_until=None, strip=True)
```

Gets the first response from the serial port after sending something.

This method works almost the same as `send()` (see `self.send()`). 
It also returns a string representing the first response from the serial port after sending.
All `*args` and `check_type`, `ending`, and `concatenate`, will be sent to `send()`.

If there is no response after reaching the timeout, then it breaks out of the method.

Parameters:

- `*args`: Everything that is to be sent, each as a separate parameter. Must have at least one parameter.
- `is_bytes`: If False, then passes to `conv_bytes_to_str()` and returns a string
with given options `read_until` and `strip`. See `conv_bytes_to_str()` for more details.
If True, then returns raw `bytes` data. By default True.
- `check_type` (bool) (optional): If types in *args should be checked. By default True.
- `ending` (str) (optional): The ending of the bytes object to be sent through the serial port. By default a carraige return ("\\r\\n")
- `concatenate` (str) (optional): What the strings in args should be concatenated by. By default a space `' '`.
- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\\n"`, and `read_until` was `\\n`, then it will return `"abcdefg123456"`.
If `read_until` is None, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips the received and processed string of whitespace and newlines, then 
returns the result. If False, then returns the raw result. By default True.

Returns:

- A string or bytes representing the first response from the serial port.
- None if there was no connection (if self.exception == False), no data, timeout reached, or send interval not reached.

May raise:

- `com_server.ConnectException` if a user calls this method when the object has not been connected and `exception` is True.

#### Connection.wait_for_response()

```py
def wait_for_response(response, after_timestamp=-1.0, read_until=None, strip=True)
```

Waits until the connection receives a given response.

This method will call `receive()` repeatedly until it
returns a string that matches `response` whose timestamp
is greater than given timestamp (`after_timestamp`).

Parameters:

- `response` (str, bytes): The receive data that the program is looking for.
If given a string, then compares the string to the response after it is decoded in `utf-8`.
If given a bytes, then directly compares the bytes object to the response.
If given anything else, converts to string.
- `after_timestamp` (float) (optional): Look for responses that came after given time as the UNIX timestamp.
If negative, the converts to time that the method was called, or `time.time()`. By default -1.0

These parameters only apply if `response` is a string:

- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\\n"`, and `read_until` was `\\n`, then it will return `"abcdefg123456"`.
If `read_until` is None, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips the received and processed string of whitespace and newlines, then 
returns the result. If False, then returns the raw result. By default True.

Returns:

- True on success
- False on failure: timeout reached because response has not been received.

May raise:

- `com_server.ConnectException` if a user calls this method when the object has not been connected and `exception` is True.

#### Connection.send_for_response()

```py
def send_for_response(response, *args, read_until=None, strip=True, check_type=True, ending='\r\n', concatenate=' ')
```

Continues sending something until the connection receives a given response.

This method will call `send()` and `receive()` repeatedly (calls again if does not match given `response` parameter).
See `send()` for more details on `*args` and `check_type`, `ending`, and `concatenate`, as these will be passed to the method.
Will return `true` on success and `false` on failure (reached timeout)

Parameters:

- `response` (str, bytes): The receive data that the program looks for after sending.
If given a string, then compares the string to the response after it is decoded in `utf-8`.
If given a bytes, then directly compares the bytes object to the response.
- `*args`: Everything that is to be sent, each as a separate parameter. Must have at least one parameter.
- `check_type` (bool) (optional): If types in *args should be checked. By default True.
- `ending` (str) (optional): The ending of the bytes object to be sent through the serial port. By default a carraige return ("\\r\\n")
- `concatenate` (str) (optional): What the strings in args should be concatenated by. By default a space `' '`

These parameters only apply if `response` is a string:

- `read_until` (str, None) (optional): Will return a string that terminates with `read_until`, excluding `read_until`. 
For example, if the string was `"abcdefg123456\\n"`, and `read_until` was `\\n`, then it will return `"abcdefg123456"`.
If `read_until` is None, the it will return the entire string. By default None.
- `strip` (bool) (optional): If True, then strips the received and processed string of whitespace and newlines, then 
returns the result. If False, then returns the raw result. By default True.

Returns:

- `true` on success: The incoming received data matching `response`.
- `false` on failure: Connection not established (if self.exception == False), incoming data did not match `response`, or `timeout` was reached, or send interval has not been reached.

May raise:

- `com_server.ConnectException` if a user calls this method when the object has not been connected and `exception` is True.

#### Connection.reconnect()

```py
def reconnect(port=None)
```

Attempts to reconnect the serial port.

This will change the `port` attribute then call `self.connect()`.
Will raise `ConnectException` if already connected, regardless
of if `exception` if True or not.

Note that `reconnect()` can be used instead of `connect()`, but
it will connect to the `port` parameter, not the `port` attribute
when the class was initialized.

This method will continuously try to connect to the port provided
(unless `port` is None, in which case it will connect to the previous port)
until it reaches given `timeout` seconds. If `timeout` is None, then it will
continuously try to reconnect indefinitely.

Parameters:

- `port` (str, None) (optional): Program will reconnect to this port. 
If None, then will reconnect to previous port. By default None.
- `timeout` (float, None) (optional): Will try to reconnect for
`timeout` seconds before returning. If None, then will try to reconnect
indefinitely. By default None.

Returns:

- True if able to reconnect
- False if not able to reconnect within given timeout

#### Connection.all_ports()

```py
def all_ports(**kwargs)
```

Lists all available serial ports.

Calls `tools.all_ports()`, which itself calls `serial.tools.list_ports.comports()`.
For more information, see [here](https://pyserial.readthedocs.io/en/latest/tools.html#module-serial.tools.list_ports).

Parameters: See link above.

Returns: A generator-like object (see link above)

---

### com_server.RestApiHandler
A handler for creating endpoints with the `Connection` and `Connection`-based objects.

This class provides the framework for adding custom endpoints for doing
custom things with the serial connection and running the local server
that will host the API. It uses a `flask_restful` object as its back end. 

Note that only one connection (one IP address) will be allowed to connect
at a time because the serial port can only handle one process. 
Additionally, endpoints cannot include `/register` or `/recall`, as that 
will be used to ensure that there is only one connection at a time. Note that unexpected behavior may occur when different processes of the same IP reach the same endpoint as they only check IPs, not processes. Finally,
resource classes have to extend the custom `ConnectionResource` class
from this library, not the `Resource` from `flask_restful`.

`500 Internal Server Error`s may occur with endpoints dealing with the connection
if the serial port is disconnected. Disconnections while the server is running
require restarts of the server and may change the port of the Arduino.

More information on [Flask](https://flask.palletsprojects.com/en/2.0.x/) and 
[flask-restful](https://flask-restful.readthedocs.io/en/latest/)

Register and recall endpoints:

- `/register` (GET): An endpoint to register an IP; other endpoints will result in `400` status code
if they are accessed without accessing this first; if an IP is already registered then this will
result in `400`; IPs must call this first before accessing serial port
- `/recall` (GET): After registered, can call `/recall` to "free" IP from server, allowing other IPs to 
call `/register` to use the serial port

#### RestApiHandler.\_\_init\_\_()

```py
def __init__(conn, **kwargs)
```

Constructor for class

Parameters:

- `conn` (`Connection`): The `Connection` object the API is going to be associated with. 
- `**kwargs`, will be passed to `flask_restful.Api()`. See [here](https://flask-restful.readthedocs.io/en/latest/api.html#id1) for more info.

May raise:

- `TypeError` if an additional argument is provided that is not in `flask_restful.Api()`

#### RestApiHandler.add_endpoint()

```py
def add_endpoint(endpoint)
```

Decorator that adds an endpoint

This decorator needs to go above a function which
contains a nested class that extends `ConnectionResource`.
The function needs a parameter indicating the serial connection.
The function needs to return that nested class.
The class should contain implementations of request
methods such as `get()`, `post()`, etc. similar to the 
`Resource` class from `flask_restful`.

For more information, see the `flask_restful` [documentation](https://flask-restful.readthedocs.io).

Note that duplicate endpoints will result in an exception.
If there are two classes of the same name, even in different
endpoints, the program will append underscores to the name
until there are no more repeats. For example, if one function
returned a class named "Hello" and another function returned a
class also named "Hello", then the second class name will be 
changed to "Hello_". This happens because `flask_restful` 
interprets duplicate class names as duplicate endpoints.

Parameters:

- `endpoint`: The endpoint to the resource. Cannot repeat.
`/register` and `/recall` cannot be used.

May raise:

- `com_server.EndpointExistsException`: If an endpoint already exists
- `TypeError` if the function does not return a class that extends `com_server.ConnectionResource`

#### RestApiHandler.add_resource()

```py
def add_resource(*args, **kwargs)
```

Calls `flask_restful.add_resource`. Allows adding endpoints
without needing a connection.

See [here](https://flask-restful.readthedocs.io/en/latest/api.html#flask_restful.Api.add_resource)
for more info on `add_resource` and [here](https://flask-restful.readthedocs.io)
for more info on `flask_restful` in general. 

May raise:

- See [here](https://flask-restful.readthedocs.io/en/latest/api.html#flask_restful.Api.add_resource)

#### RestApiHandler.run_dev()

```py
def run_dev(**kwargs)
```

Launches the Flask app as a development server.

All arguments in `**kwargs` will be passed to `Flask.run()`.
For more information, see [here](https://flask.palletsprojects.com/en/2.0.x/api/#flask.Flask.run).
For documentation on Flask in general, see [here](https://flask.palletsprojects.com/en/2.0.x/).

Automatically disconnects the `Connection` object after
the server is closed.

Some arguments include: 

- `host`: The host of the server. Ex: `localhost`, `0.0.0.0`, `127.0.0.1`, etc.
- `port`: The port to host it on. Ex: `5000` (default), `8000`, `8080`, etc.
- `debug`: If the app should be used in debug mode. 

May raise:

- See [here](https://flask-restful.readthedocs.io/en/latest/api.html#flask_restful.Api.add_resource)
- See [here](https://flask.palletsprojects.com/en/2.0.x/api/#flask.Flask.run)

#### RestApiHandler.run_prod()

```py
def run_prod(**kwargs)
```

Launches the Flask app as a Waitress production server.

All arguments in `**kwargs` will be passed to `waitress.serve()`.
For more information, see [here](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html#arguments).
For Waitress documentation, see [here](https://docs.pylonsproject.org/projects/waitress/en/stable/).

If nothing is included, then runs on `http://0.0.0.0:8080`

May raise:

- See [here](https://flask-restful.readthedocs.io/en/latest/api.html#flask_restful.Api.add_resource)
- See [here](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html)

#### RestApiHandler.flask_obj

Getter:  
Gets the `Flask` object that is the backend of the endpoints and the server.

This can be used to modify and customize the `Flask` object in this class.

#### RestApiHandler.api_obj

Getter:  
Gets the `flask_restful` API object that handles parsing the classes.

This can be used to modify and customize the `Api` object in this class.

---

### com_server.ConnectionResource

A custom resource object that is built to be used with `RestApiHandler`.

This class is to be extended and used like the `Resource` class.
Have `get()`, `post()`, and other methods for the types of responses you need.

---

### com_server.Builtins

Contains implementations of endpoints that call methods of `Connection` object

Endpoints include:

- `/send` (POST): Send something through the serial port using `Connection.send()` with parameters in request; equivalent to `Connection.send(...)`
- `/receive` (GET, POST): Respond with the most recent received string from the serial port; equivalent to `Connection.receive_str(...)`
- `/receive/all` (GET, POST): Returns the entire receive queue; equivalent to `Connection.get_all_rcv_str(...)`
- `/get` (GET, POST): Respond with the first string from serial port after request; equivalent to `Connection.get(str, ...)`
- `/send/get_first` (POST): Responds with the first string response from the serial port after sending data, with data and parameters in request; equivalent to `Connection.get_first_response(is_bytes=False, ...)`
- `/get/wait` (POST): Waits until connection receives string data given in request; different response for success and failure; equivalent to `Connection.wait_for_response(...)`
- `/send/get` (POST): Continues sending something until connection receives data given in request; different response for success and failure; equivalent to `Connection.send_for_response(...)`
- `/connected` (GET): Indicates if the serial port is currently connected or not
- `/list_ports` (GET): Lists all available Serial ports

The above endpoints will not be available if the class is used.

#### Builtins.\_\_init\_\_()

```py
def __init__(handler)
```

Constructor for class that contains builtin endpoints

Adds endpoints to given `RestApiHandler` class;
uses `Connection` object within the class to handle
serial data.

Example usage:
```py
conn = com_server.Connection(...)
handler = com_server.RestApiHandler(conn)
builtins = com_server.Builtins(handler)

handler.run() # runs the server
```

Parameters:

- `api`: The `RestApiHandler` class that this class should wrap around

---

## Exceptions

### com_server.ConnectException  

This exception is raised whenever a user tries to do an operation with the `Connection` class while it is disconnected, but the operation requires it to be connected, or vice versa.

### com_server.EndpointExistsException

This exception is raised if the user tries to add a route to the `RestApiHandler` that already exists.
