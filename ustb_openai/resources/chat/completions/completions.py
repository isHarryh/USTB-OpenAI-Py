from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    Generator,
    Iterable,
    Mapping,
    Optional,
    Union
)

import httpx_sse

if TYPE_CHECKING:
    from ...._client import USTBOpenAI
    from ..chat import Chat

from ...._utils.form_request_builder import FormRequestBody
from ...._utils.openai_stream_adaptor import OpenAIStreamAdapter
from ....types.chat import ChatCompletion


class Completions:
    _API_COMPOSE_CHAT = "/site/ai/compose_chat"

    _chat: Chat
    _client: USTBOpenAI

    def __init__(self, chat: Chat) -> None:
        self._client = chat._client

    def create(
        self,
        *,
        messages: Iterable[Mapping[str, str]],
        model: str,
        stream: Optional[bool] = None,
        **kwargs_ignored
    ) -> Union[ChatCompletion, Generator[ChatCompletion, Any, None]]:
        """Creates a new chat completion request.

        :param messages: The iterable of message dictionaries representing conversation history,
            each message dictionary in which must contain a `role` field and a `content` field;
        :param model: The identifier for the AI model to use;
        :param stream: If `True`, returns response chunks via generator,
            otherwise, returns complete response after full processing;
        :param kwargs_ignored: Additional keyword arguments are silently ignored;
        :rtype: Union[ChatCompletion, Generator];
        :returns: A generator or a full `ChatCompletion`, depending on the `stream` argument;
        """
        data = {
            "content": "",
            "history": [],
            "compose_id": 3,
            "deep_search": 1,
            "model_name": model,
            "internet_search": 2
        }
        for m in messages:
            if "role" not in m or "content" not in m:
                raise ValueError("Role and content are required")
            if m["role"] not in ("user", "system"):
                raise ValueError(f"Unknown role: {m['role']}")
            if not data["content"]:
                data["content"] = ("(system) " if m["role"] == "system" else "") + m["content"]
            else:
                data["history"].append({
                    "role": m["role"],
                    "content": m["content"]
                })

        body = FormRequestBody(data)
        headers = self._client._client.headers.copy()
        headers["Content-Type"] = body.get_content_type()
        generator = OpenAIStreamAdapter.generate_obj(
            httpx_sse.connect_sse(
                self._client._client,
                "POST",
                Completions._API_COMPOSE_CHAT,
                content=body.get_content(),
                headers=headers
            )
        )

        if stream:
            return generator
        else:
            rst = ChatCompletion()
            for obj in generator:
                rst.choices[0].message.content += obj.choices[0].delta.content
            rst.choices[0].finish_reason = "stop"
            return rst
