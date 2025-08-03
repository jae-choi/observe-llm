import os
import uvicorn
from typing import TypedDict, Optional, Literal
import uuid
import asyncio
from collections import defaultdict
import json
from contextvars import ContextVar, copy_context
import functools

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
import mistune

# Langfuse v3
from langfuse import Langfuse, observe
from langfuse.langchain import CallbackHandler

# --- 0. 환경 변수 로드 ---
load_dotenv()

# --- 1. Langfuse 초기화 ---
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000")
)
md = mistune.create_markdown()

# --- 2. FastAPI 앱 생성 ---
app_fastapi = FastAPI()

# --- Static 파일 마운트 ---
# 현재 스크립트 파일의 디렉토리 경로를 가져옵니다.
script_directory = os.path.dirname(os.path.abspath(__file__))
# static 디렉토리의 절대 경로를 구성합니다.
static_files_dir = os.path.join(script_directory, "static")
app_fastapi.mount("/static", StaticFiles(directory=static_files_dir), name="static")

# --- 4. 로그 스트리밍을 위한 설정 ---
# In-memory store for run logs. Not suitable for production.
run_logs = defaultdict(asyncio.Queue)
run_id_var = ContextVar('run_id', default=None)
original_print = print

def custom_print(*args, **kwargs):
    """A print function that also puts the message into an async queue for the current run."""
    message = " ".join(map(str, args))
    original_print(message, **kwargs) # Keep original print behavior for server console
    
    run_id = run_id_var.get()
    if run_id and run_id in run_logs:
        run_logs[run_id].put_nowait(message)

# Monkey-patch print to intercept log messages
import builtins
builtins.print = custom_print

# --- 3. 그래프용 상태 정의 ---
class AgentState(TypedDict):
    topic: str
    research_result: str
    draft: str
    critique: str
    final_output: Optional[str]
    reviser_output: str
    revision_count: int
    langfuse_handler: Optional[CallbackHandler]

# --- 5. 노드 함수 정의 (기존과 동일, print를 사용) ---
@observe(name="Researcher Node")
def researcher(state: AgentState):
    topic = state["topic"]
    handler = state.get("langfuse_handler")
    print("--- 🔬 Researching topic... ---")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, callbacks=[handler] if handler else [])
    research_result = llm.invoke(f"'{topic}'에 대한 핵심적인 사실 3가지를 알려줘.").content
    print("--- ✅ Research complete. ---")
    return {"research_result": research_result, "revision_count": 0}

@observe(name="Writer Node")
def writer(state: AgentState):
    handler = state.get("langfuse_handler")
    print("--- ✍️ Writing draft... ---")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7, callbacks=[handler] if handler else [])
    draft = llm.invoke(f"다음 정보를 바탕으로 흥미로운 단락을 작성해줘:\n\n{state['research_result']}").content
    print("--- ✅ Draft complete. ---")
    return {"draft": draft}

@observe(name="Critique Node")
def critique(state: AgentState):
    handler = state.get("langfuse_handler")
    print("--- 🤔 Critiquing draft... ---")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, callbacks=[handler] if handler else [])
    critique_text = llm.invoke(
        f"다음 글을 비평해줘. 명확성, 흥미도, 정확성을 기준으로 개선점을 찾아내고, "
        f"만약 수정이 필요하다면 'REVISE', 그렇지 않다면 'APPROVE' 라는 단어를 마지막에 포함해줘.\n\n{state['draft']}"
    ).content
    print(f"--- ✅ Critique complete: {critique_text[:20]}... ---")
    return {"critique": critique_text}

@observe(name="Reviser Node")
def reviser(state: AgentState):
    handler = state.get("langfuse_handler")
    revision_count = state.get('revision_count', 0) + 1
    print(f"--- 🔄 Revising draft (Attempt {revision_count})... ---")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.6, callbacks=[handler] if handler else [])
    revised_text = llm.invoke(
        f"다음 원본 글과 비평을 바탕으로 글을 **Markdown 형식으로** 수정해줘 그리고 안내 문구 없이 수정된 내용만 바로 출력해줘. "
        f"제목, 부제목, 글머리 기호 등을 사용하여 가독성을 높여줘.\n\n"
        f"**원본:**\n{state['draft']}\n\n"
        f"**비평:**\n{state['critique']}"
    ).content
    print("--- ✅ Revision complete. ---")
    return {"reviser_output": revised_text, "draft": revised_text, "revision_count": revision_count}

def set_final_output(state: AgentState):
    final_output = state.get("reviser_output") or state.get("draft")
    print("--- 🏁 Final output set. ---")
    return {"final_output": final_output}

