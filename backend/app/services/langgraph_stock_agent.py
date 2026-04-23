from __future__ import annotations

from typing import Any, Callable, List

from langgraph.graph import END, START, StateGraph
from typing import TypedDict

from app.schemas import SkillRunStatus, SkillUsage, StructuredResult, UserProfile


SkillExecutor = Callable[[Any, UserProfile, str], tuple[StructuredResult, List[SkillUsage], str]]
ResultEnhancer = Callable[[Any, StructuredResult, UserProfile, str], StructuredResult]


class StockAgentState(TypedDict, total=False):
    route: Any
    profile: UserProfile
    user_message: str
    skill_executor: SkillExecutor
    result_enhancer: ResultEnhancer
    result: StructuredResult
    skills_used: List[SkillUsage]
    rewritten_query: str
    should_enhance: bool


class LangGraphStockAgent:
    runtime = "langgraph"
    name = "stock_skill_agent"

    def invoke(
        self,
        *,
        route: Any,
        profile: UserProfile,
        user_message: str,
        skill_executor: SkillExecutor,
        result_enhancer: ResultEnhancer,
    ) -> tuple[StructuredResult, List[SkillUsage], str]:
        graph = self._build_graph()
        final_state = graph.invoke(
            {
                "route": route,
                "profile": profile,
                "user_message": user_message,
                "skill_executor": skill_executor,
                "result_enhancer": result_enhancer,
            }
        )
        return (
            final_state["result"],
            final_state.get("skills_used", []),
            final_state.get("rewritten_query", ""),
        )

    def _build_graph(self):
        workflow = StateGraph(StockAgentState)
        workflow.add_node("call_skills", self._call_skills)
        workflow.add_node("llm_enhance", self._llm_enhance)
        workflow.add_edge(START, "call_skills")
        workflow.add_edge("call_skills", "llm_enhance")
        workflow.add_edge("llm_enhance", END)
        return workflow.compile()

    def _call_skills(self, state: StockAgentState) -> StockAgentState:
        result, skills_used, rewritten_query = state["skill_executor"](
            state["route"],
            state["profile"],
            state.get("user_message", ""),
        )
        should_enhance = any(skill.status == SkillRunStatus.SUCCESS for skill in skills_used)
        return {
            "result": result,
            "skills_used": skills_used,
            "rewritten_query": rewritten_query,
            "should_enhance": should_enhance,
        }

    def _llm_enhance(self, state: StockAgentState) -> StockAgentState:
        if not state.get("should_enhance"):
            return {"result": state["result"]}
        result = state["result_enhancer"](
            state["route"],
            state["result"],
            state["profile"],
            state.get("user_message", ""),
        )
        return {"result": result}


langgraph_stock_agent = LangGraphStockAgent()
