from app.crew import QACrew
import os
def main():
    try:
        
        print("Hello from testing-crew-project!")
        repo_url ="https://github.com/Jatin-Gurwani/NOTES_APP_FLASK.git"
        os.environ["GITHUB_PAT"] = str(input('Enter github token. it will directly saved in os environment later will deleted after  exceution'))
        change_request = str(input("Enter your request :\n"))
        results = QACrew().crew().kickoff(inputs={'repo_url':repo_url,'user_request':change_request,'env_vars':""})
        print(results)
        print(results.token_usage)
    except Exception as e:
        pass
    finally:
        os.environ.pop("GITHUB_PAT", None)
    
    


if __name__ == "__main__":
    main()
