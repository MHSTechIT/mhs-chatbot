from abc import ABC, abstractmethod

class IChatService(ABC):
    @abstractmethod
    async def ask_question(self, question: str) -> dict:
        """
        Process the user's question, check against restricted keywords,
        and generate a response from the vector database using the LLM.
        Must return a dict with 'answer' and 'type'.
        """
        pass
