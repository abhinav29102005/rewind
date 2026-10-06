from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    APPROVER = "approver"
    VIEWER = "viewer"
