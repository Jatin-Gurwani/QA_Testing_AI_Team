from crewai import Agent as CrewAgent, Task, Crew, Process,LLM
from crewai.tools import tool as crewai_tool
from crewai.mcp import MCPServerStdio,MCPServerSSE,MCPServerHTTP
from crewai.project import CrewBase, agent, task, crew,before_kickoff,after_kickoff
import os
import sys
import dotenv
from typing import List
import git
from crewai.agents.agent_builder.base_agent import BaseAgent

output_dir = os.path.join(os.getcwd(), "outputs")
os.makedirs(output_dir, exist_ok=True)
repo_path= os.path.join(output_dir, "Repo")
os.makedirs(repo_path, exist_ok=True)
dotenv.load_dotenv('.\config\.env')

llm= LLM(model=os.getenv('MODEL','gemini/gemini-3.1-flash-lite'))   

mcp_env = os.environ.copy()
@CrewBase
class QACrew:
    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config = "../config/agents.yaml"
    tasks_config = "../config/tasks.yaml"
    
    def _get_git_mcp(self): 
        GITHUB_PAT=os.getenv('GITHUB_PAT',"-")
        print(GITHUB_PAT)
        return MCPServerHTTP(url='https://api.githubcopilot.com/mcp/',headers={"Authorization": f"Bearer {GITHUB_PAT}","X-MCP-Readonly": "true"},env=mcp_env,cache_tools_list=True)
        #MCPServerStdio(command="uvx",args=["mcp-server-git", "--repository", self.git_url],env=mcp_env,cache_tools_list=True,timeout=60,)

    if sys.platform == "win32":
        file_mcp = MCPServerStdio(
            command="cmd",
            args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", output_dir],
            cache_tools_list=True,
            timeout=60,
        )
    else:
        file_mcp = MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", output_dir],
            cache_tools_list=True,
            timeout=60,
        )
    
    @agent
    def repository_analyst(self) -> CrewAgent:
        return CrewAgent(config=self.agents_config["repository_analyst"],verbose=True,mcps=[self.file_mcp,self._get_git_mcp()],llm=llm)
    
    @agent
    def test_strategy_planner(self) -> CrewAgent:
        return CrewAgent(config=self.agents_config['test_strategy_planner'],verbose=True,mcps=[self.file_mcp],llm=llm)
    @agent
    def test_writer_agent(self) -> CrewAgent:
        return CrewAgent(config=self.agents_config['test_writer_agent'],verbose=True,mcps=[self.file_mcp],llm=llm)
    
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

    # ── Crew ──────────────────────────────────────────────────
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            #manager_agent=self.qa_manager(),
            process=Process.sequential,
            verbose=True,
            planning=True,
            planning_llm=llm
            
        )


