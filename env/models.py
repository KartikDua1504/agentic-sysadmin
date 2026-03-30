"""
Data schemas defining the strict I/O contract for the Agentic Sysadmin framework.
Ensures that commands sent to Docker, and telemetry received from Docker, 
are strictly typed and easily serializable for LLM context windows.
"""

from pydantic import BaseModel, Field

class SysAdminAction(BaseModel):
    command: str = Field(..., description="The bash command to execute in the terminal.")

class SysAdminObservation(BaseModel):
    stdout: str = Field(..., description="Standard output from the command.")
    stderr: str = Field(..., description="Standard error from the command.")
    exit_code: int = Field(..., description="Exit code of the command (0 means success).")
    cwd: str = Field(..., description="Current working directory.")

class SysAdminReward(BaseModel):
    score: float = Field(..., description="Score from 0.0 to 1.0 representing task completion.")
    is_done: bool = Field(..., description="True if the task is fully resolved or failed.")
    reasoning: str = Field(..., description="Explanation of the current score/state.")


