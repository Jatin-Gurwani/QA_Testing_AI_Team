from app.crew import QACrew
import os
from dotenv import load_dotenv
from openinference.instrumentation.crewai import CrewAIInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor
from langfuse import get_client
load_dotenv()

langfuse_available = False
try:
    langfuse = get_client()
    if langfuse.auth_check():
        print("✅ Langfuse client is authenticated and ready!")
        langfuse_available = True
        # Initialize LLM provider instrumentations BEFORE creating the crew
        LiteLLMInstrumentor().instrument(skip_dep_check=True)
        GoogleGenAIInstrumentor().instrument(skip_dep_check=True)
        OpenAIInstrumentor().instrument(skip_dep_check=True)
        CrewAIInstrumentor().instrument(skip_dep_check=True)

    else:
        print("⚠️  Langfuse authentication failed. Continuing without Langfuse.")
except Exception as e:
    print(f"⚠️  Langfuse not available ({e}). Continuing without tracing.")



def run_crew(qacrew, repo_url, change_request):
    """Execute the crew and print results."""
    result = qacrew.kickoff(inputs={'repo_url': repo_url, 'user_request': change_request})
    print(result)
    print(result.token_usage)
    return result


def main():

        print("Hello from testing-crew-project!")
        repo_url = input('Enter your Github repo : \n')
        #repo_url="https://github.com/Jatin-Gurwani/NOTES_APP_FLASK.git"
        #repo_url ="D:/QA_Testing_AI_Team/outputs/Repo/NOTES_APP_FLASK"
        #os.environ["DEBUG"]="*"
        change_request = input("Enter your request :\n")
        task_dict = {"only_generation":["Repository Analysis","Test Strategy Planning","Test Code Generation"],
                     "run_testcase":["Repository Analysis","Test Strategy Planning","Test Code Generation","Test Environment Provisioning","Test Execution & Root Cause Analysis","QA Audit & Final Report"],
                     "both":[]}
        for tk in task_dict.keys():
            print(tk)
        task_type = input("select request type from above \n")


        if langfuse_available:
            try:
                LiteLLMInstrumentor().instrument(skip_dep_check=True)
                GoogleGenAIInstrumentor().instrument(skip_dep_check=True)
                OpenAIInstrumentor().instrument(skip_dep_check=True)
                CrewAIInstrumentor().instrument(skip_dep_check=True)
                qacrew = QACrew(repo_url).crew(tasks_name_list=task_dict.get(task_type,[]))
                with langfuse.start_as_current_observation(as_type="span", name="crewai-index-trace",input={"user_request":change_request,'repo_url':repo_url,'task_type':task_type}):
                    run_crew(qacrew, repo_url, change_request)
            except Exception as e:
                print(f"⚠️  Langfuse tracing failed during run ({e}). Running crew without tracing.")
                run_crew(qacrew, repo_url, change_request)
            finally:
                try:
                    langfuse.flush()
                except Exception:
                    pass  # flush failure is non-fatal; crew already ran
        else:
            print(task_dict.get(task_type,[]))
            qacrew = QACrew(repo_url).crew(tasks_name_list=task_dict.get(task_type,[]))
            run_crew(qacrew, repo_url, change_request)


if __name__ == "__main__":
    main()