from enum import Enum

class VALIDATION_FLAGS(Enum):
    DUPLICATE_ADDRESS = 1
    ADDRESS_OUTSIDE_RANGE = 2
    INVALID_PARITY = 3
    DUPLICATE_NENA_IDENTIFIER = 4
    MISSING_NENA_IDENTIFIER = 5
    INVALID_STREET_NAME = 6
    INVALID_MSAG = 7
    INVALID_INCORPORATED_MUNICIPALITY = 8
    INVALID_UNINCORPORATED_MUNICIPALITY = 9
    INVALID_COUNTY = 10
    INVALID_ESN = 11
    