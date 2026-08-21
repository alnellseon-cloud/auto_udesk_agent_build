import json
import os
import time
import uuid
import urllib.parse
import requests
from typing import List, Tuple, Optional
from .client import UAgentClient


# ─── UAgent 平台：知识库查询 ────────────────────────────────────────────────

def get_datasets(
    client: UAgentClient,
    page: int = 1,
    page_size: int = 1000,
    name: str = "",
) -> dict:
    return client.get("/api/backend/knowledge/udeskDatasets/query", {
        "page_number": page,
        "page_size": page_size,
        "name": name,
    })


def list_datasets(client: UAgentClient) -> List[dict]:
    """返回知识库列表，每项包含 id、name、knowledge_type。"""
    resp = get_datasets(client)
    return resp.get("data", {}).get("list", [])


def build_aggregation_ids_json(datasets: List[dict]) -> str:
    """将知识库列表转换为 tool 节点 aggregation_ids 所需的 JSON 字符串。"""
    result = []
    for ds in datasets:
        result.append({
            "value": ds["id"],
            "label": ds.get("name", str(ds["id"])),
            "list": [],
        })
    return json.dumps(result, ensure_ascii=False)


def build_aggregation_ids_json_from_ids(client: UAgentClient, ids: List[int]) -> str:
    """根据知识库 ID 列表，查询名称后构建 aggregation_ids JSON 字符串。"""
    all_ds = list_datasets(client)
    id_map = {ds["id"]: ds for ds in all_ds}
    selected = []
    for i in ids:
        ds = id_map.get(i, {"id": i, "name": str(i)})
        selected.append({
            "value": ds["id"],
            "label": ds.get("name", str(ds["id"])),
            "list": [],
        })
    return json.dumps(selected, ensure_ascii=False)


def list_documents(client: UAgentClient, dataset_id: int, page: int = 1, page_size: int = 100) -> List[dict]:
    """列出 UAgent 平台知识库中的文档列表。status_type=2 表示处理完成。"""
    resp = client.get(
        "/api/backend/knowledge/udeskDatasets/%s/documents" % dataset_id,
        {"page_number": page, "page_size": page_size},
    )
    return resp.get("data", {}).get("list", [])


def list_segments(client: UAgentClient, dataset_id: int, doc_id: int, page_size: int = 100) -> List[dict]:
    """列出某文档的所有知识分片（自动翻页）。"""
    all_segs = []
    page = 1
    while True:
        resp = client.get(
            "/api/backend/knowledge/udeskDatasets/%s/%s/segments" % (dataset_id, doc_id),
            {"page_number": page, "page_size": page_size},
        )
        data = resp.get("data", {})
        batch = data.get("list", [])
        all_segs.extend(batch)
        total = data.get("total", 0)
        if len(all_segs) >= total or not batch:
            break
        page += 1
    return all_segs


def update_segment(
    client: UAgentClient,
    dataset_id: int,
    doc_id: int,
    segment_id: str,
    content: str,
    tags: Optional[List] = None,
    priority_level: int = 0,
    quality: int = 0,
) -> dict:
    """编辑知识分片内容。segment_id 是 UUID 字符串。"""
    return client.post(
        "/api/backend/knowledge/udeskDatasets/%s/%s/%s/update" % (dataset_id, doc_id, segment_id),
        {
            "content": content,
            "tags": tags or [],
            "priority_level": priority_level,
            "quality": quality,
            "last_updated_at": 0,
        },
    )


def delete_segment(
    client: UAgentClient,
    dataset_id: int,
    doc_id: int,
    segment_id: str,
) -> dict:
    """删除知识分片。segment_id 是 UUID 字符串。"""
    return client.delete(
        "/api/backend/knowledge/udeskDatasets/%s/%s/%s/delete" % (dataset_id, doc_id, segment_id),
    )


