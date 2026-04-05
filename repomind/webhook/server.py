from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from ..config import RepomindConfig
from ..utils.logging import get_logger
from .handlers.push import PushEventHandler
from .handlers.pr import PREventHandler

log = get_logger(__name__)


def create_app(config: RepomindConfig) -> FastAPI:
    app = FastAPI(title="repomind webhook", version="0.1.0")
    push_handler = PushEventHandler(config)
    pr_handler = PREventHandler(config)

    @app.post("/webhook/github")
    async def github_webhook(
        request: Request,
        x_github_event: str = Header(default=""),
        x_hub_signature_256: str = Header(default=""),
    ) -> JSONResponse:
        body = await request.body()

        # Validate HMAC-SHA256 signature
        if config.webhook.secret:
            expected = "sha256=" + hmac.new(
                config.webhook.secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, x_hub_signature_256):
                raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        event = x_github_event
        log.info("webhook_received", event=event)

        if event == "push":
            await push_handler.handle(payload)
        elif event == "pull_request":
            await pr_handler.handle(payload)
        else:
            log.debug("webhook_ignored", event=event)

        return JSONResponse({"status": "ok"})

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "repomind"})

    return app
