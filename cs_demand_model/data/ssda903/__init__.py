from pathlib import Path

import pandas as pd

from cs_demand_model.datastore import TableType


class Episodes:
    fields = [
        "CHILD",
        "DECOM",
        "RNE",
        "LS",
        "CIN",
        "PLACE",
        "PLACE_PROVIDER",
        "DEC",
        "REC",
        "REASON_PLACE_CHANGE",
        "HOME_POST",
        "PL_POST",
    ]


class Header:
    fields = ["CHILD", "SEX", "DOB", "ETHNIC", "UPN", "MOTHER", "MC_DOB"]


class Reviews:
    fields = ["CHILD", "DOB", "REVIEW", "REVIEW_CODE"]


class OC2:
    fields = [
        "CHILD",
        "DOB",
        "SDQ_SCORE",
        "SDQ_REASON",
        "CONVICTED",
        "HEALTH_CHECK",
        "IMMUNISATIONS",
        "TEETH_CHECK",
        "HEALTH_ASSESSMENT",
        "SUBSTANCE_MISUSE",
        "INTERVENTION_RECEIVED",
        "INTERVENTION_OFFERED",
    ]


class OC3:
    fields = ["CHILD", "DOB", "IN_TOUCH", "ACTIV", "ACCOM"]


class PreviousPermanence:
    fields = ["CHILD", "DOB", "PREV_PERM", "LA_PERM", "DATE_PERM"]


class UASC:
    fields = ["CHILD", "SEX", "DOB", "DUC"]


class Missing:
    fields = ["CHILD", "DOB", "MISSING", "MIS_START", "MIS_END"]


class SSDA903TableType(TableType):
    """
    A class to define the type of table.
    """

    HEADER = Header()
    EPISODES = Episodes()
    REVIEWS = Reviews()
    OC2 = OC2()
    OC3 = OC3()
    PREVIOUS_PERMANENCE = PreviousPermanence()
    UASC = UASC()
    MISSING = Missing()
