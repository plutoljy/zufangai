"""
租房合同分析流程图
使用LangGraph编排多个Agent顺序执行
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import sys
import os

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

    # Owl Analyst输出
    entities: Dict
    risk_items: List[Dict]

    # Dog Retriever输出
    legal_references: List[Dict]
    case_references: List[Dict]
    suggestions: List[str]

    # Beaver Calculator输出
    calculations: Dict

    # Cat Reporter输出
    report: Dict


# 初始化所有Agent
owl = OwlAnalyst()
dog = DogRetriever()
beaver = BeaverCalculator()
cat = CatReporter()


def owl_analyst_node(state: AnalysisState) -> AnalysisState:
    """Owl Analyst节点 - 提取实体和识别风险"""
    print("🦉 Owl Analyst: 分析合同...")
    result = owl.analyze(state["contract_text"])

    state["entities"] = result.get("entities", {})
    state["risk_items"] = result.get("risk_items", [])

    print(f"   提取实体: {len(state['entities'])}项")
    print(f"   识别风险: {len(state['risk_items'])}项")

    return state


def dog_retriever_node(state: AnalysisState) -> AnalysisState:
    """Dog Retriever节点 - 检索法律条文和案例"""
    print("🐶 Dog Retriever: 检索法律...")
    result = dog.retrieve(state["risk_items"], state["location"])

    state["legal_references"] = result.get("legal_references", [])
    state["case_references"] = result.get("case_references", [])
    state["suggestions"] = result.get("suggestions", [])

    print(f"   法律条文: {len(state['legal_references'])}条")
    print(f"   案例: {len(state['case_references'])}个")

    return state


def beaver_calculator_node(state: AnalysisState) -> AnalysisState:
    """Beaver Calculator节点 - 计算费用和检查合规性"""
    print("🦫 Beaver Calculator: 计算费用...")
    result = beaver.calculate(state["entities"], state["location"])

    state["calculations"] = result

    deposit_ok = result.get("deposit_check", {}).get("compliant", True)
    print(f"   押金检查: {'✓ 合规' if deposit_ok else '✗ 不合规'}")

    return state


def cat_reporter_node(state: AnalysisState) -> AnalysisState:
    """Cat Reporter节点 - 生成最终报告"""
    print("🐱 Cat Reporter: 生成报告...")
    result = cat.generate_report(
        entities=state["entities"],
        risk_items=state["risk_items"],
        legal_references=state["legal_references"],
        calculations=state["calculations"]
    )

    state["report"] = result

    print(f"   报告生成完成")
    print(f"   总风险: {result['summary']['total_risks']}项")

    return state


def create_analysis_graph():
    """创建分析流程图"""
    graph = StateGraph(AnalysisState)

    # 添加节点
    graph.add_node("owl_analyst", owl_analyst_node)
    graph.add_node("dog_retriever", dog_retriever_node)
    graph.add_node("beaver_calculator", beaver_calculator_node)
    graph.add_node("cat_reporter", cat_reporter_node)

    # 定义流程: owl → dog → beaver → cat → END
    graph.add_edge("owl_analyst", "dog_retriever")
    graph.add_edge("dog_retriever", "beaver_calculator")
    graph.add_edge("beaver_calculator", "cat_reporter")
    graph.add_edge("cat_reporter", END)

    # 设置入口
    graph.set_entry_point("owl_analyst")

    return graph.compile()


# 测试代码
if __name__ == "__main__":
    import json

    # 创建图
    app = create_analysis_graph()

    # 测试输入
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
        "location": "beijing"
    }

    # 执行流程
    print("=" * 50)
    print("开始分析合同...")
    print("=" * 50)

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print("分析完成!")
    print("=" * 50)

    # 输出报告
    print("\n" + final_state["report"]["report_markdown"])
