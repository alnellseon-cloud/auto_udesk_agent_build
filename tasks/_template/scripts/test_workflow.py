"""
测试工作流 — 模板
替换 APP_ID 和 TEST_CASES 后即可使用。
所有问题共用同一 DIALOG_ID，测试多轮记忆和上下文保持。
运行后自动在 logs/ 目录生成带时间戳的 UTF-8 测试报告。
"""
import sys, io, os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from uagent.client import UAgentClient
from uagent import workflow as wf_api

APP_ID = 'YOUR-APP-ID-HERE'
client = UAgentClient()

# 首次为空，从第一次响应中取 conversation_id 串联后续
# 禁止自己 uuid.uuid4() 生成——自生成 UUID 会返回 404
DIALOG_ID = ''

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, 'test_%s.txt' % datetime.now().strftime('%Y%m%d_%H%M%S'))

_log_fh = open(LOG_FILE, 'w', encoding='utf-8')


def log(text=''):
    print(text)
    _log_fh.write(text + '\n')


def run_test(idx, query, label='', check_fn=None):
    """
    check_fn: 可选，接收 final_answer -> (passed: bool, reason: str)
    首次调用 dialog_id=''，从返回事件取 conversation_id 后更新 DIALOG_ID。
    """
    global DIALOG_ID

    log()
    log('=' * 60)
    log('Q%02d[%s]: %s' % (idx, label, query))
    log('  (dialog_id=%s)' % (DIALOG_ID[:8] + '...' if DIALOG_ID else '空，首轮'))
    log('=' * 60)

    node_trace = []
    final_answer = ''
    workflow_status = ''

    try:
        events = wf_api.run_preview(client, APP_ID, query, dialog_id=DIALOG_ID)
        for ev in events:
            # 从首次响应取 conversation_id 供后续所有问题复用
            if not DIALOG_ID and ev.get('conversation_id'):
                DIALOG_ID = ev['conversation_id']
                log('  [会话ID] %s' % DIALOG_ID)

            t = ev.get('type', '')
            if t == 'node_finished':
                d = ev['data']
                ntype = d.get('node_type', '')
                nid = d.get('node_id', d.get('id', ''))
                outputs = d.get('outputs', {})
                status = d.get('status', '')

                if status == 'failed':
                    err = d.get('error', '未知错误')
                    msg = '[节点失败] %s/%s: %s' % (nid, ntype, err)
                    node_trace.append(msg)
                    log(msg)

                elif ntype == 'question-classifier-plus':
                    cls = outputs.get('class_name', outputs.get('class_id', ''))
                    msg = '[分类器] → 路径: %s' % cls
                    node_trace.append(msg)
                    log(msg)

                elif ntype == 'parameter-extractor':
                    params = {k: v for k, v in outputs.items()
                              if not k.startswith('__') and v not in (None, '', [])}
                    msg = '[参数提取] %s' % params
                    node_trace.append(msg)
                    log(msg)

                elif ntype == 'tool':
                    result = outputs.get('result', outputs.get('text', ''))
                    if result:
                        preview = str(result)[:200].replace('\n', ' ')
                        msg = '[%s/知识库] %s…' % (nid, preview)
                        node_trace.append(msg)
                        log(msg)

                elif ntype == 'llm':
                    text = outputs.get('text', '')
                    if text:
                        preview = text[:300]
                        msg = '[%s/LLM] %s' % (nid, preview)
                        node_trace.append(msg)
                        log(msg)

                elif ntype == 'answer':
                    final_answer = outputs.get('answer', '')
                    node_trace.append('[answer] (见下方最终回答)')

            elif t == 'workflow_finished':
                workflow_status = ev['data'].get('status', '')

    except Exception as e:
        log('运行异常: %s' % e)
        workflow_status = 'exception'

    log()
    log('【节点执行路径】')
    for step in node_trace:
        log('  ' + step)

    log()
    log('【最终回答】')
    log(final_answer[:600] if final_answer else '（无 answer 节点输出）')

    passed = workflow_status == 'succeeded'
    reason = ''
    if check_fn and passed:
        passed, reason = check_fn(final_answer)

    tag = '✅' if passed else '❌'
    log('\n  %s %s%s' % (tag, workflow_status, (' → ' + reason) if reason else ''))
    return passed, final_answer


# ─── 常用校验函数 ──────────────────────────────────────────────────────────────

def contains(words):
    """回答中必须包含所有关键词"""
    def fn(ans):
        ok = all(w in ans for w in words)
        return ok, '' if ok else '缺少关键词: %s' % [w for w in words if w not in ans]
    return fn

def not_contains(words):
    """回答中不应包含这些词"""
    def fn(ans):
        found = [w for w in words if w in ans]
        ok = not found
        return ok, '' if ok else '包含不应有的内容: %s' % found
    return fn

def is_fallback(ans):
    """预期兜底回答（人工客服引导）"""
    keywords = ['没有找到', '人工客服', '暂时还没', '无法', '不清楚']
    ok = any(k in ans for k in keywords)
    return ok, '' if ok else '预期兜底但模型给出了具体回答'

def not_fallback(ans):
    """预期有实质回答，而非兜底"""
    keywords = ['没有找到', '暂时还没']
    ok = not any(k in ans for k in keywords)
    return ok, '' if ok else '预期实质回答但输出了兜底话术'

def has_img(ans):
    """回答中应包含 <img> 标签"""
    ok = '<img' in ans
    return ok, '' if ok else '预期有配图但未输出 <img> 标签'


# ─── 测试用例（按实际业务路径填写）────────────────────────────────────────────
# 格式：(问题, 标签, check_fn or None)
TEST_CASES = [
    ('测试问题1', '路径A', None),
    ('测试问题2', '路径B', contains(['关键词'])),
]


# ─── 运行测试 ──────────────────────────────────────────────────────────────────
log('工作流测试报告')
log('App ID : %s' % APP_ID)
log('Dialog ID : %s' % (DIALOG_ID or '空（首轮自动获取）'))
log('测试时间 : %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
log('日志文件 : %s' % LOG_FILE)

results = []
for i, (query, label, check_fn) in enumerate(TEST_CASES, 1):
    ok, _ = run_test(i, query, label, check_fn)
    results.append((i, label, ok))

# ─── 汇总 ─────────────────────────────────────────────────────────────────────
log()
log('=' * 60)
log('测试汇总')
log('=' * 60)
passed_total = sum(1 for _, _, ok in results if ok)
failed_total = len(results) - passed_total

for idx, label, ok in results:
    tag = '✅' if ok else '❌'
    log('  %s Q%02d %s' % (tag, idx, label))

log()
log('结果：%d 通过 / %d 失败 / 共 %d 项' % (passed_total, failed_total, len(results)))
log('=' * 60)

_log_fh.close()
print('\n日志已保存至: %s' % LOG_FILE)
