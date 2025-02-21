"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import datetime

import requests
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ext_rt_key.models.db import Login
from ext_rt_key.rest.common import RoutsCommon

__all__ = ("VideoRouter",)


class VideoRouter(RoutsCommon):
    """Роутер для авторизации и видео трансляции"""

    def setup_routes(self) -> None:
        """Функция назначения маршрутов"""
        # Маршрут для HTML-страницы
        self._router.add_api_route("/video", self.video_page, methods=["GET"])

        # Маршрут для WebSocket соединения
        self._router.add_websocket_route("/ws/video", self.video_stream)

    async def video_page(self) -> HTMLResponse:
        """Отображение HTML-страницы с видео-плеером через WebSocket"""
        html_content = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>WebSocket Video Stream</title>
            </head>
            <body>
                <h1>Видео трансляция через WebSocket</h1>
                <video id="video" preload="none" autoplay="autoplay" controls height="100%" width="100%"></video>

                <script>
                    const videoElement = document.getElementById("video");
                    const mediaSource = new MediaSource();
                    const login = "79534499755";

                    videoElement.src = URL.createObjectURL(mediaSource);

                    mediaSource.addEventListener("sourceopen", () => {
                        const ws = new WebSocket("ws://localhost:8080/ws/video?login=79534499755");
                        const sourceBuffer = mediaSource.addSourceBuffer('video/mp4; codecs="avc1.64001e, mp4a.40.2"');

                        ws.binaryType = "arraybuffer";

                        ws.onmessage = function(event) {
                            console.log("Получен фрагмент видео");
                            const data = new Uint8Array(event.data);
                            if (!sourceBuffer.updating) {
                                sourceBuffer.appendBuffer(data);
                            }
                        };

                        ws.onopen = function() {
                            console.log("WebSocket соединение установлено.");
                        };

                        ws.onclose = function() {
                            console.log("WebSocket соединение закрыто.");
                        };

                        ws.onerror = function(error) {
                            console.error("WebSocket ошибка:", error);
                        };
                    });
                </script>

            </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    async def video_stream(self, websocket: WebSocket) -> None:
        """Обработка WebSocket соединения для видео трансляции"""
        await websocket.accept()
        login = websocket.query_params.get("login")

        self.logger.info(f"Подключение к WebSocket... с  {login}")

        with self.db_helper.sessionmanager() as session:
            user_model = session.query(Login).filter(Login.login == login).first()
            if not user_model:
                await websocket.close()
                return
            rt_key = user_model.token

        # Получение всех токенов к камере
        # Он тяжелый аккуратно надо, учитывая что их будет несоклько
        headers = {
            "Authorization": rt_key,
        }
        response = requests.get(
            "https://vc.key.rt.ru/api/v1/cameras?limit=100&offset=0",
            headers=headers,
        )

        response_data = response.json().get("data").get("items")

        id_ = response_data[10].get("id", {})
        streamer_token = response_data[10].get("streamer_token", {})

        ws_steam_url = f"wss://live-vdk4.camera.rt.ru/stream/{id_}/{int(datetime.datetime.now(datetime.UTC).timestamp())}.mp4?mp4-fragment-length=0.5&mp4-use-speed=0&mp4-afiller=1&token={streamer_token}"

        try:
            async with websockets.connect(ws_steam_url) as ws_client:
                while True:
                    data = await ws_client.recv()
                    if isinstance(data, bytes):
                        await websocket.send_bytes(data)
                    else:
                        self.logger.info(f"Получено текстовое сообщение: {data}")

                    # Для перемещении по времени
                    # await ws_client.send("seek: 1740148837")
        except WebSocketDisconnect:
            self.logger.info("WebSocket клиент отключился.")
        except Exception as e:
            self.logger.info(f"Ошибка при подключении к WebSocket: {e}")
        finally:
            await websocket.close()
            self.logger.info("Соединение закрыто")
