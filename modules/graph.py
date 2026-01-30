from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
import json
from modules.agents import observer_chain, interviewer_chain, feedback_chain

class AgentState(TypedDict):
    participant_name: str
    position: str
    grade: str
    history: List[str]
    turns: List[Dict]
    current_difficulty: int
    last_user_input: str
    vision_context: str
    observer_instruction: str
    all_observer_thoughts: List[str]
    final_feedback: str
    conversation_active: bool
    total_questions: int
    current_question_number: int

def observer_node(state: AgentState):
    if not state['last_user_input']:
        return {
            "observer_instruction": f"Поприветствуй {state['participant_name']} и начни собеседование на {state['position']}.",
            "all_observer_thoughts": ["Start of interview"]
        }

    try:
        response = observer_chain.invoke({
            "position": state['position'],
            "grade": state['grade'],
            "difficulty": state['current_difficulty'],
            "history": "\n".join(state['history'][-2:]),
            "last_user_input": state['last_user_input'],
            "vision_data": state['vision_context']
        })
        
        clean_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        new_diff = max(1, min(10, state['current_difficulty'] + data.get("difficulty_adjustment", 0)))
        
        turn_log = {
            "turn_id": len(state['turns']) + 1,
            "user_message": state['last_user_input'],
            "internal_thoughts": f"[Observer]: {data.get('thought_process')} | [Vision]: {state['vision_context']}"
        }
        
        return {
            "observer_instruction": data.get("next_instruction_to_interviewer"),
            "current_difficulty": new_diff,
            "all_observer_thoughts": [data.get('thought_process')],
            "turns": [turn_log],
            "conversation_active": data.get("status") != "finish"
        }
    except Exception as e:
        print(f"Observer Error: {e}")
        return {"observer_instruction": "Продолжай интервью.", "all_observer_thoughts": ["Error parsing"]}

def interviewer_node(state: AgentState):
    if not state['conversation_active']:
        return {}

    msg = interviewer_chain.invoke({
        "candidate_name": state['participant_name'],
        "position": state['position'],
        "observer_instruction": state['observer_instruction'],
        "last_user_input": state['last_user_input']
    })
    
    cur = int(state.get('current_question_number', 0)) + 1
    total = int(state.get('total_questions', 10))
    numbered_msg = f"{cur}/{total} {msg}"

    if state['turns']:
        state['turns'][-1]['agent_visible_message'] = numbered_msg
    else:
        state['turns'].append({
            "turn_id": 1,
            "agent_visible_message": numbered_msg,
            "internal_thoughts": "Intro",
            "user_message": state.get('last_user_input', '')
        })

    conversation_active = True
    if cur >= total:
        conversation_active = False

    return {
        "history": [f"User: {state['last_user_input']}", f"Agent: {numbered_msg}"],
        "current_question_number": cur,
        "conversation_active": conversation_active
    }

def feedback_node(state: AgentState):
    res = feedback_chain.invoke({
        "position": state['position'],
        "all_observer_thoughts": "\n".join(state['all_observer_thoughts'])
    })
    return {"final_feedback": res}

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("observer", observer_node)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("feedback", feedback_node)
    
    workflow.set_entry_point("observer")
    workflow.add_edge("observer", "interviewer")
    
    def router(state):
        if not state['conversation_active'] or "стоп" in state['last_user_input'].lower():
            return "feedback"
        return END

    workflow.add_conditional_edges("interviewer", router, {"feedback": "feedback", END: END})
    workflow.add_edge("feedback", END)
    
    return workflow.compile()