import pandas as pd
import json
import logging
import re
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from app.core.config import settings

# Setup logging
logger = logging.getLogger(__name__)

class DataAnalyzer:
    def __init__(self):
        # Fallback to NVIDIA NIM as OpenAI quota is exceeded
        api_key = settings.NVIDIA_API_KEY
        base_url = "https://integrate.api.nvidia.com/v1"
        
        if not api_key:
            logger.error("NVIDIA_API_KEY is missing from backend/.env")
            
        self.llm = ChatOpenAI(
            model="meta/llama-3.1-70b-instruct", # More stable version for NVIDIA NIM
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.0,
            max_tokens=1000
        )
        self.df_cache = {}

    def get_or_load_dataframes(self, datasets: List[Any]) -> Dict[str, pd.DataFrame]:
        """
        Loads dataframes from file paths with caching to improve performance.
        datasets: List of dataset objects (must have .file_path and .filename attributes)
        """
        dfs = {}
        for ds in datasets:
            path = ds.file_path
            if path in self.df_cache:
                dfs[ds.filename] = self.df_cache[path]
                continue
                
            try:
                if path.endswith('.csv'):
                    df = pd.read_csv(path)
                elif path.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(path)
                else:
                    continue
                
                # Update cache
                self.df_cache[path] = df
                dfs[ds.filename] = df
            except Exception as e:
                logger.error(f"Failed to load {ds.filename}: {e}")
                
        return dfs

    async def analyze_data(
        self, 
        query: str, 
        dataframes: Dict[str, pd.DataFrame], 
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates the analysis:
        1. Contextualize (Schema Injection)
        2. Plan & Execute (Agent)
        3. Verify & Format
        """
        if not dataframes:
            return {"explanation": "No data available.", "visualization": None, "code": None}

        # 0. Fast-track Greetings
        if query.lower().strip() in ["hi", "hello", "hey"]:
             return {"explanation": "Hello! I am your Data Analyst. How can I help you with your data today?", "visualization": None, "code": None}

        df_list = list(dataframes.values())
        filenames = list(dataframes.keys())
        
        # 1. Build System Context with Recency Bias
        system_context = self._build_context_prompt(dataframes, history)
        
        # 2. Initialize Agent & Execute
        try:
            # Using gpt-4o-mini which is near-instant for these tasks
            agent = create_pandas_dataframe_agent(
                self.llm,
                df_list,
                verbose=False,
                agent_type="openai-functions", 
                allow_dangerous_code=True,
                max_iterations=2, # Sufficient for gpt-4o-mini
                agent_executor_kwargs={"handle_parsing_errors": True},
                prefix=system_context
            )

            # Force strictly JSON output with no narrative
            final_prompt = f"""
            TASK: Process the user query and provide results in JSON format.
            QUERY: {query}
            
            RULES:
            1. OUTPUT FORMAT: You MUST output ONLY a JSON block. No introductory text.
            2. INSIGHTS: Provide professional "So What?" insights in the "explanation" field.
            3. NO CODE IN EXPLANATION: Never put python code or variable names in the "explanation".
            4. VISUALIZATION: Limit "data" to MAX 20 points. Type MUST be "bar", "line", or "pie".
            
            STRUCTURE:
            {{
                "explanation": "Executive insights...",
                "code": "pandas logic used",
                "visualization": null or {{"type": "bar", "data": [{{"x": "label", "y": 10}}, ...]}},
                "email_to_forward": "email_or_null",
                "suggestions": ["Q1", "Q2"]
            }}
            """
            
            response = await agent.ainvoke({"input": final_prompt})
            output_text = response["output"]
            
            # 4. Parse Output (Highly Resilient Parsing)
            try:
                # Find the largest block that looks like a JSON object
                json_match = re.search(r'(\{.*\})', output_text, re.DOTALL)
                json_str = json_match.group(1) if json_match else None

                result = {"explanation": "", "code": None, "visualization": None, "suggestions": []}

                if json_str:
                    try:
                        parsed = json.loads(json_str)
                        result.update(parsed)
                    except json.JSONDecodeError:
                        # Manual field extraction if JSON is malformed
                        expl_match = re.search(r'"explanation":\s*"(.*?)"', json_str, re.DOTALL)
                        if expl_match:
                            result["explanation"] = expl_match.group(1)
                        
                        # Strip other JSON clutter
                        result["explanation"] = re.sub(r'\\n', '\n', result["explanation"])
                
                # Cleanup and fallbacks
                if not result.get("explanation"):
                    # Use anything that isn't a bracket block as explanation
                    result["explanation"] = re.sub(r'\{.*\}', '', output_text, flags=re.DOTALL).strip()
                
                if not result["explanation"]:
                    result["explanation"] = "I've analyzed the data. What else would you like to know?"

                # Add suggestions if available
                if result.get("suggestions") and isinstance(result["suggestions"], list):
                    s_text = "\n\n**Suggestions:**\n" + "\n".join([f"- {s}" for s in result["suggestions"]])
                    result["explanation"] += s_text
                
                return result

            except Exception as parse_err:
                logger.warning(f"Extreme parse fallback: {parse_err}")
                return {"explanation": "I processed your request but had trouble formatting the response. " + output_text[:200], "code": None, "visualization": None}

        except Exception as e:
            logger.error(f"Analysis Error: {e}")
            return {"explanation": f"Analysis failed: {str(e)}", "visualization": None, "code": None}

    def _build_context_prompt(self, dataframes: Dict[str, pd.DataFrame], history: List[Dict[str, str]]) -> str:
        """
        Constructs the System Prompt with Schema Introspection and Recency Bias.
        """
        filenames = list(dataframes.keys())
        latest_file = filenames[-1] if filenames else ""
        
        schema_info = []
        for i, (fname, df) in enumerate(dataframes.items()):
            priority = "[CURRENT_FOCUS] " if fname == latest_file else ""
            schema_info.append(f"{priority}File: {fname} | Var: df{i+1} | Shape: {df.shape} | Cols: {list(df.columns)}")
            
        formatted_history = ""
        if history:
            for h in history:
                role = h.get("role", "unknown")
                content = h.get("content", "")
                # Escape braces for LangChain PromptTemplate (treat as literals)
                content = content.replace("{", "{{").replace("}", "}}")
                formatted_history += f"{role}: {content}\n"
        else:
            formatted_history = "No history."

        return f"""
        You are a Helpful & Intelligent Data Analyst Assistant for the 'Conversational Data Analyst' (CDA) platform.
        
        STRICT BEHAVIORAL RULES:
        1. OUT-OF-BOUNDS: If a user asks a question COMPLETELY unrelated to data analysis or the provided datasets (e.g. "Tell me a joke"), you MUST politely state:
           "I'm sorry, that's outside the scope of the data you've shared. I'm specialized in analyzing your datasets. Would you like to ask something about [Column Names] instead?"
        2. DATA FOCUS: Always steer the conversation back to the uploaded data.
        3. EMAIL DETECTION: If the user provides an email address, you MUST return a response acknowledging you will forward the summary. 
           Your JSON response should include 'email_to_forward': 'the_email_address'.
        4. EXPLORATION vs SUMMARY: If the user asks for a "summary", provide a high-level overview of row counts, key columns, and obvious trends.
        
        PERSONALITY:
        - Conversational, friendly, and professional (like Gemini).
        - If the query is ambiguous, ASK for clarification.
        
        TECHNICAL CONTEXT (The data you have):
        {chr(10).join(schema_info)}
        
        CHAT HISTORY:
        {formatted_history}
        """

    def generate_initial_visualization(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates a default visualization for a new dataframe.
        """
        try:
            # Simple automatic visualization logic
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

            if not numeric_cols:
                return None

            # Strategy: Top 10 categories by some numeric sum
            if categorical_cols and numeric_cols:
                cat = categorical_cols[0]
                num = numeric_cols[0]
                summary = df.groupby(cat)[num].sum().sort_values(ascending=False).head(10)
                
                return {
                    "type": "bar",
                    "data": [{"x": str(k), "y": float(v)} for k, v in summary.items()],
                    "xAxis": cat,
                    "yAxis": num,
                    "title": f"Top 10 {cat} by {num}"
                }
            return None
        except Exception as e:
            logger.error(f"Auto-viz error: {e}")
            return None

orchestrator = DataAnalyzer()
