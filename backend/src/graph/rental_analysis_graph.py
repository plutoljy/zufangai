"""
租房合同分析流程图
简单的线性流程：Owl → Dog → Beaver → Cat
参考: Contract-Review-Copilot 项目架构
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Optional
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.owl_analyst import OwlAnalyst
from agents.dog_retriever import DogRetriever
from agents.beaver_calculator import BeaverCalculator
from agents.cat_reporter import CatReporter


class AnalysisState(TypedDict):
    """分析状态"""
    # 输入
    contract_text: str
    location: str

    # Owl Analyst 输出
    entities: Dict
    risk_items: List[Dict]

    # Dog Retriever 输出
    legal_references: List[Dict]
    case_references: List[Dict]
    suggestions: List[str]

    # Beaver Calculator 输出
    calculations: Dict

    # Cat Reporter 输出
    report: Dict

    # 元数据
    current_step: Optional[str]
    session_id: Optional[str]


# 初始化所有 Agent
owl = OwlAnalyst()
dog = DogRetriever()
beaver = BeaverCalculator()
cat = CatReporter()


def save_state(state: AnalysisState, session_id: str):
    """保存状态到文件，支持中途介入"""
    state_dir = Path("data/sessions")
    state_dir.mkdir(parents=True, exist_ok=True)
    
    state_file = state_dir / f"{session_id}.json"
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    print(f"[State] 已保存到 {state_file}")


def load_state(session_id: str) -> Optional[AnalysisState]:
    """从文件加载状态"""
    state_file = Path(f"data/sessions/{session_id}.json")
    if not state_file.exists():
        return None
    
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    print(f"[State] 已从 {state_file} 恢复")
    return state


def owl_analyst_node(state: AnalysisState) -> AnalysisState:
    """Owl Analyst 节点 - 提取实体和识别风险"""
    print("\n[Owl Analyst] 开始分析合同...")
    result = owl.analyze(state["contract_text"])

    state["entities"] = result.get("entities", {})
    state["risk_items"] = result.get("risk_items", [])
    state["current_step"] = "owl_analyst"

    print(f"   提取实体: {len(state['entities'])} 项")
    print(f"   识别风险: {len(state['risk_items'])} 项")

    # 保存状态
    if state.get("session_id"):
        save_state(state, state["session_id"])

    return state


def dog_retriever_node(state: AnalysisState) -> AnalysisState:
    """Dog Retriever 节点 - 检索法律条文和案例"""
    print("\n[Dog Retriever] 检索法律依据...")
    result = dog.retrieve(state["risk_items"], state["location"])

    state["legal_references"] = result.get("legal_references", [])
    state["case_references"] = result.get("case_references", [])
    state["suggestions"] = result.get("suggestions", [])
    state["current_step"] = "dog_retriever"

    print(f"   法律条文: {len(state['legal_references'])} 条")
    print(f"   案例: {len(state['case_references'])} 个")

    # 保存状态
    if state.get("session_id"):
        save_state(state, state["session_id"])

    return state


def beaver_calculator_node(state: AnalysisState) -> AnalysisState:
    """Beaver Calculator 节点 - 计算费用和检查合规性"""
    print("\n[Beaver Calculator] 计算费用...")
    result = beaver.calculate(state["entities"], state["location"])

    state["calculations"] = result
    state["current_step"] = "beaver_calculator"

    deposit_ok = result.get("deposit_check", {}).get("compliant", True)
    print(f"   押金检查: {'合规' if deposit_ok else '不合规'}")

    # 保存状态
    if state.get("session_id"):
        save_state(state, state["session_id"])

    return state


def cat_reporter_node(state: AnalysisState) -> AnalysisState:
    """Cat Reporter 节点 - 生成最终报告"""
    print("\n[Cat Reporter] 生成报告...")

    # 检查是否为模板
    is_template = state.get("is_template", False)

    if is_template:
        # 模板报告：只需要 risk_items
        result = cat.generate_report(
            entities=state.get("entities", {}),
            risk_items=state.get("risk_items", []),
            is_template=True
        )
    else:
        # 完整报告
        result = cat.generate_report(
            entities=state["entities"],
            risk_items=state["risk_items"],
            legal_references=state.get("legal_references", []),
            calculations=state.get("calculations", {}),
            is_template=False
        )

    state["report"] = result
    state["current_step"] = "cat_reporter"

    print(f"   报告生成完成")
    print(f"   总风险: {result['summary']['total_risks']} 项")

    # 保存最终状态
    if state.get("session_id"):
        save_state(state, state["session_id"])

    return state


def create_analysis_graph():
    """创建分析流程图 - 简单的线性流程"""
    graph = StateGraph(AnalysisState)

    # 添加节点
    graph.add_node("owl_analyst", owl_analyst_node)
    graph.add_node("dog_retriever", dog_retriever_node)
    graph.add_node("beaver_calculator", beaver_calculator_node)
    graph.add_node("cat_reporter", cat_reporter_node)

    # 定义线性流程: owl → dog → beaver → cat → END
    graph.set_entry_point("owl_analyst")
    graph.add_edge("owl_analyst", "dog_retriever")
    graph.add_edge("dog_retriever", "beaver_calculator")
    graph.add_edge("beaver_calculator", "cat_reporter")
    graph.add_edge("cat_reporter", END)

    return graph.compile()


def run_from_step(session_id: str, start_step: str):
    """从指定步骤恢复执行（中途介入）"""
    state = load_state(session_id)
    if not state:
        raise ValueError(f"Session {session_id} not found")

    graph = create_analysis_graph()
    
    # 根据 start_step 决定从哪里开始
    step_order = ["owl_analyst", "dog_retriever", "beaver_calculator", "cat_reporter"]
    if start_step not in step_order:
        raise ValueError(f"Invalid step: {start_step}")

    # 从指定步骤开始执行
    print(f"\n[Resume] 从 {start_step} 恢复执行...")
    
    # 手动执行后续步骤
    current_idx = step_order.index(start_step)
    for step in step_order[current_idx:]:
        if step == "owl_analyst":
            state = owl_analyst_node(state)
        elif step == "dog_retriever":
            state = dog_retriever_node(state)
        elif step == "beaver_calculator":
            state = beaver_calculator_node(state)
        elif step == "cat_reporter":
            state = cat_reporter_node(state)

    return state


# 测试代码
if __name__ == "__main__":
    import uuid

    # 创建图
    app = create_analysis_graph()

    # 测试用例: 完整流程
    print("\n" + "=" * 60)
    print("测试: 完整流程（所有 Agent 都执行）")
    print("=" * 60)

    session_id = str(uuid.uuid4())[:8]
    initial_state = {
        "contract_text": """
        甲方(出租方): 张三
        乙方(承租方): 李四
        房屋地址: 北京市海淀区中关村大街1号
        月租金: 5000元
        押金: 10000元
        租期: 12个月

        特别约定:
        1. 乙方提前退租的,甲方有权扣除全部押金作为违约金
        2. 水费按9元/立方米收取,电费按1.5元/度收取
        """,
        "location": "beijing",
        "session_id": session_id
    }

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"风险数量: {len(final_state['risk_items'])}")
    print(f"法律条文: {len(final_state.get('legal_references', []))}")
    print(f"计算结果: {final_state.get('calculations', {}).get('deposit_check', {}).get('compliant', 'N/A')}")

    # 测试中途介入
    print("\n\n" + "=" * 60)
    print("测试: 中途介入（从 Dog Retriever 恢复）")
    print("=" * 60)
    
    # 模拟修改 State
    state = load_state(session_id)
    if state:
        print(f"当前步骤: {state.get('current_step')}")
        print("可以在这里修改 State，然后继续执行...")
        
        # 从 dog_retriever 恢复
        # resumed_state = run_from_step(session_id, "dog_retriever")
