import argparse
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from embedding_func import get_embedding_function


# path to the local database to fetch information that is populated by running update_database.py
DB_PATH = "database"

# prompt feeding the model to get desired response, can modify for better results, context is fetch from database, and question is user input
PROMPT_TEMPLATE = """
You are an informational agent dedicated to educating users about the Ogiek community. Given the most relevant documentations and a question either in English or Swahili from the user, 
you must answer the question in English if asked in English, in Swahili if asked in Swahili. Your answer should be short, no more than 190 characters. If a question is asked that does not relate to the documentation given,
tell the users you can only answer on what you are trained for.

Here are the documentations:
 
{context}
 
---
 
Here  is the question asked by the user: {question}

AGAIN, THE MOST IMPORTANT THINGS ARE: ANSWER IN LESS THAN 190 CHARACTERS, IN SWAHILI IF THE QUESTION IS IN SWAHILI, and only give answer derived from the source.
"""


def main():
    # grab query for chatbot from terminal
    # usage: query_data.py "Insert the question here"
    parser = argparse.ArgumentParser()
    parser.add_argument("user_question", type=str, help="The query text.")
    args = parser.parse_args()
    user_question = args.user_question

    # Query the vector database
    query_rag(user_question)

# make the function for other files to call as well as call from terminal with main()
def query_rag(user_question: str):

    # can change the model here
    MODEL_NAME = "mannix/llamax3-8b-alpaca"

    # prepare the DB.
    embedding_function = get_embedding_function(input_model= MODEL_NAME)
    db = Chroma(persist_directory=DB_PATH, embedding_function=embedding_function)

    # search the DB.
    results = db.similarity_search_with_score(user_question, k=3) # Modify this to grab more context per prompt, might hurt if too high or too low

    # make sure response is relevant
    if len(results) == 0 or results [0][1] < 0.7:
        print("Unable to find matching results.")
        return

    # combining system prompt and user query
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=user_question)

    # give the model the full prompt
    ollama_model = OllamaLLM(model = MODEL_NAME)
    model_response = ollama_model.invoke(prompt)

    # grab the sources and add it to the formatted response for traceability
    sources = [doc.metadata.get("id", None) for doc, _score in results]
    formatted_response = f"\n{MODEL_NAME}:{model_response}\n\nSources: {sources}"
    print(formatted_response)

    # return the model response
    return model_response


if __name__ == "__main__":
    main()  