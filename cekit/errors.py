class CekitError(Exception):

    def __init__(self, message, *args,  **kwargs):
        super(CekitError, self).__init__(message, *args, **kwargs)
        self.message = message
