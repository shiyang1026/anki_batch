import os
import requests
import config
import sys
from concurrent.futures import ThreadPoolExecutor
from my_decorator import time_cal

ANKI_CONNECT_URL = "http://localhost:8765"
IMAGE_PATH = config.img_path
DECK_NAME = config.deck_name  # 牌组名


def invoke(session: requests.Session, action: str, params: dict) -> dict:
    """
    向anki connect 发送请求
    """
    return session.post(
        ANKI_CONNECT_URL, json={"action": action, "version": 6, "params": params}
    ).json()


def check_anki_connect(session: requests.Session) -> None:
    """
    检查与anki connect插件的连接
    """
    try:
        response = invoke(session, "version", {})
        if response.get("error") is None:
            print(f"AnkiConnect 连接正常，版本：{response['result']}")
        else:
            print(f"AnkiConnect 连接失败: {response['error']}")
    except requests.exceptions.ConnectionError:
        print("AnkiConnect 连接失败，请确保Anki正在运行并启用了AnkiConnect插件。")
        sys.exit(1)


def create_deck(session: requests.Session, deck_name: str) -> None:
    """
    创建新的牌组
    """
    result = invoke(session, "createDeck", {"deck": deck_name})
    print(
        f"成功创建牌组: {deck_name}"
        if result.get("error") is None
        else f"创建牌组失败: {result['error']}"
    )

    result = invoke(session, "modelNames", {})
    if result.get("error") is not None:
        print(f"获取模板名失败: {result['error']}")
        sys.exit(1)

    if "Basic" not in result["result"]:
        result = invoke(
            session,
            "createModel",
            {
                "modelName": "Basic",
                "inOrderFields": ["Front", "Back"],
                "css": """
                .card {
                    font-family: arial;
                    font-size: 20px;
                    text-align: center;
                    color: black;
                    background-color: white;
                }
                """,
                "cardTemplates": [
                    {
                        "Name": "Card 1",
                        "Front": "{{Front}}",
                        "Back": "{{FrontSide}}<hr id='answer'>{{Back}}",
                    }
                ],
            },
        )
        print(
            "成功创建模板: Basic"
            if result.get("error") is None
            else f"创建模板失败: {result['error']}"
        )


def add_note_to_anki(
    session: requests.Session, deck_name: str, image_file_name: str
) -> None:
    note = {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {
            "Front": f"<img src='{image_file_name}'>",  # 只显示图片作为问题
            "Back": "",  # 答案为空
        },
        "options": {"allowDuplicate": False},
        "tags": ["confusing_points"],
        "picture": [
            {
                "filename": image_file_name,
                "path": os.path.join(IMAGE_PATH, image_file_name),
                "fields": ["Front"],  # 图片应用于卡片的正面
            }
        ],
    }
    result = invoke(session, "addNote", {"note": note})
    if result.get("error") is None:
        print(f"成功添加卡片: {image_file_name}")
    else:
        print(f"添加卡片失败: {result['error']}")


def import_image_to_anki(
    session: requests.Session, deck_name: str, image_directory: str
):
    """
    导入图片到anki牌组
    """
    with ThreadPoolExecutor() as executor:
        futures = []
        try:
            for image_file_name in os.listdir(image_directory):
                if image_file_name.endswith(".jpg") or image_file_name.endswith(".png"):
                    futures.append(
                        executor.submit(
                            add_note_to_anki, session, deck_name, image_file_name
                        )
                    )
            for future in futures:
                future.result()
        except OSError as e:
            print(f"读取目录时出错: {e}")
            sys.exit(1)


@time_cal
def main() -> None:
    with requests.Session() as session:
        check_anki_connect(session)
        create_deck(session, DECK_NAME)
        import_image_to_anki(session, DECK_NAME, IMAGE_PATH)


if __name__ == "__main__":
    main()
