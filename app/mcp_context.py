from questions import QUESTION_TEMPLATES
from logging_config import get_logger
logger = get_logger("mcp_context")

def build_mcp_context(repo_name: str, role: str, retrieved_chunks: list[str]) -> dict:
    """
    Constructs a structured context object (MCP-style) to feed into an LLM.

    Args:
        repo_name (str): Name of the repository
        role (str): User role (e.g., programmer, ceo)
        retrieved_chunks (list[str]): Retrieved code/documentation chunks

    Returns:
        dict: A standardized context object for LLM prompt rendering
    """
    role = role.lower()

    context = {
        "system_instruction": (
            "You are a technical writing assistant tasked with analyzing source code and writing a detailed report "
            "tailored to the specified role."
        ),
        "repo_name": repo_name,
        "role": role,
        "questions": QUESTION_TEMPLATES.get(role, []),
        "retrieved_chunks": retrieved_chunks,
        "output_format": "Markdown with structured sections and an Executive Summary"
    }

    return context

def render_prompt(context: dict) -> str:
        """
        Renders the final prompt string from the MCP context dictionary.

        Args:
            context (dict): A structured context object containing instructions, questions, and code chunks.

        Returns:
            str: Final formatted prompt to send to the LLM.
        """

        prompt = f"""System Instruction:
    {context['system_instruction']}
    
    Repository: {context['repo_name']}
    Role: {context['role'].title()}
    
    Executive Summary:
    Write 3–5 sentences summarizing the project’s purpose, strengths, and technical characteristics.
    
    Answer the following questions using only the retrieved content. Avoid hallucinating.
    
    """

        # Add Questions
        prompt += "Questions:\n"
        for i, q in enumerate(context.get("questions", []), start=1):
            prompt += f"{i}. {q}\n"

        # Add Retrieved Chunks
        prompt += "\nRetrieved Context:\n"
        for chunk in context.get("retrieved_chunks", []):
            prompt += f"\n---\n{chunk}\n"

        # Specify output format
        prompt += f"""\n
    Output Format:
    {context.get('output_format', 'Markdown with headings, including an Executive Summary and narrative answers.')}
    """

        return prompt

def validate_context(context: dict) -> bool:
    """
    Validates the MCP context object before rendering or sending to an LLM.

    Args:
        context (dict): The MCP context dictionary.

    Returns:
        bool: True if valid, raises ValueError if not.
    """
    logger.info("Validating MCP context...")

    required_fields = [
        "system_instruction",
        "repo_name",
        "role",
        "questions",
        "retrieved_chunks",
        "output_format"
    ]

    missing = [field for field in required_fields if field not in context or not context[field]]

    if missing:
        logger.warning(f"MCP context is invalid. Missing fields: {missing}")
        raise ValueError(f"Invalid MCP context. Missing or empty fields: {missing}")

    logger.info("MCP context validated successfully.")
    return True