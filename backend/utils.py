from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import pandas as pd
import numpy as np
import json
import io
import os
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import tempfile
from fpdf import FPDF
from datetime import datetime

class DataAnalyzer:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            model="meta/llama-4-maverick-17b-128e-instruct",
            openai_api_key=api_key, # NVIDIA API Key is passed here because we use the OpenAI-compatible client
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            top_p=1.0,
        )

    async def analyze_data(self, query: str, dataframes: Dict[str, pd.DataFrame], history: List[Dict[str, str]], summaries: Dict[str, Any] = None):
        if not dataframes:
            return {
                "explanation": "No data available. Please upload a file to analyze.",
                "visualization": None,
                "code": None
            }

        df_list = list(dataframes.values())
        
        # PROD-LEVEL UPGRADE: Delegate prompt building to helper
        context_prompt = self._build_context_prompt(dataframes)

        try:
            agent = create_pandas_dataframe_agent(
                self.llm,
                df_list,
                verbose=True,
                agent_type="openai-functions",
                allow_dangerous_code=True,
                handle_parsing_errors=True
            )
        except Exception as e:
            print(f"Agent Initialization Error: {e}")
            return {
                "explanation": f"I encountered an error initializing the analysis agent: {str(e)}",
                "code": None,
                "visualization": None
            }

        history_context = "\n".join([f"{m['role'].upper()}: {m.get('content')}" for m in history[-5:]])
        
        final_prompt = f"""
        {context_prompt}
        
        CHAT HISTORY:
        {history_context}
        
        CURRENT QUERY:
        {query}
        
        Remember to output ONLY JSON.
        """

        try:
            response = await agent.ainvoke({"input": final_prompt})
            content = response["output"]
            
            try:
                cleaned_content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(cleaned_content)
                return result
            except json.JSONDecodeError:
                return {
                    "explanation": content,
                    "code": "Agent-generated logic",
                    "visualization": None
                }

        except Exception as e:
            print(f"Agent Error: {e}")
            return {
                "explanation": f"I encountered an error analyzing the data: {str(e)}",
                "code": None,
                "visualization": None
            }

    def _build_context_prompt(self, dataframes: Dict[str, pd.DataFrame]) -> str:
        data_stats = []
        filenames = list(dataframes.keys())
        latest_file = filenames[-1] if filenames else None

        for i, (name, df) in enumerate(dataframes.items()):
            tag = "[MOST RECENT UPLOAD] " if name == latest_file else ""
            var_name = f"df{i+1}"
            data_stats.append(f"- {tag}File: {name} | Variable: {var_name} | Rows: {len(df)} | Columns: {list(df.columns)}")
        data_stats_str = "\n".join(data_stats)

        return f"""
        You are an expert Data Analyst using Python. 
        You have access to pandas dataframes.
        
        DATASET OVERVIEW (Do NOT ignore):
        {data_stats_str}
        
        GOAL:
        1. Answer the USER's specific question by writing and running pandas code.
        2. IF appropriate, return data for a visualization in the JSON response (not in the chat text).
        
        CRITICAL INSTRUCTION:
        - The dataframes are ALREADY LOADED in variables: df1, df2, etc. (See OVERVIEW above).
        - DO NOT run pd.read_csv(). Use the existing variables (e.g. df1, df2).
        - PRIORITY RULE: If multiple files contain the same column names (e.g. 'Year', 'Value'), prioritizing the [MOST RECENT UPLOAD].
        - **EXECUTION PROTOCOL**:
            1. You MUST write and execute Python code using the pandas tool.
            2. inside your code, you MUST `print()` the final result so it appears in your observation.
            3. READ the observation.
            4. ONLY THEN create the final JSON response using the Observed value.
        - **DO NOT GUESS**. If you output a number that didn't come from a code execution observation, you will be penalized.
        - EXPLANATION FIELD: Must contain the FINAL ANSWER (number, string, list) derived from the code observation.

        RESPONSE FORMAT:
        You must return a JSON object with:
        {{
            "explanation": "Markdown text containing the ACTUAL LIST OF VALUES (derived from code execution).",
            "code": "The python code you executed to get the answer.",
            "visualization": {{
                "type": "bar | line | pie | scatter", 
                "data": [{{"name": "x_val", "value": y_val}}, ...], 
                "title": "Chart Title",
                "xAxis": "X Label",
                "yAxis": "Y Label" 
            }} or null
        }}
        
        VISUALIZATION RULES:
        - If the user asks for a plot/chart/graph, OR if the data comparison is complex, provide a 'visualization' object.
        - Ensure 'data' is a list of simple dictionaries.
        """


    def _fallback_analysis(self, *args, **kwargs):
        return {"explanation": "Analysis unavailable.", "visualization": None}


def get_df_summary(df: pd.DataFrame):
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    
    return {
        "rows": len(df),
        "columns": df.columns.tolist(),
        "info": info_str
    }

def clean_text(text):
    if not text: return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2026': '...',
        '\u00a0': ' '
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf(session_title: str, messages: List[Any]):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, clean_text(session_title), ln=True, align="C")
        pdf.ln(10)
        
        for msg in messages:
            role = msg.role.upper()
            content = clean_text(msg.content or "")
            
            pdf.set_font("Arial", "B", 10)
            if role == "ASSISTANT":
                pdf.set_text_color(0, 0, 128)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, role, ln=True)
            
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 5, content)
            pdf.ln(5)
            
        return io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    except Exception as e:
        print(f"PDF Error: {e}")
        return io.BytesIO(b"Error generating PDF")
