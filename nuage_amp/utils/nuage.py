'''

Created on Jun 17, 2013



@author: Carl Verge

@copyright: Alcatel-Lucent 2013

@version: 1.0R1

'''


from httplib import HTTPSConnection

from base64 import urlsafe_b64encode

from json import loads, dumps

from pprint import pformat


class NuageHTTPError(Exception):

    """

    An exception indicating an error during an API call.

    Contains the HTTP error code and message body of the response.

    """

    def __init__(self, status, reason, body=""):

        self.status = status

        self.reason = reason

        self.body = body

    def __str__(self):

        if self.body:

            return "%d %s\n%s" % (self.status, self.reason, self.body)

        else:

            return "%d %s" % (self.status, self.reason)

    def __repr__(self):

        return str(self)


class NuageResponse(object):

    """

    An object representing a response from the VSD ReST API.

    Contains the returned attributes and methods to manipulate the result.

    """

    def __init__(self, http_response):
        """

        @param http_response: The httpresponse object from the httpconnection.

        """

        status, reason, body = http_response.status, http_response.reason, http_response.read()

        if status < 200 or status >= 300:

            raise NuageHTTPError(status, reason, body)

        self.count = http_response.getheader('X-Nuage-Count', None)

        self.page = http_response.getheader('X-Nuage-Page', None)

        self.pagesize = http_response.getheader('X-Nuage-PageSize', None)

        self.filter = http_response.getheader('X-Nuage-Filter', None)

        self.filter_type = http_response.getheader('X-Nuage-FilterType', None)

        self.orderby = http_response.getheader('X-Nuage-OrderBy', None)

        self.status = status

        self.reason = reason

        self.body = body

        self.obj_repr = loads(self.body) if body else []

    def __str__(self):

        return self.pretty_print()

    def __repr__(self):

        return self.body

    def obj(self):
        """

        Returns a python object (usually a list of dictionaries) from the response JSON.

        @return: A python object (usually a list of dictionaries) from the response JSON.

        """

        return self.obj_repr

    def pretty_print(self):
        """

        Returns a human readable string of the JSON response.

        @return: A human readable string of the JSON response.

        """

        return pformat(self.obj_repr)

    def id(self, name=None):
        """

        Returns the ID of the object in the response, optionally searches for the object with

        the specified name (returns first object with matching name).

        @param name: The name to look for.

        @return: The ID of the first matching object as a string.

        @raise KeyError: If no object with an ID or matching the name is found.

        """

        if name:

            for dct in self.obj_repr:

                try:

                    if dct["name"] == name:
                        return dct["ID"]

                except KeyError:

                    continue

            raise KeyError("No object with name %s" % name)

        else:

            try:

                return self.obj_repr[0]["ID"]

            except KeyError, IndexError:

                raise KeyError("No object in response.")