def set_split_rule(
    client: UAgentClient,
    dataset_id: int,
    dataset_name: str,
    word_split_type: str = "word_qa_title",
    excel_split_type: str = "row_split",
    excel_filter_title: bool = False,
    pdf_split_type: str = "",
    chunk_size: int = 500,
) -> dict:
    """
    设置知识库的分片策略（知识库级别，影响后续同步的所有文档）。
    word_split_type: word_qa | word_qa_title | word_big_split | (默认空)
    excel_split_type: row_split | excel_sheet_split | (默认空)
    pdf_split_type: regex | (默认空)
    注意：修改后需重新同步文档才能生效。
    """
    return client.post(
        "/api/backend/knowledge/udeskDatasets/%s/update" % dataset_id,
        {
            "id": dataset_id,
            "name": dataset_name,
            "description": "",
            "embedding_type": "OPENAI-V2",
            "split_rule": {
                "chunk_size": chunk_size,
                "is_split": "true",
                "separators": "",
                "need_semantic": "false",
                "pdf_params": {"regex": "", "split_type": pdf_split_type},
                "word_params": {"split_type": word_split_type},
                "excel_params": {"filter_title": excel_filter_title, "split_type": excel_split_type},
            },
        },
    )


# ─── KMS Token：从 UAgent 平台换取 ──────────────────────────────────────────

def get_kms_token(client: UAgentClient) -> Tuple[str, str]:
    """
    返回 (km_token, km_domain)。
    km_token 用于所有 knowledgeservice 请求的 Authorization 头。
    """
    resp = client.get("/api/backend/sys/kcs/loginToken")
    data = resp.get("data", {})
    return data["token"], data["domain"]


# ─── KMS 操作（域名由平台换取，不在代码中固定）──────────────────────────────

def _kms_session(km_token: str) -> requests.Session:
    sess = requests.Session()
    sess.headers.update({
        "Authorization": "Bearer %s" % km_token,
        "Content-Type": "application/json",
    })
    sess.trust_env = False
    return sess


def get_oss_credentials(km_domain: str, km_token: str, kb_id: int, file_path: str) -> dict:
    """
    获取阿里云 OSS 上传凭证。
    返回包含 host、key、temporaryId、policy、signature 等字段的 dict。
    """
    filename = os.path.basename(file_path)
    sess = _kms_session(km_token)
    resp = sess.get(
        "%s/api/oss/efficiency" % km_domain,
        params={
            "dataType": "document",
            "filename": filename,
            "knowledgeBaseId": kb_id,
            "token": "Bearer %s" % km_token,
            "verify": 1,
        },
    )
    resp.raise_for_status()
    return resp.json()["data"]


def upload_to_oss(oss_creds: dict, local_path: str) -> None:
    """
    将文件上传到阿里云 OSS（STS 临时凭证）。
    优先用 oss2（禁用系统代理），失败则退回 requests 直接 PUT。
    """
    _put_via_requests(oss_creds, local_path)


def _put_via_requests(oss_creds: dict, local_path: str) -> None:
    """用 requests（trust_env=False）直接 PUT 上传到 OSS，彻底绕过系统代理。"""
    import hmac as _hmac, hashlib as _hashlib, base64 as _base64
    from datetime import datetime as _dt

    access_key_id     = oss_creds["temporaryId"]   # STS AccessKeyId
    access_key_secret = oss_creds["policy"]         # STS AccessKeySecret
    security_token    = oss_creds["signature"]      # STS SecurityToken (CAIS...)
    key               = oss_creds["key"]            # Data/companyId/uuid/filename
    host              = oss_creds["host"]           # 平台返回的 OSS host
    bucket_name       = oss_creds["bucket"]         # 平台返回的 bucket

    date_str     = _dt.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    content_type = "application/octet-stream"

    # OSS 签名字符串（含 x-oss-security-token 规范头）
    canonical_resource = "/%s/%s" % (bucket_name, key)
    string_to_sign = "\n".join([
        "PUT", "", content_type, date_str,
        "x-oss-security-token:%s" % security_token,
        canonical_resource,
    ])
    sig = _base64.b64encode(
        _hmac.new(
            access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            _hashlib.sha1,
        ).digest()
    ).decode()

    url = "%s/%s" % (host, key)
    headers = {
        "Authorization":       "OSS %s:%s" % (access_key_id, sig),
        "Date":                date_str,
        "Content-Type":        content_type,
        "x-oss-security-token": security_token,
    }

    sess = requests.Session()
    sess.trust_env = False
    with open(local_path, "rb") as f:
        resp = sess.put(url, data=f, headers=headers)
    if resp.status_code not in (200, 204):
        raise RuntimeError("OSS PUT 失败: %s %s" % (resp.status_code, resp.text[:200]))


