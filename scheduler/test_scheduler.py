import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scheduler.scheduler import PriorityScheduler

class TestPriorityScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = PriorityScheduler()
        
    def test_node_ready_check(self):
        mock_node = MagicMock()
        mock_condition = MagicMock()
        mock_condition.type = "Ready"
        mock_condition.status = "True"
        mock_node.status.conditions = [mock_condition]
        
        self.assertTrue(self.scheduler.is_node_ready(mock_node))

if __name__ == '__main__':
    unittest.main()
