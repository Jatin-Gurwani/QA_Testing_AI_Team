from crewai import Agent as CrewAgent, Task, Crew, Process,LLM
from crewai.tools import tool as crewai_tool
from crewai_tools import FileWriterTool
from crewai.mcp import MCPServerStdio,MCPServerSSE,MCPServerHTTP
from crewai.mcp.filters import create_static_tool_filter
from crewai.project import CrewBase, agent, task, crew,before_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.agent.planning_config import PlanningConfig
from crewai.tasks import conditional_task,task_output
import os
import dotenv
from typing import List
from git import  Repo as Repo_init , exc as gitexc
from platform import system as pysys
from datetime import datetime

_PLATFORM = pysys()
dotenv.load_dotenv('.\config\.env')
print(os.getcwd())
os.environ["PYTHONUTF8"] = "1"   # Force UTF-8 encoding on Windows (fixes charmap errors in output_writer)
output_dir = os.getenv('OUTPUT_FOLDER',os.path.join(os.getcwd(), "outputs"))
os.makedirs(output_dir, exist_ok=True)
repo_path= os.getenv('REPO_FOLDER',os.path.join(output_dir,"repo"))
os.makedirs(repo_path, exist_ok=True)
fast_llm = LLM(model=os.getenv('FAST_MODEL', ''), temperature=0.2, timeout=60,max_tokens=230000)
strong_llm=LLM(model=os.getenv('STRONG_MODEL', ''), temperature=0.2, timeout=60)
nvidia_llm = LLM(
    model= f"openai/{os.getenv('NVIDIA_MODEL','')}",
    base_url='https://integrate.api.nvidia.com/v1',
    api_key=os.getenv('NVIDIA_NIM_API_KEY', ''),
    temperature=0.3,
    timeout=1200,
)

mcp_env = os.environ.copy()
output_writer= FileWriterTool(name='output_writer')


