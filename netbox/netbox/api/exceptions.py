from rest_framework.exceptions import APIException


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, please try again later."


class SerializerNotFound(Exception):
    pass


class GraphQLTypeNotFound(Exception):
    pass


class QuerySetNotOrdered(Exception):
    pass
