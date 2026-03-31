const BASE = "/api/v1"

export async function scanProject(
  path: string,
  llm = false,
  saveHistory = false
): Promise<import("./types").ScanResult> {
  const res = await fetch(`${BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, llm, save_history: saveHistory }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || "스캔 실패")
  }
  return res.json()
}

export async function getHistory(
  path: string,
  limit = 20
): Promise<{
  project_path: string
  records: import("./types").HistoryRecord[]
  trend: number[]
}> {
  const res = await fetch(
    `${BASE}/history?path=${encodeURIComponent(path)}&limit=${limit}`
  )
  if (!res.ok) throw new Error("이력 조회 실패")
  return res.json()
}

export async function compareProjects(paths: string[]): Promise<{
  projects: import("./types").CompareItem[]
  best_project: string
  worst_project: string
}> {
  const qs = paths.map((p) => `paths=${encodeURIComponent(p)}`).join("&")
  const res = await fetch(`${BASE}/compare?${qs}`)
  if (!res.ok) throw new Error("비교 조회 실패")
  return res.json()
}

export async function generateAgentsMd(
  path: string,
  projectName = ""
): Promise<{
  content: string
  sections: string[]
  estimated_lines: number
}> {
  const res = await fetch(`${BASE}/generate-agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, project_name: projectName }),
  })
  if (!res.ok) throw new Error("AGENTS.md 생성 실패")
  return res.json()
}
