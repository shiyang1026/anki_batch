import os
import requests
import config
import sys
from concurrent.futures import ThreadPoolExecutor

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


def check_template(session: requests.Session, template_name: str) -> None:
    """
    检查anki中存不存在Baisc模板,不存在创建一个
    """

    result = invoke(session, "modelNames", {})
    if result.get("error") is not None:
        print(f"获取模板名失败: {result['error']}")
        sys.exit(1)

    if "Basic" in result["result"]:
        print(f"模板 {template_name} 已存在, 继续导入")
        return

    # 模板不存在, 创建模板
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
    导入图片到anki牌组, 单线程版本
    """
    try:
        for image_file_name in os.listdir(image_directory):
            if image_file_name.endswith(".jpg") or image_file_name.endswith(".png"):
                add_note_to_anki(session, deck_name, image_file_name)
    except OSError as e:
        print(f"读取目录时出错: {e}")
        sys.exit(1)


def import_image_to_anki_threadpool(
    session: requests.Session, deck_name: str, image_directory: str
):
    """
    导入图片到anki牌组, 线程池版本
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


def delete_deck(session: requests.Session, deck_name: str) -> None:
    """
    删除deck
    """
    result = invoke(
        session,
        "deleteDecks",
        {"decks": [deck_name], "cardsToo": "true"},
    )
    if result.get("error") is None:
        print("牌组删除成功")
    else:
        print("牌组删除失败")


def test1() -> None:
    with requests.Session() as session:
        check_anki_connect(session)
        create_deck(session, DECK_NAME)
        check_template(session, "Basic")
        import_image_to_anki(session, DECK_NAME, IMAGE_PATH)
        delete_deck(session, config.deck_name)


def test2() -> None:
    with requests.Session() as session:
        check_anki_connect(session)
        create_deck(session, DECK_NAME)
        check_template(session, "Basic")
        import_image_to_anki_threadpool(session, DECK_NAME, IMAGE_PATH)
        delete_deck(session, config.deck_name)


def tracer_main():
    """
    直观的感受Python多线程如何为IO密集型任务提速:
    > cd tracer
    > python tacer_main.py
    > vizviewer trace1.json
    > vizviewer trace2.json
    """
    from viztracer import VizTracer

    tracer = VizTracer()
    tracer.start()
    test1()
    tracer.stop()
    tracer.save(output_file="trace1.json")  # 单线程版本

    tracer2 = VizTracer()
    tracer2.start()
    test2()
    tracer2.stop()
    tracer2.save(output_file="trace2.json")  # 线程池版本


if __name__ == "__main__":
    tracer_main()
