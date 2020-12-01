import typing
import json as json
from fastapi.responses import JSONResponse


class DataScienceJsonResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        # we need to use default json implementation and explicitly encode in utf-8 to
        # preserver `np.nan` and `np.inf` values.
        return json.dumps(content).encode("utf-8")