# --- 6. 조건부 엣지 ---
MAX_REVISIONS = 2
def should_revise(state: AgentState) -> Literal["reviser", "set_final_output"]:
    revision_count = state.get('revision_count', 0)
    if "REVISE" in state["critique"] and revision_count < MAX_REVISIONS:
        print(f"--- 🚦 Decision: Revision needed (Attempt {revision_count + 1}/{MAX_REVISIONS}). ---")
        return "reviser"
    else:
        print("--- 🚦 Decision: Approved or max revisions reached. ---")
        return "set_final_output"

# --- 7. 그래프 구축 ---
workflow = StateGraph(AgentState)
workflow.add_node("researcher", researcher)
workflow.add_node("writer", writer)
workflow.add_node("critique", critique)
workflow.add_node("reviser", reviser)
workflow.add_node("set_final_output", set_final_output)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "critique")
workflow.add_conditional_edges(
    "critique",
    should_revise,
    {"reviser": "reviser", "set_final_output": "set_final_output"}
)
workflow.add_edge("reviser", "critique")
workflow.add_edge("set_final_output", END)
graph = workflow.compile()

# --- 8. 백그라운드 작업 및 API 엔드포인트 ---
async def run_graph_background(run_id: str, topic: str, user_id: str):
    """Runs the LangGraph agent in a background thread and puts logs and results into a queue."""
    run_id_var.set(run_id)
    langfuse_handler = CallbackHandler()
    inputs = {"topic": topic, "langfuse_handler": langfuse_handler}
    config = {"callbacks": [langfuse_handler], "metadata": {"langfuse_user_id": user_id}}
    queue = run_logs[run_id]
    
    try:
        loop = asyncio.get_running_loop()
        
        # Use functools.partial to pass arguments to the target function
        # And copy_context to ensure contextvars are available in the new thread
        wrapped_invoke = functools.partial(graph.invoke, inputs, config)
        ctx = copy_context()
        result_state = await loop.run_in_executor(None, ctx.run, wrapped_invoke)

        final_output_md = result_state.get("final_output", "No output generated.")
        final_output_html = md(final_output_md)
        await queue.put({"type": "result", "data": final_output_html})
    except Exception as e:
        error_html = f"<p class='text-red-400'>An error occurred: {e}</p>"
        await queue.put({"type": "result", "data": error_html})
    finally:
        langfuse.flush()
        await queue.put({"type": "done"})

@app_fastapi.post("/invoke", response_class=JSONResponse)
async def invoke_agent_start(topic: str = Form(...), user_id: str = Form(...)):
    """Starts the agent execution and returns a unique run ID."""
    run_id = str(uuid.uuid4())
    asyncio.create_task(run_graph_background(run_id, topic, user_id))
    return {"run_id": run_id}

