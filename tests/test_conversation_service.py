import shutil
import unittest
import uuid
from datetime import datetime
from pathlib import Path

from services.conversation_service import (
    build_default_conversation_store,
    create_new_conversation,
    generate_conversation_title,
    get_conversation_by_id,
    load_conversation_store,
    save_conversation_store,
    set_current_conversation,
    update_conversation_messages,
)


class ConversationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests/.tmp") / f"conversation-{uuid.uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_default_conversation_store(self) -> None:
        store = build_default_conversation_store(now=datetime(2026, 4, 13, 18, 0, 0))
        self.assertEqual(len(store["conversations"]), 1)
        self.assertEqual(store["current_conversation_id"], store["conversations"][0]["id"])
        self.assertEqual(store["conversations"][0]["title"], "新对话")

    def test_generate_conversation_title_from_first_user_message(self) -> None:
        title = generate_conversation_title(
            [
                {"role": "assistant", "content": "你好"},
                {"role": "user", "content": "我最近总是失眠，白天犯困，应该怎么办？"},
            ]
        )
        self.assertEqual(title, "失眠调整")

    def test_generate_conversation_title_falls_back_to_trimmed_text(self) -> None:
        title = generate_conversation_title(
            [
                {"role": "assistant", "content": "你好"},
                {"role": "user", "content": "今天中午吃完饭后总觉得有一点点不舒服但是说不上来具体哪里不对"},
            ]
        )
        self.assertTrue(title.endswith("..."))
        self.assertLessEqual(len(title), 21)

    def test_update_conversation_messages_updates_title_and_content(self) -> None:
        store = build_default_conversation_store(now=datetime(2026, 4, 13, 18, 0, 0))
        conversation_id = store["current_conversation_id"]
        updated = update_conversation_messages(
            store,
            conversation_id,
            [
                {"role": "assistant", "content": "你好"},
                {"role": "user", "content": "我最近总是失眠，白天很困，怎么调整？"},
            ],
            now=datetime(2026, 4, 13, 18, 5, 0),
        )
        conversation = get_conversation_by_id(updated, conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation["title"], "失眠调整")
        self.assertEqual(len(conversation["messages"]), 2)
        self.assertEqual(conversation["updated_at"], "2026-04-13T18:05:00")

    def test_create_new_conversation_and_switch(self) -> None:
        store = build_default_conversation_store(now=datetime(2026, 4, 13, 18, 0, 0))
        created = create_new_conversation(store, now=datetime(2026, 4, 13, 18, 10, 0))
        self.assertEqual(len(created["conversations"]), 2)
        new_id = created["current_conversation_id"]
        switched = set_current_conversation(created, created["conversations"][-1]["id"])
        self.assertNotEqual(switched["current_conversation_id"], new_id)

    def test_save_and_load_conversation_store(self) -> None:
        store = build_default_conversation_store(now=datetime(2026, 4, 13, 18, 0, 0))
        conversation_id = store["current_conversation_id"]
        store = update_conversation_messages(
            store,
            conversation_id,
            [
                {"role": "assistant", "content": "你好"},
                {"role": "user", "content": "今天适合跑步吗？"},
                {"role": "assistant", "content": "如果天气不热，可以适量跑步。"},
            ],
            now=datetime(2026, 4, 13, 18, 20, 0),
        )
        saved = save_conversation_store(self.temp_dir, "alice", store)
        self.assertTrue(saved)

        loaded = load_conversation_store(self.temp_dir, "alice")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["current_conversation_id"], conversation_id)
        self.assertEqual(len(loaded["conversations"][0]["messages"]), 3)
