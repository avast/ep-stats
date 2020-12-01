import pytz


def get_utc_timestamp(dt):
    mytz = pytz.timezone("UTC")
    return mytz.normalize(mytz.localize(dt, is_dst=False))
