from fastapi import Request


def ok(request: Request, data):
    return {"success": True, "data": data, "request_id": getattr(request.state, "request_id", None)}