@app_fastapi.get("/stream-logs/{run_id}")
async def stream_logs(run_id: str = Path(...)):
    """Streams logs for a given run ID using Server-Sent Events."""
    async def event_generator():
        try:
            queue = run_logs[run_id]
            while True:
                message = await queue.get()
                if isinstance(message, dict):
                    yield f"data: {json.dumps(message)}\n\n"
                    if message.get("type") == "done":
                        break
                else:
                    yield f"data: {json.dumps({'type': 'log', 'data': message})}\n\n"
        except asyncio.CancelledError:
            print(f"Client disconnected from run_id: {run_id}")
        finally:
            if run_id in run_logs:
                del run_logs[run_id]
                original_print(f"Cleaned up queue for run_id: {run_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 9. 웹 UI ---
@app_fastapi.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" href="/static/favicon.png" type="image/png" />
        <title>Langfuse Test Agent</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <style>
            body { font-family: system-ui, sans-serif; background-color: #0a0a0a; color: #e5e5e5; }
            .card { background-color: #1c1c1c; border: 1px solid #2d2d2d; }
            .input-field { background-color: #2d2d2d; border: 1px solid #404040; color: #e5e5e5; }
            .btn-primary { background-color: #2563eb; color: white; }
            .btn-primary:disabled { background-color: #1e40af; cursor: not-allowed; }
            #loader { border: 4px solid #404040; border-top: 4px solid #2563eb; border-radius: 50%; width: 32px; height: 32px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .prose { line-height: 1.7; }
            .prose h1, .prose h2, .prose h3 { margin-top: 1.5em; margin-bottom: 0.8em; font-weight: 600; color: #f5f5f5; }
            .prose h1 { font-size: 1.875rem; } .prose h2 { font-size: 1.5rem; } .prose h3 { font-size: 1.25rem; }
            .prose p { margin-bottom: 1.25em; } .prose ul { list-style-type: disc; padding-left: 1.5em; margin-bottom: 1.25em; }
            .prose li { margin-bottom: 0.5em; } .prose strong { color: #e5e5e5; font-weight: 600; }
        </style>
    </head>
    <body class="antialiased">
        <div id="log-sidebar" class="fixed top-0 right-0 h-full w-80 bg-gray-900 text-gray-300 transform translate-x-full transition-transform duration-300 ease-in-out z-50 flex flex-col shadow-lg">
            <div class="flex justify-between items-center p-4 border-b border-gray-700 flex-shrink-0">
                <h3 class="font-bold text-lg">Agent Logs</h3>
                <button id="close-log-sidebar" class="p-1 rounded-full hover:bg-gray-700 text-2xl leading-none">&times;</button>
            </div>
            <div id="log-content" class="flex-grow p-4 overflow-y-auto text-xs font-mono space-y-1 break-words"></div>
        </div>
        <button id="open-log-sidebar" class="fixed bottom-4 right-4 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors flex items-center justify-center">
            <i data-lucide="align-left"></i>
        </button>

        <div class="container mx-auto p-4 md:p-8 max-w-2xl">
            <header class="text-center mb-8"><h1 class="text-3xl font-bold text-gray-50">LangGraph Agent with Langfuse</h1><p class="text-md text-gray-400 mt-2">AI agent with a critique and revision loop.</p></header>
            <main>
                <div class="card rounded-lg p-6">
                    <form id="agent-form">
                        <div class="space-y-4">
                            <div><label for="user_id" class="block text-sm font-medium text-gray-300 mb-1">User ID</label><input type="text" id="user_id" name="user_id" class="input-field w-full rounded-md p-2.5" placeholder="user-id-001" required></div>
                            <div><label for="topic" class="block text-sm font-medium text-gray-300 mb-1">Topic</label><textarea id="topic" name="topic" rows="2" class="input-field w-full rounded-md p-2.5" placeholder="Langfuse의 주요 기능은 무엇인가요?" required></textarea></div>
                        </div>
                        <div class="mt-6"><button type="submit" id="submit-button" class="btn-primary w-full font-semibold py-2.5 px-4 rounded-md">Run Agent</button></div>
                    </form>
                </div>
                <div id="result-container" class="card rounded-lg p-6 mt-6" style="display: none;">
                    <h2 class="text-xl font-semibold text-gray-100 mb-4">Agent Response</h2>
                    <div id="loader-container" class="flex justify-center items-center py-6"><div id="loader"></div></div>
                    <div id="response-content" class="text-gray-300 prose prose-invert max-w-none"></div>
                </div>
            </main>
        </div>
        <script>
            lucide.createIcons();

            const agentForm = document.getElementById('agent-form');
            const submitButton = document.getElementById('submit-button');
            const resultContainer = document.getElementById('result-container');
            const loaderContainer = document.getElementById('loader-container');
            const responseContent = document.getElementById('response-content');
            const logSidebar = document.getElementById('log-sidebar');
            const logContent = document.getElementById('log-content');
            const openLogSidebar = document.getElementById('open-log-sidebar');
            const closeLogSidebar = document.getElementById('close-log-sidebar');

            openLogSidebar.addEventListener('click', () => logSidebar.classList.remove('translate-x-full'));
            closeLogSidebar.addEventListener('click', () => logSidebar.classList.add('translate-x-full'));

            agentForm.addEventListener('submit', async function(event) {
                event.preventDefault();
                
                resultContainer.style.display = 'block';
                responseContent.innerHTML = '';
                logContent.innerHTML = '';
                loaderContainer.style.display = 'flex';
                submitButton.disabled = true;
                logSidebar.classList.remove('translate-x-full');

                const formData = new FormData(this);

                try {
                    const startResponse = await fetch('/invoke', {
                        method: 'POST',
                        body: formData,
                    });

                    if (!startResponse.ok) {
                        const errorText = await startResponse.text();
                        throw new Error(`Failed to start agent: ${errorText}`);
                    }

                    const { run_id } = await startResponse.json();

                    const eventSource = new EventSource(`/stream-logs/${run_id}`);

                    eventSource.onmessage = function(event) {
                        const message = JSON.parse(event.data);
                        
                        if (message.type === 'log') {
                            const logEntry = document.createElement('p');
                            logEntry.textContent = `> ${message.data}`;
                            logContent.appendChild(logEntry);
                            logContent.scrollTop = logContent.scrollHeight;
                        } else if (message.type === 'result') {
                            loaderContainer.style.display = 'none';
                            responseContent.innerHTML = message.data;
                            eventSource.close();
                        } else if (message.type === 'done') {
                            eventSource.close();
                        }
                    };

                    eventSource.onerror = function(err) {
                        console.error("EventSource failed:", err);
                        responseContent.innerHTML = `<p class="text-red-400">Log streaming connection failed. Please check the console.</p>`;
                        loaderContainer.style.display = 'none';
                        eventSource.close();
                    };

                } catch (error) {
                    loaderContainer.style.display = 'none';
                    responseContent.innerHTML = `<p class="text-red-400">An error occurred: ${error.message}</p>`;
                } finally {
                    submitButton.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """

# --- 10. 실행 (Uvicorn 사용) ---
if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
