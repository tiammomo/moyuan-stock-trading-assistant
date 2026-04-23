from __future__ import annotations

from typing import Any, Callable, List, Optional

from langgraph.graph import END, START, StateGraph
from typing import TypedDict

from app.schemas import SkillRunStatus, SkillUsage, StructuredResult, UserProfile, UserVisibleError


SkillExecutor = Callable[[Any, UserProfile, str], tuple[StructuredResult, List[SkillUsage], str, Optional[UserVisibleError]]]
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
    user_visible_error: Optional[UserVisibleError]
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
    ) -> tuple[StructuredResult, List[SkillUsage], str, Optional[UserVisibleError]]:
        base_state = self.invoke_base(
            route=route,
            profile=profile,
            user_message=user_message,
            skill_executor=skill_executor,
        )
        enhanced_result = self.enhance(
            route=route,
            profile=profile,
            user_message=user_message,
            result=base_state["result"],
            result_enhancer=result_enhancer,
            should_enhance=base_state.get("should_enhance", False),
            user_visible_error=base_state.get("user_visible_error"),
        )
        return (
            enhanced_result,
            base_state.get("skills_used", []),
            base_state.get("rewritten_query", ""),
            base_state.get("user_visible_error"),
        )

    def invoke_base(
        self,
        *,
        route: Any,
        profile: UserProfile,
        user_message: str,
        skill_executor: SkillExecutor,
    ) -> StockAgentState:
        graph = self._build_base_graph()
        return graph.invoke(
            {
                "route": route,
                "profile": profile,
                "user_message": user_message,
                "skill_executor": skill_executor,
            }
        )

    def enhance(
        self,
        *,
        route: Any,
        profile: UserProfile,
        user_message: str,
        result: StructuredResult,
        result_enhancer: ResultEnhancer,
        should_enhance: bool,
        user_visible_error: Optional[UserVisibleError],
    ) -> StructuredResult:
        graph = self._build_enhancement_graph()
        final_state = graph.invoke(
            {
                "route": route,
                "profile": profile,
                "user_message": user_message,
                "result": result,
                "result_enhancer": result_enhancer,
                "should_enhance": should_enhance,
                "user_visible_error": user_visible_error,
            }
        )
        return final_state["result"]

    def _build_base_graph(self):
        workflow = StateGraph(StockAgentState)
        workflow.add_node("call_skills", self._call_skills)
        workflow.add_edge(START, "call_skills")
        workflow.add_edge("call_skills", END)
        return workflow.compile()

    def _build_enhancement_graph(self):
        workflow = StateGraph(StockAgentState)
        workflow.add_node("llm_enhance", self._llm_enhance)
        workflow.add_edge(START, "llm_enhance")
        workflow.add_edge("llm_enhance", END)
        return workflow.compile()

    def _call_skills(self, state: StockAgentState) -> StockAgentState:
        result, skills_used, rewritten_query, user_visible_error = state["skill_executor"](
            state["route"],
            state["profile"],
            state.get("user_message", ""),
        )
        should_enhance = any(skill.status == SkillRunStatus.SUCCESS for skill in skills_used)
        return {
            "result": result,
            "skills_used": skills_used,
            "rewritten_query": rewritten_query,
            "user_visible_error": user_visible_error,
            "should_enhance": should_enhance,
        }

    def _llm_enhance(self, state: StockAgentState) -> StockAgentState:
        if not state.get("should_enhance"):
            return {
                "result": state["result"],
                "user_visible_error": state.get("user_visible_error"),
            }
        result = state["result_enhancer"](
            state["route"],
            state["result"],
            state["profile"],
            state.get("user_message", ""),
        )
        return {
            "result": result,
            "user_visible_error": state.get("user_visible_error"),
        }


langgraph_stock_agent = LangGraphStockAgent()