def register_document(
    km_domain: str,
    km_token: str,
    kb_id: int,
    oss_creds: dict,
    filename: str,
    size: int,
    category_id: int = 93031,
) -> None:
    """将已上传到 OSS 的文档注册到 KMS。"""
    oss_url = "%s/%s" % (oss_creds["host"], oss_creds["key"])
    sess = _kms_session(km_token)
    resp = sess.post(
        "%s/api/sdk/knowledgeBases/%s/materialRepositorys/batchSave" % (km_domain, kb_id),
        json={
            "categoryId": category_id,
            "materials": [
                {
                    "key": oss_creds["key"],
                    "url": oss_url,
                    "name": filename,
                    "percent": 100,
                    "size": size,
                    "status": 1,
                    "uid": str(uuid.uuid4()),
                }
            ],
            "knowledgeBaseId": str(kb_id),
            "categoryIdList": [category_id],
            "langCode": "ZH-CN",
            "tags": [],
            "accessLevel": 0,
            "availableTimeType": 0,
            "doRepeatByImport": 0,
        },
    )
    resp.raise_for_status()


def search_materials(
    km_domain: str,
    km_token: str,
    kb_id: int,
    page: int = 1,
    page_size: int = 20,
) -> List[dict]:
    """列出 KMS 知识库中的文档，含 uagentSyncStatus 字段。"""
    sess = _kms_session(km_token)
    resp = sess.post(
        "%s/api/sdk/knowledgeBases/%s/materialRepositorys/search" % (km_domain, kb_id),
        json={
            "pageNum": page,
            "pageSize": page_size,
            "knowledgeBaseId": str(kb_id),
            "status": 1,
        },
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_material_id(km_domain: str, km_token: str, kb_id: int, filename: str) -> int:
    """按文件名查找 material_id（同步时需要此 ID）。"""
    materials = search_materials(km_domain, km_token, kb_id)
    for m in materials:
        if m.get("name", "").endswith(filename) or filename in m.get("name", ""):
            return m["id"]
    raise ValueError("未找到文件 %s 对应的 material，请确认上传成功" % filename)


def get_kms_material_map(km_domain: str, km_token: str, kb_id: int, page_size: int = 100) -> dict:
    """返回 KMS 知识库文档映射 {filename: {material_id, url}}，用于构建 KB 节点过滤器。"""
    materials = search_materials(km_domain, km_token, kb_id, page_size=page_size)
    return {m["name"]: {"material_id": m["id"], "url": m.get("url", "")} for m in materials}


def build_kb_filter_item(
    material_id: int,
    doc_id: int,
    filename: str,
    url: str,
    business_type: str = "KCS",
) -> dict:
    """
    构建知识库节点 aggregation_ids.list 中的单个文件过滤项。
    必须包含全部 6 个字段，缺少 id 或 file_url 会导致平台报 int 解析错误。

    Args:
        material_id: KMS material_id（从 get_material_id 或 get_kms_material_map 获取）
        doc_id:      UAgent doc_id（从 list_documents 获取，同名取最大值）
        filename:    文件名（含扩展名）
        url:         OSS 文件 URL（从 get_kms_material_map 的 url 字段获取）
    """
    return {
        "business_type": business_type,
        "external_id": material_id,
        "file_name": filename,
        "file_url": url,
        "id": doc_id,
        "name": filename,
    }


def build_kb_filter_list(
    km_domain: str,
    km_token: str,
    km_kb_id: int,
    client: "UAgentClient",
    dataset_id: int,
    file_specs: List[dict],
) -> List[dict]:
    """
    批量构建 aggregation_ids.list 过滤项。

    file_specs 格式：
        [{"filename": "手册.docx", "material_id": 20001, "doc_id": 30001}, ...]
    material_id 和 doc_id 如不提供则自动从 KMS/UAgent 查询（同名文件取最新）。

    用法示例（KB 节点过滤到特定文件）：
        items = kb_api.build_kb_filter_list(
            km_domain, km_token, km_kb_id=40001, client=client, dataset_id=10001,
            file_specs=[
                {"filename": "手册A.docx"},
                {"filename": "手册B.docx"},
            ]
        )
        agg_value = json.dumps([{"value": 10001, "label": "知识库名", "list": items}])
    """
    kms_map = get_kms_material_map(km_domain, km_token, km_kb_id)
    docs = list_documents(client, dataset_id, page_size=200)
    uagent_latest: dict = {}
    for d in docs:
        fn = d["file_name"]
        uagent_latest[fn] = max(uagent_latest.get(fn, 0), d["id"])

    result = []
    for spec in file_specs:
        fn = spec["filename"]
        kms_info = kms_map.get(fn, {})
        mid = spec.get("material_id") or kms_info.get("material_id")
        did = spec.get("doc_id") or uagent_latest.get(fn)
        if not mid or not did:
            raise ValueError("找不到 %s 的 material_id 或 doc_id，请手动指定" % fn)
        result.append(build_kb_filter_item(
            material_id=mid,
            doc_id=did,
            filename=fn,
            url=kms_info.get("url", ""),
        ))
    return result


def delete_document_segments(client: "UAgentClient", dataset_id: int, doc_id: int) -> int:
    """
    删除某文档的所有分片（用于清理旧版本文档内容）。
    注意：UAgent 无文档级删除接口，此函数通过分片逐个删除达到清空效果。
    返回实际删除的分片数量。
    """
    segs = list_segments(client, dataset_id, doc_id)
    count = 0
    for s in segs:
        try:
            delete_segment(client, dataset_id, doc_id, s["id"])
            count += 1
        except Exception:
            pass
    return count


def sync_to_agent(km_domain: str, km_token: str, kb_id: int, material_ids: List[int]) -> None:
    """将指定文档同步到 UAgent 平台。material_ids 可批量传入。"""
    sess = _kms_session(km_token)
    resp = sess.post(
        "%s/api/sdk/knowledge/%s/agent/sync/material" % (km_domain, kb_id),
        json=material_ids,
    )
    resp.raise_for_status()


def wait_sync_done(
    km_domain: str,
    km_token: str,
    kb_id: int,
    material_id: int,
    timeout: int = 180,
    interval: int = 5,
    auto_retry: bool = True,
) -> None:
    """
    轮询等待 material 同步完成。
    uagentSyncStatus: 0=未同步, 1=成功, 100=平台正在重试中（不等于永久失败）

    平台行为：同步失败后平台会自动重试，期间 status 保持 100，
    最终可能变为 1（成功）。因此 100 不立即报错，继续等待。
    仅在 timeout 耗尽后仍为 100 时才重发一次同步请求。
    """
    deadline = time.time() + timeout
    last_status = 0
    while time.time() < deadline:
        materials = search_materials(km_domain, km_token, kb_id)
        for m in materials:
            if m["id"] == material_id:
                last_status = m.get("uagentSyncStatus", 0)
                if last_status == 1:
                    return
                break
        time.sleep(interval)

    # 超时后仍未成功，且 auto_retry 时重发一次
    if auto_retry and last_status == 100:
        sync_to_agent(km_domain, km_token, kb_id, [material_id])
        # 再等一轮
        extra = time.time() + 60
        while time.time() < extra:
            materials = search_materials(km_domain, km_token, kb_id)
            for m in materials:
                if m["id"] == material_id:
                    if m.get("uagentSyncStatus") == 1:
                        return
                    break
            time.sleep(interval)

    raise TimeoutError(
        "同步超时，material_id=%s 最终状态=%s" % (material_id, last_status)
    )