@CrewBase
class QACrew:
    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config = "../config/agents.yaml"
    tasks_config = "../config/tasks.yaml"
    _local_git =False
    _local_repo_path=""
    _repo_name =""


    def __init__(self,path:str):
        """ Path : local project path , remote public git url , local git repo path"""
        self._repo_name,self._local_repo_path,self._local_git= self._process_repo_url(path)
        return 
        
    def _process_repo_url(self, repo_url:str):
        """Process the repo URL to set git_url, repo_name, and local_repo_path."""
        _version_controlled = False
        _repo_name=_local_repo_path=""
        if str(repo_url).endswith(".git") and str(repo_url).startswith("http"):
            _repo_name = repo_url[:-4].split('/')[-1]
            _local_repo_path = os.path.join(repo_path, _repo_name)
            if not os.path.exists(_local_repo_path):
                Repo_init.clone_from(url=repo_url, to_path=_local_repo_path)
            _version_controlled = True
        else:
            try:
                _rev_git_check = Repo_init(repo_url).rev_parse
                _repo_name = repo_url.split('/')[-1] if '/' in repo_url else repo_url
                _local_repo_path = repo_url
                _version_controlled = True
            except gitexc.InvalidGitRepositoryError as e:
                _repo_name = repo_url.split('/')[-1] if '/' in repo_url else repo_url
                _local_repo_path = repo_url
            
        if _PLATFORM == "Windows" and _local_repo_path:
            _local_repo_path = _local_repo_path.replace("\\", "/")
        
        return _repo_name,_local_repo_path,_version_controlled
    
    @before_kickoff
    def input_validation(self, inputs):
        inputs['repo_name']=self._repo_name
        inputs['local_repo_path']=self._local_repo_path
        inputs['project_type']= "Version controlled" if self._local_git else "Non-Version controlled"
        inputs['output_dir']=output_dir
        current_time = datetime.now()
        inputs['exc_time'] = f"{current_time.month}-{current_time.day}-{current_time.hour}{current_time.minute}"
        print(inputs.keys())
        print(self._local_git)
            
        return inputs

    def _get_git_mcp(self):
        #return MCPServerHTTP(url='https://api.githubcopilot.com/mcp/',headers={"Authorization": f"Bearer {GITHUB_PAT}","X-MCP-Readonly": "true"},env=mcp_env,cache_tools_list=True)
        return MCPServerStdio(command="uvx",args=["mcp-server-git","--repository", self._local_repo_path,"-v"],env={'LOG_LEVEL':'DEBUG'},cache_tools_list=True,timeout=600,)

    def _get_file_mcp(self):
        if _PLATFORM == "Windows":
            file_mcp = MCPServerStdio(
                command="cmd",
                args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", output_dir,self._local_repo_path],
                cache_tools_list=True,
                tool_filter=create_static_tool_filter(blocked_tool_names=['write_file','edit_file','read_file']),
                timeout=600,
            )
        else:
            file_mcp = MCPServerStdio(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", output_dir,self._local_repo_path],
                cache_tools_list=True,
                tool_filter=create_static_tool_filter(blocked_tool_names=['write_file','edit_file','read_file']),
                timeout=600,
            )
        return file_mcp
    
    def _get_docker_mcp(self, filter:list=[]):
        if len(filter) <1 :
            return MCPServerHTTP(url="http://localhost:8000/local-docker/mcp/",streamable=False,cache_tools_list=True,timeout=6000 )
        else :
            return MCPServerHTTP(url="http://localhost:8000/local-docker/mcp/",
                                 cache_tools_list=True,
                                 streamable=False,
                                 timeout=6000,
                                 tool_filter=create_static_tool_filter(allowed_tool_names=filter) )

    
    
    @agent
    def repository_analyst(self) -> CrewAgent:
        mcps = [self._get_file_mcp()]
        if self._local_git:
            git_mcp = self._get_git_mcp()
            mcps.append(git_mcp)
        return CrewAgent(
            config=self.agents_config["repository_analyst"],
            verbose=True,
            tools=[output_writer],
            mcps=mcps,
            llm=fast_llm,
            #planning_config=PlanningConfig(reasoning_effort="medium"),
        )

    @agent
    def test_strategy_planner(self) -> CrewAgent:
        return CrewAgent(
            config=self.agents_config['test_strategy_planner'],
            verbose=True,
            mcps=[self._get_file_mcp()],
            tools=[output_writer],
            llm=strong_llm,
        )

    @agent
    def test_writer_agent(self) -> CrewAgent:
        return CrewAgent(
            config=self.agents_config['test_writer_agent'],
            verbose=True,
            mcps=[self._get_file_mcp()],
            tools=[output_writer],
            llm=strong_llm
        )
    
    @agent
    def sandbox_engineer(self)-> CrewAgent:
        return CrewAgent(
            config=self.agents_config['sandbox_engineer'],
            verbose=True,
            mcps=[self._get_file_mcp(),self._get_docker_mcp()],
            tools=[output_writer],
            llm=fast_llm
                         )
    @agent
    def senior_test_engineer(self)-> CrewAgent:
        return CrewAgent(
            config=self.agents_config['senior_test_engineer'],
            verbose=True,
            mcps=[self._get_file_mcp(),self._get_docker_mcp(filter=["get_container_logs","stop_and_remove_container","run_tests"])], #"exec_in_container"
            tools=[output_writer],
            llm=strong_llm
                         )
    @agent
    def qa_expert(self)-> CrewAgent:
        return CrewAgent(
            config=self.agents_config['qa_expert'],
            verbose=True,
            mcps=[self._get_file_mcp()],
            tools=[output_writer],
            llm=fast_llm
                         )
    
    

    # ── Tasks ─────────────────────────────────────────────────
    @task
    def repository_analysis_task(self) -> Task:
        return Task(config=self.tasks_config["repository_analysis_task"])

    @task
    def test_strategy_task(self) -> Task:
        return Task(config=self.tasks_config["test_strategy_task"])
    
    @task
    def test_generation_task(self) -> Task:
        return Task(config=self.tasks_config["test_generation_task"])
    
    @task
    def env_setup_task(self)-> Task :
        return Task(config=self.tasks_config["env_setup_task"])

    @task
    def test_execution_task(self) -> Task :
        return Task(config=self.tasks_config["test_execution_task"])

    @task
    def qa_audit_task(self) -> Task:
        return Task(config=self.tasks_config["qa_audit_task"])

    
    # ── Crew ──────────────────────────────────────────────────
    @crew
    def crew(self,tasks_name_list:list=[]) -> Crew:
        if tasks_name_list ==[]:
            return Crew(
                agents=self.agents,
                tasks=[self.tasks[0]],
                process=Process.sequential,
                verbose=True,
                max_rpm=12,
            )
        else:
            print([i.name for i in self.tasks])
            selected_tasks = [t for t in self.tasks if t.name in tasks_name_list]
            return Crew(
                agents=self.agents,
                tasks=selected_tasks,
                process=Process.sequential,
                verbose=True,
                max_rpm=12,
            )