class NuageConnection(object):

    '''

    An object representing a connection with a VSD ReST API. Only supports JSON.



    The NuageConnection will take care of authentication, setting correct headers, and JSON serialization.

    '''

    NUAGE_URLBASE = "/nuage/api"

    def __init__(self, hostname, enterprise="csp", username="csproot", password="csproot", version="v1_0", port=8443, debuglevel=0):
        '''

        Constructor



        @bug: Needs to check if API key is expired and re-acquire it.

        '''

        self._settings = locals().copy()

        self.me = None

        self._get_api_key()

    def get(self, url, filtertext=None, filtertype=None, page=None, orderby=None, user=None):
        """

        Perform a GET request on the VSD to list objects.

        @param url: The URL to GET, example: "enterprises"

        @param filter:

        @param filtertype:

        @param page:

        @param orderby:

        @param user: the proxy user to execute the command as (X-Nuage-ProxyUser)

        @return: A NuageResponse object.

        @raise NuageHTTPException: If there is an error in processing the request.

        """

        headers = {}

        if filtertype:
            headers['X-Nuage-FilterType'] = filtertype

        if filtertext:
            headers['X-Nuage-Filter'] = filtertext

        if page:
            headers['X-Nuage-Page'] = page

        if orderby:
            headers['X-Nuage-OrderBy'] = orderby

        if user:
            headers['X-Nuage-ProxyUser'] = user

        return self._do_http_request("GET", url, headers=headers)

    def post(self, url, body, user=None):
        """

        Perform a POST request on the VSD to create new objects.

        @param url: The URL to POST, example: "enterprises"

        @param body: A JSON string with the body of the POST.

        @param user: the proxy user to execute the command as (X-Nuage-ProxyUser)

        @return: A NuageResponse object.

        @raise NuageHTTPException: If there is an error in processing the request.

        """

        headers = {}

        if user:
            headers['X-Nuage-ProxyUser'] = user

        # Convert it to a JSON string if required.

        if type(body) != str:

            body = dumps(body)

        return self._do_http_request("POST", url, body, headers=headers)

    def put(self, url, body, user=None):
        """

        Perform a PUT request on the VSD to update objects.

        @param url: The URL to PUT, example: "enterprises/ENTERPRISE_ID"

        @param body: A JSON string with the body of the PUT.

        @param user: the proxy user to execute the command as (X-Nuage-ProxyUser)

        @return: A NuageResponse object.

        @raise NuageHTTPException: If there is an error in processing the request.

        """

        headers = {}

        if user:
            headers['X-Nuage-ProxyUser'] = user

        # Convert it to a JSON string if required.

        if type(body) != str:

            body = dumps(body)
        return self._do_http_request("PUT", url, body, headers=headers)

    def delete(self, url, user=None):
        """

        Perform a DELETE request on the VSD to delete objects.

        @param url: The URL to DELETE, example: "enterprises/ENTERPRISE_ID"

        @param user: the proxy user to execute the command as (X-Nuage-ProxyUser)

        @return: A NuageResponse object.

        @raise NuageHTTPException: If there is an error in processing the request.

        """

        headers = {}

        if user:
            headers['X-Nuage-ProxyUser'] = user

        return self._do_http_request("DELETE", url, headers=headers)

    def process_events(self, callback=None, *args, **kwargs):
        """

        Process PUSH events from the server (blocking).

        This method will long poll the server for events, and call the supplied callback

        with the NuageResponse and any args/kwargs provided. If no callback is given, it

        will print the events. This method will not miss events event if another is received while

        an event is being processed. This function does not return.



        @param callback: The function to call when an event is receieved. See _default_event_callback for an example.

        @param *args: Passed along to the callback function

        @param **kwargs: Passed along to the callback function.

        @return: Does not return.

        @raise NuageHTTPException: If there is an error polling for events.

        @raise: The callback may raise any exception.

        @warning: Does not lock the connection -- must not modify shared objected in the NuageConnection.

        """

        last_uuid = ""

        if not callback:

            callback = NuageConnection._default_event_callback

        while True:

            resp = self.get("events?uuid=%s" % last_uuid)

            last_uuid = resp.obj()["uuid"]

            callback(resp, *args, **kwargs)

    # Private methods

    @staticmethod
    def _default_event_callback(nuage_response, *args, **kwargs):

        print "Received Push Event:"

        print "Called with args:"

        for arg in args:
            print arg

        for kw in kwargs:
            print kw

        print nuage_response

    def _do_http_request(self, method, url, body=None, headers=None):
        """

        Wrapper for HTTP requests. Builds the authentication headers.

        Currently not reliable, that must be handled by the caller.

        """

        conn = self._get_https_conn()

        if self._settings["debuglevel"] != 0:

            conn.set_debuglevel(self._settings["debuglevel"])

        request_headers = self._get_headers()

        if headers:
            request_headers.update(headers)

        conn.request(method, "%s/%s/%s" % (self.NUAGE_URLBASE, self._settings["version"], url), body=body, headers=request_headers)

        response = conn.getresponse()

        result = NuageResponse(response)

        conn.close()

        return result

    def _get_api_key(self):
        """

        Authenticate with the password and get the API key.

        """

        self._settings["auth_string"] = "Basic %s" % urlsafe_b64encode("%s:%s" % (self._settings["username"], self._settings["password"]))

        self.me = self.get("me").obj()[0]

        self._settings["auth_string"] = "Basic %s" % urlsafe_b64encode("%s:%s" % (self._settings["username"], self.me["APIKey"]))

    def _get_https_conn(self):

        return HTTPSConnection(self._settings["hostname"], self._settings["port"])

    def _get_headers(self):

        return {

            "Content-Type": "application/json",

            "Authorization": self._settings["auth_string"],

            "X-Nuage-Organization": self._settings["enterprise"]

        }
