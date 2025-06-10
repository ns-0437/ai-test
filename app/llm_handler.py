import subprocess

def query_local_llm(prompt: str, model_name: str = "llama3") -> str:
    """
    Sends a prompt to the local LLM model via Ollama and returns the response.

    Args:
        prompt (str): The input prompt to send to the LLM.
        model_name (str): The name of the model to use (default is 'llama3').

    Returns:
        str: The response from the LLM or an error message.
    """
    try:
        result = subprocess.run(
            ["ollama", "run", model_name],
            input=prompt,
            capture_output=True,
            text=True,           # ✅ No need to manually encode/decode
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"[LLM Error]: {e.stderr.strip()}"
