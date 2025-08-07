# Import the main classes and enums
from .MFRC522 import MFRC522, NTAGType
from .SimpleMFRC522 import SimpleMFRC522

# Make sure NTAGType is available at module level
__all__ = ['MFRC522', 'NTAGType', 'SimpleMFRC522']

name = "mfrc522"
