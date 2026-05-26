"""
Judge verdict enum values. Kept in a separate module to avoid circular imports
between app.core and app.prompts (agent_prompt imports verdict_enums from app.core).
"""

pre_execution_verdict_enums = [
    'SAFE',
    'UNSAFE_CODE',
    'UNEXECUTABLE_CODE',
    'MISMATCH_TOOL_INPUTS',
    'MISMATCH_INPUTS_INTENT',
]

post_execution_verdict_enums = [
    'SAFE',
    'DISCOVERY_PROMPT_INJECTION',
    'UNTRUSTED_TOOL_OUTPUT',
    'EXCEPTION',
]