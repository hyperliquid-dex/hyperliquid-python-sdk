class Error(Exception):
    pass


class ClientError(Error):
    def __init__(self, status_code, error_code, error_message, header, error_data=None):
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message
        self.header = header
        self.error_data = error_data


class ServerError(Error):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
