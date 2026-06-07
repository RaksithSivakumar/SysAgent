import unittest
from unittest.mock import patch, MagicMock
from sysagent.agent.core import GeminiAgent
from sysagent.config import Config

class TestAgent(unittest.TestCase):

    @patch("sysagent.agent.core.get_api_key")
    def test_agent_missing_api_key(self, mock_get_key):
        mock_get_key.return_value = None
        
        agent = GeminiAgent()
        res_list = list(agent.agentic_loop("How much RAM is free?"))
        
        self.assertTrue(any("GEMINI_API_KEY" in chunk or "Setup required" in chunk for chunk in res_list))

    @patch("sysagent.agent.core.get_api_key")
    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_agent_tool_dispatch_in_loop(self, mock_configure, mock_gen_model, mock_get_key):
        mock_get_key.return_value = "fake_key_123"
        
        # Setup mocks for chat response
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_gen_model.return_value = mock_model
        mock_model.start_chat.return_value = mock_chat
        
        # Mock responses
        # 1. First response: Gemini requests get_cpu_info tool
        mock_part_tool = MagicMock()
        mock_part_tool.function_call.name = "get_cpu_info"
        mock_part_tool.function_call.args = {}
        
        # 2. Second response: Gemini returns final answer text
        mock_part_text = MagicMock()
        del mock_part_text.function_call # remove attribute to trigger text fallback
        mock_part_text.text = "You have 8 physical CPU cores."
        
        # Configure chat.send_message responses sequentially
        mock_response_tool = MagicMock()
        mock_response_tool.candidates = [MagicMock(content=MagicMock(parts=[mock_part_tool]))]
        
        mock_response_text = MagicMock()
        mock_response_text.candidates = [MagicMock(content=MagicMock(parts=[mock_part_text]))]
        
        mock_chat.send_message.side_effect = [mock_response_tool, mock_response_text]

        # Instantiating agent
        agent = GeminiAgent()
        
        # Register a mock cpu collector inside sandbox
        agent.sandbox.register_collector("get_cpu_info", lambda: {"physical_cores": 8})
        
        # Run agentic loop
        res_list = list(agent.agentic_loop("How many CPU cores do I have?"))
        
        # Assertions
        # Loop should have triggered call to get_cpu_info, yielded running message, and then the final answer.
        self.assertTrue(any("get_cpu_info" in chunk for chunk in res_list))
        self.assertTrue(any("8 physical CPU cores" in chunk for chunk in res_list))
        self.assertEqual(mock_chat.send_message.call_count, 2)

    def test_conversation_memory_history_export(self):
        from sysagent.agent.memory import ConversationMemory
        mock_chat = MagicMock()
        mock_msg = MagicMock(role="model")
        mock_part = MagicMock()
        mock_part.text = "Hello system user"
        mock_msg.parts = [mock_part]
        mock_chat.history = [mock_msg]

        memory = ConversationMemory(mock_chat)
        history = memory.export_chat_history()
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "agent")
        self.assertEqual(history[0]["text"], "Hello system user")

    @patch("sysagent.agent.memory._get_snapshots_dir")
    def test_snapshots_real_handling(self, mock_snap_dir):
        import os
        import tempfile
        import shutil
        from sysagent.agent.memory import save_snapshot, compare_snapshots, list_snapshots

        with tempfile.TemporaryDirectory() as tempdir:
            mock_snap_dir.return_value = tempdir
            
            data1 = {
                "get_cpu_info": {"usage_overall_pct": 10.0},
                "get_memory_info": {"ram_usage_pct": 40.0},
                "get_processes": {"top_cpu": [{"pid": 100, "name": "python", "cpu_pct": 5.0}], "top_memory": []},
                "get_firewall_info": {"listening_ports": [{"port": 80}]},
                "get_os_info": {"uptime_seconds": 1000}
            }
            data2 = {
                "get_cpu_info": {"usage_overall_pct": 15.0},
                "get_memory_info": {"ram_usage_pct": 45.0},
                "get_processes": {"top_cpu": [{"pid": 100, "name": "python", "cpu_pct": 5.0}, {"pid": 200, "name": "node", "cpu_pct": 10.0}], "top_memory": []},
                "get_firewall_info": {"listening_ports": [{"port": 80}, {"port": 443}]},
                "get_os_info": {"uptime_seconds": 2200}
            }

            path1 = save_snapshot(data1)
            path2 = save_snapshot(data2)
            
            self.assertTrue(os.path.exists(path1))
            self.assertTrue(os.path.exists(path2))

            snaps = list_snapshots()
            self.assertEqual(len(snaps), 2)

            diff = compare_snapshots(path1, path2)
            self.assertEqual(diff["cpu_usage_change_pct"], 5.0)
            self.assertEqual(diff["ram_usage_change_pct"], 5.0)
            self.assertIn("443", str(diff["new_exposed_ports"]))
            self.assertIn("node", str(diff["new_processes"]))
            self.assertIn("20m", diff["uptime_change_str"])

