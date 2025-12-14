"""
A simple numpy based vector store for small datasets, storing and searching embeddings.
"""
from typing import Iterator
import numpy as np
import openai
import os
import pickle

# async_openai_client = openai.AsyncOpenAI(
#     api_key=os.getenv("OPENAI_API_KEY"),
# )

openai_client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


class EmbeddingComputer:

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        assert model in ["text-embedding-3-small", "text-embedding-3-medium", "text-embedding-ada-002"]
        self.model = model

    def get_embedding(self, text: str) -> list[float]:
        """Get the embedding of a single text."""
        response = openai_client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def get_embeddings(self, documents: list[str]) -> list[list[float]]:
        """Get the embeddings of multiple documents."""
        response = openai_client.embeddings.create(input=documents, model=self.model)
        return [embedding.embedding for embedding in response.data]


def _vector_search(
    query_embedding: np.ndarray, embeddings_matrix: np.ndarray, num_results: int = 9, result_offset: int = 0
) -> tuple[list[int], list[float]]:
    """Perform a vector search with a query embedding and an embedding matrix.

    Parameters
        query_embedding (np.ndarray): Embedding of the query to be searched.
        embeddings_matrix (np.ndarray): Matrix of embeddings representing the database.
        num_results (int): The number of results to return.
        result_offset (int): The number of results to skip.

    Returns
        A list of tuples with the index and the similarity score.
    """

    scores = np.dot(embeddings_matrix, query_embedding)
    top_indices = np.argsort(scores)[::-1][result_offset : result_offset + num_results]
    top_scores = scores[top_indices]
    assert len(top_indices) == len(top_scores)

    return list(top_indices), list(top_scores)


class VectorDB2:
    """
    Simple numpy based vector store for small datasets, storing and searching embeddings.
    """

    def __init__(self, documents: list[str], embedding_computer: EmbeddingComputer, batch_call: bool = True) -> None:
        """
        Initialize the VectorDB.

        Parameters:
            documents (list[str]): List of documents corresponding to the embeddings.
            embedding_computer (EmbeddingComputer): Object to compute embeddings from text.
            batch_call (bool): Whether to compute all embeddings in a single call.
        """
        self.documents: list[str] = documents
        self.embedding_computer: EmbeddingComputer = embedding_computer
        if batch_call:
            self.embedding_matrix = np.array(embedding_computer.get_embeddings(documents))
        else:
            self.embedding_matrix = np.array([embedding_computer.get_embedding(doc) for doc in documents])

    def search_with_embedding(
        self, query_embedding: list[float], num_results: int = 9, result_offset: int = 0
    ) -> Iterator[tuple[str, float]]:
        """Performs a vector search for a given query embedding.

        Parameters
            query_embedding (list[float]): Embedding of the query.
            num_results (int): The number of results to return.
            result_offset (int): The number of results to skip, for pagination.

        Returns
            (Iterator[tuple[str, float]]): Documents and similarity scores of the vector search.
        """

        indices, scores = _vector_search(
            np.array(query_embedding),
            embeddings_matrix=self.embedding_matrix,
            num_results=num_results,
            result_offset=result_offset,
        )
        result_docs = [self.documents[i] for i in indices]
        return zip(result_docs, scores)

    def search_with_query(
        self, query: str, num_results: int = 9, result_offset: int = 0
    ) -> Iterator[tuple[str, float]]:
        """Performs a vector search for a given query string.

        Parameters
            query (str): Query for which to perform search.
            num_results (int): The number of results to return.
            result_offset (int): The number of results to skip.

        Returns
            (Iterator[tuple[str, float]]): Documents and similarity scores of the vector search.
        """
        query_embedding = self.embedding_computer.get_embedding(query)
        return self.search_with_embedding(query_embedding, num_results=num_results, result_offset=result_offset)

    def store_to_disk(self, path: str) -> None:
        """Store the VectorDB to disk using pickle.

        Parameters
            path (str): Path to store the VectorDB.
        """
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load_from_disk(path: str) -> "VectorDB2":
        """Load the VectorDB from disk.

        Parameters
            path (str): Path to load the VectorDB.

        Returns
            (VectorDB2): The loaded VectorDB.
        """
        with open(path, "rb") as f:
            return pickle.load(f)


def main():
    import tempfile

    documents = [
        "The quick brown fox jumps over the lazy dog.",
        "Never gonna give you up, never gonna let you down.",
        "To be or not to be, that is the question.",
        "All that glitters is not gold.",
        "A journey of a thousand miles begins with a single step.",
        "An apple a day keeps the doctor away.",
        "The early bird catches the worm.",
    ]

    embedding_computer = EmbeddingComputer(model="text-embedding-3-small")
    vectordb = VectorDB2(documents, embedding_computer)

    query = "Give me a quote about an insect."
    results = vectordb.search_with_query(query)

    for doc, score in results:
        print(f"Document: {doc}, Score: {score}")

    print("Storing and loading from disk...")
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        vectordb.store_to_disk(f.name)
        vectordb_loaded = VectorDB2.load_from_disk(f.name)
        results_loaded = vectordb_loaded.search_with_query(query)
        for doc, score in results_loaded:
            print(f"Document: {doc}, Score: {score}")


if __name__ == "__main__":
    main()
